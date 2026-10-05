from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from accounts.models import AuthEmailOutbox, EmailVerificationToken, User
from accounts.outbox import process_auth_email_outbox
from accounts.services import issue_invitation, issue_verification_token


@pytest.mark.django_db
def test_session_bootstrap_exact_contract_and_csrf_cookie(api_client: APIClient) -> None:
    anonymous = api_client.get("/api/auth/session/")
    assert anonymous.status_code == 200
    assert anonymous.json() == {"authenticated": False, "user": None}
    assert "csrftoken" in anonymous.cookies

    user = User.objects.create_user(email="session@example.com", password="test-password")
    api_client.force_login(user)
    authenticated = api_client.get("/api/auth/session/")
    assert authenticated.json() == {
        "authenticated": True,
        "user": {"id": user.id, "email": user.email, "email_verified": False},
    }


@pytest.mark.django_db
def test_unsafe_public_request_requires_csrf() -> None:
    client = APIClient(enforce_csrf_checks=True)

    response = client.post("/api/auth/login/", {"email": "a@example.com", "password": "x"})

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "csrf_failed", "message": "CSRF validation failed."}
    }


@pytest.mark.django_db
def test_registration_logs_in_and_returns_canonical_user(csrf_api_client: APIClient) -> None:
    issued = issue_invitation(email="applicant@example.com", actor=None, request_id="invite")

    response = csrf_api_client.post(
        "/api/auth/register/",
        {
            "invitation_token": issued.token,
            "email": "Applicant@Example.COM",
            "password": "A-long-unique-password-42!",
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="applicant@example.com")
    assert response.json() == {
        "user": {"id": user.id, "email": "applicant@example.com", "email_verified": False}
    }
    session = csrf_api_client.get("/api/auth/session/").json()
    assert session["authenticated"] is True


@pytest.mark.django_db
def test_registration_invitation_errors_are_enumeration_safe(api_client: APIClient) -> None:
    issued = issue_invitation(email="expected@example.com", actor=None, request_id="invite")
    responses = [
        api_client.post(
            "/api/auth/register/",
            {
                "invitation_token": "invalid",
                "email": "expected@example.com",
                "password": "A-long-unique-password-42!",
            },
            format="json",
        ),
        api_client.post(
            "/api/auth/register/",
            {
                "invitation_token": issued.token,
                "email": "wrong@example.com",
                "password": "A-long-unique-password-42!",
            },
            format="json",
        ),
    ]

    assert {response.status_code for response in responses} == {400}
    assert responses[0].json() == responses[1].json()
    assert responses[0].json()["error"]["code"] == "invalid_invitation"


@pytest.mark.django_db
def test_password_validation_uses_stable_field_errors(api_client: APIClient) -> None:
    issued = issue_invitation(email="weak@example.com", actor=None, request_id="invite")

    response = api_client.post(
        "/api/auth/register/",
        {"invitation_token": issued.token, "email": "weak@example.com", "password": "1"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["fields"]["password"]


@pytest.mark.django_db
def test_login_failure_is_identical_for_unknown_wrong_and_inactive(api_client: APIClient) -> None:
    user = User.objects.create_user(email="known@example.com", password="correct-password")
    inactive = User.objects.create_user(
        email="inactive@example.com", password="correct-password", is_active=False
    )
    payloads = [
        {"email": "unknown@example.com", "password": "correct-password"},
        {"email": user.email, "password": "wrong-password"},
        {"email": inactive.email, "password": "correct-password"},
    ]

    responses = [
        api_client.post("/api/auth/login/", payload, format="json") for payload in payloads
    ]

    assert [response.status_code for response in responses] == [400, 400, 400]
    assert responses[0].json() == responses[1].json() == responses[2].json()
    assert responses[0].json()["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_login_rotates_session_and_logout_is_idempotent(api_client: APIClient) -> None:
    User.objects.create_user(email="login@example.com", password="correct-password")
    session = api_client.session
    session["before"] = True
    session.save()
    before = session.session_key

    response = api_client.post(
        "/api/auth/login/",
        {"email": "LOGIN@example.com", "password": "correct-password"},
        format="json",
    )

    assert response.status_code == 200
    assert api_client.session.session_key != before
    assert api_client.post("/api/auth/logout/").status_code == 204
    assert api_client.post("/api/auth/logout/").status_code == 204
    assert api_client.get("/api/auth/session/").json()["authenticated"] is False


@pytest.mark.django_db
def test_verification_confirmation_does_not_switch_existing_session(api_client: APIClient) -> None:
    logged_in = User.objects.create_user(email="logged@example.com", password="test-password")
    target = User.objects.create_user(email="target@example.com", password="test-password")
    issued = issue_verification_token(target)
    assert issued is not None
    api_client.force_login(logged_in)

    response = api_client.post(
        "/api/auth/email-verification/confirm/", {"token": issued.token}, format="json"
    )

    assert response.status_code == 200
    assert response.json() == {"status": "verified"}
    assert api_client.get("/api/auth/session/").json()["user"]["id"] == logged_in.id
    target.refresh_from_db()
    assert target.email_verified is True


@pytest.mark.django_db(transaction=True)
def test_verification_resend_sends_email_and_replaces_token(api_client: APIClient) -> None:
    user = User.objects.create_user(email="resend@example.com", password="test-password")
    first = issue_verification_token(user)
    assert first is not None
    api_client.force_login(user)

    response = api_client.post("/api/auth/email-verification/request/", format="json")

    assert response.status_code == 202
    first.verification.refresh_from_db()
    assert first.verification.revoked_at is not None
    assert EmailVerificationToken.objects.filter(user=user, revoked_at__isnull=True).count() == 1
    assert len(mail.outbox) == 0
    process_auth_email_outbox()
    assert len(mail.outbox) == 1


@pytest.mark.django_db(transaction=True)
def test_password_reset_request_is_enumeration_safe_and_confirm_invalidates_session(
    api_client: APIClient,
) -> None:
    user = User.objects.create_user(email="reset@example.com", password="old-password-42!")
    api_client.force_login(user)
    known = api_client.post(
        "/api/auth/password-reset/request/", {"email": user.email}, format="json"
    )
    unknown = api_client.post(
        "/api/auth/password-reset/request/", {"email": "unknown@example.com"}, format="json"
    )
    inactive = User.objects.create_user(
        email="inactive-reset@example.com", password="old-password-42!", is_active=False
    )
    inactive_response = api_client.post(
        "/api/auth/password-reset/request/", {"email": inactive.email}, format="json"
    )
    assert known.status_code == unknown.status_code == inactive_response.status_code == 202
    assert known.json() == unknown.json() == inactive_response.json() == {"status": "accepted"}
    assert len(mail.outbox) == 0
    assert AuthEmailOutbox.objects.filter(kind="password_reset").count() == 3
    process_auth_email_outbox()
    assert len(mail.outbox) == 1

    reset_url = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
    query = parse_qs(urlparse(reset_url).query)
    confirm = APIClient().post(
        "/api/auth/password-reset/confirm/",
        {
            "uid": query["uid"][0],
            "token": query["token"][0],
            "new_password": "new-secure-password-84!",
        },
        format="json",
    )
    assert confirm.status_code == 204
    assert api_client.get("/api/auth/session/").json()["authenticated"] is False
    user.refresh_from_db()
    assert user.check_password("new-secure-password-84!")
    assert user.email_verified is False


@pytest.mark.django_db
def test_password_reset_token_replay_is_rejected(api_client: APIClient) -> None:
    user = User.objects.create_user(email="replay@example.com", password="old-password-42!")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    payload = {"uid": uid, "token": token, "new_password": "new-secure-password-84!"}

    assert (
        api_client.post("/api/auth/password-reset/confirm/", payload, format="json").status_code
        == 204
    )
    replay = api_client.post("/api/auth/password-reset/confirm/", payload, format="json")
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "invalid_or_expired_token"


def test_verified_guard_exception_has_stable_api_error() -> None:
    from accounts.api_errors import stable_exception_handler
    from accounts.exceptions import EmailVerificationRequiredError

    response = stable_exception_handler(EmailVerificationRequiredError(), {})

    assert response is not None
    assert response.status_code == 403
    assert response.data == {
        "error": {
            "code": "email_verification_required",
            "message": "Email verification is required.",
        }
    }


@pytest.mark.django_db
def test_authenticated_endpoint_returns_stable_anonymous_error(api_client: APIClient) -> None:
    response = api_client.post("/api/auth/email-verification/request/", format="json")

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "not_authenticated", "message": "Authentication is required."}
    }


@pytest.mark.parametrize(
    ("endpoint", "authenticated"),
    [
        ("/api/auth/register/", False),
        ("/api/auth/login/", False),
        ("/api/auth/logout/", False),
        ("/api/auth/email-verification/request/", True),
        ("/api/auth/email-verification/confirm/", True),
        ("/api/auth/password-reset/request/", False),
        ("/api/auth/password-reset/confirm/", False),
    ],
)
@pytest.mark.django_db
def test_malformed_json_uses_stable_error_without_parser_detail(
    api_client: APIClient, endpoint: str, authenticated: bool
) -> None:
    if authenticated:
        user = User.objects.create_user(
            email=f"malformed-{endpoint.count('/')}@example.com",
            password="test-password",
        )
        api_client.force_login(user)

    response = api_client.generic(
        "POST",
        endpoint,
        data='{"malformed":',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed.",
        }
    }
    rendered = response.content.decode()
    assert "detail" not in response.json()
    assert "JSON parse error" not in rendered
    assert "Expecting" not in rendered


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
@pytest.mark.django_db
@override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"])
def test_browser_origin_login_accepts_matching_cookie_and_header_and_rotates_csrf(
    origin: str,
) -> None:
    client = APIClient(enforce_csrf_checks=True)
    user = User.objects.create_user(email="browser-origin@example.com", password="correct-password")
    bootstrap = client.get("/api/auth/session/")
    before = client.cookies["csrftoken"].value

    response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "correct-password"},
        format="json",
        HTTP_X_CSRFTOKEN=before,
        HTTP_ORIGIN=origin,
        HTTP_REFERER=f"{origin}/login",
    )

    assert bootstrap.status_code == 200
    assert response.status_code == 200
    assert client.cookies["csrftoken"].value != before
    assert "sessionid" in client.cookies
    assert client.get("/api/auth/session/").json()["authenticated"] is True


@pytest.mark.django_db
@override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:5173"])
def test_browser_origin_login_still_rejects_untrusted_origin_with_matching_tokens() -> None:
    client = APIClient(enforce_csrf_checks=True)
    User.objects.create_user(email="untrusted-origin@example.com", password="correct-password")
    client.get("/api/auth/session/")
    token = client.cookies["csrftoken"].value

    response = client.post(
        "/api/auth/login/",
        {"email": "untrusted-origin@example.com", "password": "correct-password"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://evil.example",
        HTTP_REFERER="https://evil.example/login",
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "csrf_failed", "message": "CSRF validation failed."}
    }
