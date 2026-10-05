# 003 — Private SPV project drafts and activation

## Status

Design approved on 2026-10-05. The specification is ready for final written review before implementation planning begins.

## Goal

Allow an authenticated applicant to create and manage multiple private SPV project drafts, activate a complete project, continue editing it while active, and return it to draft status.

This slice establishes project ownership and lifecycle foundations for the later questionnaire and assessment slices. It does not publish projects to other users.

```text
authenticated applicant
→ creates a private SPV project
→ saves and resumes the draft
→ completes the required summary fields
→ activates the project
→ edits it while it remains active
→ optionally returns it to draft
```

## Product decisions

- A project is always private to its owner in this slice.
- `active` means activated by the owner; it does not mean publicly published.
- `published` is reserved for a future marketplace lifecycle.
- An unverified applicant may create and edit drafts.
- Verified email is required to activate a project.
- Active projects remain editable if the resulting data still satisfies activation requirements.
- An owner may return an active project to draft.
- Project deletion and archiving are not included.
- Contacts and notification channels belong to the user profile or a future notification module, not to each project.
- Account email remains private. It may be used by the application for transactional notifications.

## Domain model

Create a dedicated Django `projects` application. Do not place project business logic in `accounts`.

### Project

```text
id: UUID primary key
owner: protected FK to accounts.User
title: string, required, trimmed, maximum 200 characters
description: text, optional for draft, maximum 5,000 characters
investment_amount: decimal(20, 2), optional for draft, positive when present
currency: KZT | USD | EUR, default KZT
status: draft | active, default draft
created_at: datetime
updated_at: datetime
activated_at: nullable datetime
```

Rules:

- duplicate titles are allowed, including for the same owner;
- `owner` never comes from request data and cannot be reassigned;
- draft projects have `activated_at = null`;
- active projects have a non-null `activated_at`;
- deactivation clears `activated_at`;
- reactivation records a new activation timestamp;
- no questionnaire, score, document, contact, public slug, or publication fields are added in this slice;
- no project deletion API or Django Admin deletion path is introduced.

### Activation requirements

A project can become or remain active only when:

- the owner has a verified email;
- `title` is non-empty after trimming;
- `description` is non-empty after trimming;
- `investment_amount` is present and greater than zero;
- `currency` is one of `KZT`, `USD`, or `EUR`.

Editing an active project must validate the complete resulting state. A partial update that would clear or invalidate an activation-required field is rejected without changing the stored project.

## Backend architecture

Use the existing modular-monolith flow:

```text
DRF view
→ projects application service
→ Project model and Django ORM
```

The projects module exposes a small application-service interface:

```text
create_project(actor, data)
update_project(actor, project_id, patch)
activate_project(actor, project_id)
deactivate_project(actor, project_id)
```

The application service owns authorization, lifecycle validation, transactions, and state changes. Serializers validate request shape but do not own lifecycle rules. Views do not mutate projects directly.

State-changing operations lock the target project in a short database transaction. Repeating `activate` for an already active valid project or `deactivate` for a draft is idempotent and returns the current state. Concurrent ordinary edits use last-write-wins semantics in this slice; revision conflicts are deferred.

## API contract

All endpoints use the existing Django session and CSRF authentication. Anonymous access returns the established JSON `not_authenticated` error. All project lookups are owner-scoped; a missing project and another owner's project both return `404`.

### Project representation

```json
{
  "id": "8d9690f5-9e0a-4477-9382-99c2df385f34",
  "title": "Solar generation project",
  "description": "Construction of a regional solar power facility.",
  "investment_amount": "250000000.00",
  "currency": "KZT",
  "status": "draft",
  "created_at": "2026-10-05T10:00:00Z",
  "updated_at": "2026-10-05T10:00:00Z",
  "activated_at": null
}
```

The owner is not exposed as a writable or public field.

### `GET /api/projects/`

Returns `200`:

```json
{
  "projects": []
}
```

Projects are ordered by `updated_at` descending and then `created_at` descending. Pagination, search, and filtering are not included.

### `POST /api/projects/`

Request:

```json
{
  "title": "Solar generation project",
  "description": "",
  "investment_amount": null,
  "currency": "KZT"
}
```

Creates a draft owned by the authenticated user and returns `201` with the project representation. Only `title` and `currency` are required at creation.

### `GET /api/projects/{id}/`

Returns the owner-scoped project representation with `200`.

### `PATCH /api/projects/{id}/`

Accepts any subset of:

```text
title
description
investment_amount
currency
```

Returns the updated representation with `200`. It does not accept `id`, `owner`, `status`, or timestamp fields. An invalid update uses the existing `validation_error` envelope and leaves the project unchanged.

### `POST /api/projects/{id}/activate/`

Takes no request body and returns the active project representation with `200`.

- unverified email: `403 email_verification_required`;
- incomplete or invalid project: `400 validation_error` with field errors;
- missing or foreign project: `404`.

### `POST /api/projects/{id}/deactivate/`

Takes no request body and returns the draft project representation with `200`.

### Stable error behavior

