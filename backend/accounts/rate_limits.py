import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.exceptions import RateLimitExceededError
from accounts.models import AuthRateLimitBucket
from accounts.security import identifier_digest


@dataclass(frozen=True)
class RateLimit:
    scope: str
    identifier: str
    limit: int
    window_seconds: int


def _window_start(now: datetime, window_seconds: int) -> datetime:
    timestamp = int(now.timestamp())
    return datetime.fromtimestamp(
        timestamp - (timestamp % window_seconds),
        tz=now.tzinfo,
    )


def consume_rate_limit(rate_limit: RateLimit) -> None:
    now = timezone.now()
    window_start = _window_start(now, rate_limit.window_seconds)
    expires_at = window_start + timedelta(seconds=rate_limit.window_seconds)
    digest = identifier_digest(rate_limit.scope, rate_limit.identifier)

    with transaction.atomic():
        try:
            with transaction.atomic():
                bucket = AuthRateLimitBucket.objects.create(
                    scope=rate_limit.scope,
                    identifier_digest=digest,
                    window_start=window_start,
                    count=1,
                    expires_at=expires_at,
                )
        except IntegrityError:
            bucket = AuthRateLimitBucket.objects.select_for_update().get(
                scope=rate_limit.scope,
                identifier_digest=digest,
                window_start=window_start,
            )
            bucket.count += 1
            bucket.expires_at = expires_at
            bucket.save(update_fields=("count", "expires_at"))
        count = bucket.count

    if count > rate_limit.limit:
        retry_after = math.ceil((expires_at - now).total_seconds())
        raise RateLimitExceededError(retry_after)


def consume_rate_limits(*rate_limits: RateLimit) -> None:
    for rate_limit in rate_limits:
        consume_rate_limit(rate_limit)
