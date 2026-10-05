class AccountsServiceError(Exception):
    pass


class InvalidInvitationError(AccountsServiceError):
    pass


class InvalidTokenError(AccountsServiceError):
    pass


class EmailVerificationRequiredError(AccountsServiceError):
    pass


class RateLimitExceededError(AccountsServiceError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("Authentication rate limit exceeded")
