from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts.services import issue_invitation


class Command(BaseCommand):
    help = "Issue or replace an applicant invitation and send its email"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("email")

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        email = str(options["email"])
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("A valid email address is required") from exc
        issued = issue_invitation(
            email=email,
            actor=None,
            request_id="management-command",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Invitation {issued.invitation.id} issued for "
                f"{issued.invitation.email}; email queued."
            )
        )
