# Editorial workflow

This document describes the public-safe editorial flow for News Dispatch.

## 1. Signal collection

Daily Radar collects public RSS/Atom items from configured feeds and writes raw signal files under `signals/`.

Signals are not dispatches. A signal confirms only that a public source item appeared in a feed. It does not confirm context, impact or interpretation.

## 2. Signal filtering

`tools/filter_daily_signals.py` removes obvious low-value items such as deal, discount and shopping noise before the reviewed layer.

Filtered items remain an operational artifact, not a reader-facing issue.

## 3. Source health

`tools/source_health.py` writes `validation/source-health-latest.json` so source availability can be reviewed separately from editorial quality.

A temporary source error is not automatically a reason to remove a source. Repeated errors should trigger source review.

## 4. Reviewed radar

`tools/build_radar_review.py` writes `validation/reviewed-radar-latest.md`.

This is a pre-publication review artifact. It groups retained signals by stream and adds minimal editorial metadata: topic, source class, signal path, confirmation level and next check.

It is not a published dispatch.

## 5. Candidate dispatch

`tools/build_candidate_dispatch.py` writes `validation/candidate-dispatch-latest.md`.

This is a candidate artifact only. It must not be moved to `dispatches/` automatically. It is a workspace for editorial promotion.

`tools/validate_candidate_dispatch.py` verifies that the candidate artifact still carries candidate-only disclaimers and does not claim published status.

## 6. Promotion gate

Before any candidate is moved into `dispatches/`, use `templates/promotion-checklist.md`.

The checklist verifies source boundary, editorial boundary and publication boundary.

The promotion decision is manual.

## 7. Published dispatch validation

`tools/validate_published.py` validates reader-facing published issues. It blocks missing sources, private/internal phrasing, weak source handling errors, advertising language and pre-publication artifact leakage.

A dispatch may be marked `published` only after the promotion checklist is satisfied and the published validation passes.

## Non-goals

- Daily Radar must not auto-publish dispatches.
- Candidate artifacts must not become reader-facing content without editorial promotion.
- The project must not publish investment advice, legal advice, private context or internal company information.
