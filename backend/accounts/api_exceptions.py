from collections.abc import Mapping
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException


class StableAPIError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_message = "Request validation failed."

    def __init__(
        self,
        *,
        code: str | None = None,
        message: str | None = None,
        status_code: int | None = None,
        fields: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        error: dict[str, Any] = {
            "code": code or self.default_code,
            "message": message or self.default_message,
        }
        if fields:
            error["fields"] = fields
        super().__init__({"error": error}, code=code or self.default_code)
        if status_code is not None:
            self.status_code = status_code  # type: ignore[assignment]
        self.headers = dict(headers or {})
