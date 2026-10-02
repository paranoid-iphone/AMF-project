from django.urls import reverse
from rest_framework.test import APIClient


def test_schema_is_available(api_client: APIClient) -> None:
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/health/" in schema["paths"]
    success_schema = schema["paths"]["/api/health/"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert success_schema == {"$ref": "#/components/schemas/Health"}
