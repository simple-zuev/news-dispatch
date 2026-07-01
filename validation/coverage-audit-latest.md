# Coverage Audit — News Dispatch

Date: 2026-07-01

Status: audit report only. This file does not change sources, signals, Daily Radar workflow, publication state or reader output.

## Scope and Inputs

This audit checks whether registered News Dispatch streams, rubrics and reader surfaces are connected to source feeds and generated artifacts.

Inputs inspected:

- `data/streams.json`
- `data/rubrics.json`
- `sources/feeds.json`
- `signals/`
- `validation/daily-radar-latest.json`
- `validation/daily-radar-ranking-latest.json`
- `validation/reader-policy-latest.json`
- `validation/reviewed-radar-latest.md`
- `validation/auto-dispatch-latest.json`
- generated `site/` output from `python3 tools/build_site.py --ranking-mode fixture --media-mode skip`
- `.github/workflows/daily-radar.yml`
- `.github/workflows/pages.yml`
- `docs/daily-radar-automation-branch-policy.md`

Important date note:

- Latest generated Daily Radar artifact date: `2026-06-30`.
- Latest signal directory date found locally: `2026-06-30`.
- Fixture Today ranking date from the requested build: `2026-06-28`.
- Production Pages workflow uses live ranking, not fixture ranking.

## Registered Streams

| Stream | Reader title | Strict | Topic keywords present | Source count | Active sources | Source classes | Active source exists | Recent signals on latest day | In Daily Radar output | In `site/radar/` | In `site/streams/` | Today can use it now |
|---|---|---:|---:|---:|---:|---|---|---:|---|---|---|---|
| `finance` | Финансы: Россия и мир | yes | yes | 3 | 3 | `official_source`, `public_media` | yes | 15 | yes, 7 signals | yes | yes | eligible, but not selected by fixture Today |
| `crypto-finance` | Криптофинансы: Россия и мир | yes | yes | 4 | 4 | `official_source`, `specialized_media` | yes | 15 | yes, 6 signals | yes | yes | yes, 1 reader-safe fixture item |
| `ai` | Искусственный интеллект | no | yes | 4 | 3 | `official_source`, `public_media` | yes | 2 | yes, 1 signal | yes | yes | eligible, but not selected by fixture Today |
| `tech-hardware-software` | Железо и программное обеспечение | no | yes | 5 | 5 | `official_source`, `public_media`, `specialized_media` | yes | 7 | yes, 4 signals | yes | yes | eligible, but not selected by fixture Today |
| `gear-style-edc` | Вещи, стиль и EDC | no | yes | 2 | 2 | `specialized_media` | yes | 1 | no current retained radar item | yes, empty/low-signal page | yes | weak: underfed in current radar |
| `moscow-city` | Москва: события и места | no | yes | 3 | 1 | `official_source`, `public_media` | yes | 1 | yes, 1 signal | yes | yes | eligible, but source depth is weak |
| `dj-audio-creative` | DJ, аудио и креативные технологии | no | yes | 2 | 2 | `specialized_media` | yes | 0 | no current retained radar item | yes, empty/low-signal page | yes | weak: no recent signal on latest day |
| `science-discovery` | Наука и открытия | no | yes | 3 | 2 | `research_media`, `specialized_media` | yes | 5 | yes, 3 signals | yes | yes | eligible, but not selected by fixture Today |
| `general` | Общий радар | no | no | 0 | 0 | none | no | 0 | no | yes, empty/special page | yes | decorative/special-use only |

## Current Stream Status

Fully operational for Daily Radar / Radar / Stream reader surfaces:

- `finance`
- `crypto-finance`
- `ai`
- `tech-hardware-software`
- `moscow-city`
- `science-discovery`

Operational but weak or underfed:

- `gear-style-edc`: active sources exist and recent signal exists, but the current retained Daily Radar artifact did not include this stream.
- `dj-audio-creative`: active sources exist, but no signals on the latest local signal day and no current retained Daily Radar item.
- `moscow-city`: technically operational, but only one active public-media source remains; the official Moscow source is disabled.

Decorative / special-use:

- `general`: registered and rendered as a stream/radar page, but intentionally has no feeds and no topic keywords. It is a cross-domain special stream, not a normal Daily Radar source category.

