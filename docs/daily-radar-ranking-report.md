# Daily Radar Ranking Report

`validation/daily-radar-ranking-latest.json` is a diagnostic report that explains why public RSS/Atom items were accepted, filtered, selected, or not selected by Daily Radar.

It is not a reader-facing publication and does not add analytical conclusions.

## Main fields

- `feed_id`
- `configured_stream`
- `routed_stream`
- `language`
- `translation_required`
- `relevance_score`
- `min_relevance_score`
- `include_hits`
- `exclude_hits`
- `boost_hits`
- `penalty_hits`
- `stream_keyword_hits`
- `source_rule_status`
- `final_score`
- `selected`
- `selection_reason`

## Selection reasons

- `filtered_by_source_rules`
- `not_selected_after_ranking`
- `selected_top_ranked`

## Boundary

The report only explains public-source intake. It does not publish investment advice, legal advice, private context, internal company information or non-public material.
