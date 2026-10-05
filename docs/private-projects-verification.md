# Private project workspace — verification

Date: 2026-10-05. Application revision: `f021508`; authentication baseline: `6a62cd2`.
Scope: completed specification `specs/done/003-spv-project-drafts.md`.

The user approved the manager running the remaining command and browser checks.
The verifier independently evaluates all acceptance criteria against code and
recorded evidence. On 2026-10-05, the user reported a satisfactory review and
authorized saving the result in place of waiting for the interrupted final
automated diff review. No production code changed after the command checks below.

## Final quality gates

Executed in Docker Compose backend, all exit 0:

| Command | Observed result |
| --- | --- |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 68 files already formatted |
| `mypy .` | No issues in 58 source files |
| `pytest` | 154 passed in 40.61 seconds |
| `python manage.py spectacular --file /tmp/schema.yaml --validate --fail-on-warn` | Validated export, exit 0 |

Executed from `frontend`: `npm run verify`, exit 0. Current OpenAPI and generated
TypeScript contracts, dependency audit (0 vulnerabilities), ESLint, TypeScript,
43 tests in 4 files, and production build all passed.

The build reports two pre-existing Rollup warnings about removable annotations
inside installed Zod sources. They do not fail the build and were not suppressed
or addressed through an unrelated dependency change.

## Acceptance evidence

| # | Requirement | Evidence checked by manager |
| --- | --- | --- |
| 1 | Multiple independent drafts | Real HTTP flow and two browser-created drafts |
| 2 | Trimmed title, default KZT | Service/API tests; title-only browser creation |
| 3 | Persistence | HTTP logout/login and backend restart; browser reload, logout/login, backend/frontend restart |
| 4 | Owner-only deterministic list | PostgreSQL HTTP flow; API tests; browser ordering |
| 5 | Foreign/missing IDs both 404 for all four operations | Real HTTP flow and API tests; foreign project UI shows only a safe Russian error |
| 6 | Unverified drafts allowed, activation forbidden | HTTP flow, service/API tests, browser confirmation banner and disabled activation |
| 7 | Complete valid activation state | Service/API boundary tests; incomplete browser activation errors |
| 8 | Status/timestamp lifecycle | HTTP flow and tests; visible final-code activation/deactivation statuses and success messages |
| 9 | Idempotent transitions | HTTP flow, service/API tests |
| 10 | Valid active edits stay active | HTTP flow, service/API tests, browser valid active edit |
| 11 | Invalid active edit is atomic | PostgreSQL HTTP flow and tests; browser blocks blank active description; reload restores stored values |
| 12 | Accessible workspace/editor states | RTL user flows, Russian labels/alerts/statuses; browser form/list and keyboard focus ring |
| 13 | No deferred project/contact controls | Scoped UI review and rendered screens; own account email appears only in the private header |
| 14 | No DELETE/Admin deletion path | API tests and HTTP 405; model tests and no Project Admin registration |
| 15 | Stable errors and CSRF | Real HTTP session/CSRF; backend/transport tests; RTL stale-CSRF test; real browser expired-session Save redirects without false success and leaves stored title unchanged |
| 16 | Current generated contract | Backend schema validation and frontend API freshness/type gates |
| 17 | Auth, health, backend, frontend, Docker regressions | Full 154/43 test suites; all quality gates; Compose health/database ok after restart |

## Browser and PostgreSQL observations

Tests used only disposable local fixtures, not real user accounts. Amount
`999999999999999999.99` survives save/reload without rounding; the list formats
it as `999 999 999 999 999 999,99 USD`. Unsaved changes disappear on reload,
confirming explicit save and no autosave. Lifecycle actions are disabled while
dirty and show save-first guidance.

Final-code browser checks confirmed `Проект активирован.` and
`Проект возвращён в черновик.`, a safe foreign-ID error, logout/login persistence,
visible keyboard focus, and unchanged project values after an expired-session
save. Restarting backend/frontend preserved both drafts and authentication.
The final screenshot is retained in the task's visualization directory.

On this Windows setup, Vite occasionally served cached transforms despite
matching host/container source files; restarting frontend exposed current code.
No volumes were deleted and no configuration changes were made for this issue.

## Independent gates

- Task-scoped domain, API, transport and UI reviews completed. API review found
  create-currency optionality in generated TypeScript and an impossible extra
  deactivate 400 response; both were fixed with regression tests and re-reviewed.
- Independent verifier: **PASS, 17/17**, application revision `f021508`.
  Independently inspected the baseline diff, implementation, migration, schema,
  generated contract, tests, evidence, and final screenshot. No supporting
  evidence gap or observed acceptance failure was found. Full suites and live
  interactions remain manager-observed, not claimed as independently repeated.
- Final acceptance: the user reported reviewing the result and approved saving
  it on 2026-10-05. The separate automated final whole-diff reviewer was
  interrupted and returned no verdict; no claim of a completed automated final
  technical review is made. The independent task-scoped reviews and 17/17
  verifier result above remain the available technical review evidence.

## Execution decisions

- Existing checkout on a dedicated branch was used to preserve the dirty auth
  baseline and Compose bind mounts. Tradeoff: less filesystem isolation,
  mitigated by sequential workers and exact staging.
- Artifact helpers were adapted to PowerShell after Windows path failures.
  Tradeoff: artifact formatting only; task text still comes from the plan.
- User-approved change: manager runs final commands/browser checks; independent
  verification evaluates evidence rather than duplicating the complete suites.
- User-approved completion: retain the interrupted final-review limitation and
  save locally after the user's own review; no merge or remote push is requested.

No deletion, public marketplace, questionnaire, scoring, contacts, Telegram or
project notifications are implemented in this slice. Active projects remain
private to the owner.
