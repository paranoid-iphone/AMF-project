# Product context

## Document status

**Discovery draft.** This document is updated during product discovery. It is not an implementation specification. Items are explicitly marked as `DECIDED`, `ASSUMED`, or `OPEN` so that tentative ideas do not silently become requirements.

Last updated: 2026-09-30.

## Product overview

The product is intended to connect owners of business projects seeking financing with investors. The initial product slice focuses on helping an applicant structure and assess a project before it is shown to investors.

The longer-term product may combine:

1. a structured project application and transparent rules-based score;
2. AI-generated explanations and improvement recommendations;
3. an investor-facing marketplace for discovering suitable projects and expressing interest.

The first milestone does **not** include the investor marketplace.

The primary product interface is a web application. A Telegram bot is planned as a secondary notification and deep-link channel after the core web workflow exists. A Telegram Mini App is a future option, not part of the initial scope.

## Problem

Project owners currently submit substantially the same information to separate investment agencies. Each agency sees only its own applications. Applications are often poorly structured, so investors spend significant time filtering them and requesting missing information. Project owners may use intermediaries to prepare a project for financing, but those services can require a significant fee or percentage.

## Target users

### Initial user

An owner or initiator of a new business project seeking investment and wanting to understand the project's investment readiness.

### Future user

An investor who wants to reduce time spent reviewing unstructured or unsuitable projects and define an individual minimum passing score.

### Terminology

`Applicant` or `project owner` is preferred over `borrower`: the source criteria describe equity investment and business acquisition as well as potential financing, not only repayable loans.

## Value proposition

### For project owners

- structure project information using a consistent questionnaire;
- receive a transparent formal score;
- see weak areas and critical-risk warnings;
- receive AI-generated explanations and practical improvement recommendations;
- improve the project without immediately paying an investment intermediary.

### For investors (future)

- receive more consistently structured applications;
- filter projects using approved investor preferences and evidence/risk requirements;
- spend less time on clearly unsuitable or incomplete applications.

## Main MVP flow

`Register with email and password → create an SPV project → upload an optional PDF/DOCX business plan → system extracts questionnaire answers → applicant supplies missing information and resolves conflicts → applicant reviews and edits the complete questionnaire → receive a deterministic score plus AI assessment and recommendations → edit the project and run the assessment again`

An applicant without a suitable document can complete the questionnaire manually. File-analysis failure must not prevent this manual path.

## Roles

### Applicant — DECIDED

- can own multiple projects;
- can see only their own projects in the first milestone;
- can save an incomplete project as a draft;
- can edit answers and reassess a project;
- receives a rules-based score and AI feedback.

### Investor — FUTURE / PARTIALLY DECIDED

- is not included in the first milestone;
- may later configure selection preferences after the common methodology is validated;
- may discover projects matching those preferences, evidence requirements, and acceptable risk status.

### Administrator — DECIDED FOR MVP

- reviews document/answer discrepancies within granted permissions;
- records verification status and review comments;
- sees project score, evidence status, and risks separately;
- can decide whether a project is publishable;
- resolves conflicts, returns projects for correction, approves and publishes;
- cannot publish while an active Hard Stop exists;
- can trigger an audited recalculation.

The MVP Admin scope is defined in `docs/spv-scoring-methodology-v1.md`. Administrative verification must not be presented as full due diligence unless a separate procedure is defined.

## Evaluation model

The source criteria are stored in `project-evaluation-criteria.docx`. It currently describes three application types:

1. new project (SPV);
2. operating business;
3. sale of a business.

Only the **new project (SPV)** form is in the MVP.

The extracted rules and contradictions are maintained in `docs/scoring-methodology-review.md`, with decision history in `docs/scoring-methodology-decisions.md`. The approved product and calculation baseline is `docs/spv-scoring-methodology-v1.md`; it is ready to be converted into feature-level implementation specifications.

### A: project quality and readiness — DECIDED

