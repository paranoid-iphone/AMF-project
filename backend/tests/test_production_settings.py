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
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.example.com",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "smtp-user",
    "EMAIL_HOST_PASSWORD": "smtp-password-with-high-entropy",
    "EMAIL_USE_TLS": "true",
    "EMAIL_USE_SSL": "false",
    "EMAIL_TIMEOUT": "10",
    "DEFAULT_FROM_EMAIL": "AMF <no-reply@example.com>",
    "PUBLIC_APP_URL": "https://app.example.com",
    "AUTH_RATE_LIMIT_HMAC_KEY": "production-rate-limit-hmac-key-with-enough-entropy",
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
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_HOST": "smtp.example.com",
            "EMAIL_PORT": "587",
            "EMAIL_HOST_USER": "smtp-user",
            "EMAIL_HOST_PASSWORD": "smtp-password-with-high-entropy",
            "EMAIL_USE_TLS": "true",
            "EMAIL_USE_SSL": "false",
            "EMAIL_TIMEOUT": "10",
            "DEFAULT_FROM_EMAIL": "AMF <no-reply@example.com>",
            "PUBLIC_APP_URL": "https://app.example.com",
            "AUTH_RATE_LIMIT_HMAC_KEY": "production-rate-limit-hmac-key-with-enough-entropy",
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


def test_production_rejects_unsafe_email_backend() -> None:
    result = run_settings({"EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"})

    assert_configuration_rejected(result, "must deliver transactional email")


def test_production_rejects_local_email_host() -> None:
    result = run_settings({"EMAIL_HOST": "mailpit"})

    assert_configuration_rejected(result, "must not use a local development host")


def test_production_rejects_non_https_public_url() -> None:
    result = run_settings({"PUBLIC_APP_URL": "http://app.example.com"})

    assert_configuration_rejected(result, "PUBLIC_APP_URL must use HTTPS")


def test_production_rejects_missing_transactional_email_settings() -> None:
    result = run_settings(remove=("EMAIL_HOST",))

    assert_configuration_rejected(result, "Explicit production email settings are required")


def test_production_rejects_plaintext_smtp() -> None:
    result = run_settings({"EMAIL_USE_TLS": "false", "EMAIL_USE_SSL": "false"})

    assert_configuration_rejected(result, "exactly one")


def test_production_rejects_simultaneous_tls_and_ssl() -> None:
    result = run_settings({"EMAIL_USE_TLS": "true", "EMAIL_USE_SSL": "true"})

    assert_configuration_rejected(result, "exactly one")


def test_production_requires_explicit_smtp_credentials() -> None:
    result = run_settings(remove=("EMAIL_HOST_PASSWORD",))

    assert_configuration_rejected(result, "Explicit production email settings are required")


def test_production_rejects_weak_rate_limit_hmac_key() -> None:
    result = run_settings({"AUTH_RATE_LIMIT_HMAC_KEY": "unsafe-local-rate-limit-key"})

    assert_configuration_rejected(result, "independent high-entropy")


def test_production_rejects_rate_limit_key_equal_to_django_secret() -> None:
    result = run_settings({"AUTH_RATE_LIMIT_HMAC_KEY": PRODUCTION_ENV["DJANGO_SECRET_KEY"]})

    assert_configuration_rejected(result, "independent high-entropy")


def test_production_rejects_low_diversity_rate_limit_hmac_key() -> None:
    result = run_settings({"AUTH_RATE_LIMIT_HMAC_KEY": "a" * 64})

    assert_configuration_rejected(result, "independent high-entropy")


def test_production_rejects_local_development_csrf_trusted_origins() -> None:
    result = run_settings(
        {"DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173"}
    )

    assert_configuration_rejected(result, "must not include local development origins")
