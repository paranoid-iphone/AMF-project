# Project lifecycle and contact channel opportunities

## Status

Backlog only. These items are not approved for implementation and must receive their own product decisions, security review, specification, verification criteria, and review.

## Project deletion and archive

Future discovery must decide:

- whether applicants archive, soft-delete, or permanently delete projects;
- whether only drafts can be deleted;
- whether deleted projects can be restored and for how long;
- how questionnaires, assessments, documents, evidence, reviews, and audit records behave;
- which commercial, privacy, legal, or operational retention periods apply;
- how account deletion interacts with retained project records;
- whether administrators can access archived or deleted records and under what authority.

Until those decisions are approved, project deletion must not be exposed through the API, web application, or Django Admin.

## Public publication

The current `active` state is private and must not be presented as public publication. A future `published` lifecycle requires decisions about:

- audience: anonymous visitors, authenticated applicants, approved investors, or individually authorized users;
- which project fields are safe to disclose;
- owner consent and a publication preview;
- moderation and approval requirements;
- contact-request behavior without exposing personal addresses or phone numbers;
- search, filters, expiry, suspension, unpublication, and audit history;
- handling active Hard Stops and administrator decisions;
- Kazakhstan privacy, advertising, investment-intermediation, and regulatory implications.

## Email phone and Telegram

Notification channels belong to the user rather than to an individual project unless a later product decision explicitly allows project-specific representatives.

Future work should define:

- verified email notification preferences beyond authentication mail;
- phone-number collection, normalization, verification, and consent;
- secure Telegram account linking to an existing authenticated user;
- notification opt-in, granular preferences, and unlinking;
- deep links from notifications to private web pages;
- suppression of confidential project details in notification bodies;
- delivery retries, failure visibility, and audit metadata;
- a clear distinction between notification delivery and a public contact channel.

Telegram remains a secondary notification and deep-link channel. Project, questionnaire, scoring, and document business logic must remain in the web application's backend.
