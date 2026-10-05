from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuthEmailOutbox


class Command(BaseCommand):
    help = "Delete terminal authentication email outbox rows past their retention period"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--retention-seconds", type=int)

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        del args
        configured = options.get("retention_seconds")
        retention_seconds = (
            settings.AUTH_EMAIL_OUTBOX_RETENTION_SECONDS if configured is None else int(configured)
        )
        if retention_seconds < 0:
            raise CommandError("Retention seconds must be non-negative")
        cutoff = timezone.now() - timedelta(seconds=retention_seconds)
        terminal = AuthEmailOutbox.objects.filter(
            Q(sent_at__isnull=False, sent_at__lte=cutoff)
            | Q(failed_at__isnull=False, failed_at__lte=cutoff)
        )
        deleted, _ = terminal.delete()
        self.stdout.write(f"Deleted {deleted} terminal authentication email outbox row(s).")
