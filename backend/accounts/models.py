import uuid
from typing import Any, ClassVar, NoReturn

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.managers import UserManager, canonicalize_email


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True, db_index=True)
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

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    def __str__(self) -> str:
        return self.email

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = canonicalize_email(self.email)
        super().save(*args, **kwargs)


class InvitationEmailLock(models.Model):
    email = models.EmailField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.email

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = canonicalize_email(self.email)
        super().save(*args, **kwargs)


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    secret_digest = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accepted_invitations",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")),
                name="accounts_invitation_email_lowercase",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=models.Q(revoked_at__isnull=True, accepted_at__isnull=True),
                name="accounts_invitation_one_pending_email",
            ),
            models.CheckConstraint(
                condition=models.Q(revoked_at__isnull=True) | models.Q(accepted_at__isnull=True),
                name="accounts_invitation_not_revoked_and_accepted",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(accepted_at__isnull=True, accepted_by__isnull=True)
                    | models.Q(accepted_at__isnull=False, accepted_by__isnull=False)
                ),
                name="accounts_invitation_acceptance_consistent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.state})"

    @property
    def state(self) -> str:
        if self.accepted_at is not None:
            return "accepted"
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at <= timezone.now():
            return "expired"
        return "pending"


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    secret_digest = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "expires_at"), name="accounts_verify_user_exp_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revoked_at__isnull=True) | models.Q(consumed_at__isnull=True),
                name="accounts_verify_not_revoked_consumed",
            )
        ]

    def __str__(self) -> str:
        return f"Verification token {self.id}"


class AuthEmailOutbox(models.Model):
    class Kind(models.TextChoices):
        INVITATION = "invitation"
        VERIFICATION = "verification"
        PASSWORD_RESET = "password_reset"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    deduplication_key = models.CharField(max_length=128, unique=True)
    recipient = models.EmailField(blank=True)
    recipient_digest = models.CharField(max_length=64)
    credential_state_digest = models.CharField(max_length=64, blank=True)
    invitation = models.ForeignKey(
        Invitation,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="email_jobs",
    )
    verification = models.ForeignKey(
        EmailVerificationToken,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="email_jobs",
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(
                fields=("sent_at", "failed_at", "available_at"),
                name="accounts_email_pending_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sent_at__isnull=True) | models.Q(failed_at__isnull=True),
                name="accounts_email_not_sent_failed",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="invitation",
                        invitation__isnull=False,
                        verification__isnull=True,
                        user__isnull=True,
                    )
                    | models.Q(
                        kind="verification",
                        invitation__isnull=True,
                        verification__isnull=False,
                        user__isnull=False,
                    )
                    | models.Q(
                        kind="password_reset",
                        invitation__isnull=True,
                        verification__isnull=True,
                    )
                ),
                name="accounts_email_target_matches_kind",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} email job {self.id}"


class AuthRateLimitBucket(models.Model):
    scope = models.CharField(max_length=64)
    identifier_digest = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("scope", "identifier_digest", "window_start"),
                name="accounts_rate_bucket_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.scope} at {self.window_start}"


class AppendOnlySecurityEventQuerySet(models.QuerySet["AccountSecurityEvent"]):
    @staticmethod
    def _deny() -> NoReturn:
        raise TypeError("AccountSecurityEvent records are append-only")

    def update(self, **kwargs: Any) -> NoReturn:
        del kwargs
        self._deny()

    def delete(self) -> NoReturn:
        self._deny()

    def bulk_update(self, objs: Any, fields: Any, batch_size: int | None = None) -> NoReturn:
        del objs, fields, batch_size
        self._deny()


class AccountSecurityEventManager(
    models.Manager.from_queryset(AppendOnlySecurityEventQuerySet)  # type: ignore[misc]
):
    pass


class AccountSecurityEvent(models.Model):
    class Code(models.TextChoices):
        INVITATION_ISSUED = "invitation_issued"
        INVITATION_REVOKED = "invitation_revoked"
        INVITATION_ACCEPTED = "invitation_accepted"
        APPLICANT_REGISTERED = "applicant_registered"
        EMAIL_VERIFIED = "email_verified"
        PASSWORD_RESET_COMPLETED = "password_reset_completed"

    code = models.CharField(max_length=64, choices=Code.choices)
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="security_events_as_actor",
    )
    target = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="security_events_as_target",
    )
    invitation_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_correlation_id = models.CharField(max_length=64)
    client_ip_digest = models.CharField(max_length=64, blank=True)

    objects = AccountSecurityEventManager()

    class Meta:
        ordering = ("-created_at",)
        base_manager_name = "objects"
        default_manager_name = "objects"

    def __str__(self) -> str:
        return f"{self.code} at {self.created_at}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None and type(self).objects.filter(pk=self.pk).exists():
            raise TypeError("AccountSecurityEvent records are append-only")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        del args, kwargs
        raise TypeError("AccountSecurityEvent records are append-only")
