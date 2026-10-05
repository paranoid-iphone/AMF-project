import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def local_email_backend(settings):  # type: ignore[no-untyped-def]
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "AMF <no-reply@example.test>"
    settings.PUBLIC_APP_URL = "http://testserver"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def csrf_api_client() -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/auth/session/")
    assert response.status_code == 200
    token = client.cookies["csrftoken"].value
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client
