import time

from django.core.management.base import BaseCommand

from accounts.outbox import process_auth_email_outbox


class Command(BaseCommand):
    help = "Process durable authentication email outbox jobs"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=float, default=2.0)
        parser.add_argument("--batch-size", type=int, default=25)

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        del args
        watch = bool(options["watch"])
        interval = max(0.1, float(options["interval"]))
        batch_size = max(1, int(options["batch_size"]))
        try:
            while True:
                processed = process_auth_email_outbox(limit=batch_size)
                if not watch:
                    if processed < batch_size:
                        break
                    continue
                if processed == 0:
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("Authentication email worker stopped.")
