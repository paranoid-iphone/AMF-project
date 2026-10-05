from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.exceptions import (
    EmailVerificationRequiredError,
    InvalidInvitationError,
    InvalidTokenError,
)
from accounts.guards import require_verified_email
from accounts.models import (
    AccountSecurityEvent,
    AuthEmailOutbox,
    EmailVerificationToken,
    Invitation,
    User,
)
from accounts.outbox import process_auth_email_outbox
from accounts.security import secret_digest
from accounts.services import (
    confirm_email_verification,
    issue_invitation,
    issue_verification_token,
    register_applicant,
    revoke_invitation,
)


@pytest.mark.django_db(transaction=True)
def test_invitation_issue_replaces_pending_and_sends_mail_without_storing_secret() -> None:
    first = issue_invitation(email=" Applicant@Example.COM ", actor=None, request_id="req-1")
    second = issue_invitation(email="applicant@example.com", actor=None, request_id="req-2")

    assert len(mail.outbox) == 0
    assert AuthEmailOutbox.objects.count() == 2
    process_auth_email_outbox()
    first.invitation.refresh_from_db()
    second.invitation.refresh_from_db()
    raw_secret = second.token.split(".", 1)[1]
    assert first.invitation.state == "revoked"
    assert second.invitation.state == "pending"
    assert second.invitation.email == "applicant@example.com"
    assert second.invitation.secret_digest == secret_digest(raw_secret)
    assert raw_secret not in second.invitation.secret_digest
    assert second.invitation.sent_at is not None
    assert len(mail.outbox) == 1
    assert second.token in mail.outbox[-1].body
    assert (
        AccountSecurityEvent.objects.filter(
            code=AccountSecurityEvent.Code.INVITATION_ISSUED
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_revoke_invitation_is_idempotent() -> None:
    issued = issue_invitation(email="a@example.com", actor=None, request_id="req")

    assert revoke_invitation(selector=issued.invitation.id, actor=None, request_id="req") is True
    assert revoke_invitation(selector=issued.invitation.id, actor=None, request_id="req") is True
    assert (
        AccountSecurityEvent.objects.filter(
            code=AccountSecurityEvent.Code.INVITATION_REVOKED
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_registration_accepts_invitation_atomically_without_privileges() -> None:
    issued = issue_invitation(email="applicant@example.com", actor=None, request_id="invite")

    user = register_applicant(
        invitation_token=issued.token,
        email="Applicant@Example.COM",
        password="A-long-unique-password-42!",
        request_id="register",
        ip_address="192.0.2.1",
    )

    issued.invitation.refresh_from_db()
    assert user.email == "applicant@example.com"
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.email_verified is False
    assert issued.invitation.accepted_by == user
    assert EmailVerificationToken.objects.filter(user=user, revoked_at__isnull=True).count() == 1
    assert AccountSecurityEvent.objects.filter(target=user).count() == 2


@pytest.mark.django_db
def test_all_invitation_failures_use_same_service_error() -> None:
    issued = issue_invitation(email="expected@example.com", actor=None, request_id="invite")
    cases = [
        ("invalid", "expected@example.com"),
        (issued.token, "other@example.com"),
    ]
    issued.invitation.expires_at = timezone.now() - timedelta(seconds=1)
    issued.invitation.save(update_fields=("expires_at",))
    cases.append((issued.token, "expected@example.com"))

    for token, email in cases:
        with pytest.raises(InvalidInvitationError):
            register_applicant(
                invitation_token=token,
                email=email,
                password="A-long-unique-password-42!",
                request_id="register",
            )


@pytest.mark.django_db
def test_verification_replacement_revokes_old_and_token_cannot_replay() -> None:
    user = User.objects.create_user(email="verify@example.com", password="test-password")
    first = issue_verification_token(user)
    second = issue_verification_token(user)
    assert first is not None and second is not None
    first.verification.refresh_from_db()
    assert first.verification.revoked_at is not None

    with pytest.raises(InvalidTokenError):
        confirm_email_verification(token=first.token, request_id="confirm")
    confirmed = confirm_email_verification(token=second.token, request_id="confirm")
    assert confirmed.email_verified is True
    with pytest.raises(InvalidTokenError):
        confirm_email_verification(token=second.token, request_id="confirm-again")


@pytest.mark.django_db
def test_verified_user_does_not_get_new_verification_token() -> None:
    user = User.objects.create_user(email="verified@example.com", password="test-password")
    user.email_verified_at = timezone.now()
    user.save(update_fields=("email_verified_at",))

    assert issue_verification_token(user) is None
    assert EmailVerificationToken.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_verified_email_guard() -> None:
    user = User.objects.create_user(email="guard@example.com", password="test-password")
    with pytest.raises(EmailVerificationRequiredError):
        require_verified_email(user)

    user.email_verified_at = timezone.now()
    require_verified_email(user)


@pytest.mark.django_db
def test_database_prevents_invitation_accepted_and_revoked_state() -> None:
    user = User.objects.create_user(email="constraint@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        Invitation.objects.create(
            email=user.email,
            secret_digest="a" * 64,
            expires_at=timezone.now() + timedelta(days=1),
            revoked_at=timezone.now(),
            accepted_at=timezone.now(),
            accepted_by=user,
        )


@pytest.mark.django_db
def test_expired_verification_token_is_rejected() -> None:
    user = User.objects.create_user(email="expired-verify@example.com", password="test-password")
    issued = issue_verification_token(user)
    assert issued is not None
    EmailVerificationToken.objects.filter(pk=issued.verification.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    with pytest.raises(InvalidTokenError):
        confirm_email_verification(token=issued.token, request_id="expired")


@pytest.mark.django_db(transaction=True)
def test_email_delivery_failure_does_not_rollback_committed_registration() -> None:
    issued = issue_invitation(email="delivery-failure@example.com", actor=None, request_id="invite")
    user = register_applicant(
        invitation_token=issued.token,
        email="delivery-failure@example.com",
        password="A-long-unique-password-42!",
        request_id="register",
    )
    with patch("accounts.outbox.send_templated_email", return_value=False):
        process_auth_email_outbox()

    issued.invitation.refresh_from_db()
    assert User.objects.filter(pk=user.pk).exists()
    assert issued.invitation.accepted_by_id == user.pk
    assert EmailVerificationToken.objects.filter(user=user).exists()
    assert AuthEmailOutbox.objects.filter(sent_at__isnull=True, failed_at__isnull=True).exists()


@pytest.mark.django_db
def test_invitation_expiry_is_recomputed_after_authoritative_lock() -> None:
    issued = issue_invitation(email="lock-time@example.com", actor=None, request_id="invite")
    base = timezone.now()
    Invitation.objects.filter(pk=issued.invitation.pk).update(
        expires_at=base + timedelta(seconds=1)
    )

    with (
        patch("accounts.services.timezone.now", side_effect=[base, base + timedelta(seconds=2)]),
        pytest.raises(InvalidInvitationError),
    ):
        register_applicant(
            invitation_token=issued.token,
            email="lock-time@example.com",
            password="A-long-unique-password-42!",
            request_id="register",
        )

    issued.invitation.refresh_from_db()
    assert issued.invitation.accepted_at is None


@pytest.mark.django_db
def test_verification_expiry_is_checked_after_user_and_token_locks() -> None:
    user = User.objects.create_user(email="verify-lock-time@example.com", password="test-password")
    issued = issue_verification_token(user)
    assert issued is not None
    expiry = timezone.now() + timedelta(seconds=1)
    EmailVerificationToken.objects.filter(pk=issued.verification.pk).update(expires_at=expiry)

    with (
        patch("accounts.services.timezone.now", return_value=expiry + timedelta(seconds=1)),
        pytest.raises(InvalidTokenError),
    ):
        confirm_email_verification(token=issued.token, request_id="expired-after-lock")

    issued.verification.refresh_from_db()
    assert issued.verification.consumed_at is None
