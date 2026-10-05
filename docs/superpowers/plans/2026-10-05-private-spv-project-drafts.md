# Private SPV Project Drafts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an owner-private SPV project workspace where applicants can create and edit drafts, activate complete projects after email verification, and return active projects to draft.

**Architecture:** Add a dedicated Django `projects` application whose service layer owns authorization, transactions, and lifecycle rules; expose it through owner-scoped DRF endpoints and the existing stable error envelope. Generate the OpenAPI contract before implementing a typed React transport and a small set of workspace, create, and edit screens using TanStack Query, React Hook Form, and Zod.

**Tech Stack:** Python 3.12, Django 5.2, Django REST Framework 3.16, PostgreSQL, pytest, Ruff, mypy, drf-spectacular; React 19, TypeScript 5.9, React Router 7, TanStack Query 5, React Hook Form 7, Zod 4, Vitest, React Testing Library, Vite 7.

**Spec:** `specs/done/003-spv-project-drafts.md`

**Completion:** The user reported a satisfactory review and authorized local saving on 2026-10-05. All 17 acceptance criteria passed independent verification. The separate final automated diff review was interrupted without a verdict and is closed by user approval, not represented as a completed technical review.

**Verification adjustment approved by the user:** On 2026-10-05, the manager takes over the remaining command and browser checks to avoid additional handoffs. The independent verifier checks all acceptance criteria against code and the manager's recorded evidence, running targeted checks only where evidence is insufficient. The final diff review remains independent and follows verification.

## Global Constraints

- Projects stay private to their owner; `active` is not public publication.
- Draft creation and editing do not require a verified email; activation does.
- Supported currencies are exactly `KZT`, `USD`, and `EUR`; the default is `KZT`.
- There is no project delete/archive API, Admin registration, public slug, questionnaire, scoring, documents, contacts, phone, Telegram, or notification preferences in this slice.
- The backend never accepts or exposes a writable owner field and returns the same `404` for missing and foreign UUIDs.
- All unsafe endpoints keep the existing session and CSRF protection and all errors use the stable JSON envelope.
- User-facing copy added by this feature is Russian.
- OpenAPI is authoritative; generated frontend schema files are never edited manually.
- Reject unknown and read-only request keys explicitly; DRF's silent ignoring is insufficient.
- Project query keys include authenticated user.id; logout and global 401 cancel and remove all project queries.
- Lifecycle actions operate on saved state and stay disabled while the editor is dirty, with Russian save-first guidance.
- Preserve all unrelated working-tree changes. Do not stage `.kilo/**` or `.serena/**`.
- Backend and frontend production code is delegated: `gpt-6-luna` at high reasoning for implementation; `gpt-5.6-sol` high for verification and xhigh for final review.

## Review Focus

- A partial edit of an active project that omits required fields must validate the complete merged state, while an explicit blank/null must fail atomically and preserve stored values.
- Missing and foreign project UUIDs must be indistinguishable across read, edit, activate, and deactivate operations.
- Amount boundaries—blank, zero, negative, more than two decimal places, and values beyond `decimal(20, 2)`—must fail predictably without a database error.
- Repeated activate/deactivate calls must be idempotent; deactivation clears `activated_at` and reactivation records a newer timestamp.
- Session expiry or a stale CSRF token during save/lifecycle actions must show the established Russian error/re-auth behavior without displaying a false success or stale project state.

---

### Task 0: Stabilize the completed authentication baseline

**Files:**
- Existing scope only: root environment/Compose/README files, `backend/accounts/**`, existing backend configuration/tests/docs, existing frontend authentication/API/UI/tests, and `specs/done/002-authentication-private-workspace.md`
- Exclude: `.kilo/**`, `.serena/**`, `specs/ready/003-spv-project-drafts.md`, and this plan

**Interfaces:**
- Consumes: the already completed authentication and private-workspace implementation in the current dirty worktree
- Produces: a verified checkpoint commit so project commits contain only project-slice changes

- [x] **Step 1: Inventory the baseline without changing it**

Run `git status --short` and classify every existing path as authentication baseline, manager tooling, or project planning. Stop if any application change cannot be classified.

- [x] **Step 2: Verify the existing backend baseline**

Run from `backend`:

