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


def test_authentication_openapi_contracts(api_client: APIClient) -> None:
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
    schema = response.json()
    auth_paths = {
        "/api/auth/session/": "get",
        "/api/auth/register/": "post",
        "/api/auth/login/": "post",
        "/api/auth/logout/": "post",
        "/api/auth/email-verification/request/": "post",
        "/api/auth/email-verification/confirm/": "post",
        "/api/auth/password-reset/request/": "post",
        "/api/auth/password-reset/confirm/": "post",
    }

    for path, method in auth_paths.items():
        assert method in schema["paths"][path]
        if method == "post":
            parameters = schema["paths"][path][method]["parameters"]
            assert any(parameter["name"] == "X-CSRFToken" for parameter in parameters)

    register_responses = schema["paths"]["/api/auth/register/"]["post"]["responses"]
    assert {"201", "400", "403", "429"}.issubset(register_responses)
    verify_responses = schema["paths"]["/api/auth/email-verification/confirm/"]["post"]["responses"]
    assert {"200", "400", "403", "429"}.issubset(verify_responses)
    assert schema["components"]["securitySchemes"]["cookieAuth"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "sessionid",
    }
