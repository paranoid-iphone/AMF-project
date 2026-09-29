# Kilo Multi-Agent Starter

A reusable GitHub Template for building software projects with **Kilo Code** using a manager-led multi-agent workflow.

The goal of this repository is to provide a clean project structure where you communicate with a single primary agent, while specialized subagents handle architecture, implementation, verification, and review.

## Workflow

```text
You
 ↓
Manager
 ├── Architect
 ├── Frontend Worker
 ├── Backend Worker
 ├── Verifier
 └── Reviewer
```

You normally interact only with the **Manager**.

The Manager is responsible for understanding the request, inspecting the repository, creating an implementation-ready specification, splitting the work into tasks, delegating implementation, running verification, requesting review, and reporting the final result.

Typical feature flow:

```text
request
→ specification
→ architecture/contracts if needed
→ task decomposition
→ implementation
→ tests/build
→ verification
→ review
→ final report
```

Specifications are the source of truth for feature scope.

## Agents

Project-level agents are stored in:

```text
.kilo/agents/
```

### Manager

Primary agent and main entry point.

Responsibilities:

- understand requests written in normal language;
- inspect the existing repository before proposing changes;
- ask questions only when the answer materially affects implementation;
- create implementation-ready specifications;
- decompose work into tasks and dependencies;
- delegate architecture work when needed;
- delegate frontend work to `frontend-worker`;
- delegate backend/database work to `backend-worker`;
- run verification after implementation;
- request an independent final review;
- report completed work, verification results, risks, and unresolved questions.

The Manager should avoid writing production code unless necessary.

### Architect

Used for architecture decisions, API contracts, schemas, dependencies, and system design.

The Architect is primarily read-only and should not implement production code unless explicitly required.

### Frontend Worker

Handles frontend implementation.

Expected behavior:

- follow the current specification;
- inspect existing project patterns first;
- avoid unrelated refactors;
- preserve existing contracts;
- run relevant lint, type-check, tests, and build commands;
- report changed files and unresolved problems.

### Backend Worker

Handles backend, API, database, and server-side implementation.

Expected behavior:

- follow existing architecture;
- respect API contracts and backward compatibility;
- treat migrations carefully;
- consider validation, authorization, transactions, and error handling;
- run relevant tests, type-check, and build commands;
- report changed files and unresolved problems.

### Verifier

Checks whether the implementation actually satisfies the specification.

The Verifier should not silently fix implementation problems.

Typical checks include:

- acceptance criteria;
- tests;
- lint;
- type-check;
- build;
- browser verification for UI changes when available.

Results should clearly distinguish between:

```text
PASS
FAIL
NOT VERIFIED
```

### Reviewer

Performs an independent review of the final diff.

The Reviewer looks for:

- bugs;
- security issues;
- regressions;
- architecture violations;
- edge cases;
- unnecessary complexity;
- divergence from the original specification.

Findings should include severity and file references where possible.

If there are no blocking issues, the Reviewer should say so explicitly.

## Repository Structure

```text
.
├── .kilo/
│   └── agents/
│       ├── manager.md
│       ├── architect.md
│       ├── frontend-worker.md
│       ├── backend-worker.md
│       ├── verifier.md
│       └── reviewer.md
│
├── docs/
│   ├── product.md
│   └── architecture.md
│
├── specs/
│   ├── backlog/
│   ├── ready/
│   └── done/
│
├── AGENTS.md
├── kilo.json
└── README.md
```

## Specifications

Feature specifications move through three states:

```text
specs/backlog/
specs/ready/
specs/done/
```

Recommended lifecycle:

1. A request starts in `backlog`.
2. The Manager turns it into an implementation-ready specification.
3. Once scope and acceptance criteria are clear, it moves to `ready`.
4. After implementation, verification, and review are complete, it moves to `done`.

For feature work, the intended workflow is:

```text
spec → plan → patch → test → browser → review → commit
```

## Project Documentation

### `docs/product.md`

Contains product-level context such as:

- product purpose;
- users;
- key workflows;
- business rules;
- feature boundaries.

### `docs/architecture.md`

Contains technical context such as:

- system overview;
- technology stack;
- major components;
- API contracts;
- data flow;
- architecture decisions;
- quality requirements.

These files should be updated as the project evolves.

## AGENTS.md

`AGENTS.md` contains repository-wide rules shared by the agents.

Core principles include:

- keep changes small and scoped;
- inspect existing patterns before introducing new ones;
- avoid unrelated refactors;
- treat the specification as the source of truth for scope;
- verify work before declaring it complete;
- never commit secrets or credentials.

## Using This Template

1. Click **Use this template** on GitHub.
2. Create a new repository.
3. Clone or open the repository in VS Code.
4. Open the project with Kilo Code.
5. Configure your preferred AI provider and models in Kilo.
6. Start a conversation with the `manager` agent.
7. Describe the product or feature you want to build.

Example:

```text
Build authentication with email and password.

Users should be able to register, log in, log out, and access a protected dashboard.
Use the existing project architecture and create a specification before implementation.
```

The Manager should inspect the repository and coordinate the rest of the workflow.

## Model and Provider Configuration

This template intentionally does **not** hardcode a specific AI provider or model.

Configure models and providers through your own Kilo Code settings.

This keeps the repository portable and allows each user to choose the models that fit their environment, budget, and workflow.

## Local Runtime Files

Some Kilo features may create local runtime or session files such as:

```text
.kilo/agent-manager.json
```

These files may contain temporary session, worktree, or runtime state and should not be committed to the template repository.

Keep them excluded through `.gitignore`.

## Git and Worktrees

The Manager may use Agent Manager/worktrees for independent tasks when appropriate.

Temporary worktree paths, branch state, session IDs, or machine-specific runtime information should never become part of the reusable template.

## Starting a New Project

Before implementation begins, update at least:

```text
docs/product.md
docs/architecture.md
```

Then describe the first feature to the Manager.

A good starting request is:

```text
Read the repository and help me define this product.

First update the product and architecture documentation.
Then create the initial implementation specification.
Do not start coding until the specification is ready.
```

## Philosophy

This template is intentionally lightweight.

It does not prescribe a frontend framework, backend framework, database, deployment platform, or AI provider.

The purpose of the template is to standardize the **development workflow**, not the technology stack.
