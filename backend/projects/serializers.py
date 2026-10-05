from collections.abc import Mapping
from decimal import Decimal
from typing import Any, cast

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail

from projects.models import Project


class ProjectSerializer(serializers.ModelSerializer[Project]):
    class Meta:
        model = Project
        fields = (
            "id",
            "title",
            "description",
            "investment_amount",
            "currency",
            "status",
            "created_at",
            "updated_at",
            "activated_at",
        )
        read_only_fields = fields


class ProjectWriteSerializer(serializers.Serializer[dict[str, Any]]):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=5000, allow_blank=True, required=False)
    investment_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal("0.01"),
        allow_null=True,
        required=False,
    )
    currency = serializers.ChoiceField(
        choices=Project.Currency.choices,
        default=Project.Currency.KZT,
        required=False,
    )

    writable_input_keys = frozenset({"title", "description", "investment_amount", "currency"})
    read_only_input_keys = frozenset(
        {"id", "owner", "status", "created_at", "updated_at", "activated_at"}
    )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, Mapping):
            errors: dict[str, list[ErrorDetail]] = {}
            for key in data:
                if key in self.writable_input_keys:
                    continue
                code = "read_only" if key in self.read_only_input_keys else "unknown"
                errors[str(key)] = [ErrorDetail("This field is not writable.", code=code)]
            if errors:
                raise serializers.ValidationError(errors)
        return cast(dict[str, Any], super().to_internal_value(data))


class ProjectListEnvelopeSerializer(serializers.Serializer[dict[str, Any]]):
    projects = ProjectSerializer(many=True)
