# 002 — Email authentication and private workspace

## Status

Completed, independently verified, and reviewed on 2026-10-04. Product decisions: invite-only pilot registration, draft access before verification, verified email required for future submission/review, self-service password reset, and internal-only administrator provisioning.

## Goal

Deliver a secure applicant identity loop:

```text
internal invitation
→ applicant registration
→ authenticated private workspace
→ verification email and resend
→ logout/login
→ forgot/reset password
```

The slice establishes reusable session, CSRF, email, token, invitation, rate-limit, and route-guard foundations. It does not implement projects or scoring.

## User roles

### Applicant

- registers only with a valid invitation bound to the same canonical email;
- receives a normal non-staff/non-superuser account;
- can enter the private workspace while email is unverified;
- can verify email, log in/out, and reset password.

### Administrator/operator

- is created only through `createsuperuser` or trusted internal management;
- can issue/revoke applicant invitations through a management command and a minimal superuser-only Django Admin integration;
- has no public registration endpoint.

## Backend architecture

Implement inside the existing `accounts` Django app:

```text
DRF view
→ accounts application service
→ Django auth/ORM/email adapter
```

- Use Django session authentication and CSRF.
- Do not introduce JWT, browser token storage, django-allauth, social login, Redis, project CRUD, or product Admin workflow.
- Registration, token consumption, verification, password changes, and invitation state changes use short `transaction.atomic()` blocks.
- Email sending happens after successful commit and cannot roll back committed identity state.
- Passwords, raw tokens, session IDs, and email bodies are never logged or stored in audit data.

## Data model

### User additions

```text
email_verified_at: nullable datetime, indexed
```

Expose `email_verified` as a derived read-only property. Do not add a separately mutable boolean.

The existing canonical policy remains authoritative: trim whitespace and lowercase the full email address, enforced in application code and PostgreSQL.

### Invitation

```text
id: UUID primary key / public selector
email: canonical email
secret_digest: SHA-256 digest, unique
created_by: nullable FK User
created_at
sent_at: nullable datetime
expires_at
revoked_at: nullable datetime
accepted_at: nullable datetime
accepted_by: nullable FK User
```

Token format:

```text
<invitation UUID>.<256-bit random secret>
```

Only the digest is stored. Default lifetime is seven days and environment-configurable.

Rules:

- invitation is bound to exactly one canonical email;
- states are derived as `pending / expired / revoked / accepted`;
- accepted and revoked are mutually exclusive;
- replacement issuance revokes previous pending invitations for that email;
- acceptance and applicant creation occur atomically;
- invalid, unknown, expired, revoked, accepted, mismatched-email, and account-conflict cases share one public `invalid_invitation` error;
- invitation possession does not verify email.

### EmailVerificationToken

```text
id: UUID public selector
user: FK User
secret_digest: SHA-256 digest
created_at
expires_at
consumed_at: nullable datetime
revoked_at: nullable datetime
```

Token format is `<selector>.<secret>`. Default lifetime is 24 hours. Issuing a new usable token revokes older unused tokens. Confirmation atomically consumes the token and sets `email_verified_at`. Token confirmation never creates or switches a login session.

### AuthRateLimitBucket

PostgreSQL-backed fixed-window rate-limit records:

```text
scope
identifier_digest
window_start
count
expires_at
unique(scope, identifier_digest, window_start)
```

- Identifier digest is HMAC-based using server secret material.
- Raw tokens, raw reset targets, and raw passwords are never stored.
- Increments must be safe across concurrent web processes.
- Expired buckets can be deleted through an idempotent management command.
- Limits are environment-configurable.

Initial defaults:

| Operation | Limits |
|---|---|
| Login | 10/IP and 5/account per 15 minutes |
| Registration | 10/IP and 5/invitation per hour |
| Reset request | 5/IP and 3/email per hour |
| Verification resend | 10/IP and 5/user per hour |
| Token confirmation | 10/IP and 5/token selector per hour |

Return `429 rate_limited` with `Retry-After`. Account-keyed and IP-keyed limits are both required. Do not trust forwarded IP headers until a trusted proxy topology is explicitly configured.

### AccountSecurityEvent

Append-only low-volume events:

- invitation issued/revoked/accepted;
- applicant registered;
- email verified;
- password reset completed.

Store event code, actor/target identifiers where applicable, timestamp, request correlation ID, and optionally hashed client IP. High-volume login failures and reset requests go to security logs/metrics and rate-limit buckets, not an unbounded audit table.

## API conventions

### User representation

```json
{
  "id": 42,
  "email": "applicant@example.com",
  "email_verified": false
}
```

