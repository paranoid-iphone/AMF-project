# AMF backend

Django 5.2 LTS API using Django REST Framework, drf-spectacular, Django ORM, and PostgreSQL. The backend contains the application foundation plus invite-only applicant authentication.

## Local environment

Install Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/), then run:

```bash
cd backend
uv sync --all-groups
```

Django reads PostgreSQL, session, email, and security settings from the environment documented in the root `.env.example`. SQLite is not supported as an application or test database. Docker Compose routes SMTP to Mailpit at `mailpit:1025`; captured messages are visible at <http://localhost:8025>. A separate `auth-email-worker` process claims durable PostgreSQL outbox jobs and performs SMTP delivery outside business transactions.

## Quality commands

Run these from `backend/` with PostgreSQL available:

```bash
uv run python manage.py check
uv run python manage.py migrate
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
uv run python manage.py spectacular --file schema.yaml --validate --fail-on-warn
```

`schema.yaml` is a local generated artifact and is ignored. The authoritative schema is served at `GET /api/schema/`; Swagger UI is served at `GET /api/docs/` only while `DJANGO_DEBUG=true`.

## Local CSRF origins

Compose passes `DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` to the web process because browser `Origin` remains the frontend origin while Vite proxies `/api` with a backend target host. These are explicit development-only origins, not wildcards. Production rejects them and must use only deployment-appropriate HTTPS origins when an explicit trusted origin is needed.

A `csrf_failed` login accompanied by `Origin checking failed` in Django logs means the browser origin is absent from this setting. Recreate the backend service after environment changes. Cookie/header mismatches and origin failures are separate checks; do not work around either by disabling CSRF.
## Foundation contract

`GET /api/health/` remains unauthenticated and executes `SELECT 1`. Success is exactly `{"status":"ok","database":"ok"}`. Database failure returns HTTP 503 with `{"status":"unavailable","database":"unavailable"}` and no connection details.

## Authentication API

The browser uses same-origin Django session cookies and CSRF, not JWT. Start every client session with `GET /api/auth/session/`; it returns anonymous or authenticated state and establishes the readable `csrftoken` cookie. Every unsafe request must send that current value as `X-CSRFToken`.

Endpoints:

```text
GET  /api/auth/session/
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/email-verification/request/
POST /api/auth/email-verification/confirm/
POST /api/auth/password-reset/request/
POST /api/auth/password-reset/confirm/
```

Registration is invitation-only. Unverified applicants may use the private draft workspace, while future submission/review services must call `accounts.guards.require_verified_email`. Invitations and verification tokens store only SHA-256 digests. Rate-limit identifiers and client IPs are HMAC digests stored in PostgreSQL. Material identity changes create append-only `AccountSecurityEvent` rows without passwords, raw tokens, session IDs, or email bodies. Restricted queryset/instance write paths prevent updates or deletes, and protected user/invitation references keep audit retention immutable.

All API failures use a stable `{"error":{"code":"...","message":"..."}}` envelope, optionally with structured field errors. Invitation and credential failures do not reveal account existence.

## Invitation operations

Trusted operators can use the superuser-only Django Admin invitation screen or these commands:

```bash
uv run python manage.py invite_applicant applicant@example.com
uv run python manage.py revoke_invitation <invitation-uuid>
uv run python manage.py cleanup_auth_buckets
uv run python manage.py cleanup_auth_email_outbox
uv run python manage.py process_auth_email_outbox
```

The invitation command commits an outbox job and prints only the selector and canonical recipient, never the raw token. Reissuing for an email is serialized by canonical address, revokes its older pending invitation, and is protected by a PostgreSQL one-pending-invitation constraint. The worker uses row locking with `SKIP LOCKED`, retry backoff, stale-claim recovery, terminal state markers, and deterministic token derivation so raw token secrets are never stored in the outbox.

Email delivery is **at-least-once**, not exactly-once. Normal and concurrent reprocessing skips terminal jobs, while stale leases are deliberately reclaimed. A crash after SMTP accepts a message but before PostgreSQL records `sent_at` can therefore cause a duplicate. Email content and single-use token handlers are designed to remain safe under duplicate delivery.

Password-reset jobs store an HMAC credential-state fingerprint captured at request time. Password, email, activation, or login-state changes before worker processing cause a terminal `credential_state_changed` result without sending. Token derivation mismatches after secret-key rotation terminate with `token_derivation_mismatch`; operators can safely reissue the invitation or verification message.

## Authentication email outbox retention

`AUTH_EMAIL_OUTBOX_RETENTION_SECONDS` controls how long terminal (`sent_at` or `failed_at`) authentication-email jobs remain in PostgreSQL; the default is 2,592,000 seconds (30 days). Run the idempotent cleanup command periodically:

```bash
uv run python manage.py cleanup_auth_email_outbox
```

An explicit one-off override is available as `--retention-seconds`. Pending/retrying/leased jobs are never deleted by this command. Unknown-address reset jobs follow the same terminal retention rule. This is narrowly an authentication-delivery operational metadata policy and does not define or replace future retention/deletion rules for uploaded project documents.

## Email identity policy

`accounts.User.email` is the login identity. Application writes and natural-key lookups strip surrounding whitespace and lowercase the complete address. PostgreSQL enforces lowercase storage and case-insensitive uniqueness. The policy intentionally does not remove dots or plus tags because those rules are provider-specific.

## Production configuration

Local defaults apply only to `DJANGO_ENVIRONMENT=development`. Production must explicitly provide:

- `DJANGO_ENVIRONMENT=production` and `DJANGO_DEBUG=false`;
- a non-development `DJANGO_SECRET_KEY` containing at least 50 characters;
- non-local `DJANGO_ALLOWED_HOSTS`;
- all `POSTGRES_*` connection settings;
- an independent `AUTH_RATE_LIMIT_HMAC_KEY`;
- `PUBLIC_APP_URL` using HTTPS;
- Django SMTP `EMAIL_BACKEND`, non-local `EMAIL_HOST`, `EMAIL_PORT`, explicit `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`, and a non-local `DEFAULT_FROM_EMAIL`;
- exactly one encrypted SMTP mode: `EMAIL_USE_TLS=true` or `EMAIL_USE_SSL=true`, never neither or both.

Production rejects non-SMTP/console/in-memory/file/dummy email backends; plaintext or simultaneously enabled TLS/SSL modes; missing SMTP credentials/settings; Mailpit/localhost SMTP; non-HTTPS public links; and `.local` sender addresses. `AUTH_RATE_LIMIT_HMAC_KEY` must be independent from `DJANGO_SECRET_KEY`, at least 32 characters, diverse, and not a known development value. Secure cookies, HTTPS redirect, and one year of HSTS default on. HSTS subdomain coverage and preload remain explicit opt-ins.

Configurable authentication values include token lifetimes, seven-day rolling session age, and each IP/account/token rate limit. Defaults are defined in `config/settings.py` and match `specs/ready/002-authentication-private-workspace.md`.