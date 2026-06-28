# Content Intelligence Contract

## Purpose

News Dispatch should work as a Russian-language analytical reader, not as a raw RSS mirror. A raw item becomes useful only after it is normalized into an enriched signal: what happened, how reliable the source is, why the item matters, who is affected, what may change, what is still unknown, and what should be watched next.

This contract defines the target shape for that enriched signal. It is intentionally public-safe and source-first.

## Boundary

The contract does not publish content by itself. It does not change feed fetching, routing, Pages deployment or publication rules. It defines the data object that future scoring, Russian summaries and Today Radar pages should consume.

The contract must keep these separations explicit:

- fact: confirmed by an official, primary or otherwise attributable public source;
- source-reported claim: reported by a public source but not independently confirmed;
- editorial inference: a causal or impact interpretation derived from public signals;
- weak signal: early indication with limited confirmation;
- rumor or unverified item: allowed only when explicitly marked and never presented as fact.

## Required reader value

Each enriched signal should answer:

1. What happened?
2. Why was it selected?
3. Why does it matter?
4. Who or what may be affected?
5. What effects are plausible?
6. What remains uncertain?
7. What should be monitored next?
8. Why is it safe to show publicly?

## Required fields

The canonical schema is `schemas/content-intelligence-signal.schema.json`.

Core identity:

- `id`
- `date`
- `stream`
- `source_title`
- `source_url`
- `source_class`
- `language`

Russian reader layer:

- `original_title`
- `ru_title`
- `ru_summary`

Evidence and confirmation:

- `claim_type`
- `confirmation_level`

Scoring:

- `relevance_score`
- `impact_score`
- `freshness_score`
- `novelty_score`

Analytical explanation:

- `why_selected`
- `why_it_matters`
- `affected_actors`
- `possible_effects`
- `uncertainties`
- `watch_next`
- `public_safety_notes`

## Scoring interpretation

Scores are normalized from `0` to `1`.

- `relevance_score`: fit to the configured stream and user-facing topic model.
- `impact_score`: potential market, regulatory, product, infrastructure or organizational effect.
- `freshness_score`: recency of the item and whether it updates the current radar.
- `novelty_score`: whether the item adds new information compared with already seen signals.

A future ranking layer should prefer high relevance and impact, penalize duplicates and off-topic items, and keep low-confidence items visible only when they are clearly marked as weak signals.

## Russian analytical card target

A future card derived from this object should use this reader-facing form:

```text
[Stream] Russian title

Тезис:
...

Аргумент:
...

Следствие/Риск:
...

Источник и уровень подтверждения:
...

Что проверить дальше:
...
```

## Public-safety rule

The enriched signal must not contain private company data, personal data, non-public documents, confidential strategy, direct investment advice, legal advice or undisclosed paid promotion. If uncertainty exists, the object must mark it in `public_safety_notes` and keep the signal in review-only mode until resolved.
