from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.management import call_command
from django.db import close_old_connections
from django.db.models.deletion import ProtectedError
from django.test import override_settings
from django.utils import timezone

from accounts.models import (
    AccountSecurityEvent,
    AuthEmailOutbox,
    User,
)
from accounts.outbox import process_auth_email_outbox
from accounts.services import issue_invitation, request_password_reset


@pytest.mark.django_db(transaction=True)
def test_outbox_delivery_is_idempotent() -> None:
    issued = issue_invitation(email="outbox@example.com", actor=None, request_id="outbox")

    assert len(mail.outbox) == 0
    assert process_auth_email_outbox() == 1
    assert process_auth_email_outbox() == 0

    assert len(mail.outbox) == 1
    assert issued.token in mail.outbox[0].body
    job = AuthEmailOutbox.objects.get()
    assert job.sent_at is not None
    assert job.attempts == 1


@pytest.mark.django_db(transaction=True)
@override_settings(AUTH_EMAIL_OUTBOX_MAX_ATTEMPTS=2, AUTH_EMAIL_OUTBOX_RETRY_BASE_SECONDS=0)
def test_outbox_retries_then_marks_terminal_without_logging_secret(caplog) -> None:  # type: ignore[no-untyped-def]
    issued = issue_invitation(email="retry@example.com", actor=None, request_id="retry")

    with patch("accounts.outbox.send_templated_email", return_value=False):
        assert process_auth_email_outbox() == 1
        assert process_auth_email_outbox() == 1

    job = AuthEmailOutbox.objects.get()
    assert job.attempts == 2
    assert job.failed_at is not None
    assert job.last_error_code == "delivery_failed"
    assert issued.token not in caplog.text
    assert issued.invitation.secret_digest not in caplog.text


@pytest.mark.django_db
def test_reset_requests_enqueue_comparable_jobs_without_synchronous_delivery() -> None:
    active = User.objects.create_user(email="known@example.com", password="test-password")
    User.objects.create_user(
        email="inactive@example.com", password="test-password", is_active=False
    )

    with patch("accounts.outbox.send_templated_email") as sender:
        request_password_reset(active.email)
        request_password_reset("unknown@example.com")
        request_password_reset("inactive@example.com")

    assert sender.call_count == 0
    jobs = list(AuthEmailOutbox.objects.order_by("created_at"))
    assert len(jobs) == 3
    assert [job.kind for job in jobs] == ["password_reset"] * 3
    assert [job.user_id is not None for job in jobs] == [True, False, False]
    assert all(job.recipient_digest for job in jobs)
    assert jobs[1].recipient == jobs[2].recipient == ""


@pytest.mark.django_db
def test_account_security_event_is_append_only_across_all_write_paths() -> None:
    event = AccountSecurityEvent.objects.create(
        code=AccountSecurityEvent.Code.EMAIL_VERIFIED,
        request_correlation_id="test",
    )
    event.code = AccountSecurityEvent.Code.PASSWORD_RESET_COMPLETED

    with pytest.raises(TypeError, match="append-only"):
        event.save()
    with pytest.raises(TypeError, match="append-only"):
        event.delete()
    with pytest.raises(TypeError, match="append-only"):
        AccountSecurityEvent.objects.filter(pk=event.pk).update(code="changed")
    with pytest.raises(TypeError, match="append-only"):
        AccountSecurityEvent.objects.filter(pk=event.pk).delete()

    event.refresh_from_db()
    assert event.code == AccountSecurityEvent.Code.EMAIL_VERIFIED


@pytest.mark.django_db
def test_accepted_invitation_protects_retained_user_identity() -> None:
    issued = issue_invitation(email="retained@example.com", actor=None, request_id="invite")
    user = User.objects.create_user(email="retained@example.com", password="test-password")
    invitation = issued.invitation
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(update_fields=("accepted_at", "accepted_by"))

    with pytest.raises(ProtectedError):
        user.delete()


@pytest.mark.django_db
def test_append_only_manager_still_allows_event_creation_with_nullable_actor() -> None:
    event = AccountSecurityEvent.objects.create(
        code=AccountSecurityEvent.Code.INVITATION_ISSUED,
        actor=None,
        target=None,
        request_correlation_id="management-command",
    )

    assert event.actor is None
    assert event.target is None
    assert not isinstance(event.actor, AnonymousUser)


@pytest.mark.django_db(transaction=True)
def test_concurrent_outbox_workers_claim_a_job_once() -> None:
    issue_invitation(email="worker-race@example.com", actor=None, request_id="worker-race")
    barrier = Barrier(2)

    def process(_: int) -> int:
        close_old_connections()
        barrier.wait()
        try:
            return process_auth_email_outbox(limit=1)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        processed = list(pool.map(process, range(2)))

    assert sum(processed) == 1
    assert len(mail.outbox) == 1
    job = AuthEmailOutbox.objects.get()
    assert job.sent_at is not None
    assert job.attempts == 1


@pytest.mark.django_db
def test_security_event_protects_associated_user_identity() -> None:
    user = User.objects.create_user(email="event-retention@example.com", password="test-password")
    event = AccountSecurityEvent.objects.create(
        code=AccountSecurityEvent.Code.PASSWORD_RESET_COMPLETED,
        actor=user,
        target=user,
        request_correlation_id="retention",
    )

    with pytest.raises(ProtectedError):
        user.delete()

    event.refresh_from_db()
    assert event.actor == user
    assert event.target == user


