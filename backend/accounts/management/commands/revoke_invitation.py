import uuid

from django.core.management.base import BaseCommand, CommandError

from accounts.services import revoke_invitation


class Command(BaseCommand):
    help = "Revoke a pending applicant invitation"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("selector")

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        try:
            selector = uuid.UUID(str(options["selector"]))
        except ValueError as exc:
            raise CommandError("Invitation selector must be a UUID") from exc
        if not revoke_invitation(
            selector=selector,
            actor=None,
            request_id="management-command",
        ):
            raise CommandError("Pending invitation not found")
        self.stdout.write(self.style.SUCCESS(f"Invitation {selector} revoked."))
