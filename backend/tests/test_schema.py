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


def test_project_openapi_contracts(api_client: APIClient) -> None:
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
    schema = response.json()
    paths = schema["paths"]
    expected_methods = {
        "/api/projects/": {"get", "post"},
        "/api/projects/{id}/": {"get", "patch"},
        "/api/projects/{id}/activate/": {"post"},
        "/api/projects/{id}/deactivate/": {"post"},
    }
    expected_responses = {
        ("/api/projects/", "get"): {"200", "401"},
        ("/api/projects/", "post"): {"201", "400", "401", "403"},
        ("/api/projects/{id}/", "get"): {"200", "401", "404"},
        ("/api/projects/{id}/", "patch"): {"200", "400", "401", "403", "404"},
        ("/api/projects/{id}/activate/", "post"): {"200", "400", "401", "403", "404"},
        ("/api/projects/{id}/deactivate/", "post"): {"200", "401", "403", "404"},
    }

    for path, methods in expected_methods.items():
        assert set(paths[path]) == methods
        for method, operation in paths[path].items():
            assert "delete" not in operation
            assert set(operation["responses"]) == expected_responses[(path, method)]
            for status_code in ("400", "401", "403", "404"):
                if status_code in operation["responses"]:
                    error_schema = operation["responses"][status_code]["content"][
                        "application/json"
                    ]["schema"]
                    assert error_schema == {"$ref": "#/components/schemas/ErrorEnvelope"}
            if method in {"post", "patch"}:
                parameters = operation["parameters"]
                assert any(parameter["name"] == "X-CSRFToken" for parameter in parameters)

    assert "delete" not in paths["/api/projects/{id}/"]
    assert paths["/api/projects/"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ProjectListEnvelope"}
    assert paths["/api/projects/"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ProjectWriteRequest"}
    assert paths["/api/projects/"]["post"]["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/Project"}
    detail = paths["/api/projects/{id}/"]
    assert any(
        parameter["name"] == "id" and parameter["in"] == "path"
        for parameter in detail["get"]["parameters"]
    )
    assert detail["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Project"
    }
    assert detail["patch"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PatchedProjectWriteRequest"
    }
    for path in ("/api/projects/{id}/activate/", "/api/projects/{id}/deactivate/"):
        operation = paths[path]["post"]
        assert "requestBody" not in operation
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/Project"
        }

    assert {
        "Project",
        "ProjectWriteRequest",
        "PatchedProjectWriteRequest",
        "ProjectListEnvelope",
    }.issubset(schema["components"]["schemas"])
    create_request = schema["components"]["schemas"]["ProjectWriteRequest"]
    patch_request = schema["components"]["schemas"]["PatchedProjectWriteRequest"]
    assert set(create_request.get("required", [])) == {"title"}
    assert not patch_request.get("required", [])
    assert create_request["properties"]["currency"]["default"] == "KZT"
    assert patch_request["properties"]["currency"]["default"] == "KZT"
    project_properties = schema["components"]["schemas"]["Project"]["properties"]
    assert "owner" not in project_properties
    assert all(property_schema.get("readOnly") for property_schema in project_properties.values())
    error_code_schema = schema["components"]["schemas"]["ErrorDetail"]["properties"]["code"]
    error_code_component = error_code_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    error_codes = schema["components"]["schemas"][error_code_component]["enum"]
    assert {"not_found", "method_not_allowed"}.issubset(error_codes)
