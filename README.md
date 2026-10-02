# AMF application

Foundation for the AMF investment-project assessment web application. The approved architecture is a React/TypeScript/Vite SPA backed by a Django 5.2 LTS + Django REST Framework modular monolith and PostgreSQL.

This slice contains infrastructure only: no authentication flows, projects, scoring, AI, documents, workers, or product administration workflow.

## Repository layout

```text
backend/       Django API, migrations, tests, and Python lock file
frontend/      React/Vite client (maintained by the frontend workstream)
compose.yaml   local PostgreSQL, Django, and Vite services
.env.example   non-secret local configuration template
docs/          product and architecture decisions
specs/         implementation specifications
```

## Prerequisites

- Docker with Docker Compose, or PostgreSQL 17 + Python 3.12/3.13 + uv + Node.js 22.12 or newer + npm
- Copy `.env.example` to `.env` for Compose. Values are intentionally local-only and must not be reused in production.

PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

POSIX shell:

```bash
cp .env.example .env
docker compose up --build -d
```

Open the frontend at <http://localhost:5173>. The backend is available at <http://localhost:8000>, with readiness at `/api/health/`, OpenAPI at `/api/schema/`, and development-only Swagger UI at `/api/docs/`.

Stop local services while retaining the database volume:

```bash
docker compose down
```

Delete local database and dependency volumes as well:

```bash
docker compose down --volumes
```

If port 5432 is already occupied, set `POSTGRES_HOST_PORT=55432` in `.env`; containers continue to use port 5432 internally.

## Database and Django commands

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py check
docker compose exec backend python manage.py createsuperuser
```

The first application migration creates `accounts.User`, whose email field is the login identifier. Application writes trim surrounding whitespace and lowercase the complete address. PostgreSQL enforces both lowercase storage and case-insensitive uniqueness, so `Applicant@Example.com` and `applicant@example.com` are one identity. No provider-specific dot or plus-address rewriting is performed. There is intentionally no required username and no registration/login API yet.

## Backend quality gates

```bash
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend mypy .
docker compose exec backend pytest
docker compose exec backend python manage.py spectacular --file /tmp/schema.yaml --validate --fail-on-warn
```

Equivalent host commands are documented in [`backend/README.md`](backend/README.md). Backend dependencies are declared in `backend/pyproject.toml` and reproducibly locked in `backend/uv.lock`.

## Frontend development and quality gates

Run the client directly from `frontend/`. The default Vite proxy target is `http://localhost:8000`; set `VITE_API_PROXY_TARGET` only when Django is available at another origin.

```bash
cd frontend
npm ci
npm run dev
```

Run the UI-only frontend gates from `frontend/`:

```powershell
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

With the Compose backend running, `npm run verify` is the cross-platform, fail-fast frontend and API-contract gate. It runs the authoritative schema freshness check followed by lint, typecheck, tests, and build without relying on shell-specific command chaining.

The application uses React Router and TanStack Query, and calls `/api/health/` through `openapi-fetch` with types generated in `frontend/src/api/schema.d.ts`. Vite proxies `/api` to Django in development; no CORS workaround is required.

## OpenAPI and generated frontend types

Start the Compose backend, then export its validated schema and regenerate TypeScript. These commands work in Windows PowerShell 5.1 and do not use native-output redirection:

```powershell
docker compose up -d db backend
Push-Location frontend
npm ci
npm run api:export
npm run api:generate
npm run api:check
Pop-Location
```

`api:export` invokes the backend's existing `manage.py spectacular --validate --fail-on-warn` command through Docker Compose and writes UTF-8 directly from Node. `api:check` independently exports Django OpenAPI again, compares it with `frontend/openapi-schema.yaml`, and only then verifies that `frontend/src/api/schema.d.ts` is current. It exits non-zero if either checked-in artifact is stale, including when both frontend artifacts agree with each other but have drifted from Django. Generated API artifacts are never edited manually. `/api/health/` has the exact success response:

```json
{
  "status": "ok",
  "database": "ok"
}
```

A database readiness failure returns HTTP 503 without exception or connection details.

## Compose and complete verification

Windows PowerShell 5.1:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend mypy .
docker compose exec backend pytest
docker compose exec backend python manage.py spectacular --file /tmp/schema.yaml --validate --fail-on-warn
Invoke-RestMethod -Uri http://localhost:5173/api/health/
Push-Location frontend
npm run verify
$frontendExitCode = $LASTEXITCODE
Pop-Location
if ($frontendExitCode -ne 0) { exit $frontendExitCode }
docker compose down
```

## Production boundary

Cloud deployment is outside this slice. Production must use same-origin routing:

```text
/        -> built React SPA
/api/   -> Django REST API
/admin/ -> internal Django Admin
```

Production configuration must set `DJANGO_ENVIRONMENT=production`, `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY` of at least 50 characters, explicit non-local `DJANGO_ALLOWED_HOSTS`, and every `POSTGRES_*` connection setting. Known development secrets, local database credentials, and local Compose hosts are rejected. Changing only `DJANGO_DEBUG` in `.env.example` therefore cannot accidentally start a production-mode service with development defaults.

Production defaults enable secure session/CSRF cookies, HTTPS redirect, and one year of HSTS. HSTS `includeSubDomains` and preload are intentionally off unless `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true` and `DJANGO_SECURE_HSTS_PRELOAD=true` are explicitly set after confirming that every affected hostname is permanently HTTPS-capable. No wildcard CORS policy is configured.

## Development workflow

Specifications in `specs/` are the source of truth. Repository-wide agent and engineering rules remain in [`AGENTS.md`](AGENTS.md); stable architecture decisions remain in [`docs/architecture.md`](docs/architecture.md).