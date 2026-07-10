# Public Reader Architecture Audit — 2026-07

Scope: public News Dispatch reader, daily news/product surface, source hygiene, reader policy, rendering, preview/production validation, and operational release discipline.

This audit uses expert lenses from product architecture, data engineering, editorial/content systems, security/privacy, SRE/reliability, frontend performance, QA automation, and public-safe compliance.

## Executive verdict

The current direction is correct: a public-safe reader with separate Today, News, Digests, Sources, preview artifacts, privacy scan, HTML scan, content quality checks, and production Pages gates.

The current implementation is functional, with a typed public-reader boundary, production smoke checks, and artifact-based review. Quality is still protected by a chain of scripts, post-build steps, and validators. That is acceptable for the current stage, but it should not become the long-term design.

Refactoring is recommended. It should be incremental and contract-driven, not a rewrite.

## Current architecture map

Pipeline as of the audit:

```text
sources / feeds
  -> daily radar ranking report
  -> public source filter
  -> reader policy
  -> markdown/static rendering
  -> news/today/sources builders
  -> HTML enhancement
  -> media preview application
  -> reader structure/layout postprocessors
  -> title quality cleanup
  -> reader/render/privacy validation
  -> public HTML scan and content quality check
  -> PR preview artifacts or production Pages deploy
```

The most important recent correction is that public source filtering now happens before reader policy and rendering. That is the right direction because weak or non-article rows should not enter the public reader contract.

## Expert lenses

### 1. Product architecture lens

Strengths:

- The reader now has a coherent product surface: homepage, Today, News, Digests, Sources.
- The public reader is not a raw diagnostics console.
- PR preview artifacts create a reviewable product boundary before merge.

Risks:

- Product semantics are spread across multiple renderer and postprocessor scripts.
- Some product rules are inferred from HTML structure rather than represented as first-class data.
- `PublicReaderItem` defines the public-only fields, but existing renderers have not migrated to it yet.

Recommendation:

Migrate renderers incrementally to the existing typed reader contract before further large UI changes.

### 2. Data engineering and data quality lens

Strengths:

- Ranking output and reader policy are separated.
- Source filtering is now explicitly represented.
- Content quality produces a machine-readable JSON artifact.

Risks:

- `dict[str, Any]` rows remain the dominant interchange model.
- Source hygiene still partly occurs after ranking, not at source registry or ingestion time.
- Diagnostics and public-facing fields live near each other, which increases leakage risk.

Recommendation:

Keep `PublicReaderItem` as the only public payload shape. Expand its focused unit coverage while keeping ranking diagnostics outside the model.

### 3. Editorial/content systems lens

Strengths:

- The project has a clear rule: public pages must distinguish source messages from conclusions.
- The reader has source actions and reliability labels.
- No-advice and public-safe boundaries are now guarded.

Risks:

- Generic titles and feed artifacts can still appear unless upstream hygiene and title rules remain strict.
- The system does not yet score content usefulness beyond basic fallback/duplicate checks.
- Today could pass technically while still being too weak editorially.

Recommendation:

Add a model-level editorial validator before HTML render: concrete title, source type, why it matters, uncertainty/boundary note where required, and no generic category-only title.

### 4. Security, privacy, and public-safety lens

Strengths:

- Privacy scan and public HTML scan are part of the workflow.
- Production Pages now has content quality validation before deployment.
- Review criteria explicitly prohibit diagnostic fields, raw timestamps, scores, source-rule internals, and comment-feed URLs.

Risks:

- HTML postprocessors can accidentally mutate links or expose fields if they operate on raw HTML.
- Public safety is mostly enforced by scanning after generation, not by a strict public model boundary.
- A future renderer can bypass shared presenter logic unless the contract is enforced.

Recommendation:

Make the public model the only input type accepted by public renderers. Keep scans as defense-in-depth, not the primary safety mechanism.

### 5. SRE/reliability lens

Strengths:

- PR preview and production deploy have explicit gates.
- Regression tests lock critical order in the build pipeline.
- Artifacts are available for review.

Risks:

- The build pipeline is a sequential script chain. Order is critical and can become brittle.
- Production smoke fetches the deployed Pages URL after a successful deploy and on an hourly schedule.
- Failures are not yet summarized as release health states.

Recommendation:

Extend the existing production smoke contract only when a new public route or reader-facing safety boundary is introduced.

### 6. Frontend performance and UX lens

Strengths:

- Static Pages architecture is performant by default.
- The reader avoids heavy client-side dependencies.
- The CSS direction is compact and text-first.

Risks:

- Multiple postprocessors make it harder to reason about final HTML structure.
- There is no explicit page budget for HTML size, number of links, or rendering complexity.
- Visual acceptance is artifact-based but not yet automated as a screenshot/layout diff.

Recommendation:

Keep static rendering. Add simple page budgets and eventually screenshot-based smoke only for major UI changes.

### 7. QA automation lens

Strengths:

- Regression tests, public HTML scan, privacy scan, link QA, trust QA, and content quality QA exist.
- #162 adds direct tests for source filtering and workflow ordering.

Risks:

- Some tests assert strings in workflows and scripts. That is useful, but can become brittle.
- The most important model-level behavior does not yet have enough unit tests.
- PR artifacts and production smoke cover both pre-merge and deployed-reader checks.

