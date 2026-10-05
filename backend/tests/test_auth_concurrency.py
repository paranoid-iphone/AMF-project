from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from accounts.exceptions import InvalidInvitationError, InvalidTokenError
from accounts.models import (
    AuthEmailOutbox,
    AuthRateLimitBucket,
    Invitation,
    InvitationEmailLock,
    User,
)
from accounts.rate_limits import RateLimit, consume_rate_limit
from accounts.services import (
    confirm_email_verification,
    issue_invitation,
    issue_verification_token,
    register_applicant,
)


@pytest.mark.django_db(transaction=True)
def test_concurrent_invitation_acceptance_creates_exactly_one_user() -> None:
    issued = issue_invitation(email="race@example.com", actor=None, request_id="invite")
    barrier = Barrier(2)

    def attempt(number: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            user = register_applicant(
                invitation_token=issued.token,
                email="race@example.com",
                password=f"Race-password-{number}-42!",
                request_id=f"race-{number}",
            )
        except InvalidInvitationError:
            return "invalid"
        finally:
            close_old_connections()
        return f"created:{user.pk}"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert sum(result.startswith("created:") for result in results) == 1
    assert results.count("invalid") == 1
    assert User.objects.filter(email="race@example.com").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_consumption_succeeds_once() -> None:
    user = User.objects.create_user(email="verify-race@example.com", password="test-password")
    issued = issue_verification_token(user)
    assert issued is not None
    barrier = Barrier(2)

    def attempt(number: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            confirm_email_verification(token=issued.token, request_id=f"verify-{number}")
        except InvalidTokenError:
            return "invalid"
        finally:
            close_old_connections()
        return "verified"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert results.count("verified") == 1
    assert results.count("invalid") == 1
    issued.verification.refresh_from_db()
    assert issued.verification.consumed_at is not None


@pytest.mark.django_db(transaction=True)
def test_rate_limit_increments_are_safe_across_connections() -> None:
    workers = 6
    barrier = Barrier(workers)

    def increment(_: int) -> None:
        close_old_connections()
        barrier.wait()
        try:
            consume_rate_limit(RateLimit("concurrency", "same-account", 100, 3600))
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(increment, range(workers)))

    bucket = AuthRateLimitBucket.objects.get(scope="concurrency")
    assert bucket.count == workers
    assert bucket.identifier_digest != "same-account"


@pytest.mark.django_db(transaction=True)
def test_concurrent_invitation_issuance_keeps_exactly_one_pending() -> None:
    barrier = Barrier(2)

    def issue(number: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            result = issue_invitation(
                email="Concurrent@Example.COM" if number else "concurrent@example.com",
                actor=None,
                request_id=f"issue-{number}",
            )
            return str(result.invitation.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        selectors = list(pool.map(issue, range(2)))

    assert len(set(selectors)) == 2
    invitations = Invitation.objects.filter(email="concurrent@example.com")
    assert invitations.count() == 2
    assert invitations.filter(revoked_at__isnull=True, accepted_at__isnull=True).count() == 1
    assert invitations.filter(revoked_at__isnull=False).count() == 1
    assert InvitationEmailLock.objects.filter(email="concurrent@example.com").count() == 1
    assert AuthEmailOutbox.objects.filter(kind="invitation").count() == 2


@pytest.mark.django_db(transaction=True)
def test_verification_resend_and_confirm_share_user_first_lock_order_without_deadlock() -> None:
    user = User.objects.create_user(email="mixed-race@example.com", password="test-password")
    issued = issue_verification_token(user)
    assert issued is not None
    barrier = Barrier(2)

    def confirm() -> str:
        close_old_connections()
        barrier.wait()
        try:
            confirm_email_verification(token=issued.token, request_id="mixed-confirm")
            return "confirmed"
        except InvalidTokenError:
            return "invalid"
        finally:
            close_old_connections()

    def resend() -> str:
        close_old_connections()
        barrier.wait()
        try:
            result = issue_verification_token(User.objects.get(pk=user.pk))
            return "issued" if result is not None else "already-verified"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        confirm_future = pool.submit(confirm)
        resend_future = pool.submit(resend)
        results = {confirm_future.result(timeout=15), resend_future.result(timeout=15)}

    assert results in ({"confirmed", "already-verified"}, {"invalid", "issued"})
    user.refresh_from_db()
    active_tokens = user.verification_tokens.filter(
        consumed_at__isnull=True, revoked_at__isnull=True
    ).count()
    assert (user.email_verified and active_tokens == 0) or (
        not user.email_verified and active_tokens == 1
    )
