from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AuthRateLimitBucket


class Command(BaseCommand):
    help = "Delete expired authentication rate-limit buckets"

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        del args, options
        deleted, _ = AuthRateLimitBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Deleted {deleted} expired authentication bucket row(s).")
