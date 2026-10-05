import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode

from accounts.exceptions import InvalidInvitationError, InvalidTokenError
from accounts.managers import canonicalize_email
from accounts.models import (
    AccountSecurityEvent,
    EmailVerificationToken,
    Invitation,
    InvitationEmailLock,
    User,
)
from accounts.outbox import (
    enqueue_invitation_email,
    enqueue_password_reset_email,
    enqueue_verification_email,
)
from accounts.security import (
    client_ip_digest,
    derived_token_secret,
    digest_matches,
    parse_selector_token,
    secret_digest,
)


@dataclass(frozen=True)
class IssuedInvitation:
    invitation: Invitation
    token: str


@dataclass(frozen=True)
class IssuedVerification:
    verification: EmailVerificationToken
    token: str


def _event(
    *,
    code: str,
    request_id: str,
    ip_address: str | None,
    actor: User | None = None,
    target: User | None = None,
    invitation_id: uuid.UUID | None = None,
) -> None:
    AccountSecurityEvent.objects.create(
        code=code,
        actor=actor,
        target=target,
        invitation_id=invitation_id,
        request_correlation_id=request_id,
        client_ip_digest=client_ip_digest(ip_address),
    )


def _lock_invitation_email(canonical_email: str) -> InvitationEmailLock:
    try:
        with transaction.atomic():
            InvitationEmailLock.objects.create(email=canonical_email)
    except IntegrityError:
        pass
    return InvitationEmailLock.objects.select_for_update().get(pk=canonical_email)


def issue_invitation(
    *,
    email: str,
    actor: User | None,
    request_id: str,
    ip_address: str | None = None,
) -> IssuedInvitation:
    canonical_email = canonicalize_email(email)
    if not canonical_email:
        raise ValueError("Email is required")
    selector = uuid.uuid4()
    secret = derived_token_secret("invitation", selector)
    with transaction.atomic():
        _lock_invitation_email(canonical_email)
        now = timezone.now()
        previous_pending = list(
            Invitation.objects.select_for_update().filter(
                email=canonical_email,
                revoked_at__isnull=True,
                accepted_at__isnull=True,
            )
        )
        if previous_pending:
            Invitation.objects.filter(pk__in=[item.pk for item in previous_pending]).update(
                revoked_at=now
            )
            for previous in previous_pending:
                _event(
                    code=AccountSecurityEvent.Code.INVITATION_REVOKED,
                    actor=actor,
                    invitation_id=previous.id,
                    request_id=request_id,
                    ip_address=ip_address,
                )
        invitation = Invitation.objects.create(
            id=selector,
            email=canonical_email,
            secret_digest=secret_digest(secret),
            created_by=actor,
            expires_at=now + timedelta(seconds=settings.AUTH_INVITATION_TTL_SECONDS),
        )
        _event(
            code=AccountSecurityEvent.Code.INVITATION_ISSUED,
            actor=actor,
            invitation_id=invitation.id,
            request_id=request_id,
            ip_address=ip_address,
        )
        enqueue_invitation_email(invitation)
    return IssuedInvitation(invitation=invitation, token=f"{invitation.id}.{secret}")


def revoke_invitation(
    *,
    selector: uuid.UUID,
    actor: User | None,
    request_id: str,
    ip_address: str | None = None,
) -> bool:
    with transaction.atomic():
        invitation = Invitation.objects.select_for_update().filter(pk=selector).first()
        if invitation is None or invitation.accepted_at is not None:
            return False
        if invitation.revoked_at is None:
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=("revoked_at",))
            _event(
                code=AccountSecurityEvent.Code.INVITATION_REVOKED,
                actor=actor,
                invitation_id=invitation.id,
                request_id=request_id,
                ip_address=ip_address,
            )
    return True


def _create_verification_token(user: User) -> IssuedVerification:
    now = timezone.now()
    EmailVerificationToken.objects.select_for_update().filter(
        user=user,
        consumed_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now)
    selector = uuid.uuid4()
    secret = derived_token_secret("verification", selector)
    verification = EmailVerificationToken.objects.create(
        id=selector,
        user=user,
        secret_digest=secret_digest(secret),
        expires_at=now + timedelta(seconds=settings.AUTH_VERIFICATION_TTL_SECONDS),
    )
    enqueue_verification_email(verification)
    return IssuedVerification(verification=verification, token=f"{verification.id}.{secret}")


def issue_verification_token(user: User) -> IssuedVerification | None:
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.email_verified:
            return None
        return _create_verification_token(locked_user)