@pytest.mark.django_db(transaction=True)
def test_reset_delivery_is_suppressed_after_password_state_changes() -> None:
    user = User.objects.create_user(email="state-change@example.com", password="old-password-42!")
    request_password_reset(user.email)
    job = AuthEmailOutbox.objects.get(kind="password_reset")
    original_fingerprint = job.credential_state_digest

    assert len(original_fingerprint) == 64
    assert original_fingerprint != user.password
    assert user.password not in original_fingerprint

    user.set_password("new-password-84!")
    user.save(update_fields=("password",))
    process_auth_email_outbox()

    job.refresh_from_db()
    assert len(mail.outbox) == 0
    assert job.sent_at is None
    assert job.failed_at is not None
    assert job.last_error_code == "credential_state_changed"


@pytest.mark.django_db(transaction=True)
def test_reset_delivery_is_suppressed_after_account_is_deactivated() -> None:
    user = User.objects.create_user(email="deactivated@example.com", password="old-password-42!")
    request_password_reset(user.email)
    user.is_active = False
    user.save(update_fields=("is_active",))

    process_auth_email_outbox()

    job = AuthEmailOutbox.objects.get(kind="password_reset")
    assert len(mail.outbox) == 0
    assert job.sent_at is None
    assert job.failed_at is not None
    assert job.last_error_code == "credential_state_changed"


@pytest.mark.django_db(transaction=True)
def test_invitation_key_rotation_mismatch_is_failed_and_reissuable() -> None:
    first = issue_invitation(email="rotated-invite@example.com", actor=None, request_id="first")
    with patch("accounts.outbox.derived_token_secret", return_value="rotated-secret"):
        process_auth_email_outbox()

    first_job = AuthEmailOutbox.objects.get(invitation=first.invitation)
    assert first_job.sent_at is None
    assert first_job.failed_at is not None
    assert first_job.last_error_code == "token_derivation_mismatch"
    assert len(mail.outbox) == 0

    second = issue_invitation(email="rotated-invite@example.com", actor=None, request_id="second")
    process_auth_email_outbox()

    second_job = AuthEmailOutbox.objects.get(invitation=second.invitation)
    assert second_job.sent_at is not None
    assert len(mail.outbox) == 1
    assert second.token in mail.outbox[0].body


@pytest.mark.django_db(transaction=True)
def test_verification_key_rotation_mismatch_is_failed_and_reissuable() -> None:
    from accounts.services import issue_verification_token

    user = User.objects.create_user(email="rotated-verify@example.com", password="test-password")
    first = issue_verification_token(user)
    assert first is not None
    with patch("accounts.outbox.derived_token_secret", return_value="rotated-secret"):
        process_auth_email_outbox()

    first_job = AuthEmailOutbox.objects.get(verification=first.verification)
    assert first_job.sent_at is None
    assert first_job.failed_at is not None
    assert first_job.last_error_code == "token_derivation_mismatch"

    second = issue_verification_token(user)
    assert second is not None
    process_auth_email_outbox()
    assert len(mail.outbox) == 1
    assert second.token in mail.outbox[0].body


@pytest.mark.django_db(transaction=True)
@override_settings(AUTH_EMAIL_OUTBOX_LOCK_TIMEOUT_SECONDS=60)
def test_stale_outbox_lease_is_reclaimed_without_normal_duplicate() -> None:
    issue_invitation(email="stale-lease@example.com", actor=None, request_id="stale")
    stale_at = timezone.now() - timedelta(seconds=61)
    AuthEmailOutbox.objects.update(locked_at=stale_at, attempts=1)

    assert process_auth_email_outbox() == 1
    assert process_auth_email_outbox() == 0

    job = AuthEmailOutbox.objects.get()
    assert job.attempts == 2
    assert job.sent_at is not None
    assert len(mail.outbox) == 1


@pytest.mark.django_db(transaction=True)
def test_cleanup_auth_email_outbox_removes_only_expired_terminal_rows() -> None:
    request_password_reset("unknown-cleanup@example.com")
    process_auth_email_outbox()
    unknown_job = AuthEmailOutbox.objects.get(kind="password_reset")

    failed = issue_invitation(email="failed-cleanup@example.com", actor=None, request_id="failed")
    with patch("accounts.outbox.derived_token_secret", return_value="rotated-secret"):
        process_auth_email_outbox()
    failed_job = AuthEmailOutbox.objects.get(invitation=failed.invitation)

    pending = issue_invitation(
        email="pending-cleanup@example.com", actor=None, request_id="pending"
    )
    old = timezone.now() - timedelta(days=31)
    AuthEmailOutbox.objects.filter(pk=unknown_job.pk).update(sent_at=old)
    AuthEmailOutbox.objects.filter(pk=failed_job.pk).update(failed_at=old)
    output = StringIO()

    call_command("cleanup_auth_email_outbox", "--retention-seconds", "2592000", stdout=output)
    call_command("cleanup_auth_email_outbox", "--retention-seconds", "2592000", stdout=output)

    assert not AuthEmailOutbox.objects.filter(pk__in=(unknown_job.pk, failed_job.pk)).exists()
    assert AuthEmailOutbox.objects.filter(invitation=pending.invitation).exists()
    assert "Deleted 2" in output.getvalue()
    assert "Deleted 0" in output.getvalue()