## Source Mapping Findings

- Feed validation passed.
- Stream registry validation passed for 9 streams.
- Unknown stream mappings: 0.
- Every primary stream except `general` has at least one active source.
- No source appears to be mapped to a non-existent stream.

Disabled sources that affect coverage:

| Stream | Source | Class | Reason |
|---|---|---|---|
| `ai` | `the-verge-ai` | `public_media` | Broad feed produced cross-topic noise; disabled until per-section filtering exists. |
| `moscow-city` | `mos-ru-news` | `official_source` | Repeated timeout; needs stable official Moscow feed or fallback. |
| `moscow-city` | `the-village` | `public_media` | Repeated timeout; needs stable replacement or recovery. |
| `science-discovery` | `nature-news` | `research_media` | XML parse errors; needs valid replacement endpoint. |

## Registered Rubrics and Reader Taxonomy

Registered rubrics:

| Rubric | Title | Connected status |
|---|---|---|
| `reg-watch` | Регуляторный контур | rendered in `site/rubrics/`; used by published dispatches |
| `market-structure` | Структура рынка | rendered in `site/rubrics/`; used by published dispatches |
| `infrastructure` | Инфраструктура | rendered in `site/rubrics/`; used by published dispatches |
| `product-platform` | Продукт и платформа | rendered in `site/rubrics/`; no current published dispatch in this rubric |
| `security-abuse` | Безопасность и злоупотребления | rendered in `site/rubrics/`; no current published dispatch in this rubric |
| `research-evidence` | Исследования и доказательная база | rendered in `site/rubrics/`; no current published dispatch in this rubric |
| `consumer-use` | Пользовательская практика | rendered in `site/rubrics/`; no current published dispatch in this rubric |
| `city-culture` | Город и культура | rendered in `site/rubrics/`; no current published dispatch in this rubric |
| `weak-signals` | Слабые сигналы | rendered in `site/rubrics/`; no current published dispatch in this rubric |

Registered issue types:

- `daily-radar-review`
- `weekly-digest`
- `reg-brief`
- `claim-check`
- `market-structure-note`
- `infrastructure-radar`
- `source-dossier`
- `special-issue`

Registered reader sections:

- `issue-panel`
- `executive-brief`
- `main-editorial-essay`
- `key-signals`
- `community-radar`
- `buying-material-culture-radar`
- `finance-consumer-environment`
- `horizon-notes`
- `signal-vs-noise`
- `risks-and-limits`
- `decisions-with-criteria`
- `change-in-worldview`

Claim taxonomy:

- `confirmed_fact`
- `source_reported_claim`
- `corroborated_signal`
- `research_result`
- `benchmark_result`
- `community_signal`
- `weak_signal`
- `rumor`
- `forecast`
- `marketing_claim`
- `editorial_inference`

Confidence levels:

- `high`
- `medium`
- `low`
- `unknown`

Publication modes:

- `published`
- `limited_publication`
- `draft_only`
- `blocked`

## Reviewed Radar Topics Currently Present

Topics observed in `validation/reviewed-radar-latest.md`:

| Stream | Topics observed |
|---|---|
| `finance` | `general-monitoring` x6, `regulation` x1 |
| `crypto-finance` | `general-monitoring` x5, `market` x1 |
| `ai` | `general-monitoring` x1 |
| `tech-hardware-software` | `infrastructure` x2, `ai-platforms` x2 |
| `moscow-city` | `general-monitoring` x1 |
| `science-discovery` | `general-monitoring` x3 |
| `gear-style-edc` | none in current reviewed radar |
| `dj-audio-creative` | none in current reviewed radar |
| `general` | none |

## Reader Surface Update Path

Daily Radar / Today / Radar / Streams path:

