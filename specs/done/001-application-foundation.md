# 001 — Application foundation

## Status

Completed and independently verified on 2026-10-02. Approved architecture: React/TypeScript/Vite SPA plus Django/DRF modular monolith, Django ORM, PostgreSQL, and local Docker Compose.

## Goal

Create the smallest runnable full-stack foundation on which authentication and the manual SPV assessment can be implemented without replacing the frontend/backend boundary, auth owner, database, or API contract tooling.

The completed slice must prove:

```text
Docker Compose starts PostgreSQL, Django, and React
→ Django connects to PostgreSQL
→ React calls a typed Django health endpoint through /api
→ OpenAPI generates frontend types
→ backend and frontend quality gates pass
```

## Scope

### Repository layout

```text
backend/                 Django backend
frontend/                React/Vite frontend
compose.yaml             local development services
.env.example             non-secret configuration template
```

Existing `docs/`, `specs/`, `.kilo/`, and workflow files remain intact.

### Backend foundation

- Current supported Django LTS.
- Django REST Framework.
- `drf-spectacular` OpenAPI generation.
- Django ORM with PostgreSQL only; SQLite is not an application runtime database.
- A custom email-first User model exists from the first migration:
  - email is unique and the login identifier;
  - no required username field;
  - no registration/login API is included yet.
- Initial logical apps are limited to what foundation needs, such as `accounts` and a small API/core module. Do not create empty apps for every future domain.
- `GET /api/health/` returns HTTP 200 and a stable JSON contract when application and database are available:

```json
{
  "status": "ok",
  "database": "ok"
}
```

- Database failure produces a non-2xx readiness response without exposing credentials or internal exception details.
- OpenAPI schema is available at `/api/schema/`; interactive API documentation may be exposed at `/api/docs/` in development.
- Session authentication and CSRF middleware are enabled as the browser-auth foundation. No JWT/localStorage auth is introduced.
- Configuration is environment-driven with safe development defaults and fail-safe production settings.
- Console logging is configured without sensitive values.

### Frontend foundation

- React + TypeScript + Vite.
- React Router application shell.
- TanStack Query provider.
- Tailwind CSS and shadcn-compatible component configuration.
- A small accessible home/status page that:
  - identifies the AMF application;
  - calls `/api/health/` through the typed API layer;
  - shows loading, success, and failure states;
  - does not include mock product data or business features.
- Vite development server proxies `/api` to Django so browser requests use a same-origin path and do not require broad CORS rules.
- Frontend API types are generated from Django OpenAPI. Use a reproducible script based on `openapi-typescript`; use `openapi-fetch` or an equivalently small typed transport rather than handwritten duplicate response interfaces.
- Generated artifacts are never edited manually.

### Local development and build

- Docker Compose provides:
  - PostgreSQL;
  - Django development service;
  - Vite development service.
- Service readiness/health checks are defined where practical.
- Backend and frontend use lock files.
- `.env.example` contains names and safe example values only; no credential or API secret is committed.
- The root README documents exact setup, start, stop, migration, test, lint, typecheck, contract-generation, and build commands.
- Production topology is documented as same-origin routing (`/` to built SPA, `/api/` to Django), but production cloud deployment is not implemented in this slice.

### Quality gates

Backend:

- Django system check;
- migration consistency check;
- Ruff lint/format check;
- pytest with pytest-django;
- static type checking using mypy/django-stubs or an explicitly documented equivalent.

Frontend:

- ESLint;
- TypeScript no-emit check;
- Vitest + React Testing Library;
- production Vite build.

Contract:

- Django OpenAPI schema validates;
- frontend types can be regenerated from it deterministically;
- a test or CI-friendly check detects stale generated API types.

## Architecture rules

- Django owns authoritative validation, users, sessions, permissions, and database writes.
- React owns presentation and UX state only.
- No business/scoring logic is added in this slice.
- No generic repository, CQRS, event bus, microservice, Redis, Celery, or speculative abstraction is introduced.
- Future business logic will follow `API → application service → domain logic → Django ORM/integration adapters`.
- Long-running operations will use persistent workers later; no in-process fire-and-forget background task is added now.

## API contract

### `GET /api/health/`

Successful response:

```json
{
  "status": "ok",
  "database": "ok"
}
```

Properties are required strings. Additional undocumented business fields are not added.

The endpoint is unauthenticated and contains no deployment version, hostname, environment value, database identifier, or secret.

## Data model

Only the custom User model is required in this slice. Product, questionnaire, scoring, evidence, risk, document, review, and audit tables are explicitly deferred to their feature specifications.

## Security requirements

- Secret key and database credentials come from environment variables.
- Production configuration must not silently run with debug enabled or an insecure default secret.
- Session cookies have production-safe settings controlled by environment.
- CSRF protection remains enabled.
- No wildcard production CORS policy.
- Health errors do not return stack traces or database connection details.
- Dependencies and generated files contain no secrets.

## Non-goals

- registration, login, logout, verification, or password reset UI/API;
- project CRUD;
- questionnaires or scoring;
- Project IRR;
- AI, documents, object storage, or background worker;
- Admin product workflow;
- Telegram bot or Mini App;
- public landing/SEO site;
- cloud infrastructure or production deployment;
- final visual design system beyond a clean accessible foundation.

## Acceptance criteria

1. Repository contains the approved `backend/`, `frontend/`, and local Compose structure without deleting planning/workflow files.
2. PostgreSQL is the configured application database and Django migrations apply successfully.
3. The first migration creates an email-first custom User model; the project does not depend on Django's default username-based User.
4. `GET /api/health/` returns the exact success contract and verifies database readiness.
5. The React status page consumes the endpoint through OpenAPI-generated types and visibly handles loading, success, and failure.
6. Vite proxies `/api` in development; broad wildcard CORS is not used as a workaround.
7. OpenAPI schema generation and frontend type regeneration are documented and reproducible.
8. Backend checks, lint, typecheck, tests, and migration consistency checks pass.
9. Frontend lint, typecheck, tests, and production build pass.
10. Docker Compose configuration validates and, when Docker is available, all three services start and the browser-facing integration works.
11. No secrets, production data, or unrelated feature code are introduced.
12. README commands are sufficient for a new developer to run and verify the foundation.

## Verification plan

Run the repository-documented equivalents of:

```text
docker compose config
docker compose up --build -d
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
backend lint / format-check / typecheck / pytest
frontend lint / typecheck / test / build
OpenAPI validation and generated-type freshness check
HTTP health check through the frontend development origin
browser check of loading, healthy, and backend-unavailable states
docker compose down
```

If Docker or browser tooling is unavailable, Verifier must report those checks as `NOT VERIFIED`, not silently replace them with weaker claims.

## Implementation task boundaries

### Backend worker

- implement backend, PostgreSQL configuration, custom User, health/OpenAPI contracts, backend quality tooling, and root local infrastructure;
- do not implement product features or frontend application code;
- leave a clear integration contract for the frontend worker.

### Frontend worker

- implement the React/Vite application shell, typed health integration, frontend quality tooling, and complete frontend-related Compose/docs integration;
- do not add authentication or product screens.

### Verifier

- verify every acceptance criterion, including real integration and browser behavior when available.

### Reviewer

- review the final combined diff for security, unnecessary complexity, architecture drift, missing reproducibility, and accidental scope expansion.
