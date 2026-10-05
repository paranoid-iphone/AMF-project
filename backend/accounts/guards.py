from accounts.exceptions import EmailVerificationRequiredError
from accounts.models import User


def require_verified_email(actor: User) -> None:
    if not actor.email_verified:
        raise EmailVerificationRequiredError
