# Synthesis quality gate

This document defines minimum quality requirements for generated synthesis drafts.

The gate applies to current non-archive files in `validation/auto-dispatches/` and to `validation/candidate-dispatch-latest.md`.

It does not approve publication. It only verifies that draft artifacts contain enough structure for human editorial review.

## Auto draft requirements

Every generated auto-radar draft must remain draft-only and must include:

- `status: "draft"`;
- `publication_mode: "draft_only"`;
- `verification_gap`;
- `confidence`;
- `claim_types`;
- `privacy_review: "auto_passed_public_sources_only"`;
- `editorial_review: "automatic_draft_needs_human_review"`.

## Required reader sections

Every auto-radar draft must contain these sections:

- `## Лид`;
- `## Главное`;
- `## Что произошло`;
- `## Почему это важно`;
- `## Аналитическая рамка`;
- `## Реестр подтверждения`;
- `## Что проверять дальше`;
- `## Статус`.

The sections may remain conservative. They must not convert source-reported claims into confirmed conclusions without primary evidence.

## Confirmation and safety requirements

Drafts must separate source-reported claims, editorial inference, confidence and verification gaps.

Drafts must not contain investment advice, legal advice, paid promotion or claims of publication readiness.

Candidate dispatch artifacts must remain pre-publication workspaces and must not claim published status.

The quality gate is structural. Semantic topic routing, primary-source enrichment and final editorial synthesis are separate layers.
