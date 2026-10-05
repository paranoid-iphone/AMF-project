from typing import Any, cast
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from projects.models import Project


def _valid_project_payload(**overrides: object) -> dict[str, object]:
    return {
        "title": "Solar project",
        "description": "A regional solar facility.",
        "investment_amount": "100.00",
        **overrides,
    }


def _create_project(client: APIClient, **overrides: object) -> dict[str, object]:
    response = client.post("/api/projects/", _valid_project_payload(**overrides), format="json")
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.django_db
def test_project_endpoints_require_authentication(api_client: APIClient) -> None:
    project_id = uuid4()

    responses = [
        api_client.get("/api/projects/"),
        api_client.post("/api/projects/", {"title": "Draft"}, format="json"),
        api_client.get(f"/api/projects/{project_id}/"),
        api_client.patch(f"/api/projects/{project_id}/", {"title": "Changed"}, format="json"),
        api_client.post(f"/api/projects/{project_id}/activate/", format="json"),
        api_client.post(f"/api/projects/{project_id}/deactivate/", format="json"),
    ]

    assert [response.status_code for response in responses] == [401] * 6
    assert all(response.json()["error"]["code"] == "not_authenticated" for response in responses)


@pytest.mark.django_db
def test_project_create_rejects_requests_without_csrf() -> None:
    client = APIClient(enforce_csrf_checks=True)
    user = User.objects.create_user(email="csrf-project@example.com", password="test-password")
    client.force_login(user)

    response = client.post("/api/projects/", {"title": "Draft"}, format="json")

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "csrf_failed", "message": "CSRF validation failed."}
    }


@pytest.mark.django_db
def test_project_list_is_owner_scoped_and_uses_envelope_and_default_order(
    api_client: APIClient,
) -> None:
    owner = User.objects.create_user(email="list-owner@example.com", password="test-password")
    other = User.objects.create_user(email="list-other@example.com", password="test-password")
    api_client.force_login(owner)
    first = _create_project(api_client, title="First")
    second = _create_project(api_client, title="Second")
    Project.objects.create(owner=other, title="Private to other")

    response = api_client.get("/api/projects/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["projects"]] == [second["id"], first["id"]]


@pytest.mark.django_db
def test_project_list_returns_empty_envelope(api_client: APIClient) -> None:
    user = User.objects.create_user(email="empty-list@example.com", password="test-password")
    api_client.force_login(user)

    response = api_client.get("/api/projects/")

    assert response.status_code == 200
    assert response.json() == {"projects": []}


@pytest.mark.django_db
def test_project_create_defaults_to_kzt_and_retrieve_returns_canonical_representation(
    api_client: APIClient,
) -> None:
    owner = User.objects.create_user(email="create-api@example.com", password="test-password")
    api_client.force_login(owner)

    response = api_client.post("/api/projects/", {"title": "  Solar project  "}, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Solar project"
    assert body["description"] == ""
    assert body["investment_amount"] is None
    assert body["currency"] == "KZT"
    assert body["status"] == "draft"
    assert "owner" not in body
    project = Project.objects.get(pk=body["id"])
    assert project.owner == owner

    retrieved = api_client.get(f"/api/projects/{project.pk}/")
    assert retrieved.status_code == 200
    assert retrieved.json() == body


@pytest.mark.django_db
def test_project_patch_is_partial_and_preserves_omitted_values(api_client: APIClient) -> None:
    owner = User.objects.create_user(email="patch-api@example.com", password="test-password")
    api_client.force_login(owner)
    project = _create_project(api_client, currency="EUR")

    response = api_client.patch(
        f"/api/projects/{project['id']}/", {"title": " Revised "}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Revised"
    assert response.json()["description"] == "A regional solar facility."
    assert response.json()["investment_amount"] == "100.00"
    assert response.json()["currency"] == "EUR"


@pytest.mark.parametrize(
    "field",
    ["id", "owner", "status", "created_at", "updated_at", "activated_at", "extra"],
)
@pytest.mark.django_db
def test_project_create_rejects_read_only_and_unknown_keys(
    api_client: APIClient, field: str
) -> None:
    user = User.objects.create_user(email=f"reject-{field}@example.com", password="test-password")
    api_client.force_login(user)
    payload: dict[str, object] = {"title": "Project", field: "attempted"}

    response = api_client.post("/api/projects/", payload, format="json")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert field in error["fields"]
    expected_code = (
        "read_only"
        if field
        in {
            "id",
            "owner",
            "status",
            "created_at",
            "updated_at",
            "activated_at",
        }
        else "unknown"
    )
    assert error["fields"][field][0]["code"] == expected_code


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"title": "Project", "description": "x" * 5001}, "description"),
        ({"title": "Project", "investment_amount": "0"}, "investment_amount"),
        ({"title": "Project", "investment_amount": "-1"}, "investment_amount"),
        ({"title": "Project", "investment_amount": "1.001"}, "investment_amount"),
        ({"title": "Project", "investment_amount": "1000000000000000000.00"}, "investment_amount"),
        ({"title": "Project", "currency": "GBP"}, "currency"),
    ],
)
@pytest.mark.django_db
def test_project_create_returns_stable_field_validation_errors(
    api_client: APIClient, payload: dict[str, object], field: str
) -> None:
    user = User.objects.create_user(email=f"invalid-{field}@example.com", password="test-password")
    api_client.force_login(user)

    response = api_client.post("/api/projects/", payload, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "Request validation failed."
    assert response.json()["error"]["fields"][field]
    assert Project.objects.filter(owner=user).count() == 0


@pytest.mark.parametrize("field,value", [("description", ""), ("investment_amount", None)])
@pytest.mark.django_db
def test_project_draft_patch_accepts_explicit_blank_or_null(
    api_client: APIClient, field: str, value: object
) -> None:
    owner = User.objects.create_user(email=f"clear-{field}@example.com", password="test-password")
    api_client.force_login(owner)
    project = _create_project(api_client)

    response = api_client.patch(f"/api/projects/{project['id']}/", {field: value}, format="json")

    assert response.status_code == 200
    assert response.json()[field] == value


@pytest.mark.django_db
def test_project_active_edit_rejects_invalid_result_without_mutation(api_client: APIClient) -> None:
    owner = User.objects.create_user(email="active-api@example.com", password="test-password")
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    api_client.force_login(owner)
    project = _create_project(api_client)
    activated = api_client.post(f"/api/projects/{project['id']}/activate/", format="json")
    assert activated.status_code == 200

    response = api_client.patch(
        f"/api/projects/{project['id']}/", {"description": ""}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["fields"]["description"][0]["code"] == "required_for_activation"
    saved = Project.objects.get(pk=cast(str, project["id"]))
    assert saved.description == "A regional solar facility."
    assert saved.status == Project.Status.ACTIVE


@pytest.mark.django_db
def test_project_activation_and_deactivation_are_idempotent(api_client: APIClient) -> None:
    owner = User.objects.create_user(email="lifecycle-api@example.com", password="test-password")
    owner.email_verified_at = timezone.now()
    owner.save(update_fields=("email_verified_at",))
    api_client.force_login(owner)
    project = _create_project(api_client)
    endpoint = f"/api/projects/{project['id']}"

    active = api_client.post(f"{endpoint}/activate/", format="json")
    repeated_active = api_client.post(f"{endpoint}/activate/", format="json")
    assert active.status_code == repeated_active.status_code == 200
    assert active.json()["status"] == repeated_active.json()["status"] == "active"
    assert active.json()["activated_at"] == repeated_active.json()["activated_at"]

    draft = api_client.post(f"{endpoint}/deactivate/", format="json")
    repeated_draft = api_client.post(f"{endpoint}/deactivate/", format="json")
    assert draft.status_code == repeated_draft.status_code == 200
    assert repeated_draft.json()["status"] == "draft"
    assert repeated_draft.json()["activated_at"] is None


@pytest.mark.django_db
def test_unverified_user_gets_exact_activation_error(api_client: APIClient) -> None:
    user = User.objects.create_user(email="unverified-api@example.com", password="test-password")
    api_client.force_login(user)
    project = _create_project(api_client)

    response = api_client.post(f"/api/projects/{project['id']}/activate/", format="json")

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "email_verification_required",
            "message": "Email verification is required.",
        }
    }


