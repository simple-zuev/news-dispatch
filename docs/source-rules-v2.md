# Source Rules v2

## Purpose

Source Rules v2 moves Daily Radar from feed-owned intake toward meaning-aware selection. A feed can still provide a default stream, but each item is now checked against source-level relevance rules before it becomes a signal.

This prevents broad RSS feeds from filling a stream with off-topic material and creates the base for Russian analytical cards and Today Radar.

## Rule fields

Each feed in `sources/feeds.json` may define:

- `language`: source language, for example `ru` or `en`.
- `translation_required`: whether a future Russian reader layer should translate and normalize the item.
- `include_keywords`: terms that indicate the item fits the configured stream.
- `exclude_keywords`: terms that make the item off-topic for the stream.
- `boost_keywords`: terms that increase selection strength.
- `penalty_keywords`: terms that reduce selection strength without hard-blocking.
- `min_relevance_score`: minimum normalized relevance score required before the item can become a Daily Radar signal.

## Selection behavior

Daily Radar computes a normalized relevance score from `0` to `1`.

- Any `exclude_keywords` match returns relevance `0`.
- `include_keywords`, `boost_keywords` and stream keywords increase relevance.
- `penalty_keywords` reduce relevance.
- Feeds with `include_keywords` are penalized when none of those terms match.
- Items below `min_relevance_score` are ignored before signal files are written.

## Editorial meaning

The rules do not publish analytical conclusions. They only improve intake quality.

A selected item is still only a public signal. The future Content Intelligence layer must still add Russian title, summary, confirmation level, why it matters, affected actors, possible effects, uncertainty and watch-next fields.

## Public-safety boundary

The rule layer does not use private context and does not fetch non-public material. It only filters public RSS/Atom items using configured public-safe terms.
