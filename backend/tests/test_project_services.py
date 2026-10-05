from decimal import Decimal
from uuid import uuid4

import pytest
from django.utils import timezone

from accounts.exceptions import EmailVerificationRequiredError
from accounts.models import User
from projects.exceptions import ProjectNotFoundError, ProjectValidationError
from projects.models import Project
from projects.services import (
    ProjectPatch,
    activate_project,
    create_project,
    deactivate_project,
    update_project,
)


def _field_code(error: ProjectValidationError, field: str) -> str:
    return error.field_errors[field][0]["code"]


@pytest.mark.django_db
def test_create_project_trims_title_and_applies_private_draft_defaults() -> None:
    owner = User.objects.create_user(email="create-project@example.com", password="test-password")

    project = create_project(
        actor=owner,
        data={"title": "  Solar project  ", "description": "  Concept  "},
    )

    assert project.title == "Solar project"
    assert project.description == "Concept"
    assert project.owner_id == owner.pk
    assert project.status == Project.Status.DRAFT
    assert project.currency == Project.Currency.KZT
    assert project.investment_amount is None
    assert project.activated_at is None


@pytest.mark.django_db
def test_create_project_rejects_title_that_is_blank_after_trimming() -> None:
    owner = User.objects.create_user(email="blank-title@example.com", password="test-password")

    with pytest.raises(ProjectValidationError) as caught:
        create_project(actor=owner, data={"title": "  "})

    assert _field_code(caught.value, "title") == "blank"
    assert Project.objects.count() == 0


@pytest.mark.django_db
def test_project_mutation_uses_same_not_found_error_for_missing_and_foreign_ids() -> None:
    owner = User.objects.create_user(email="project-owner2@example.com", password="test-password")
    other = User.objects.create_user(email="project-other2@example.com", password="test-password")
    project = create_project(actor=owner, data={"title": "Private"})

    with pytest.raises(ProjectNotFoundError):
        update_project(actor=other, project_id=project.id, patch={"title": "Probe"})
    with pytest.raises(ProjectNotFoundError):
        update_project(actor=other, project_id=uuid4(), patch={"title": "Probe"})

    project.refresh_from_db()
    assert project.title == "Private"


@pytest.mark.django_db
@pytest.mark.parametrize("operation", [activate_project, deactivate_project])
def test_foreign_lifecycle_lookup_precedes_email_verification_guard(operation) -> None:  # type: ignore[no-untyped-def]
    owner = User.objects.create_user(email="lifecycle-owner@example.com", password="test-password")
    unverified = User.objects.create_user(
        email="lifecycle-unverified@example.com", password="test-password"
    )
    project = create_project(actor=owner, data={"title": "Private"})

    with pytest.raises(ProjectNotFoundError):
        operation(actor=unverified, project_id=project.id)


@pytest.mark.django_db
def test_activation_requires_verified_email() -> None:
    owner = User.objects.create_user(
        email="unverified-project@example.com", password="test-password"
    )
    project = create_project(
        actor=owner,
        data={"title": "Complete", "description": "Ready", "investment_amount": Decimal("10.00")},
    )

    with pytest.raises(EmailVerificationRequiredError):
        activate_project(actor=owner, project_id=project.id)

    project.refresh_from_db()
    assert project.status == Project.Status.DRAFT
    assert project.activated_at is None


@pytest.mark.django_db
def test_activation_reports_every_missing_required_field() -> None:
    owner = User.objects.create_user(
        email="incomplete-project@example.com", password="test-password"
    )
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    project = create_project(actor=owner, data={"title": "Incomplete"})

    with pytest.raises(ProjectValidationError) as caught:
        activate_project(actor=owner, project_id=project.id)

    assert {field: _field_code(caught.value, field) for field in caught.value.field_errors} == {
        "description": "required_for_activation",
        "investment_amount": "required_for_activation",
    }


@pytest.mark.django_db
def test_active_project_can_be_edited_if_result_remains_complete() -> None:
    owner = User.objects.create_user(email="active-edit@example.com", password="test-password")
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    project = create_project(
        actor=owner,
        data={"title": "Ready", "description": "Plan", "investment_amount": Decimal("10.00")},
    )
    activate_project(actor=owner, project_id=project.id)

    updated = update_project(
        actor=owner, project_id=project.id, patch={"title": " Revised ", "currency": "EUR"}
    )

    assert updated.title == "Revised"
    assert updated.currency == Project.Currency.EUR
    assert updated.status == Project.Status.ACTIVE
    assert updated.description == "Plan"
    assert updated.investment_amount == Decimal("10.00")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("patch", "field"),
    [({"description": ""}, "description"), ({"investment_amount": None}, "investment_amount")],
)
def test_invalid_active_edit_is_rejected_without_changing_saved_state(
    patch: ProjectPatch, field: str
) -> None:
    owner = User.objects.create_user(
        email=f"rollback-{field}@example.com", password="test-password"
    )
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    project = create_project(
        actor=owner,
        data={"title": "Ready", "description": "Plan", "investment_amount": Decimal("10.00")},
    )
    activate_project(actor=owner, project_id=project.id)

    with pytest.raises(ProjectValidationError) as caught:
        update_project(actor=owner, project_id=project.id, patch=patch)

    assert _field_code(caught.value, field) == "required_for_activation"
    project.refresh_from_db()
    assert project.description == "Plan"
    assert project.investment_amount == Decimal("10.00")
    assert project.status == Project.Status.ACTIVE


