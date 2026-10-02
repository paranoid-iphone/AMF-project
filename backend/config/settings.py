import os

from django.core.exceptions import ImproperlyConfigured


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value")


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "development").strip().lower()
if ENVIRONMENT not in {"development", "production"}:
    raise ImproperlyConfigured("DJANGO_ENVIRONMENT must be development or production")

DEBUG = env_bool("DJANGO_DEBUG", ENVIRONMENT == "development")
if ENVIRONMENT == "production" and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false when DJANGO_ENVIRONMENT is production")
if not DEBUG and ENVIRONMENT != "production":
    raise ImproperlyConfigured("DJANGO_ENVIRONMENT must be production when DJANGO_DEBUG is false")

DEVELOPMENT_SECRET_KEYS = {
    "unsafe-development-key-do-not-use-in-production",
    "unsafe-local-development-key-do-not-use-in-production",
    "unsafe-local-compose-key-do-not-use-in-production",
    "unsafe-local-example-key-do-not-use-in-production",
}
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production")
    SECRET_KEY = "unsafe-development-key-do-not-use-in-production"
if not DEBUG and (SECRET_KEY in DEVELOPMENT_SECRET_KEYS or SECRET_KEY.startswith("unsafe-")):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not use a known development value")
if not DEBUG and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must contain at least 50 characters in production"
    )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "backend"] if DEBUG else []
)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is required in production")
if not DEBUG and set(ALLOWED_HOSTS) & {"localhost", "127.0.0.1", "backend"}:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must not use the local development hosts in production"
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

DATABASE_ENVIRONMENT_NAMES = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)
if not DEBUG:
    missing_database_settings = [name for name in DATABASE_ENVIRONMENT_NAMES if not os.getenv(name)]
    if missing_database_settings:
        names = ", ".join(missing_database_settings)
        raise ImproperlyConfigured(f"Explicit production database settings are required: {names}")
    if os.getenv("POSTGRES_USER") == "amf":
        raise ImproperlyConfigured("POSTGRES_USER must not use the local development value")
    if os.getenv("POSTGRES_PASSWORD") == "amf-local-only":
        raise ImproperlyConfigured("POSTGRES_PASSWORD must not use the local development value")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "amf"),
        "USER": os.getenv("POSTGRES_USER", "amf"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "amf-local-only"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "0")),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "AMF API",
    "DESCRIPTION": "Application API for AMF.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "{levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
