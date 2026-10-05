import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Project(models.Model):
    class Currency(models.TextChoices):
        KZT = "KZT"
        USD = "USD"
        EUR = "EUR"

    class Status(models.TextChoices):
        DRAFT = "draft"
        ACTIVE = "active"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5000, blank=True, default="")
    investment_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.KZT)
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated_at", "-created_at")
        constraints = [
            models.CheckConstraint(
                condition=Q(investment_amount__isnull=True) | Q(investment_amount__gt=0),
                name="projects_project_amount_positive",
            ),
            models.CheckConstraint(
                condition=Q(currency__in=("KZT", "USD", "EUR")),
                name="projects_project_currency_supported",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="draft", activated_at__isnull=True)
                    | Q(status="active", activated_at__isnull=False)
                ),
                name="projects_project_status_activation_consistent",
            ),
        ]

    def __str__(self) -> str:
        return self.title