- Criteria and answer scores are common across the platform.
- The formal score is calculated deterministically from predefined answer values.
- A is a numeric score out of 100 using the approved five blocks and nine weighted criteria documented in `docs/spv-scoring-methodology-v1.md`.
- Weights are: finances 30%, team 20%, product/readiness 20%, economics/market 20%, legal 10%.
- AI does not change the formal score.
- A does not represent funding probability, business-success probability, a credit rating, or investment advice.
- An investor may later configure selection preferences; investor-specific scoring behavior is not currently approved.

### Pilot result presentation — DECIDED

- Show the numeric A score without `low / medium / high` categories during the pilot.
- Calibrate any future categories and thresholds using at least 15–20, preferably 20–30, real projects and expert outcomes.
- The previously proposed `0–39 / 40–69 / 70–100` bands are withdrawn.

### B: evidence level — DECIDED

- B is separate from A and shows how strongly applicant claims are supported by documents and review.
- B does not automatically replace answers or modify A.
- Each criterion receives an evidence coefficient `1.0`, `0.5`, or `0`; conflict also creates a flag.
- B uses the same criterion weights as A: `B = Σ weight × verification coefficient`.
- `A × B / 100` may be used only for internal Admin prioritization, not as the sole public investor score.

### Risk flags and hard stops — DECIDED FOR MVP

- Risks are shown separately and cannot be hidden by a high A.
- Warnings do not block continued review.
- Hard stops block publication until resolved or explicitly overridden by an authorized administrator.
- MVP Hard Stops: no responsible project executor; missing required data; critical unresolved contradiction; unidentified applicant/project owner.
- MVP Risk Flags include no confirmed sales, debt, litigation, no co-financing, low IRR, weak team, and low evidence.
- `Publish` is unavailable while a Hard Stop is active.

### SPV rubric clarifications — DECIDED WITH OPEN DETAILS

- The target metric is Project IRR calculated deterministically from nominal after-tax unlevered project cash flows over 5–10 forecast years. Exceptional/multiple IRR cases receive `IRR_REQUIRES_REVIEW`.
- If an earlier slice omits the financial model, the user-supplied value is called `declared annual project return`, not IRR.
- The offered investor share is removed from A and moved to Investment Terms. The financial block is split between own funds and co-financing at 15% each.
- `What the project already has` describes resources actually available or secured at the time of application, not items planned for future purchase.
- That resource criterion is a multi-select. Its raw maximum remains 9.5 and is proposed to be normalized using `raw / 9.5 × 10`, subject to methodology-owner approval.
- `Only the project / nothing else exists` is mutually exclusive with all resource selections.
- Own-funds ranges are interpreted as: `<10%` → 2; `10–<20%` → 4; `20–<30%` → 6; `30–<40%` → 8; `40–50%` → 9; `>50%` → 10.
- Double participation of own funds and contracts/offtake is intentional because the occurrences describe different aspects.

### AI feedback — DECIDED WITH OPEN DETAILS

- AI explains the score and weak criteria.
- AI provides recommendations for improving the project.
- AI may identify missing information and contradictions.
- The preferred input flow starts with uploaded project-plan files.
- AI extracts proposed questionnaire answers from the files.
- The system asks the applicant for required information that could not be extracted reliably.
- Conflicts between documents and manually entered information are shown to the applicant for resolution; the system does not silently choose one source.
- Before assessment, the complete questionnaire is shown to the applicant for review and editing.
- The formal score is calculated only from the applicant-confirmed questionnaire.
- AI generates the broader qualitative assessment and recommendations using the confirmed questionnaire and available document context.
- Each extracted answer is accompanied by its document source, such as file, page, section, or source excerpt where technically available.
- Missing information is collected through a structured form with highlighted unanswered fields, not through an AI chat in the MVP.
- AI may identify useful issues outside the ten formal criteria, but these are presented separately as additional observations and do not affect the formal score.
- PDF and DOCX are supported initially. Broader file support is a future opportunity.
- File upload is optional; the questionnaire can be completed manually.
- If extraction or AI analysis fails, the applicant is notified and can continue manually.
- Size limits, low-confidence presentation, exact citation format, and exact retry behavior remain open.