1. `.github/workflows/daily-radar.yml` runs on schedule four times per day and via `workflow_dispatch`.
2. It runs `python tools/run_daily_radar_safe.py`.
3. That runner validates feeds, collects signals, filters signals, builds source health/governance, reviewed radar, candidate dispatch, auto-dispatch drafts and radar artifact validation.
4. The workflow commits generated `signals/`, `data/` and `validation/` changes to the persistent `automation/daily-radar` branch.
5. It opens or updates a PR titled `dispatch: update daily radar content`.
6. The policy document and validator preserve `automation/daily-radar` and prohibit deleting it after Daily Radar PR merges.
7. After generated artifacts reach `main`, `.github/workflows/pages.yml` builds Pages using `python tools/build_site.py --ranking-mode live --media-mode live`.
8. `tools/build_site.py` renders:
   - `site/today.html` from ranking, reader policy, reviewed radar and auto-dispatch artifacts;
   - `site/radar/*.html` from `validation/daily-radar-latest.json`;
   - `site/streams/*.html` from published dispatches plus signal/radar context;
   - `site/rubrics/*.html` from published dispatch metadata.

Conclusion: generated artifacts do feed Today, Radar and Streams. Rubric pages are reader-visible but update primarily when published dispatch metadata changes, not directly from raw Daily Radar signals.

## Reader Sections Update Status

Today digest sections update: yes. `site/today.html` now renders an autonomous digest with:

- `Главное за период`
- `События с наибольшим эффектом`
- `Регуляторика и правовой контур`
- `Инфраструктура и участники рынка`
- `Продуктовые и организационные импликации`
- `Радар слабых сигналов`
- `Что проверять дальше`
- `Источники и уровень надёжности`
- automated gate status and verification gaps

Radar pages update: yes, from `validation/daily-radar-latest.json`.

Stream pages update: yes, from stream registry, published dispatches and current signal/radar context.

Rubric pages update: partially. The pages render for all registered rubrics, but only rubrics used by published dispatches currently have substantive published content. The remaining rubric pages are valid navigation shells rather than active Daily Radar surfaces.

## Decorative or Underfed Sections

Decorative / intentionally special:

- `general`: no active sources, no recent signals, no retained radar output. This is acceptable only as a cross-domain special stream.

Underfed:

- `dj-audio-creative`: no latest-day signals and no current retained radar output.
- `gear-style-edc`: one latest-day signal but no current retained radar output.
- `moscow-city`: one active source and no active official source; current radar output exists but source depth is thin.

Rendered but currently sparse:

- rubric pages for `product-platform`, `security-abuse`, `research-evidence`, `consumer-use`, `city-culture`, `weak-signals`.

Potentially fragile source classes:

- `gear-style-edc` and `dj-audio-creative` rely entirely on specialized media.
- `moscow-city` currently relies only on public media because the official city source is disabled.

## Operational Classification

Fully operational:

- `finance`
- `crypto-finance`
- `ai`
- `tech-hardware-software`
- `science-discovery`

Operational but weak:

- `moscow-city`
- `gear-style-edc`
- `dj-audio-creative`

Decorative / special-use:

- `general`

## Risks

- Fixture build proves the rendering path, but live Today coverage depends on live ranking output and source availability.
- Some streams have enough source registration to pass coverage tests but not enough recent retained signals to feel alive every day.
- Rubric pages can look broader than the current published archive because several rubrics have no current published dispatch content.
- Disabled high-trust sources reduce confirmation strength in `moscow-city` and `science-discovery`.
- Today can only synthesize streams that survive reader policy and ranking gates; a stream can have fresh signals and still not appear in Today.

## Recommended Next Fixes

1. Add or restore a stable official Moscow source for `moscow-city`.
2. Add at least one high-trust or official source for `gear-style-edc` and `dj-audio-creative`, or mark them as lower-frequency streams in reader copy.
3. Add replacement research/official source coverage for `science-discovery` while `nature-news` is disabled.
4. Add a small coverage/status panel to generated stream pages showing active source count, latest signal date and current radar availability.
5. Add rubric freshness/empty-state copy that distinguishes active rubrics from taxonomy-only rubrics.
6. Consider a machine-readable coverage audit generator if this report becomes recurring.

## Validation Summary

Commands already run before writing this report:

- `python3 tools/build_site.py --ranking-mode fixture --media-mode skip`
- `python3 tools/validate_stream_registry.py`
- `python3 tools/validate_feeds.py`
- `python3 tools/validate_daily_radar_branch_policy.py`
- `python3 tools/validate_architecture_consistency.py`

Final required validation should be run after this report is written.
