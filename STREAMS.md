# Dispatch Streams

News Dispatch is a multi-stream editorial hub.

A stream is an independent dispatch line with its own scope, cadence, source model, public-safety boundary, and output format.

## Principle

All repository content is public-by-default.

Private calibration can influence topic selection and editorial judgment, but committed output must remain anonymized, public-source-based, and editorially clean.

## Initial streams

| Stream | Path | Purpose | Review level |
|---|---|---|---|
| General Dispatch | `streams/general/` | Broad analytical dispatch across technology, culture, science, finance, gear, cities, and product thinking. | standard_public_review |
| Work Dispatch | `streams/work/` | Public-signal-based work, product, market, AI, UX, org/process, and competitive intelligence. | strict_publication_review |
| Finance Dispatch | `streams/finance/` | Rates, banking products, subscriptions, consumer economics, liquidity, large purchases. Educational and scenario-based only. | strict_publication_review |
| Digital Assets Infrastructure Dispatch | `streams/digital-assets-infrastructure/` | Public-source analysis of digital asset infrastructure, regulation, restrictions, technology, market structure, competitors, and vendor landscape. | strict_publication_review |
| Home & Environment Dispatch | `streams/home-environment/` | Home, smart home, energy, safety, infrastructure patterns, comfort, practical systems. | strict_publication_review |
| Gear & Material Culture Dispatch | `streams/gear/` | EDC, bags, watches, tools, apparel, materials, ownership, repairability, carry culture. | standard_public_review |
| City & Culture Dispatch | `streams/city-culture/` | City life, culture, media, events, urban services, lifestyle signals. | standard_public_review |
| Audio & Creative Tech Dispatch | `streams/audio-creative/` | DJ gear, audio, MIDI, music production, performance interfaces, creator tools. | standard_public_review |
| Horizon Notes | `streams/horizon/` | Science, futures, materials, robotics, biotech, cognition, HCI, systems thinking. | standard_public_review |

## Adding a stream

1. Create `streams/<stream-slug>/README.md`.
2. Define scope and anti-scope.
3. Define review level.
4. Define source model.
5. Define publishable boundary.
6. Add tags to `data/taxonomy.yml`.

## Review levels

- `standard_public_review`: normal editorial review plus privacy check.
- `strict_publication_review`: enhanced review for sensitive domains; no internal or personal context may be committed.

## Neutral conclusion rule

A dispatch should not name its intended beneficiary.

Do not write:

- for our product;
- for our company;
- for our team;
- for teams building X;
- for operators of Y.

Prefer:

- the signal may indicate;
- the likely implication is;
- the observed mechanism is;
- the position changes if;
- the hypothesis should be tested against.