Recommendation:

Move the next test layer closer to pure functions: source hygiene, reader model creation, title selection, excerpt selection, reliability label mapping, and stream routing.

## Key findings

### Finding A — The public reader needs a first-class data contract

Severity: high.

Current state: rendering still relies on dict rows and shared helper functions. This works, but it makes field leaks and inconsistent rendering more likely.

Target state: a typed public model, for example:

```text
ReaderItem
- item_key
- stream
- title_ru
- excerpt_ru
- source_name
- source_type_label
- reliability_label
- published_label
- url
- is_selected_for_today
- public_boundary_notes
```

Ranking-only fields such as scores, thresholds, source_rule_status, feed_id, and validation details must not be part of this model.

### Finding B — Post-build HTML mutation should be reduced

Severity: high.

Current state: multiple scripts mutate generated HTML after rendering. Some are layout-oriented; some encode product logic.

Target state:

- business/product decisions happen before render;
- renderers emit final public HTML from a public model;
- HTML enhancement is limited to decorations such as metadata, links, and safe layout wrappers.

### Finding C — Source hygiene should move upstream

Severity: high.

Current state: `filter_public_source_items.py` is a necessary safety net and now runs before reader policy. That is good. But comment-feed rows should ideally never reach ranking as public candidates.

Target state:

- source registry validates feed URL quality;
- ingestion marks source-health reason codes;
- ranking receives only candidate article/update feeds;
- post-ranking filter remains as defense-in-depth.

### Finding D — Production smoke is in place

Severity: medium-high.

Current state: `public-site-smoke.yml` runs after a successful Pages deployment and hourly. It checks the public root, News, and Today routes, required reader markers, and forbidden public patterns; it also stores a JSON report artifact.

Next improvement: include any newly introduced primary public route in this small contract, rather than creating a parallel smoke path.

### Finding E — Editorial quality gates are still basic

Severity: medium.

Current state: content quality catches generic strings, excessive duplicates, missing source actions, missing metadata, empty Today, and comment-feed URLs.

Target state:

- model-level check for title concreteness;
- minimum evidence/source label coverage;
- Today must contain a short reason/importance signal, not only a headline.

## Refactor roadmap

### P0 — Audit baseline and release discipline

Status: this document.

Deliverables:

- architecture audit;
- risk register;
- refactor backlog;
- review criteria.

No runtime behavior changes.

### P1 — Public Reader model contract

Status: delivered in #164 and enforced by the build pipeline.

Delivered:

- `PublicReaderItem` dataclass and a conversion boundary from ranking rows;
- explicit public-only render fields;
- tests preventing score/feed/source-rule leakage;
- model validation before rendering.

Remaining: migrate renderers without changing public output.

### P2 — Renderer consolidation

Goal: all pages use the same public card/row components.

Scope:

- shared news row renderer;
- shared metadata renderer;
- shared source action renderer;
- shared empty state renderer;
- homepage/news/today migration in small PRs.

Risk: medium. Requires artifact review.

### P3 — Source hygiene upstream

Status: partially delivered. Comment-feed and low-quality feed rows are filtered before reader policy as a defense-in-depth gate.

Goal: move these checks closer to source registry/ingestion without changing source coverage unintentionally.

Scope:

- source URL quality checks;
- source-health reason codes;
- tests for article feed vs comment feed;
- keep post-ranking filter as safety net.

Risk: medium. Could change coverage if source registry contains bad feeds.

### P4 — Validation tiering

Status: substantially delivered.

Delivered:

- model-level validation before HTML;
- HTML-level validation after render;
- production smoke after deploy with an artifact report.


### P5 — Reduce HTML postprocessors

Goal: move product logic out of HTML mutation scripts.

Scope:

- classify existing postprocessors as layout, decoration, or product logic;
- remove/merge product-logic postprocessors after model migration;
- keep only safe decoration postprocessors.

Risk: medium-high. Do after P1/P2.

## Recommended next PRs

1. `renderer migration`
   Move the shared news row to `PublicReaderItem`; compare the generated preview artifact before each small merge.

2. `source registry hygiene`
   Move comment-feed detection closer to sources/ingestion without changing coverage.

3. `postprocessor reduction`
   Classify and remove product-logic HTML mutations after the renderer migration is stable.

## Risk register

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Public renderer leaks diagnostic fields | High | Medium | Typed public model plus public HTML scan |
| Generic titles reappear in live feed | Medium | Medium | Source hygiene plus model title validator |
| Postprocessor order breaks page structure | Medium | Medium | Renderer consolidation and workflow order tests |
| Production differs from PR preview | High | Medium | Production smoke artifact |
| Source filtering removes useful items | Medium | Low-Medium | Reason codes and source-level tests |
| Refactor changes public UI accidentally | Medium | Medium | One-layer PRs and preview artifact review |

## Decision

Proceed with incremental refactor.

Do not rewrite the reader. First create a typed public model and model-level validation. Then consolidate renderers and reduce post-build HTML mutation.

The safe sequence is:

```text
Reader model and validator -> shared render components -> upstream source hygiene -> postprocessor reduction
```

This keeps the product usable while reducing architectural risk.
