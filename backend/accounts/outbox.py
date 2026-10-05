import hmac
import logging
import uuid
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.emails import send_templated_email
from accounts.models import AuthEmailOutbox, EmailVerificationToken, Invitation, User
from accounts.security import (
    credential_state_fingerprint,
    derived_token_secret,
    digest_matches,
    identifier_digest,
)

logger = logging.getLogger(__name__)


class PermanentOutboxFailure(Exception):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


def _invitation_url(token: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/register?invite={quote(token, safe='')}"


def _verification_url(token: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/verify-email?token={quote(token, safe='')}"


def _reset_url(uid: str, token: str) -> str:
    return (
        f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password"
        f"?uid={quote(uid, safe='')}&token={quote(token, safe='')}"
    )


def enqueue_invitation_email(invitation: Invitation) -> AuthEmailOutbox:
    return AuthEmailOutbox.objects.create(
        kind=AuthEmailOutbox.Kind.INVITATION,
        deduplication_key=f"invitation:{invitation.pk}",
        recipient=invitation.email,
        recipient_digest=identifier_digest("outbox_recipient", invitation.email),
        invitation=invitation,
    )


def enqueue_verification_email(verification: EmailVerificationToken) -> AuthEmailOutbox:
    return AuthEmailOutbox.objects.create(
        kind=AuthEmailOutbox.Kind.VERIFICATION,
        deduplication_key=f"verification:{verification.pk}",
        recipient=verification.user.email,
        recipient_digest=identifier_digest("outbox_recipient", verification.user.email),
        verification=verification,
        user=verification.user,
    )


def enqueue_password_reset_email(*, canonical_email: str, user: User | None) -> AuthEmailOutbox:
    job_id = uuid.uuid4()
    deliverable_user = (
        user if user is not None and user.is_active and user.has_usable_password() else None
    )
    return AuthEmailOutbox.objects.create(
        id=job_id,
        kind=AuthEmailOutbox.Kind.PASSWORD_RESET,
        deduplication_key=f"password-reset:{job_id}",
        recipient=deliverable_user.email if deliverable_user is not None else "",
        recipient_digest=identifier_digest("password_reset_email", canonical_email),
        credential_state_digest=(
            credential_state_fingerprint(deliverable_user) if deliverable_user is not None else ""
        ),
        user=deliverable_user,
    )


def _mark_terminal(job: AuthEmailOutbox, *, error_code: str = "") -> None:
    now = timezone.now()
    AuthEmailOutbox.objects.filter(pk=job.pk, sent_at__isnull=True, failed_at__isnull=True).update(
        sent_at=now if not error_code else None,
        failed_at=now if error_code else None,
        locked_at=None,
        last_error_code=error_code,
    )


def _retry(job: AuthEmailOutbox) -> None:
    now = timezone.now()
    if job.attempts >= settings.AUTH_EMAIL_OUTBOX_MAX_ATTEMPTS:
        AuthEmailOutbox.objects.filter(pk=job.pk).update(
            failed_at=now,
            locked_at=None,
            last_error_code="delivery_failed",
        )
        return
    delay_seconds = settings.AUTH_EMAIL_OUTBOX_RETRY_BASE_SECONDS * (2 ** (job.attempts - 1))
    AuthEmailOutbox.objects.filter(pk=job.pk).update(
        available_at=now + timedelta(seconds=delay_seconds),
        locked_at=None,
        last_error_code="delivery_failed",
    )


def _deliver_invitation(job: AuthEmailOutbox) -> bool | None:
    invitation = job.invitation
    now = timezone.now()
    if (
        invitation is None
        or invitation.revoked_at is not None
        or invitation.accepted_at is not None
        or invitation.expires_at <= now
    ):
        return None
    secret = derived_token_secret("invitation", invitation.id)
    if not digest_matches(secret, invitation.secret_digest):
        raise PermanentOutboxFailure("token_derivation_mismatch")
    token = f"{invitation.id}.{secret}"
    delivered = send_templated_email(
        template_name="invitation",
        subject="Your AMF pilot invitation",
        recipient=invitation.email,
        context={"registration_url": _invitation_url(token), "expires_at": invitation.expires_at},
    )
    if delivered:
        Invitation.objects.filter(pk=invitation.pk, sent_at__isnull=True).update(
            sent_at=timezone.now()
        )
    return delivered


def _deliver_verification(job: AuthEmailOutbox) -> bool | None:
    verification = job.verification
    now = timezone.now()
    if (
        verification is None
        or verification.revoked_at is not None
        or verification.consumed_at is not None
        or verification.expires_at <= now
        or verification.user.email_verified
    ):
        return None
    secret = derived_token_secret("verification", verification.id)
    if not digest_matches(secret, verification.secret_digest):
        raise PermanentOutboxFailure("token_derivation_mismatch")
    token = f"{verification.id}.{secret}"
    return send_templated_email(
        template_name="verification",
        subject="Verify your AMF email",
        recipient=verification.user.email,
        context={
            "verification_url": _verification_url(token),
            "expires_at": verification.expires_at,
        },
    )


def _deliver_password_reset(job: AuthEmailOutbox) -> bool | None:
    user = job.user
    if user is None:
        return None
    current_fingerprint = credential_state_fingerprint(user)
    if not hmac.compare_digest(current_fingerprint, job.credential_state_digest):
        raise PermanentOutboxFailure("credential_state_changed")
    if not user.is_active or not user.has_usable_password():
        return None
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return send_templated_email(
        template_name="password_reset",
        subject="Reset your AMF password",
        recipient=user.email,
        context={"reset_url": _reset_url(uid, token)},
    )


def _deliver_job(job_id: uuid.UUID) -> None:
    job = (
        AuthEmailOutbox.objects.select_related("invitation", "verification__user", "user")
        .filter(pk=job_id)
        .first()
    )
    if job is None or job.sent_at is not None or job.failed_at is not None:
        return
    try:
        if job.kind == AuthEmailOutbox.Kind.INVITATION:
            delivered = _deliver_invitation(job)
        elif job.kind == AuthEmailOutbox.Kind.VERIFICATION:
            delivered = _deliver_verification(job)
        else:
            delivered = _deliver_password_reset(job)
    except PermanentOutboxFailure as exc:
        _mark_terminal(job, error_code=exc.error_code)
        logger.warning(
            "Authentication email job requires reissuance",
            extra={
                "outbox_id": str(job.id),
                "email_kind": job.kind,
                "error_code": exc.error_code,
            },
        )
        return
    if delivered is None:
        _mark_terminal(job)
    elif delivered:
        _mark_terminal(job)
    else:
        _retry(job)
        logger.warning(
            "Authentication email delivery deferred",
            extra={"outbox_id": str(job.id), "email_kind": job.kind},
        )


def process_auth_email_outbox(*, limit: int = 25) -> int:
    now = timezone.now()
    stale_before = now - timedelta(seconds=settings.AUTH_EMAIL_OUTBOX_LOCK_TIMEOUT_SECONDS)
    with transaction.atomic():
        jobs = list(
            AuthEmailOutbox.objects.select_for_update(skip_locked=True)
            .filter(
                sent_at__isnull=True,
                failed_at__isnull=True,
                available_at__lte=now,
            )
            .filter(Q(locked_at__isnull=True) | Q(locked_at__lte=stale_before))
            .order_by("created_at")[:limit]
        )
        for job in jobs:
            job.locked_at = now
            job.attempts += 1
            job.save(update_fields=("locked_at", "attempts"))
    for job in jobs:
        _deliver_job(job.id)
    return len(jobs)
