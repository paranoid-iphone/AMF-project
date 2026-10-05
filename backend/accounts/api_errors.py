from collections.abc import Mapping
from typing import Any

from django.http import JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from accounts.api_exceptions import StableAPIError
from accounts.exceptions import EmailVerificationRequiredError


def _field_errors(detail: Any) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    if not isinstance(detail, Mapping):
        return result
    for field, errors in detail.items():
        values = errors if isinstance(errors, list) else [errors]
        result[str(field)] = [
            {
                "code": str(getattr(value, "code", "invalid")),
                "message": str(value),
            }
            for value in values
        ]
    return result


def stable_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, EmailVerificationRequiredError):
        exc = StableAPIError(
            code="email_verification_required",
            message="Email verification is required.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, StableAPIError):
        response = exception_handler(exc, context)
        if response is not None:
            for name, value in exc.headers.items():
                response[name] = value
        return response
    if isinstance(exc, exceptions.ParseError):
        stable = StableAPIError()
        return exception_handler(stable, context)
    if isinstance(exc, exceptions.ValidationError):
        stable = StableAPIError(fields=_field_errors(exc.detail))
        return exception_handler(stable, context)
    if isinstance(exc, exceptions.NotAuthenticated):
        stable = StableAPIError(
            code="not_authenticated",
            message="Authentication is required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return exception_handler(stable, context)
    if isinstance(exc, (exceptions.PermissionDenied, exceptions.AuthenticationFailed)):
        stable = StableAPIError(
            code="not_authenticated",
            message="Authentication is required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return exception_handler(stable, context)
    return exception_handler(exc, context)


def csrf_failure(request: Any, reason: str = "") -> JsonResponse:
    del request, reason
    return JsonResponse(
        {"error": {"code": "csrf_failed", "message": "CSRF validation failed."}},
        status=403,
    )
