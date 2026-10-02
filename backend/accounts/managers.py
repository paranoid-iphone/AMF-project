from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from accounts.models import User


def canonicalize_email(email: str) -> str:
    """Return the stored email identity: trimmed and lowercased in full."""
    return email.strip().lower()


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> User:
        if not email or not email.strip():
            raise ValueError("The email address must be provided")
        user = self.model(email=canonicalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username: str | None) -> User:
        return self.get(email=canonicalize_email(username or ""))

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)
