import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRODUCTION_ENV = {
    "DJANGO_ENVIRONMENT": "production",
    "DJANGO_DEBUG": "false",
    "DJANGO_SECRET_KEY": "production-test-secret-key-that-is-longer-than-fifty-characters-12345",
    "DJANGO_ALLOWED_HOSTS": "app.example.com",
    "POSTGRES_DB": "amf_production",
    "POSTGRES_USER": "amf_production_user",
    "POSTGRES_PASSWORD": "production-test-password-not-for-real-use",
    "POSTGRES_HOST": "postgres.example.internal",
    "POSTGRES_PORT": "5432",
}


def run_settings(
    overrides: dict[str, str] | None = None, remove: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DJANGO_") and not key.startswith("POSTGRES_")
    }
    environment.update(PRODUCTION_ENV)
    environment.update(overrides or {})
    for name in remove:
        environment.pop(name, None)
    command = [
        sys.executable,
        "-c",
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'debug': s.DEBUG, "
            "'session_secure': s.SESSION_COOKIE_SECURE, "
            "'csrf_secure': s.CSRF_COOKIE_SECURE, "
            "'ssl_redirect': s.SECURE_SSL_REDIRECT, "
            "'hsts_seconds': s.SECURE_HSTS_SECONDS, "
            "'hsts_subdomains': s.SECURE_HSTS_INCLUDE_SUBDOMAINS, "
            "'hsts_preload': s.SECURE_HSTS_PRELOAD"
            "}))"
        ),
    ]
    return subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_configuration_rejected(result: subprocess.CompletedProcess[str], message: str) -> None:
    assert result.returncode != 0
    assert message in result.stderr


def test_effective_local_example_cannot_switch_to_production_by_debug_flag_only() -> None:
    environment = {
        "DJANGO_ENVIRONMENT": "development",
        "DJANGO_SECRET_KEY": "unsafe-local-development-key-do-not-use-in-production",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,backend",
        "POSTGRES_DB": "amf",
        "POSTGRES_USER": "amf",
        "POSTGRES_PASSWORD": "amf-local-only",
    }
    environment.update({"DJANGO_DEBUG": "false", "POSTGRES_HOST": "db", "POSTGRES_PORT": "5432"})

    result = run_settings(environment)

    assert_configuration_rejected(result, "DJANGO_ENVIRONMENT must be production")


def test_effective_compose_defaults_are_rejected_after_production_marker_is_set() -> None:
    environment = {
        "DJANGO_ENVIRONMENT": "development",
        "DJANGO_SECRET_KEY": "unsafe-local-development-key-do-not-use-in-production",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,backend",
        "POSTGRES_DB": "amf",
        "POSTGRES_USER": "amf",
        "POSTGRES_PASSWORD": "amf-local-only",
    }
    environment.update(
        {
            "DJANGO_ENVIRONMENT": "production",
            "DJANGO_DEBUG": "false",
            "POSTGRES_HOST": "db",
            "POSTGRES_PORT": "5432",
        }
    )

    result = run_settings(environment)

    assert_configuration_rejected(result, "known development value")


def test_production_rejects_local_development_allowed_hosts() -> None:
    result = run_settings({"DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,backend"})

    assert_configuration_rejected(result, "local development hosts")


def test_production_rejects_implicit_allowed_hosts() -> None:
    result = run_settings(remove=("DJANGO_ALLOWED_HOSTS",))

    assert_configuration_rejected(result, "DJANGO_ALLOWED_HOSTS is required")


def test_production_rejects_local_database_user() -> None:
    result = run_settings({"POSTGRES_USER": "amf"})

    assert_configuration_rejected(result, "POSTGRES_USER must not use")


def test_production_rejects_local_database_credentials() -> None:
    result = run_settings({"POSTGRES_PASSWORD": "amf-local-only"})

    assert_configuration_rejected(result, "local development value")


def test_production_defaults_are_secure_without_implicit_hsts_scope() -> None:
    result = run_settings()

    assert result.returncode == 0, result.stderr
    settings: dict[str, Any] = json.loads(result.stdout)
    assert settings == {
        "debug": False,
        "session_secure": True,
        "csrf_secure": True,
        "ssl_redirect": True,
        "hsts_seconds": 31536000,
        "hsts_subdomains": False,
        "hsts_preload": False,
    }


def test_hsts_subdomains_and_preload_require_explicit_opt_in() -> None:
    result = run_settings(
        {
            "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
            "DJANGO_SECURE_HSTS_PRELOAD": "true",
        }
    )

    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["hsts_subdomains"] is True
    assert settings["hsts_preload"] is True