Reuse the existing error envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "fields": {
      "description": [
        {"code": "required_for_activation", "message": "Description is required to activate the project."}
      ]
    }
  }
}
```

No error reveals whether another user's project exists.

## Frontend behavior

### Routes

```text
/app
/app/projects/new
/app/projects/:id
```

All routes remain protected by the existing session bootstrap and `RequireAuth` behavior.
All new user-facing copy is Russian, consistent with the pilot product language.

### Workspace

Replace the empty project placeholder on `/app` with:

- a `Create project` action;
- loading, error, empty, and populated states;
- one list ordered by last update;
- project title, formatted amount and currency, status label, and last-updated time;
- a link to open each project.

Do not add tabs, search, filters, pagination, public links, or deletion actions.

### Create and edit form

Use React Hook Form and Zod for client-side usability while keeping Django authoritative.

- `/app/projects/new` creates a project through an explicit `Save draft` action and redirects to its edit page.
- `/app/projects/:id` loads the owner-scoped project and saves edits through an explicit `Save` action.
- There is no autosave in this slice.
- Successful saves update TanStack Query data without a full page reload.
- The page clearly shows `Draft` or `Active`.
- A draft exposes `Activate`; an active project exposes `Return to draft`.
- An unverified user sees that email confirmation is required for activation, with access to the existing resend flow.
- Client-side activation checks improve feedback, but the backend remains authoritative.
- An active project cannot submit edits that would make its activation-required fields invalid.

## Email and contact handling

- Do not copy account email into the project.
- Do not expose email, phone number, or Telegram identity in project API responses.
- Existing email infrastructure remains available for authentication messages and future transactional notifications.
- Phone and Telegram linking require separate verification, consent, disablement, and notification-preference contracts and are deferred.

## Security and privacy

- Authentication is required for every project endpoint.
- Querysets and application services scope access by `owner`.
- The backend never accepts an owner identifier from the client.
- Foreign project identifiers return the same `404` behavior as missing identifiers.
- Draft access does not require verified email.
- Activation enforces verified email both at the endpoint and application-service layer.
- No project data becomes public in this slice.
- Project values and personal data are not written to application logs.

## Non-goals

- project deletion, trash, restore, or archive;
- public publication or a project catalog;
- investor accounts, contact requests, messaging, or offers;
- phone or Telegram account linking;
- notification preferences or project-status notifications;
- SPV questionnaire answers or confirmation;
- deterministic scoring, Risk Flags, or Hard Stops;
- Project IRR or cash-flow input;
- PDF/DOCX upload, extraction, AI, or evidence scoring;
- Admin project review or moderation;
- project limits, search, filtering, or pagination;
- optimistic concurrency or visible revision history.

## Acceptance criteria

1. An authenticated applicant can create multiple independent SPV project drafts.
2. A new project requires a trimmed title and uses `KZT` by default unless another supported currency is supplied.
3. Projects persist across logout, login, page reload, and service restart.
4. `/api/projects/` returns only the current owner's projects in deterministic last-updated order.
5. A user cannot read, edit, activate, or deactivate another user's project; missing and foreign IDs both return `404`.
6. An unverified applicant can create and edit drafts but receives `403 email_verification_required` when activating.
7. Activation requires a non-empty title and description, a positive investment amount, and a supported currency.
8. Successful activation sets `status=active` and `activated_at`; successful deactivation restores `status=draft` and clears `activated_at`.
9. Repeated activation or deactivation is idempotent.
10. An active project can be edited without deactivation when the resulting state remains valid.
11. An invalid edit of an active project is rejected atomically and preserves the previous stored state.
12. The workspace implements accessible loading, error, empty, list, create, edit, activation, and deactivation states.
13. The UI does not expose deletion, public publication, account email, phone, or Telegram information.
14. There is no `DELETE` project endpoint and no project deletion behavior in Django Admin.
15. API errors use the established stable JSON envelope and unsafe requests include the current CSRF token.
16. OpenAPI and generated frontend TypeScript contracts are current.
17. Existing authentication, health, backend, frontend, and Docker integration behavior remains green.

## Verification plan

Backend:

```text
Django system check and migration consistency
model and database-constraint tests
application-service lifecycle tests
owner-isolation API tests
verified-email activation tests
atomic invalid-active-edit tests
Ruff lint and format check
mypy
pytest
OpenAPI validation
```

Frontend:

```text
API contract freshness check
ESLint
TypeScript no-emit check
Vitest and React Testing Library project flows
production build
```

Integration:

```text
create two invited applicants
create multiple projects for each applicant
confirm cross-owner access returns 404
confirm unverified draft access and activation rejection
verify email and activate a complete project
edit the active project and return it to draft
restart the application and confirm persistence
exercise the complete browser flow
```

## Implementation boundaries

### Architect

- confirm the project model, lifecycle invariants, error mapping, and OpenAPI shapes before dependent implementation begins;
- prevent questionnaire, marketplace, notification, and Admin concerns from entering this slice.

### Backend worker

- implement the `projects` Django app, migration, services, API, OpenAPI schema, and backend tests;
- do not implement frontend pages or future product features.

### Frontend worker

- implement typed project transport, routes, workspace list, create/edit UI, lifecycle actions, and frontend tests;
- consume generated OpenAPI types and do not duplicate backend contracts manually.

### Verifier

- independently verify every acceptance criterion, including real PostgreSQL ownership isolation and the browser flow when available.

### Reviewer

- independently review privacy, authorization, lifecycle invariants, transaction safety, API compatibility, accessible UI behavior, and scope discipline.
