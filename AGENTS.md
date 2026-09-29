# Multi-Agent Development Workflow

This repository uses a manager-to-worker workflow. The `manager` agent is the primary user-facing agent and coordinates all specialized work.

## Roles

- `manager`: understands requests, inspects the repository, prepares specifications, delegates work, and reports outcomes.
- `architect`: analyzes architecture and defines APIs, schemas, contracts, and implementation recommendations.
- `frontend-worker`: implements assigned frontend and client-side tasks.
- `backend-worker`: implements assigned backend, API, database, migration, and server-side tasks.
- `verifier`: independently checks the implementation against every acceptance criterion without editing files.
- `reviewer`: independently reviews the final diff without editing files.

## Required Flow

1. The manager inspects the repository and understands the product request.
2. The manager asks only questions whose answers materially affect implementation.
3. Important work is captured in a specification under `specs/`.
4. Architecture and shared contracts are decided before dependent implementation begins.
5. The manager delegates implementation to the appropriate worker instead of writing production code.
6. The verifier checks every acceptance criterion and runs available quality gates.
7. The reviewer independently reviews the final diff after verification.
8. The manager summarizes changes, verification, review findings, risks, and user decisions.

## Engineering Rules

- Keep changes small, focused, and easy to verify.
- Inspect and follow existing architecture, conventions, and patterns before introducing new ones.
- Do not perform unrelated refactors, redesigns, cleanup, or scope expansion.
- Treat the current approved specification as the source of truth for feature scope and acceptance criteria.
- Complete relevant tests, lint, type checking, builds, and targeted manual checks before declaring work complete.
- Do not commit credentials, tokens, private keys, environment files containing secrets, or other sensitive data.
- Escalate conflicts between the specification and existing behavior to the manager rather than guessing.
- Record material architecture and product decisions in `docs/` when they become stable.

## Specification Lifecycle

- `specs/backlog/`: ideas and requests that are not implementation-ready.
- `specs/ready/`: approved, implementation-ready specifications and acceptance criteria.
- `specs/done/`: completed specifications retained as scope and decision history.

Moving a specification to `done` does not replace verification or review evidence.

## Worktree Coordination

Agent Manager worktrees may be used for independent tasks. Stabilize shared contracts before parallel implementation, avoid assigning overlapping files to separate workers, and integrate dependent work in dependency order. Do not use shared git stashes as a worktree coordination mechanism.