### Stable error shape

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "fields": {
      "password": [
        {"code": "password_too_short", "message": "..."}
      ]
    }
  }
}
```

`fields` is omitted when irrelevant. Codes are stable; user-facing messages may later be localized.

Common codes:

```text
validation_error
invalid_credentials
invalid_invitation
invalid_or_expired_token
not_authenticated
csrf_failed
email_verification_required
rate_limited
```

CSRF failures must return JSON in this shape, never an HTML error page.

## API endpoints

### `GET /api/auth/session/`

Public. Ensures the CSRF cookie exists.

Anonymous `200`:

```json
{"authenticated": false, "user": null}
```

Authenticated `200`:

```json
{
  "authenticated": true,
  "user": {"id": 42, "email": "applicant@example.com", "email_verified": false}
}
```

### `POST /api/auth/register/`

```json
{
  "invitation_token": "selector.secret",
  "email": "Applicant@Example.com",
  "password": "..."
}
```

Success `201`:

```json
{"user": {"id": 42, "email": "applicant@example.com", "email_verified": false}}
```

Behavior:

- canonicalize email;
- validate invitation/email match;
- validate password with Django validators using candidate User context;
- create only non-staff/non-superuser applicant;
- accept invitation atomically;
- log user in and rotate session/CSRF state;
- issue verification token and send email after commit;
- handle uniqueness/concurrency races without account enumeration.

All invitation failures return `400 invalid_invitation`.

### `POST /api/auth/login/`

```json
{"email": "applicant@example.com", "password": "..."}
```

Success `200` returns `{"user": ...}`. Unknown email, wrong password, and inactive user return the same `400 invalid_credentials`. Django login rotates the session and CSRF token.

### `POST /api/auth/logout/`

Idempotent for authenticated and anonymous clients. Flush session and return `204`.

### `POST /api/auth/email-verification/request/`

Authenticated. No body. Return generic `202` whether already verified or email is queued. Do not create a new usable token for an already verified account.

### `POST /api/auth/email-verification/confirm/`

```json
{"token": "selector.secret"}
```

May be anonymous but requires CSRF. Success: `200 {"status":"verified"}`. Invalid/expired/consumed/revoked tokens: `400 invalid_or_expired_token`. Never creates or changes a session.

### `POST /api/auth/password-reset/request/`

```json
{"email": "applicant@example.com"}
```

Always return the same `202` body and comparable public behavior for unknown, inactive, known, or delivery-failure cases. Use Django's password-reset token generator and URL-safe encoded user ID.

### `POST /api/auth/password-reset/confirm/`

```json
{"uid": "...", "token": "...", "new_password": "..."}
```

Success `204`.

- `PASSWORD_RESET_TIMEOUT = 3600`;
- apply all Django password validators with real user context;
- do not auto-login;
- do not mark email verified;
- password change invalidates existing sessions through the session auth hash;
- invalid UID/token returns `400 invalid_or_expired_token`.

## Invitation operations

Mandatory management commands:

```text
invite_applicant <email>
revoke_invitation <selector>
cleanup_auth_buckets
```

`invite_applicant` creates/replaces the invitation and sends a registration link derived from `PUBLIC_APP_URL`. Add a minimal superuser-only Django Admin interface for listing, issuing, and revoking invitations if it can reuse the same application services without duplicating rules.

There is no public invitation-management API.

## Email and local development

Add Mailpit to Docker Compose:

```text
SMTP: mailpit:1025
UI: http://localhost:8025
```

- Development uses SMTP/Mailpit, not raw token logging.
- Links derive from configured `PUBLIC_APP_URL`.
- Production startup rejects console/in-memory/file email backends, non-HTTPS `PUBLIC_APP_URL`, or missing explicit transactional-email settings.
- Delivery failure is logged safely and does not roll back committed registration/token state; resend remains possible.

## Verified-email domain guard

Do not require verified email globally. `/app` and future private draft creation/editing require authentication only.

Provide an application-service guard:

```text
require_verified_email(actor)
```

Future meaningful transitions (questionnaire confirmation, assessment/submission, review submission, publication request) must enforce it both at API boundary and application-service layer. Failure is `403 email_verification_required`.

## Browser/session security

- same-origin Django sessions only;
- session cookie HttpOnly, SameSite=Lax, Secure in production;
- CSRF cookie readable by frontend, SameSite=Lax, Secure in production;
- explicit `credentials: "same-origin"` in API transport;
- current `csrftoken` sent as `X-CSRFToken` on every unsafe request;
- configurable seven-day rolling inactivity session lifetime;
- no session/reset/verification/invitation secrets in localStorage or sessionStorage;
- token query parameters removed from browser URL/history immediately after capture;
- only safe same-origin relative return paths are accepted.

## Frontend routes and behavior

```text
/
/status
/login
/register?invite=...
/forgot-password
/reset-password?uid=...&token=...
/verify-email?token=...
/app
```

- Root redirects based on bootstrapped session state.
- `/status` retains the foundation health page.
- Session state bootstraps only from `GET /api/auth/session/`.
- `RequireAuth` protects `/app` but does not require verification.
- Anonymous-only routes redirect authenticated users to `/app`.
- Guards render loading state before redirect/content to avoid private-content flash.
- `/app` is a private workspace shell only; no project CRUD.
- Workspace shows email, logout, and an unverified-email banner with resend action.
- Banner disappears after session refresh returns verified state.
- Forms use React Hook Form and Zod for UX, while backend remains authoritative.
- TanStack Query session data refetches after register, login, logout, and verification.
- DTOs come from generated OpenAPI types.
- API field errors map accessibly to form fields; generic failures do not reveal account existence.

## Non-goals

- open/public registration;
- social login, MFA, or magic-link login;
- JWT/localStorage authentication;
- project CRUD, questionnaire, scoring, AI, documents, or applicant submissions;
- product Admin review workflow;
- complex RBAC;
- Telegram account linking;
- production email vendor selection;
- account deletion/retention policy;
- styling beyond a clean, responsive, accessible auth/workspace experience.

## Acceptance criteria

1. Pilot applicant registration succeeds only with a valid unexpired invitation bound to the canonical email.
2. Invitation tokens are stored only as digests, are single-use/revocable/expiring, and concurrent acceptance cannot create duplicate users.
3. Registration cannot create staff/superuser privileges and logs the applicant into a rotated Django session.
4. Session bootstrap returns the exact anonymous/authenticated contracts and establishes CSRF.
5. Login failures are enumeration-safe; logout is idempotent and invalidates the session.
6. Unverified authenticated users can access `/app`; the reusable verified-email service guard rejects them with `email_verification_required`.
7. Verification tokens expire, cannot be replayed, replacement revokes old tokens, and confirmation does not create/switch sessions.
8. Password reset request is enumeration-safe; confirmation validates password, expires, invalidates existing sessions, and does not verify email or auto-login.
9. Rate limits work across database-backed state, use no raw sensitive identifiers, and return stable JSON `429` with `Retry-After`.
10. CSRF failures and all auth errors use the stable JSON contract; unsafe SPA requests send the current CSRF header.
11. Mailpit receives invitation, verification, and password-reset messages containing working local links; raw tokens do not appear in backend logs.
12. Production configuration rejects unsafe email backends, missing email settings, or non-HTTPS public URL.
13. `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, and `/app` implement accessible loading/success/error behavior and route guards without protected-content flash.
14. Token query parameters are removed from the URL after capture; arbitrary external return redirects are rejected.
15. Invitation management is internal-only through management commands and optional superuser Django Admin; no public invitation administration endpoint exists.
16. AccountSecurityEvent records material identity events without secrets; email or database failures cannot leave partially accepted invitation/user state.
17. OpenAPI and generated TypeScript contracts are current; existing health behavior remains unchanged.
18. Existing backend/frontend quality gates, Docker integration, and foundation tests remain green.
19. No project/scoring/document/AI/Admin-product scope is introduced.

