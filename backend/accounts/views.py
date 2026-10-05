from collections.abc import Callable
from typing import Any, cast

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_exceptions import StableAPIError
from accounts.exceptions import InvalidInvitationError, InvalidTokenError, RateLimitExceededError
from accounts.managers import canonicalize_email
from accounts.models import User
from accounts.rate_limits import RateLimit, consume_rate_limits
from accounts.security import parse_selector_token, request_correlation_id
from accounts.serializers import (
    AcceptedSerializer,
    ErrorEnvelopeSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SessionSerializer,
    TokenSerializer,
    UserEnvelopeSerializer,
    UserSerializer,
    VerifiedSerializer,
)
from accounts.services import (
    confirm_email_verification,
    confirm_password_reset,
    issue_verification_token,
    register_applicant,
    request_password_reset,
)

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description="Current csrftoken cookie value for every unsafe request.",
)


def _parse_request_body(request: Request) -> None:
    parsed_body = request.data
    del parsed_body


def _ip(request: Request) -> str:
    return str(request.META.get("REMOTE_ADDR", "unknown"))


def _request_id(request: Request) -> str:
    return request_correlation_id(request.headers.get("X-Request-ID"))


def _selector(value: str) -> str:
    parsed = parse_selector_token(value)
    return str(parsed[0]) if parsed else "invalid"


def _password_fields(
    exc: DjangoValidationError, field_name: str
) -> dict[str, list[dict[str, str]]]:
    return {
        field_name: [
            {
                "code": error.code or "invalid",
                "message": error.message % (error.params or {}),
            }
            for error in exc.error_list
        ]
    }


def _service_call(call: Callable[[], Any], *, password_field: str | None = None) -> Any:
    try:
        return call()
    except DjangoValidationError as exc:
        if password_field is None:
            raise
        raise StableAPIError(fields=_password_fields(exc, password_field)) from exc
    except RateLimitExceededError as exc:
        raise StableAPIError(
            code="rate_limited",
            message="Too many requests.",
            status_code=429,
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: SessionSerializer})
    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": UserSerializer(request.user).data})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        parameters=[CSRF_HEADER],
        responses={
            201: UserEnvelopeSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _service_call(
            lambda: consume_rate_limits(
                RateLimit("registration_ip", _ip(request), settings.AUTH_REGISTER_IP_LIMIT, 3600)
            )
        )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "registration_invitation",
                    _selector(data["invitation_token"]),
                    settings.AUTH_REGISTER_INVITATION_LIMIT,
                    3600,
                )
            )
        )
        try:
            user = _service_call(
                lambda: register_applicant(
                    invitation_token=data["invitation_token"],
                    email=data["email"],
                    password=data["password"],
                    request_id=_request_id(request),
                    ip_address=_ip(request),
                ),
                password_field="password",
            )
        except InvalidInvitationError as exc:
            raise StableAPIError(
                code="invalid_invitation",
                message="The invitation is invalid or unavailable.",
            ) from exc
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        parameters=[CSRF_HEADER],
        responses={
            200: UserEnvelopeSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _service_call(
            lambda: consume_rate_limits(
                RateLimit("login_ip", _ip(request), settings.AUTH_LOGIN_IP_LIMIT, 900)
            )
        )
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = canonicalize_email(serializer.validated_data["email"])
        _service_call(
            lambda: consume_rate_limits(
                RateLimit("login_account", email, settings.AUTH_LOGIN_ACCOUNT_LIMIT, 900)
            )
        )
        user = authenticate(
            request=request._request,
            username=email,
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            raise StableAPIError(
                code="invalid_credentials",
                message="Email or password is incorrect.",
            )
        login(request._request, user)
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        parameters=[CSRF_HEADER],
        responses={204: None, 403: ErrorEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        _parse_request_body(request)
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerificationRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        parameters=[CSRF_HEADER],
        responses={
            202: AcceptedSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _parse_request_body(request)
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "verification_resend_ip", _ip(request), settings.AUTH_VERIFY_IP_LIMIT, 3600
                ),
                RateLimit(
                    "verification_resend_user",
                    str(request.user.pk),
                    settings.AUTH_VERIFY_USER_LIMIT,
                    3600,
                ),
            )
        )
        issue_verification_token(cast(User, request.user))
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)


class VerificationConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=TokenSerializer,
        parameters=[CSRF_HEADER],
        responses={
            200: VerifiedSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "token_confirm_ip", _ip(request), settings.AUTH_TOKEN_CONFIRM_IP_LIMIT, 3600
                )
            )
        )
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "token_confirm_selector",
                    _selector(token),
                    settings.AUTH_TOKEN_CONFIRM_SELECTOR_LIMIT,
                    3600,
                )
            )
        )
        try:
            confirm_email_verification(
                token=token,
                request_id=_request_id(request),
                ip_address=_ip(request),
            )
        except InvalidTokenError as exc:
            raise StableAPIError(
                code="invalid_or_expired_token",
                message="The token is invalid or expired.",
            ) from exc
        return Response({"status": "verified"})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        parameters=[CSRF_HEADER],
        responses={
            202: AcceptedSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _service_call(
            lambda: consume_rate_limits(
                RateLimit("reset_request_ip", _ip(request), settings.AUTH_RESET_IP_LIMIT, 3600)
            )
        )
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = canonicalize_email(serializer.validated_data["email"])
        _service_call(
            lambda: consume_rate_limits(
                RateLimit("reset_request_email", email, settings.AUTH_RESET_EMAIL_LIMIT, 3600)
            )
        )
        request_password_reset(email)
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        parameters=[CSRF_HEADER],
        responses={
            204: None,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "token_confirm_ip", _ip(request), settings.AUTH_TOKEN_CONFIRM_IP_LIMIT, 3600
                )
            )
        )
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _service_call(
            lambda: consume_rate_limits(
                RateLimit(
                    "token_confirm_selector",
                    data["uid"],
                    settings.AUTH_TOKEN_CONFIRM_SELECTOR_LIMIT,
                    3600,
                )
            )
        )
        try:
            _service_call(
                lambda: confirm_password_reset(
                    uid=data["uid"],
                    token=data["token"],
                    new_password=data["new_password"],
                    request_id=_request_id(request),
                    ip_address=_ip(request),
                ),
                password_field="new_password",
            )
        except InvalidTokenError as exc:
            raise StableAPIError(
                code="invalid_or_expired_token",
                message="The token is invalid or expired.",
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
