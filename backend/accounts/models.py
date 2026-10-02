from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.managers import UserManager, canonicalize_email


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")),
                name="accounts_user_email_lowercase",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = canonicalize_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