## Verification plan

Backend:

```text
Django check and migration consistency
Ruff, format, mypy, pytest
clean PostgreSQL migrations
invitation lifecycle and concurrent acceptance tests
session/CSRF rotation and JSON error tests
verification expiry/replay/replacement/concurrency tests
reset expiry/validation/session invalidation tests
database-backed rate-limit tests
verified-email service-guard tests
production email configuration rejection tests
OpenAPI validation
```

Frontend:

```text
npm API contract freshness check
ESLint, TypeScript, Vitest/RTL, production build
session bootstrap and route-guard tests
registration/login/logout/reset/verification form tests
CSRF header tests
unverified banner/resend tests
URL token removal and safe return-path tests
```

Integration:

```text
Docker Compose with PostgreSQL, backend, frontend, and Mailpit
issue invitation through management command
register through frontend/API and inspect Mailpit verification email
verify email and confirm workspace state
logout/login
request password reset through Mailpit and confirm old session invalidation
exercise 429 and Retry-After
confirm health and OpenAPI contracts remain valid
browser flow when browser tooling is available
```

## Implementation task boundaries

### Backend worker

- models/migrations, invitation services/commands/admin, session/CSRF/auth endpoints, tokens, email adapter/templates, rate limiting, audit events, OpenAPI, Mailpit/Compose/backend docs, and backend tests;
- do not implement frontend screens or product features.

### Frontend worker

- typed auth client/CSRF handling, routes, forms, guards, private workspace shell, verification banner, URL sanitization, responsive accessible UI, OpenAPI regeneration, frontend tests/docs;
- do not implement projects or scoring.

### Verifier

- reproduce all acceptance criteria with real PostgreSQL/Mailpit/session cookies and browser checks where possible.

### Reviewer

- review auth/token/rate-limit security, transaction races, enumeration safety, CSRF/session handling, production configuration, frontend privacy, and scope discipline.
