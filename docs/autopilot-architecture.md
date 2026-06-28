# Autopilot architecture

News Dispatch is a zero-touch, public-safe analytical radar.

The system should operate without routine manual source selection, manual signal triage or manual issue promotion. Human intervention is an optional override and audit mechanism, not the normal publishing path.

## Target operating model

```text
source search
-> source discovery
-> source lifecycle
-> signal ingestion
-> signal scoring
-> clustering
-> analytical card builder
-> publication policy gate
-> static publishing
-> observability
```

## Source lifecycle

Sources must be managed by policy, not by routine manual selection.

```text
discovered
-> probation
-> active
-> degraded
-> suspended
-> rejected
```

A source may enter `probation` when it passes technical and topical checks:

- RSS/Atom endpoint is reachable and parseable;
- feed has enough recent items;
- sample density is above stream-specific threshold or the source has strict filtering rules;
- deny-term and spam signals stay below threshold;
- source is not an obvious duplicate of an active source;
- source class and stream are inferable from public metadata.

A source may become `active` only after repeated successful runs. A source must be downgraded or suspended when it repeatedly fails health, density, freshness or safety checks.

## Publication policy

Automation may publish only when all required policy gates pass:

- source boundary: public sources only;
- evidence boundary: fact, source-reported claim, inference, forecast, rumor and weak signal are separated;
- safety boundary: no private/internal data, no investment/legal/tax advice, no advertising or paid promotion;
- stream boundary: item belongs to a canonical stream and is not dumped into `general`;
- confidence boundary: high-impact claims require primary support or explicit limitation;
- output boundary: reader-facing wording must be analytical, non-directive and public-safe.

If an item fails policy, automation must either block it, keep it as an operational artifact, lower confidence, or publish only a limited monitoring note.

## Human role

Human review is not part of the normal operating path.

Allowed human actions:

- adjust policies and thresholds;
- inspect audit reports;
- override a source state;
- disable a broken workflow;
- publish a special issue manually when needed.

Routine operation should remain autonomous.

## Audit requirements

Every automated decision must be inspectable through JSON or markdown artifacts:

- why a source was added, promoted, downgraded or suspended;
- why a signal was selected, rejected or clustered;
- which source rules and discovery rules fired;
- which safety gates passed or blocked publication;
- which uncertainty and verification gaps remain.

## Non-goals

Autopilot does not mean unconstrained generation.

The system must not:

- publish unsupported conclusions as facts;
- publish private or internal data;
- publish investment, legal, tax or operational advice;
- add arbitrary sources without lifecycle checks;
- treat rumors, forum posts or social media claims as confirmed facts;
- turn `general` into a dumping ground for unrelated items.