@pytest.mark.parametrize("operation", ["get", "patch", "activate", "deactivate"])
@pytest.mark.django_db
def test_missing_and_foreign_project_ids_have_identical_not_found_responses(
    api_client: APIClient, operation: str
) -> None:
    owner = User.objects.create_user(email="private-owner@example.com", password="test-password")
    reader = User.objects.create_user(email="private-reader@example.com", password="test-password")
    project = Project.objects.create(owner=owner, title="Private")
    api_client.force_login(reader)
    missing = str(uuid4())
    foreign = str(project.pk)

    def call(project_id: str) -> Any:
        route = f"/api/projects/{project_id}"
        if operation == "get":
            return api_client.get(f"{route}/")
        if operation == "patch":
            return api_client.patch(f"{route}/", {"title": "Probe"}, format="json")
        return api_client.post(f"{route}/{operation}/", format="json")

    missing_response = call(missing)
    foreign_response = call(foreign)

    expected = {"error": {"code": "not_found", "message": "Project not found."}}
    assert missing_response.status_code == foreign_response.status_code == 404
    assert missing_response.json() == foreign_response.json() == expected


@pytest.mark.parametrize("operation", ["get", "patch", "activate", "deactivate"])
@pytest.mark.django_db
def test_malformed_project_ids_use_stable_not_found_envelope(
    api_client: APIClient, operation: str
) -> None:
    user = User.objects.create_user(email="malformed-id@example.com", password="test-password")
    api_client.force_login(user)
    route = "/api/projects/not-a-uuid"
    if operation == "get":
        response = api_client.get(f"{route}/")
    elif operation == "patch":
        response = api_client.patch(f"{route}/", {"title": "Probe"}, format="json")
    else:
        response = api_client.post(f"{route}/{operation}/", format="json")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Project not found."}}


@pytest.mark.django_db
def test_project_delete_returns_stable_method_not_allowed(api_client: APIClient) -> None:
    user = User.objects.create_user(email="delete-method@example.com", password="test-password")
    api_client.force_login(user)
    project = _create_project(api_client)

    response = api_client.delete(f"/api/projects/{project['id']}/")

    assert response.status_code == 405
    assert response.json() == {
        "error": {"code": "method_not_allowed", "message": "Method not allowed."}
    }
