from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_returns_exact_success_contract(api_client: APIClient) -> None:
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_hides_database_error_details(api_client: APIClient) -> None:
    with patch("core.views.connection.cursor", side_effect=DatabaseError("secret-db-detail")):
        response = api_client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert "secret-db-detail" not in response.content.decode()