@pytest.mark.django_db
def test_idempotent_lifecycle_and_reactivation_record_fresh_timestamp() -> None:
    owner = User.objects.create_user(email="lifecycle@example.com", password="test-password")
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    project = create_project(
        actor=owner,
        data={"title": "Ready", "description": "Plan", "investment_amount": Decimal("10.00")},
    )

    first_active = activate_project(actor=owner, project_id=project.id)
    repeated_active = activate_project(actor=owner, project_id=project.id)
    assert first_active.activated_at is not None
    assert repeated_active.activated_at == first_active.activated_at
    first_draft = deactivate_project(actor=owner, project_id=project.id)
    repeated_draft = deactivate_project(actor=owner, project_id=project.id)
    assert repeated_draft.activated_at is None
    assert repeated_draft.updated_at == first_draft.updated_at
    reactivated = activate_project(actor=owner, project_id=project.id)

    assert reactivated.status == Project.Status.ACTIVE
    assert reactivated.activated_at is not None
    assert reactivated.activated_at > first_active.activated_at


@pytest.mark.django_db
def test_patch_distinguishes_omitted_values_from_explicit_blank_and_null() -> None:
    owner = User.objects.create_user(email="patch-values@example.com", password="test-password")
    project = create_project(
        actor=owner,
        data={"title": "Draft", "description": "Existing", "investment_amount": Decimal("20.00")},
    )

    unchanged = update_project(actor=owner, project_id=project.id, patch={"title": "Updated"})
    assert unchanged.description == "Existing"
    assert unchanged.investment_amount == Decimal("20.00")
    cleared = update_project(
        actor=owner,
        project_id=project.id,
        patch={"description": "", "investment_amount": None},
    )
    assert cleared.description == ""
    assert cleared.investment_amount is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("data", "field", "code"),
    [
        ({"title": "x" * 201}, "title", "max_length"),
        ({"title": "Valid", "description": "x" * 5001}, "description", "max_length"),
        ({"title": "Valid", "investment_amount": ""}, "investment_amount", "invalid"),
        ({"title": "Valid", "investment_amount": Decimal("0")}, "investment_amount", "min_value"),
        ({"title": "Valid", "investment_amount": Decimal("-1")}, "investment_amount", "min_value"),
        (
            {"title": "Valid", "investment_amount": Decimal("1.001")},
            "investment_amount",
            "max_decimal_places",
        ),
        (
            {"title": "Valid", "investment_amount": Decimal("1000000000000000000.00")},
            "investment_amount",
            "max_digits",
        ),
        (
            {"title": "Valid", "investment_amount": Decimal("1E+19")},
            "investment_amount",
            "max_digits",
        ),
    ],
)
def test_create_validates_project_field_boundaries(
    data: dict[str, str | Decimal], field: str, code: str
) -> None:
    owner = User.objects.create_user(
        email=f"boundary-{field}-{code}@example.com", password="test-password"
    )

    with pytest.raises(ProjectValidationError) as caught:
        create_project(actor=owner, data=data)  # type: ignore[arg-type]

    assert _field_code(caught.value, field) == code
    assert Project.objects.filter(owner=owner).count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("title", ["x" * 200, " x "])
def test_create_accepts_trimmed_titles_at_valid_boundary(title: str) -> None:
    owner = User.objects.create_user(
        email=f"valid-title-{len(title)}-{title[0]}@example.com", password="test-password"
    )

    project = create_project(actor=owner, data={"title": title})

    assert len(project.title) <= 200
    assert project.title == title.strip()


@pytest.mark.django_db
@pytest.mark.parametrize("description", ["x" * 5000, "x" * 4998 + "  "])
def test_create_accepts_description_at_valid_length_boundary(description: str) -> None:
    owner = User.objects.create_user(
        email=f"valid-description-{len(description)}@example.com", password="test-password"
    )

    project = create_project(actor=owner, data={"title": "Valid", "description": description})

    assert len(project.description) <= 5000
