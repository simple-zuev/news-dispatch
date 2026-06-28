# Autonomous editorial workflow

This document describes the public-safe autonomous workflow for News Dispatch.

News Dispatch is not a raw feed and not a manual editorial queue. It is a policy-gated analytical radar that turns public signals into reader-facing radar pages and dispatches through automated checks.

## Core principle

```text
zero-touch operation
manual override optional
policy gates mandatory
```

The system should not require routine manual source selection, manual issue promotion or manual signal triage. Manual review is an override/audit path, not the default operating model.

## Editorial layers

Do not mix these layers:

```text
stream -> rubric -> issue_type -> evidence ledger -> reader sections -> policy gate
```

- `stream` answers what domain a dispatch belongs to: finance, crypto-finance, ai, tech-hardware-software, gear-style-edc, moscow-city, dj-audio-creative, science-discovery or general.
- `rubric` answers what analytical lens is used: regulation, market structure, infrastructure, security, research evidence, consumer use, weak signals and related lenses from `data/rubrics.json`.
- `issue_type` answers what product format is being published: daily radar review, weekly digest, reg brief, claim check, market structure note, infrastructure radar, source dossier or special issue.
- `evidence ledger` records claim type, source support, confidence, gaps and publication mode.
- `reader sections` are the recurring blocks inside an issue.
- `policy gate` decides whether output can be published, downgraded, blocked or retained as an operational artifact.

A stream is not a rubric. A rubric is not a section. A Daily Radar artifact is not a published dispatch.

## 1. Signal collection

Daily Radar collects public RSS/Atom items from configured feeds and writes raw signal files under `signals/`.

Signals are not dispatches. A signal confirms only that a public source item appeared in a feed. It does not confirm context, impact or interpretation.

## 2. Signal filtering

`tools/filter_daily_signals.py` removes obvious low-value items such as deal, discount and shopping noise before the reviewed layer.

Filtered items remain operational artifacts unless they later pass publication policy.

## 3. Source health

`tools/source_health.py` writes `validation/source-health-latest.json` so source availability can be reviewed separately from editorial quality.

A temporary source error is not automatically a reason to delete a source. Repeated errors should trigger automated downgrade or suspension.

## 4. Reviewed radar

`tools/build_radar_review.py` writes `validation/reviewed-radar-latest.md`.

This is a pre-publication review artifact. It groups retained signals by stream and adds minimal editorial metadata: topic, source class, signal path, confirmation level and next check.

It is not a published dispatch.

## 5. Candidate dispatch

`tools/build_candidate_dispatch.py` writes `validation/candidate-dispatch-latest.md`.

This is a candidate artifact only. It must not be moved to `dispatches/` automatically. It is a workspace for editorial promotion.

`tools/validate_candidate_dispatch.py` verifies that the candidate artifact still carries candidate-only disclaimers and does not claim published status.

## 6. Rubric classification

Before promotion, classify the candidate by `primary_rubric`, optional additional `rubrics` and `issue_type`.

Use `data/rubrics.json` as the source of truth for editorial rubrics, issue types, reader sections, claim types, confidence levels and publication modes.

Examples:

```text
stream: crypto-finance
primary_rubric: reg-watch
rubrics: [reg-watch, market-structure]
issue_type: reg-brief
```

```text
stream: tech-hardware-software
primary_rubric: infrastructure
rubrics: [infrastructure, security-abuse]
issue_type: infrastructure-radar
```

```text
stream: gear-style-edc
primary_rubric: consumer-use
rubrics: [consumer-use]
issue_type: weekly-digest
```

## 7. Evidence ledger

Every high-impact claim should be checked at claim level.

Use this model:

```text
claim -> claim_type -> primary_source -> secondary_source -> confidence -> verification_gap -> publication_mode
```

Claim types should distinguish confirmed fact, source-reported claim, corroborated signal, research result, benchmark result, community signal, weak signal, rumor, forecast, marketing claim and editorial inference.

For finance, crypto-finance, regulation, sanctions, legal, AML/CFT, taxation, security and compliance-sensitive topics, do not publish high-impact conclusions without a primary source or an explicit limitation. If primary support is absent, use `limited_publication`, `draft_only` or `blocked` rather than overstating the claim.

## 8. Publication policy gate

Before reader-facing publication, automation must verify source boundary, evidence boundary, safety boundary, canonical stream, acceptable confidence and public-safe language.

If checks pass, an item or issue may be published automatically. If checks fail, it must remain blocked, downgraded or operational-only.

Manual review is an override/audit path, not the default operating model.

## 9. Published dispatch validation

`tools/validate_published.py` validates reader-facing published issues. It blocks missing sources, private/internal phrasing, weak source handling errors, advertising language and pre-publication artifact leakage.

A dispatch may be marked `published` only after automated policy gates and published validation pass.

## Reader-section guidance

The old rubric-like blocks remain useful, but they are reader sections, not streams:

- Issue Panel — compact metadata: stream, rubric, issue type, confidence and publication mode.
- Executive Brief — concise decision-grade summary.
- Main Editorial Essay — central analytical narrative.
- Key Signals — important signals with source class and confidence.
- Community Radar — user/community evidence and repeated patterns.
- Buying and Material-Culture Radar — product, gear, EDC and ownership-oriented evidence, without advertising.
- Finance and Consumer Environment — consumer finance and household financial context.
- Horizon Notes — long-horizon science, technology and culture signals.
- Signal vs Noise — what matters, what should be ignored and what needs more evidence.
- Risks and Limits — uncertainty, missing sources and potential analytical errors.
- Decisions with Criteria — non-directive criteria for monitoring and future editorial prioritization.
- Change in Worldview — what the reader should understand differently after the issue.

## Non-goals

- Autopilot must not publish unsupported conclusions as facts.
- Autopilot must not promote sources without lifecycle checks.
- The project must not publish investment advice, legal advice, private context or internal company information.
- Rubrics must not become a dumping ground for unrelated topics.
- Reader sections must not be confused with thematic streams.
