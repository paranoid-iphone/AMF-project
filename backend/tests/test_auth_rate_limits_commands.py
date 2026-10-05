from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuthRateLimitBucket, Invitation, User
from accounts.outbox import process_auth_email_outbox
from accounts.security import identifier_digest
from accounts.services import issue_invitation


@pytest.mark.django_db
@override_settings(AUTH_LOGIN_IP_LIMIT=1, AUTH_LOGIN_ACCOUNT_LIMIT=100)
def test_api_rate_limit_returns_stable_error_and_retry_after(api_client: APIClient) -> None:
    payload = {"email": "unknown@example.com", "password": "wrong"}
    first = api_client.post("/api/auth/login/", payload, format="json")
    second = api_client.post("/api/auth/login/", payload, format="json")

    assert first.status_code == 400
    assert second.status_code == 429
    assert second.json() == {"error": {"code": "rate_limited", "message": "Too many requests."}}
    assert 1 <= int(second["Retry-After"]) <= 900
    bucket = AuthRateLimitBucket.objects.get(scope="login_ip")
    assert bucket.identifier_digest == identifier_digest("login_ip", "127.0.0.1")
    assert "127.0.0.1" not in bucket.identifier_digest


@pytest.mark.django_db
def test_cleanup_auth_buckets_is_idempotent() -> None:
    AuthRateLimitBucket.objects.create(
        scope="expired",
        identifier_digest="a" * 64,
        window_start=timezone.now() - timedelta(hours=2),
        count=1,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    output = StringIO()

    call_command("cleanup_auth_buckets", stdout=output)
    call_command("cleanup_auth_buckets", stdout=output)

    assert not AuthRateLimitBucket.objects.exists()
    assert "Deleted 1" in output.getvalue()
    assert "Deleted 0" in output.getvalue()


@pytest.mark.django_db(transaction=True)
def test_invitation_management_commands_do_not_print_raw_token() -> None:
    output = StringIO()
    call_command("invite_applicant", "command@example.com", stdout=output)

    invitation = Invitation.objects.get(email="command@example.com")
    assert str(invitation.id) in output.getvalue()
    assert invitation.secret_digest not in output.getvalue()
    assert len(mail.outbox) == 0
    process_auth_email_outbox()
    assert len(mail.outbox) == 1

    call_command("revoke_invitation", str(invitation.id), stdout=output)
    invitation.refresh_from_db()
    assert invitation.revoked_at is not None


@pytest.mark.django_db
def test_invitation_admin_is_superuser_only(api_client: APIClient) -> None:
    staff = User.objects.create_user(
        email="staff@example.com", password="test-password", is_staff=True
    )
    api_client.force_login(staff)
    denied = api_client.get("/admin/accounts/invitation/")
    assert denied.status_code == 403

    superuser = User.objects.create_superuser(email="super@example.com", password="test-password")
    api_client.force_login(superuser)
    allowed = api_client.get("/admin/accounts/invitation/invite/")
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_revoking_accepted_invitation_is_rejected() -> None:
    issued = issue_invitation(email="accepted@example.com", actor=None, request_id="invite")
    user = User.objects.create_user(email="accepted@example.com", password="test-password")
    Invitation.objects.filter(pk=issued.invitation.pk).update(
        accepted_at=timezone.now(), accepted_by=user
    )
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("revoke_invitation", str(issued.invitation.id), stdout=output)
