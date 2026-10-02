# AMF backend

Django 5.2 LTS API using Django REST Framework, drf-spectacular, Django ORM, and PostgreSQL. The backend intentionally contains only the application foundation: the custom email-first user model and readiness/schema endpoints.

## Local environment

Install Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/), then run:

```bash
cd backend
uv sync --all-groups
```

Django reads PostgreSQL and security settings from the environment documented in the root `.env.example`. SQLite is not supported as an application or test database.

## Commands

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

`schema.yaml` is a local generated artifact and is ignored. The authoritative schema is also served at `GET /api/schema/`; Swagger UI is served at `GET /api/docs/` only while `DJANGO_DEBUG=true`.

## API foundation contract

`GET /api/health/` is unauthenticated. It executes `SELECT 1` against the configured database. Success is exactly:

```json
{"status": "ok", "database": "ok"}
```

A database error returns HTTP 503 and a stable non-sensitive body:

```json
{"status": "unavailable", "database": "unavailable"}
```

All future browser authentication is expected to use Django sessions and CSRF protection. No registration, login, or token API is included in this slice.
## Email identity policy

`accounts.User.email` is the login identity. All application saves strip surrounding whitespace and lowercase the complete address before persistence. PostgreSQL adds a lowercase check constraint and a functional unique constraint on `LOWER(email)`, so direct or bulk database writes cannot create differently-cased identities. The migration refuses to continue if pre-existing rows collapse to the same canonical address. The policy intentionally does not remove dots or plus tags because those rules are provider-specific.

## Production configuration

Local defaults apply only to `DJANGO_ENVIRONMENT=development`. Production must explicitly provide:

- `DJANGO_ENVIRONMENT=production` and `DJANGO_DEBUG=false`;
- a non-development `DJANGO_SECRET_KEY` containing at least 50 characters;
- non-local `DJANGO_ALLOWED_HOSTS`;
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`.

Django rejects the values from `.env.example` in production mode. Secure cookies, HTTPS redirect, and one year of HSTS default on in production. HSTS subdomain coverage and browser preload remain off unless explicitly enabled through `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` and `DJANGO_SECURE_HSTS_PRELOAD` after the deployment is ready for their long-lived scope.