def register_applicant(
    *,
    invitation_token: str,
    email: str,
    password: str,
    request_id: str,
    ip_address: str | None = None,
) -> User:
    canonical_email = canonicalize_email(email)
    parsed = parse_selector_token(invitation_token)
    if parsed is None:
        raise InvalidInvitationError
    selector, secret = parsed
    preliminary_now = timezone.now()
    preliminary = Invitation.objects.filter(pk=selector).first()
    preliminary_invalid = (
        preliminary is None
        or not digest_matches(secret, preliminary.secret_digest)
        or preliminary.email != canonical_email
        or preliminary.expires_at <= preliminary_now
        or preliminary.revoked_at is not None
        or preliminary.accepted_at is not None
    )
    if preliminary_invalid or User.objects.filter(email=canonical_email).exists():
        raise InvalidInvitationError
    candidate = User(email=canonical_email, is_staff=False, is_superuser=False)
    validate_password(password, user=candidate)

    with transaction.atomic():
        invitation = Invitation.objects.select_for_update().filter(pk=selector).first()
        locked_now = timezone.now()
        invalid = (
            invitation is None
            or not digest_matches(secret, invitation.secret_digest)
            or invitation.email != canonical_email
            or invitation.expires_at <= locked_now
            or invitation.revoked_at is not None
            or invitation.accepted_at is not None
        )
        if invalid:
            raise InvalidInvitationError
        assert invitation is not None
        if User.objects.filter(email=canonical_email).exists():
            raise InvalidInvitationError
        try:
            with transaction.atomic():
                user = User.objects.create_user(email=canonical_email, password=password)
        except IntegrityError as exc:
            raise InvalidInvitationError from exc
        invitation.accepted_at = locked_now
        invitation.accepted_by = user
        invitation.save(update_fields=("accepted_at", "accepted_by"))
        _event(
            code=AccountSecurityEvent.Code.INVITATION_ACCEPTED,
            target=user,
            invitation_id=invitation.id,
            request_id=request_id,
            ip_address=ip_address,
        )
        _event(
            code=AccountSecurityEvent.Code.APPLICANT_REGISTERED,
            target=user,
            invitation_id=invitation.id,
            request_id=request_id,
            ip_address=ip_address,
        )
        _create_verification_token(user)
    return user


def confirm_email_verification(
    *, token: str, request_id: str, ip_address: str | None = None
) -> User:
    parsed = parse_selector_token(token)
    if parsed is None:
        raise InvalidTokenError
    selector, secret = parsed
    preliminary = EmailVerificationToken.objects.filter(pk=selector).only("user_id").first()
    if preliminary is None:
        raise InvalidTokenError
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=preliminary.user_id)
        verification = (
            EmailVerificationToken.objects.select_for_update()
            .filter(pk=selector, user=user)
            .first()
        )
        locked_now = timezone.now()
        invalid = (
            verification is None
            or not digest_matches(secret, verification.secret_digest)
            or verification.expires_at <= locked_now
            or verification.consumed_at is not None
            or verification.revoked_at is not None
        )
        if invalid:
            raise InvalidTokenError
        assert verification is not None
        verification.consumed_at = locked_now
        verification.save(update_fields=("consumed_at",))
        if user.email_verified_at is None:
            user.email_verified_at = locked_now
            user.save(update_fields=("email_verified_at",))
            _event(
                code=AccountSecurityEvent.Code.EMAIL_VERIFIED,
                target=user,
                request_id=request_id,
                ip_address=ip_address,
            )
    return user


def request_password_reset(email: str) -> None:
    canonical_email = canonicalize_email(email)
    with transaction.atomic():
        user = User.objects.select_for_update().filter(email=canonical_email).first()
        enqueue_password_reset_email(canonical_email=canonical_email, user=user)


def _user_from_uid(uid: str) -> User:
    try:
        decoded = urlsafe_base64_decode(uid).decode()
        return User.objects.get(pk=decoded, is_active=True)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError, User.DoesNotExist) as exc:
        raise InvalidTokenError from exc


def confirm_password_reset(
    *,
    uid: str,
    token: str,
    new_password: str,
    request_id: str,
    ip_address: str | None = None,
) -> None:
    user = _user_from_uid(uid)
    if not default_token_generator.check_token(user, token):
        raise InvalidTokenError
    validate_password(new_password, user=user)
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if not default_token_generator.check_token(locked_user, token):
            raise InvalidTokenError
        locked_user.set_password(new_password)
        locked_user.save(update_fields=("password",))
        _event(
            code=AccountSecurityEvent.Code.PASSWORD_RESET_COMPLETED,
            target=locked_user,
            request_id=request_id,
            ip_address=ip_address,
        )