### Evidence and verification — DECIDED CONCEPT, MVP DEPTH OPEN

- Applicant answers are self-reported and are not verified in the MVP.
- Values extracted from applicant-uploaded documents are also self-reported until independently verified.
- The result must clearly state that the underlying information has not been independently verified.
- Uploaded files do not automatically make an answer verified.
- Declared values, document values, sources, verification statuses, and administrator comments remain distinct.
- Minimum statuses are `unverified`, `matched`, and `conflict`; an additional audited `admin_verified` state is proposed.
- Missing required answers make A preliminary and block publication; they are not removed from the denominator.
- Verification by the application is not described as full due diligence.

## Result shown to the applicant — DECIDED

The initial result contains:

- total formal score;
- a diagram or visual breakdown by criterion;
- evidence level B;
- weak areas;
- AI recommendations;
- additional AI observations outside the formal rubric, clearly separated from scored criteria;
- critical-risk warnings when applicable;
- hard-stop and publication status when applicable;
- a notice that applicant-provided information is unverified.

## MVP scope — DECIDED SO FAR

- Russian-language web experience;
- registration and authentication using email and password;
- multiple projects per applicant;
- SPV application only;
- persistent draft application;
- structured scoring questionnaire;
- optional PDF/DOCX project-plan upload;
- AI-assisted extraction and questionnaire prefilling;
- source references for extracted questionnaire values;
- collection of missing answers and explicit resolution of conflicting information;
- final applicant review and editing of the full questionnaire before assessment;
- deterministic scoring;
- AI qualitative assessment, explanations, and recommendations based on confirmed answers and document context;
- Project IRR calculation from structured project cash flows, unless intentionally deferred to a later MVP slice under the declared-return fallback;
- deterministic A and B calculations plus separate Risk Flags and Hard Stops;
- Admin project list, project review, verification, conflict resolution, recalculation, publication actions, and audit log;
- versioned scoring results; the applicant-facing MVP may show only the latest while preserving score-at-submission internally;
- projects visible only to their authors and explicitly authorized administrators.

## Explicit non-goals for the first milestone

- investor registration or investor dashboard;
- project marketplace, search, and filtering;
- investor offers or legally binding transactions;
- movement of money through the platform;
- operating-business and business-sale application forms;
- manual due diligence;
- automatic verification of applicant claims;
- custom criteria or custom weights per investor;
- public low/medium/high score bands before pilot calibration;
- spreadsheets, presentations, images, scanned-document OCR, and other file types beyond PDF/DOCX;
- Kazakh or English localization;
- Telegram bot and Telegram Mini App;
- guarantee of funding or investment performance.

## Business and product rules

- One applicant can create multiple projects.
- An incomplete questionnaire can be saved and resumed.
- Only the project owner and explicitly authorized administrators can access a project; exact administrator scope in the first milestone remains open.
- A project can be edited and assessed again.
- The formal score must be reproducible for the same questionnaire answers.
- AI output must not silently alter the formal score.
- AI observations outside the rubric must be clearly separated and must not affect the formal score.
- Extracted answers must not become final until the applicant reviews and confirms the questionnaire.
- Conflicting sources must be surfaced to the applicant rather than resolved silently.
- A document-processing failure must not block manual questionnaire completion.
- Risk flags remain separate from A and B.
- An approved hard stop blocks publication rather than altering A.
- The platform must distinguish declared, document-supported, administrator-verified, and formally assessed information.
- Every score stores the methodology version used to calculate it.
- Historical scores must never be silently recalculated after a methodology change.

## Geography

**DECIDED:** the initial jurisdiction and market are Kazakhstan. Legal and regulatory analysis becomes blocking before introducing investor matching, offers, transactions, or claims that could be interpreted as regulated financial advice.

## Important open questions

