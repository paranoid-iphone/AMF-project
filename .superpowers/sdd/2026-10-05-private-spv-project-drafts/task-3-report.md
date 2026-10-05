# Task 3 — Private project API and OpenAPI

## Result

Implemented owner-scoped project list, create, retrieve, partial update, activate, and deactivate endpoints. All mutations use the Task 2 project services. The response serializer exposes no owner field; request validation explicitly rejects read-only and unknown keys. Malformed, missing, and foreign IDs return the same stable `404 not_found` envelope. Unsupported project methods return stable `405 method_not_allowed`; no DELETE operation is documented.

## TDD evidence

- RED: `docker compose exec -T backend uv run pytest tests/test_projects_api.py -q` — 35 failed because project routes and serializers were not implemented; malformed project paths fell through to Django's HTML 404.
- RED: `docker compose exec -T backend uv run pytest tests/test_schema.py::test_project_openapi_contracts -q` — failed because `/api/projects/` was absent from OpenAPI.
- GREEN: `docker compose exec -T backend uv run pytest tests/test_projects_api.py tests/test_schema.py -q --tb=short` — 38 passed after implementation and final schema assertions.
- Full backend suite: `docker compose exec -T backend uv run pytest -q` — 154 passed.

An intermediate run found a serializer attribute shadowing DRF's internal writable-field iterator and a schema enum component reference assumption. Both were corrected. A later overlapping test invocation also collided on the shared `test_amf` database; subsequent test runs were single-flight and completed cleanly.

## Quality and integration evidence

- Ruff check: passed.
- Ruff format check: passed (68 files already formatted).
- mypy: passed (58 source files).
- Django system check: passed with no issues.
- Migration consistency: `makemigrations --check --dry-run` reported no changes.
- OpenAPI: `manage.py spectacular --file schema.yaml --validate --fail-on-warn` exited successfully without warnings.
- Development migration: `manage.py migrate --noinput` reported no migrations pending.
- Frontend contract: `npm run api:export`, `npm run api:generate`, and `npm run api:check` passed; generated schema and TypeScript types are current.
- `git diff --check`: passed.
- Manager's separate real HTTP integration run passed; evidence is in `integration-report.md`.

## Files

- Added `backend/projects/serializers.py`, `backend/projects/views.py`, and `backend/projects/urls.py`.
- Mounted project routes in `backend/config/urls.py` and documented the new stable error codes in `backend/accounts/serializers.py`.
- Added endpoint coverage in `backend/tests/test_projects_api.py`; pinned the API contract in `backend/tests/test_schema.py`.
- Added the deferred foreign lifecycle lookup-order regression in `backend/tests/test_project_services.py` and the inverse status/timestamp constraint case in `backend/tests/test_project_model.py`.
- Regenerated `frontend/openapi-schema.yaml` and `frontend/src/api/schema.d.ts` through the repository scripts.

## Self-review and concerns

Reads are owner-filtered, and service calls remain responsible for all project writes and lifecycle rules. PATCH uses `partial=True`, preserving omitted values while retaining explicit blank/null values for service validation. Lifecycle endpoints have no OpenAPI request body and every unsafe operation documents `X-CSRFToken`. OpenAPI paths retain `{id}` and contain no DELETE operation.

No known Task 3 contract or privacy concerns remain. The only initial test-run issue was shared test-database contention from overlapping invocations; the final full suite ran once without contention and passed.
