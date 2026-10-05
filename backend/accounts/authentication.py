from rest_framework.authentication import CSRFCheck, SessionAuthentication
from rest_framework.request import Request

from accounts.api_exceptions import StableAPIError


def _dummy_get_response(request: object) -> None:
    del request


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    def authenticate(self, request: Request):  # type: ignore[no-untyped-def]
        self.enforce_csrf(request)
        user = getattr(request._request, "user", None)
        if not user or not user.is_active:
            return None
        return user, None

    def enforce_csrf(self, request: Request) -> None:
        check = CSRFCheck(_dummy_get_response)  # type: ignore[arg-type]
        check.process_request(request)
        reason = check.process_view(request, None, (), {})  # type: ignore[arg-type]
        if reason:
            raise StableAPIError(
                code="csrf_failed",
                message="CSRF validation failed.",
                status_code=403,
            )
