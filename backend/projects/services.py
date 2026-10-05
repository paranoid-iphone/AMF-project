from decimal import Decimal
from typing import NotRequired, TypedDict
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from accounts.guards import require_verified_email
from accounts.models import User
from projects.exceptions import ProjectNotFoundError, ProjectValidationError
from projects.models import Project


class ProjectCreateData(TypedDict):
    title: str
    description: NotRequired[str]
    investment_amount: NotRequired[Decimal | None]
    currency: NotRequired[str]


class ProjectPatch(TypedDict, total=False):
    title: str
    description: str
    investment_amount: Decimal | None
    currency: str


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _validate_values(
    *,
    title: object,
    description: object,
    investment_amount: object,
    currency: object,
    activation_required: bool,
) -> tuple[str, str, Decimal | None, str]:
    errors: dict[str, list[dict[str, str]]] = {}

    if isinstance(title, str):
        normalized_title = title.strip()
        if not normalized_title:
            code = "required_for_activation" if activation_required else "blank"
            message = (
                "Title is required to activate the project."
                if activation_required
                else "This field may not be blank."
            )
            errors["title"] = [_error(code, message)]
        elif len(normalized_title) > 200:
            errors["title"] = [
                _error("max_length", "Ensure this field has no more than 200 characters.")
            ]
    else:
        normalized_title = ""
        errors["title"] = [_error("invalid", "Expected a string value.")]

    if isinstance(description, str):
        normalized_description = description.strip()
        if activation_required and not normalized_description:
            errors["description"] = [
                _error(
                    "required_for_activation",
                    "Description is required to activate the project.",
                )
            ]
        elif len(normalized_description) > 5000:
            errors["description"] = [
                _error("max_length", "Ensure this field has no more than 5000 characters.")
            ]
    else:
        normalized_description = ""
        errors["description"] = [_error("invalid", "Expected a string value.")]

    normalized_amount: Decimal | None
    if investment_amount is None:
        normalized_amount = None
        if activation_required:
            errors["investment_amount"] = [
                _error(
                    "required_for_activation",
                    "Investment amount is required to activate the project.",
                )
            ]
    elif not isinstance(investment_amount, Decimal):
        normalized_amount = None
        errors["investment_amount"] = [_error("invalid", "A valid number is required.")]
    elif not investment_amount.is_finite():
        normalized_amount = None
        errors["investment_amount"] = [_error("invalid", "A valid number is required.")]
    else:
        normalized_amount = investment_amount
        amount_tuple = investment_amount.as_tuple()
        exponent = amount_tuple.exponent
        assert isinstance(exponent, int)
        decimal_places = max(-exponent, 0)
        total_digits = len(amount_tuple.digits) + max(exponent, 0)
        whole_digits = max(total_digits - decimal_places, 0)
        if investment_amount <= 0:
            errors["investment_amount"] = [
                _error("min_value", "Ensure this value is greater than 0.")
            ]
        elif decimal_places > 2:
            errors["investment_amount"] = [
                _error("max_decimal_places", "Ensure that there are no more than 2 decimal places.")
            ]
        elif total_digits > 20 or whole_digits > 18:
            errors["investment_amount"] = [
                _error("max_digits", "Ensure that there are no more than 20 digits in total.")
            ]

    if isinstance(currency, str) and currency in Project.Currency.values:
        normalized_currency = currency
    else:
        normalized_currency = ""
        errors["currency"] = [_error("invalid_choice", "Select a valid choice.")]

    if errors:
        raise ProjectValidationError(errors)
    return normalized_title, normalized_description, normalized_amount, normalized_currency


def create_project(*, actor: User, data: ProjectCreateData) -> Project:
    with transaction.atomic():
        title, description, amount, currency = _validate_values(
            title=data["title"],
            description=data.get("description", ""),
            investment_amount=data.get("investment_amount"),
            currency=data.get("currency", Project.Currency.KZT),
            activation_required=False,
        )
        return Project.objects.create(
            owner=actor,
            title=title,
            description=description,
            investment_amount=amount,
            currency=currency,
        )


def _locked_owned_project(*, actor: User, project_id: UUID) -> Project:
    try:
        return Project.objects.select_for_update().get(id=project_id, owner=actor)
    except Project.DoesNotExist as error:
        raise ProjectNotFoundError from error


def update_project(*, actor: User, project_id: UUID, patch: ProjectPatch) -> Project:
    with transaction.atomic():
        project = _locked_owned_project(actor=actor, project_id=project_id)
        values: dict[str, object] = {
            "title": project.title,
            "description": project.description,
            "investment_amount": project.investment_amount,
            "currency": project.currency,
        }
        values.update(patch)
        title, description, amount, currency = _validate_values(
            title=values["title"],
            description=values["description"],
            investment_amount=values["investment_amount"],
            currency=values["currency"],
            activation_required=project.status == Project.Status.ACTIVE,
        )
        changed = {
            "title": title != project.title,
            "description": description != project.description,
            "investment_amount": amount != project.investment_amount,
            "currency": currency != project.currency,
        }
        if any(changed.values()):
            project.title = title
            project.description = description
            project.investment_amount = amount
            project.currency = currency
            project.save(
                update_fields=tuple(name for name, differs in changed.items() if differs)
                + ("updated_at",)
            )
        return project


def activate_project(*, actor: User, project_id: UUID) -> Project:
    with transaction.atomic():
        project = _locked_owned_project(actor=actor, project_id=project_id)
        require_verified_email(actor)
        _validate_values(
            title=project.title,
            description=project.description,
            investment_amount=project.investment_amount,
            currency=project.currency,
            activation_required=True,
        )
        if project.status != Project.Status.ACTIVE:
            project.status = Project.Status.ACTIVE
            project.activated_at = timezone.now()
            project.save(update_fields=("status", "activated_at", "updated_at"))
        return project


def deactivate_project(*, actor: User, project_id: UUID) -> Project:
    with transaction.atomic():
        project = _locked_owned_project(actor=actor, project_id=project_id)
        if project.status == Project.Status.ACTIVE:
            project.status = Project.Status.DRAFT
            project.activated_at = None
            project.save(update_fields=("status", "activated_at", "updated_at"))
        return project
