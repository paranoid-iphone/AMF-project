import base64
import hashlib
import hmac
import secrets
import uuid

from django.conf import settings


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def secret_digest(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def digest_matches(secret: str, expected_digest: str) -> bool:
    return hmac.compare_digest(secret_digest(secret), expected_digest)


def identifier_digest(scope: str, identifier: str) -> str:
    material = f"{scope}\x00{identifier}".encode()
    return hmac.new(
        settings.AUTH_RATE_LIMIT_HMAC_KEY.encode(), material, hashlib.sha256
    ).hexdigest()


def parse_selector_token(value: str) -> tuple[uuid.UUID, str] | None:
    try:
        selector_value, secret = value.split(".", 1)
        selector = uuid.UUID(selector_value)
    except (ValueError, AttributeError):
        return None
    if not secret:
        return None
    return selector, secret


def request_correlation_id(value: str | None) -> str:
    if value:
        try:
            return str(uuid.UUID(value.strip()))
        except ValueError:
            pass
    return str(uuid.uuid4())


def client_ip_digest(ip_address: str | None) -> str:
    if not ip_address:
        return ""
    return identifier_digest("client_ip", ip_address)


def derived_token_secret(purpose: str, selector: uuid.UUID) -> str:
    material = f"auth-token:{purpose}:{selector}".encode()
    digest = hmac.new(str(settings.SECRET_KEY).encode(), material, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def credential_state_fingerprint(user: object) -> str:
    password = str(getattr(user, "password", ""))
    last_login = getattr(user, "last_login", None)
    last_login_value = last_login.isoformat() if last_login is not None else ""
    material = "\x00".join(
        (
            str(getattr(user, "pk", "")),
            password,
            last_login_value,
            str(bool(getattr(user, "is_active", False))),
            str(getattr(user, "email", "")),
        )
    ).encode()
    return hmac.new(
        str(settings.SECRET_KEY).encode(),
        b"password-reset-state\x00" + material,
        hashlib.sha256,
    ).hexdigest()