- `uv run python manage.py check`
- `uv run python manage.py makemigrations --check --dry-run`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`
- `uv run pytest`
- `uv run python manage.py spectacular --file schema.yaml --validate --fail-on-warn`

Expected: every command exits `0`.

- [x] **Step 3: Verify the existing frontend baseline**

Run from `frontend`: `npm run verify`

Expected: API freshness, lint, type checking, tests, and production build all pass.

- [x] **Step 4: Create a narrow checkpoint commit**

Stage only the classified authentication/application paths, inspect `git diff --cached --stat` and `git diff --cached --check`, then commit with `feat: complete private workspace authentication`. Leave `.kilo/**` and `.serena/**` untouched.

### Task 1: Architecture and shared-contract gate

**Files:**
- Read-only: `specs/ready/003-spv-project-drafts.md`
- Read-only: this plan and the existing authentication/backend/frontend seams named below

**Interfaces:**
- Consumes: the approved product decisions and the existing stable-error, verified-email, CSRF, OpenAPI, and session-bootstrap interfaces
- Produces: written confirmation of the model invariants, service signatures, error mapping, serializer/component names, endpoint shapes, and generated TypeScript type names used by Tasks 2–5

- [x] **Step 1: Dispatch the architect**

Use a fresh `gpt-5.6-sol` high-reasoning agent. It must inspect the approved spec, this plan, and the named code seams without editing files or expanding scope.

- [x] **Step 2: Check the shared contracts**

Require an explicit verdict on database constraints, service-only mutations, owner-scoped `404` behavior, transaction locking, `ProjectWriteSerializer` create-versus-PATCH requirements, stable error codes, bodyless lifecycle actions, and expected generated OpenAPI component names.

- [x] **Step 3: Reconcile material findings before code**

If the architect finds a contract conflict, update the plan/spec through the manager and obtain user direction only when product behavior or scope would change. Do not dispatch implementation until the contract is internally consistent.

### Task 2: Project model and lifecycle service

**Files:**
- Create: `backend/projects/__init__.py`
- Create: `backend/projects/apps.py`
- Create: `backend/projects/models.py`
- Create: `backend/projects/exceptions.py`
- Create: `backend/projects/services.py`
- Create: `backend/projects/migrations/__init__.py`
- Create: `backend/projects/migrations/0001_initial.py`
- Create: `backend/tests/test_project_model.py`
- Create: `backend/tests/test_project_services.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: `accounts.models.User` and `accounts.guards.require_verified_email(actor: User) -> None`
- Produces: `Project`, `ProjectCreateData`, `ProjectPatch`, `ProjectNotFoundError`, `ProjectValidationError.field_errors: dict[str, list[dict[str, str]]]`, `create_project(*, actor: User, data: ProjectCreateData) -> Project`, `update_project(*, actor: User, project_id: UUID, patch: ProjectPatch) -> Project`, `activate_project(*, actor: User, project_id: UUID) -> Project`, and `deactivate_project(*, actor: User, project_id: UUID) -> Project`

- [x] **Step 1: Write failing model and migration tests**

Add tests proving UUID primary keys, protected ownership, default `draft/KZT` state, deterministic ordering, duplicate titles, positive nullable amount, supported currency, status/`activated_at` consistency, and that `Project` is not registered in Django Admin.

- [x] **Step 2: Run the model tests and confirm the red state**

Run from `backend`: `uv run pytest tests/test_project_model.py -q`

Expected: collection/import failure because `projects` does not exist.

- [x] **Step 3: Implement the model and initial migration**

Define `Project.Currency` (`KZT`, `USD`, `EUR`), `Project.Status` (`draft`, `active`), the exact fields from the spec, `Meta.ordering = ("-updated_at", "-created_at")`, and database constraints for amount, currency, and status/timestamp consistency. Add `projects` to `INSTALLED_APPS` and exclude `projects/migrations/` from strict mypy and migration lint in the same way as accounts.

- [x] **Step 4: Run model tests and migration consistency**

Run `uv run pytest tests/test_project_model.py -q` and `uv run python manage.py makemigrations --check --dry-run`.

Expected: tests pass and Django reports no model changes.

- [x] **Step 5: Write failing service lifecycle tests**

Cover trimmed title creation, omitted currency defaulting to `KZT`, owner assignment, owner isolation, verified activation, unverified activation, incomplete activation field codes, active valid edit, active invalid edit rollback, idempotent transitions, and a newer `activated_at` after deactivate/reactivate. Explicitly test omitted versus blank/null patch fields; 200/201-character title and 5,000/5,001-character description boundaries; and blank, zero, negative, scale, and overflow amount inputs.

- [x] **Step 6: Run service tests and confirm the red state**

Run `uv run pytest tests/test_project_services.py -q`.

Expected: failures for missing service interfaces.

- [x] **Step 7: Implement the service as the only mutation seam**

Use `TypedDict` inputs for `ProjectCreateData` and total-false `ProjectPatch`. Normalize strings, validate draft invariants, merge patches before validating active invariants, owner-scope every target, and wrap state changes in `transaction.atomic()` with `select_for_update()`. Raise project-domain exceptions rather than DRF exceptions; do not log project values.

- [x] **Step 8: Run the focused backend tests**

Run `uv run pytest tests/test_project_model.py tests/test_project_services.py -q`.

Expected: all pass.

- [x] **Step 9: Commit the domain slice**

Stage only Task 2 files and commit with `feat: add private project lifecycle`.

### Task 3: Owner-scoped project API and OpenAPI contract

**Files:**
- Create: `backend/projects/serializers.py`
- Create: `backend/projects/views.py`
- Create: `backend/projects/urls.py`
- Create: `backend/tests/test_projects_api.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/accounts/serializers.py`
- Modify: `backend/tests/test_schema.py`
- Modify generated: `frontend/openapi-schema.yaml`
- Modify generated: `frontend/src/api/schema.d.ts`

**Interfaces:**
- Consumes: all Task 2 service functions and domain exceptions
- Produces: `GET/POST /api/projects/`, `GET/PATCH /api/projects/{id}/`, `POST /api/projects/{id}/activate/`, `POST /api/projects/{id}/deactivate/`, plus generated `Project`, `ProjectWriteRequest`, `PatchedProjectWriteRequest`, and `ProjectListEnvelope` frontend schema types

- [x] **Step 1: Write failing endpoint tests**

Test anonymous `401`, CSRF rejection, empty/list ordering envelope, draft creation defaults, retrieve, partial update, rejected read-only fields, activation/deactivation, stable field errors, and `404 not_found` for both missing and foreign IDs on all four owner-scoped operations.

- [x] **Step 2: Add focused regression tests for API edge cases**

Add tests for zero/negative/over-precision/overflow amounts, explicit blank/null active edits preserving the database row, repeated lifecycle actions, and activation without verified email returning exactly `403 email_verification_required`.

- [x] **Step 3: Run API tests and confirm the red state**

Run `uv run pytest tests/test_projects_api.py -q`.

Expected: failures because project URLs and serializers do not exist.

- [x] **Step 4: Implement serializers and thin views**

Create `ProjectSerializer`, `ProjectWriteSerializer`, and `ProjectListEnvelopeSerializer`. The write serializer requires only `title` on create, defaults omitted `currency` to `KZT`, and is partial for PATCH. Views may owner-scope read queries but must route all mutations through Task 2 services. Map `ProjectNotFoundError` to `StableAPIError(code="not_found", status_code=404)` and `ProjectValidationError.field_errors` to `validation_error`. Add `not_found` to the documented error-code choices.

- [x] **Step 5: Register project URLs**

Mount `projects.urls` at `/api/projects/` without adding a `DELETE` route or Admin registration.

- [x] **Step 6: Run project API and auth regression tests**

Run `uv run pytest tests/test_projects_api.py tests/test_auth_api.py tests/test_schema.py -q`.

Expected: all pass.

- [x] **Step 7: Pin the OpenAPI shapes**

Extend `test_schema.py` to assert every project path/method, request/response component, stable error response, and the absence of `delete`. Run `uv run python manage.py spectacular --file schema.yaml --validate --fail-on-warn`.

Expected: schema generation exits `0` with no warnings.

- [x] **Step 8: Regenerate the checked-in frontend contract**

With Docker Compose running, run from `frontend`: `npm run api:export`, `npm run api:generate`, and `npm run api:check`. Do not hand-edit either generated file.

Expected: generated files are current.

- [x] **Step 9: Commit the API slice**

Stage only Task 3 files and commit with `feat: expose private project API`.

### Task 4: Shared typed frontend transport

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/projects.ts`
- Create: `frontend/src/api/projects.test.ts`
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/errors.ts`

**Interfaces:**
- Consumes: Task 3 generated `paths` and `components`
- Produces: shared `ApiError`, `apiClient`, `csrfParameters()`, `throwApiError(error, response)` and project operations `listProjects()`, `getProject(id)`, `createProject(input)`, `updateProject(id, patch)`, `activateProject(id)`, `deactivateProject(id)`

- [x] **Step 1: Write failing transport tests**

Assert exact HTTP methods/paths, CSRF headers for every mutation, request bodies, list-envelope unwrapping, stable field-error propagation, `401` unauthorized event dispatch, and `403 email_verification_required` preservation.

- [x] **Step 2: Run the transport tests and confirm the red state**

Run from `frontend`: `npm test -- --run src/api/projects.test.ts`.

Expected: failure because `api/projects.ts` does not exist.

- [x] **Step 3: Extract the shared client without changing auth behavior**

Move the existing OpenAPI client, cookie/CSRF handling, `ApiError`, and error conversion from `auth.ts` to `client.ts`. Keep every auth function signature unchanged and change `errors.ts` to import `ApiError` from the shared module.

- [x] **Step 4: Implement typed project transport**

Use only generated `ProjectWriteRequest`/`PatchedProjectWriteRequest` request types and `Project`/`ProjectListEnvelope` response types. Return project objects rather than raw OpenAPI envelopes, and route all non-success responses through the shared error helper.

- [x] **Step 5: Run transport and authentication regressions**

Run `npm test -- --run src/api/projects.test.ts src/auth-flow.test.tsx src/app.test.tsx` and `npm run typecheck`.

Expected: all tests and type checking pass.

- [x] **Step 6: Commit the transport slice**

Stage only Task 4 files and commit with `feat: add typed project client`.

### Task 5: Workspace list and project editor

**Files:**
- Create: `frontend/src/api/project-query-keys.ts`
- Create: `frontend/src/api/project-cache.ts`
- Create: `frontend/src/components/workspace/workspace-shell.tsx`
- Create: `frontend/src/components/workspace/email-verification-banner.tsx`
- Create: `frontend/src/components/projects/project-form.tsx`
- Create: `frontend/src/pages/project-create-page.tsx`
- Create: `frontend/src/pages/project-edit-page.tsx`
- Create: `frontend/src/project-flow.test.tsx`
- Modify: `frontend/src/pages/workspace-page.tsx`
- Modify: `frontend/src/app.tsx`
- Modify: `frontend/src/api/errors.ts`
- Modify as needed for feature styling: `frontend/src/index.css`
- Modify: `frontend/src/auth/session.ts`
- Modify: `frontend/src/app-providers.tsx`
- Modify as needed for real session-event coverage: `frontend/src/test/render.tsx`

**Interfaces:**
- Consumes: Task 4 transport functions, existing session hooks, `RequireAuth`, `Button`, and generated `Project` types
- Produces: protected routes `/app`, `/app/projects/new`, `/app/projects/:id` with loading, error, empty, list, create, edit, activate, and deactivate states

- [x] **Step 1: Write failing workspace-flow tests**

Test Russian loading/error/empty/populated states, deterministic rendered order, formatted amount/currency/status/update time, navigation to create/edit pages, and absence of delete/public/contact controls.

- [x] **Step 2: Write failing editor-flow tests**

Test explicit draft save and redirect, existing-project load/save without reload, no autosave, draft activation, active deactivation, unverified activation guidance, client-side incomplete activation feedback, active-invalid-edit blocking, server field errors, and session/CSRF failure messaging without false success.

- [x] **Step 3: Run the UI tests and confirm the red state**

Run `npm test -- --run src/project-flow.test.tsx`.

Expected: failures because routes and pages do not exist.

- [x] **Step 4: Extract the reusable authenticated workspace shell**

Move header, logout, email display, and verification resend behavior out of `WorkspacePage` without changing existing auth behavior. Keep the banner available on list and editor routes.

- [x] **Step 5: Implement the workspace list**

Use a TanStack Query key shared by all project screens. Render accessible live loading/error states, the Russian empty state, `Создать проект`, and owner project cards with the specified fields and links.

- [x] **Step 6: Implement one reusable project form**

Use React Hook Form and Zod with fields `title`, `description`, `investment_amount`, and `currency`. Keep the amount as an input string and map blank to `null` at the transport boundary; use explicit submit only. Draft validation permits blank description/amount while active validation requires complete valid values.

- [x] **Step 7: Implement create/edit and lifecycle mutations**

Creation redirects to `/app/projects/:id`. Saves update detail and list query caches. Activation/deactivation replaces cached project state. Disable activation for unverified users with an explanation and keep the backend authoritative for every lifecycle rule.

Use account-scoped project keys. Cancel and remove all project queries on logout and global 401. Keep lifecycle actions disabled while the form is dirty; successful save resets the form to returned values. Translate backend project field-error codes into Russian rather than displaying English messages directly.

Map `email_verification_required` to `Подтвердите email, чтобы активировать проект.` and `not_found` to `Проект не найден или недоступен.`. Format amounts with `Intl.NumberFormat("ru-RU")` and update times with `Intl.DateTimeFormat("ru-RU")`.

- [x] **Step 8: Run focused and full frontend verification**

Run `npm test -- --run src/project-flow.test.tsx src/auth-flow.test.tsx src/app.test.tsx`, then `npm run verify`.

Expected: all checks pass and the production build succeeds.

- [x] **Step 9: Commit the UI slice**

Stage only Task 5 files and commit with `feat: add private project workspace`.

### Task 6: Integrated behavior and focused documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify if a stable decision changed: `docs/architecture.md`
- Move after all gates pass: `specs/ready/003-spv-project-drafts.md` to `specs/done/003-spv-project-drafts.md`

**Interfaces:**
- Consumes: Tasks 2–5 as one runnable Docker Compose application
- Produces: documented local workflow and evidence that the feature survives real PostgreSQL, authentication, and browser boundaries

- [x] **Step 1: Run all backend quality gates**

Run the seven Task 0 backend commands again from `backend`.

Expected: every command exits `0`.

- [x] **Step 2: Run all frontend quality gates**

Run `npm run verify` from `frontend`.

Expected: every check exits `0`.

- [x] **Step 3: Exercise the Docker API flow against PostgreSQL**

Create two invited applicants, create multiple projects for each, verify owner ordering/isolation and foreign `404`, verify unverified activation rejection, verify email, activate/edit/deactivate/reactivate a complete project, restart the services, and confirm the same rows remain.

- [x] **Step 4: Exercise the browser flow**

In the actual application, confirm login, empty state, draft create/edit, reload persistence, activation guidance, activation, valid active edit, rejected invalid active edit, deactivation, logout/login persistence, keyboard navigation, visible focus, and readable error states.

- [x] **Step 5: Update documentation and specification state**

Document the project endpoints, commands, and local browser flow without documenting future features as present. Move the approved spec to `specs/done` only after verification succeeds.

- [x] **Step 6: Commit the integration evidence**

Stage only documentation and the spec move, then commit with `docs: document private project workflow`.

### Task 7: Independent verifier gate

**Files:**
- Read-only verification; no production edits

**Interfaces:**
- Consumes: the complete implementation and all 17 acceptance criteria in the spec
- Produces: a criterion-by-criterion pass/fail report with commands, observed results, and any unverified item

- [x] **Step 1: Dispatch the verifier**

Use a fresh `gpt-5.6-sol` high-reasoning agent. It must inspect the diff and explicitly check each acceptance criterion against the manager's command, PostgreSQL, and browser evidence. It runs targeted checks where evidence is insufficient; it does not duplicate the complete quality gates without a concrete reason.

- [x] **Step 2: Resolve any failure through the owning worker**

Send backend findings to the backend worker and frontend findings to the frontend worker; require a regression test for each code fix, then rerun the affected verifier checks.

- [x] **Step 3: Record a clean verifier result**

Do not continue to final review until all criteria pass or the user explicitly accepts a clearly stated environmental limitation.

### Task 8: Final diff review and user acceptance

Completion adjustment: the automated reviewer was dispatched but interrupted without a verdict. The user then reported their own satisfactory review and authorized saving. Prior independent task-scoped reviews and the 17/17 verifier result remain technical evidence; the final automated review is not claimed complete.

**Files:**
- Read-only review; no production edits

**Interfaces:**
- Consumes: verifier-approved implementation and the full diff from the authentication baseline checkpoint
- Produces: severity-ranked findings covering correctness, security/privacy, architecture, accessibility, regressions, and scope

- [x] **Step 1: Dispatch the reviewer**

Use a fresh `gpt-5.6-sol` xhigh-reasoning agent. Review owner isolation, service-only mutations, transaction/constraint safety, stable errors, CSRF behavior, generated-contract correctness, accessible UI states, and absence of deferred features.

- [x] **Step 2: Resolve every actionable finding**

Route fixes to the owning worker, rerun focused tests and the relevant full quality gate, then ask the same reviewer to re-check the fixes.

- [x] **Step 3: Final manager reconciliation**

Compare the final diff with the approved spec, confirm no unrelated paths were staged, summarize verified behavior and remaining limitations, and only then report completion to the user.
