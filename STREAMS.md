# Dispatch Streams

News Dispatch is a multi-stream editorial hub.

A stream is an independent digest line with its own scope, cadence, source model, privacy boundary, and output format.

## Principle

Personal context can calibrate relevance, but publishable output must remain anonymized and editorially clean.

## Initial streams

| Stream | Path | Purpose | Sensitivity |
|---|---|---|---|
| General Dispatch | `streams/general/` | Broad analytical dispatch across technology, culture, science, finance, gear, cities, and product thinking. | Medium |
| Work Dispatch | `streams/work/` | Public-signal-based work, product, market, AI, UX, org/process, and competitive intelligence. | High |
| Finance Dispatch | `streams/finance/` | Rates, banking products, subscriptions, consumer economics, liquidity, large purchases. Educational and scenario-based only. | High |
| Home & Environment Dispatch | `streams/home-environment/` | Home, smart home, energy, safety, infrastructure patterns, comfort, practical systems. | High |
| Gear & Material Culture Dispatch | `streams/gear/` | EDC, bags, watches, tools, apparel, materials, ownership, repairability, carry culture. | Medium |
| City & Culture Dispatch | `streams/city-culture/` | City life, culture, media, events, urban services, lifestyle signals. | Low/Medium |
| Audio & Creative Tech Dispatch | `streams/audio-creative/` | DJ gear, audio, MIDI, music production, performance interfaces, creator tools. | Low/Medium |
| Horizon Notes | `streams/horizon/` | Science, futures, materials, robotics, biotech, cognition, HCI, systems thinking. | Low |

## Adding a stream

1. Create `streams/<stream-slug>/README.md`.
2. Define scope and anti-scope.
3. Define sensitivity level.
4. Define sources.
5. Define publishable boundary.
6. Add tags to `data/taxonomy.yml`.

## Sensitivity levels

- `Low`: normal editorial review.
- `Medium`: anonymization required before publishing.
- `High`: strict privacy review required before publishing.