- How are low-confidence extractions presented?
- What file-size, page-count, and file-count limits apply?
- What exact citation format is feasible for each supported document format?
- What exact textual fields accompany the structured SPV questionnaire?
- What exact publication audience and visibility does `Published` create before investor matching exists?
- What password recovery and email-verification behavior is required?
- What retention and deletion rules apply to commercially sensitive project files?
- Which AI provider and data-processing terms are acceptable for confidential business information?
- What business model will be used after product value is validated?

## Decision log

- 2026-09-29: selected the SPV application as the first form.
- 2026-09-29: selected hybrid evaluation: deterministic score plus AI explanations and recommendations.
- 2026-09-29: selected self-reported, unverified data for MVP.
- 2026-09-29: selected warnings rather than automatic rejection for critical risks.
- 2026-09-29: accepted provisional readiness bands of 0–39, 40–69, and 70–100; superseded on 2026-09-30 by pilot calibration without bands.
- 2026-09-29: excluded the investor role from the first milestone.
- 2026-09-29: selected multiple projects, saved drafts, repeat assessment, author-only access, email/password authentication, and Russian as the MVP language. Author-only access was later expanded in the target architecture to explicitly authorized administrators; exact MVP admin scope remains open.
- 2026-09-29: established that uploaded project-plan files are intended to inform AI feedback; processing details remain open.
- 2026-09-30: made PDF/DOCX upload optional and selected a document-first assisted flow: extract proposed answers, request missing data, surface conflicts, show the full questionnaire for applicant confirmation, then calculate the score and produce AI feedback. Manual completion remains available as a fallback.
- 2026-09-30: selected latest-result-only presentation for the MVP; visible assessment history and comparison are deferred.
- 2026-09-30: confirmed that the formal score comes only from the applicant-confirmed questionnaire; AI cannot adjust it.
- 2026-09-30: required source references for extracted answers, structured collection of missing fields, and separately labeled AI observations outside the formal rubric.
- 2026-09-30: selected a category-cap model; superseded later the same day by separate A, B, risk-flag, and hard-stop layers.
- 2026-09-30: initial category caps were proposed; superseded by risk flags and publication-blocking hard stops.
- 2026-09-30: clarified that the return criterion may mean IRR and approved non-overlapping own-funds ranges. The later baseline prefers Project IRR when calculated by the platform.
- 2026-09-30: adopted the baseline split into A (quality/readiness), B (evidence), separate risk flags/hard stops, AI assistance, and administrator review.
- 2026-09-30: withdrew pilot score bands, removed investor share from A subject to methodology-owner approval, adopted methodology versioning, and required historical results not to be silently recalculated.
- 2026-09-30: approved `SPV-1.0` product baseline: five weighted A blocks, weighted B formula, initial Hard Stops/Risk Flags, deterministic Project IRR rules, and the Admin MVP workflow. Details are consolidated in `docs/spv-scoring-methodology-v1.md`.

## Agreed delivery slicing

The following is the current preferred implementation order, not a set of implementation-ready specifications:

1. Manual SPV questionnaire → deterministic score → basic result.
2. AI recommendations based on the applicant-confirmed questionnaire.
3. Optional PDF/DOCX upload → extraction → missing/conflicting information review → applicant confirmation.
4. Broader AI document analysis and separately labeled additional observations.

Each slice must remain usable and verifiable on its own. Document automation is part of the intended MVP, but it must not block delivery of the simpler scoring flow.

## Delivery planning

- Ordered feature sequence: `docs/initial-feature-backlog.md`.
- Recommended smallest working slice: `docs/first-milestone.md`.
- Each backlog item still requires its own implementation-ready specification before production work begins.

## Client channels

### DECIDED

- Web application is the primary interface for questionnaires, documents, results, conflicts, and Admin workflows.
- Telegram bot is added after the core web backend for notifications and links to relevant web pages.
- Sensitive business-plan documents are uploaded directly to the application's private storage, not sent through Telegram by default.

### FUTURE

- Telegram Mini App may provide the web interface inside Telegram after the normal web flow is stable.
- Rich questionnaire completion inside a chat conversation is not currently planned.
