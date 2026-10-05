import uuid
from datetime import timedelta

import pytest
from django.contrib import admin
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from projects.models import Project


@pytest.mark.django_db
def test_project_defaults_to_private_draft_with_uuid_and_kzt() -> None:
    owner = User.objects.create_user(email="project-owner@example.com", password="test-password")

    project = Project.objects.create(owner=owner, title="Solar project")

    assert isinstance(project.id, uuid.UUID)
    assert project.owner_id == owner.pk
    assert project.status == Project.Status.DRAFT
    assert project.currency == Project.Currency.KZT
    assert project.description == ""
    assert project.investment_amount is None
    assert project.activated_at is None


@pytest.mark.django_db
def test_project_fields_keep_protected_ownership_and_spec_limits() -> None:
    owner_field = Project._meta.get_field("owner")
    assert owner_field.remote_field.on_delete is pytest.importorskip("django.db.models").PROTECT
    assert owner_field.remote_field.related_name == "projects"
    assert Project._meta.get_field("title").max_length == 200
    assert Project._meta.get_field("description").max_length == 5000


@pytest.mark.django_db
def test_project_ordering_is_newest_update_then_creation() -> None:
    owner = User.objects.create_user(email="ordering@example.com", password="test-password")
    older = Project.objects.create(owner=owner, title="Older")
    newer = Project.objects.create(owner=owner, title="Newer")
    Project.objects.filter(pk=older.pk).update(updated_at=timezone.now() + timedelta(days=1))

    assert list(Project.objects.values_list("pk", flat=True)) == [older.pk, newer.pk]


@pytest.mark.django_db
def test_duplicate_project_titles_are_allowed_for_same_owner() -> None:
    owner = User.objects.create_user(email="duplicate@example.com", password="test-password")

    Project.objects.create(owner=owner, title="Same title")
    Project.objects.create(owner=owner, title="Same title")

    assert Project.objects.filter(owner=owner, title="Same title").count() == 2


@pytest.mark.django_db
def test_database_rejects_non_positive_project_amount() -> None:
    owner = User.objects.create_user(email="amount@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.create(owner=owner, title="Invalid amount", investment_amount="0.00")


@pytest.mark.django_db
def test_database_rejects_unsupported_project_currency() -> None:
    owner = User.objects.create_user(email="currency@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.create(owner=owner, title="Invalid currency", currency="GBP")


@pytest.mark.django_db
def test_database_requires_activation_timestamp_to_match_status() -> None:
    owner = User.objects.create_user(email="status@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.create(
            owner=owner,
            title="Inconsistent project",
            status=Project.Status.ACTIVE,
            activated_at=None,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Project.objects.create(
            owner=owner,
            title="Draft with activation timestamp",
            status=Project.Status.DRAFT,
            activated_at=timezone.now(),
        )


def test_project_is_not_registered_in_django_admin() -> None:
    assert Project not in admin.site._registry
