# Coverage Audit — News Dispatch

Date: 2026-07-01

Status: source coverage expanded and audited. This file does not publish content, does not edit generated signals, and does not change Daily Radar branch policy.

## Scope and Inputs

This audit checks whether registered News Dispatch streams, rubrics and reader surfaces are connected to source feeds and generated artifacts after the 2026-07-01 source expansion.

Inputs inspected:

- `data/streams.json`
- `data/rubrics.json`
- `sources/feeds.json`
- `sources/feed-candidates.json`
- `sources/official-candidates.json`
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
- New feeds will affect recent-signal and Today coverage only after the next Daily Radar ingestion run.
- Production Pages workflow uses live ranking, not fixture ranking.

## Source Coverage Before / After

| Stream | Before active / total | After active / total | After active source classes | Active official / high-trust | Coverage status after change |
|---|---:|---:|---|---:|---|
| `finance` | 3 / 3 | 4 / 4 | `official_source` x2, `public_media` x2 | 2 / 2 | stronger official coverage |
| `crypto-finance` | 4 / 4 | 6 / 6 | `official_source` x3, `specialized_media` x3 | 3 / 3 | stronger official coverage |
| `ai` | 3 / 4 | 5 / 6 | `official_source` x4, `public_media` x1 | 4 / 4 | stronger official coverage; one noisy broad feed remains disabled |
| `tech-hardware-software` | 5 / 5 | 7 / 7 | `official_source` x4, `public_media` x1, `specialized_media` x2 | 4 / 4 | stronger official coverage |
| `gear-style-edc` | 2 / 2 | 3 / 3 | `specialized_media` x3 | 0 / 0 | broader, still no active official source |
| `moscow-city` | 1 / 3 | 1 / 3 | `public_media` x1 | 0 / 0 | still underfed; official candidates failed probe |
| `dj-audio-creative` | 2 / 2 | 6 / 6 | `official_source` x2, `specialized_media` x4 | 2 / 2 | no longer source-underfed |
| `science-discovery` | 2 / 3 | 4 / 5 | `official_source` x1, `research_media` x1, `specialized_media` x2 | 2 / 2 | stronger official/research coverage; Nature remains disabled |
| `general` | 0 / 0 | 0 / 0 | none | 0 / 0 | special-use only; intentionally not a catch-all feed |

Repository total: 22 / 26 active sources before; 36 / 40 active sources after.

## New Active Sources

| Stream | Source | Class | Reliability tier | Expected signal type | Status |
|---|---|---|---|---|---|
| `finance` | `federal-reserve-press` | `official_source` | A | official policy or supervisory release | active |
| `crypto-finance` | `eba-news` | `official_source` | A | official regulatory release | active |
| `crypto-finance` | `esma-news` | `official_source` | A | official market regulatory release | active |
| `ai` | `openai-news` | `official_source` | A | official product, research or policy release | active |
| `ai` | `google-ai-blog` | `official_source` | A | official product, research or policy release | active |
| `tech-hardware-software` | `cloudflare-blog` | `official_source` | A | official platform, security or infrastructure release | active |
| `tech-hardware-software` | `google-security-blog` | `official_source` | A | official security research or platform release | active |
| `gear-style-edc` | `worn-and-wound` | `specialized_media` | C | industry product or design signal | active |
| `dj-audio-creative` | `musictech` | `specialized_media` | C | industry product or workflow signal | active |
| `dj-audio-creative` | `attack-magazine` | `specialized_media` | C | electronic music industry or workflow signal | active |
| `dj-audio-creative` | `native-instruments-blog` | `official_source` | A | official product or workflow release | active |
| `dj-audio-creative` | `ableton-blog` | `official_source` | A | official product or workflow release | active |
| `science-discovery` | `nasa-news-releases` | `official_source` | A | official science or space release | active |
| `science-discovery` | `phys-org` | `specialized_media` | C | research media signal | active |

All new active rows include `stream`, `source_class`, `reliability_tier`, `language`, `expected_signal_type`, `source_marker` and `lifecycle_state`.

## Disabled / Candidate Sources

Existing disabled live feeds:

| Stream | Source | Class | Reason |
|---|---|---|---|
| `ai` | `the-verge-ai` | `public_media` | Broad feed produced cross-topic noise; disabled until per-section filtering exists. |
| `moscow-city` | `mos-ru-news` | `official_source` | Repeated timeout; still not re-enabled. Corrected probe returned HTTP 403 for the alternate `mos.ru` URL. |
| `moscow-city` | `the-village` | `public_media` | Repeated timeout; needs stable replacement or recovery. |
| `science-discovery` | `nature-news` | `research_media` | XML parse errors; NASA and Phys.org were added instead of re-enabling it. |

Candidate / held feeds recorded in `sources/feed-candidates.json`:

| Stream | Candidate | Status | Reason |
|---|---|---|---|
| `moscow-city` | `mos-ru-news-reprobe` | held-probe-403 | Official Moscow feed returned HTTP 403 in corrected probe. |
| `moscow-city` | `transport-mos-news-candidate` | held-probe-477 | Official transport feed returned HTTP 477. |
| `gear-style-edc` | `gearpatrol-candidate` | held-xml-parse-error | Relevant candidate reached HTTP 200, but corrected probe failed XML parsing. |
| `science-discovery` | `eurekalert-candidate` | held-probe-403 | High-volume science candidate returned HTTP 403. |
| `finance` | `moex-news-candidate` | held-probe-403 | Useful exchange candidate returned HTTP 403. |
| `moscow-city` | `mskagency-candidate` | rejected-404 | Configured RSS URL returned 404 in earlier probe. |
| `moscow-city` | `interfax-moscow-candidate` | held-too-broad | Valid broad feed, but too broad for Moscow without section filtering. |

## Registered Streams and Reader Connectivity

| Stream | Source coverage | Recent local signals on latest day | In Daily Radar output | In `site/radar/` | In `site/streams/` | Today can use it |
|---|---|---:|---|---|---|---|
| `finance` | strong | 15 | yes, 7 signals | yes | yes | yes after ranking / reader gates |
| `crypto-finance` | strong | 15 | yes, 6 signals | yes | yes | yes; fixture selected 1 reader-safe item |
| `ai` | strong | 2 | yes, 1 signal | yes | yes | yes after ranking / reader gates |
| `tech-hardware-software` | strong | 7 | yes, 4 signals | yes | yes | yes after ranking / reader gates |
| `gear-style-edc` | moderate | 1 | no current retained radar item | yes | yes | source-ready, but needs next ingestion/ranking |
| `moscow-city` | weak | 1 | yes, 1 signal | yes | yes | yes, but source depth remains weak |
| `dj-audio-creative` | stronger | 0 | no current retained radar item | yes | yes | source-ready, but needs next ingestion/ranking |
| `science-discovery` | stronger | 5 | yes, 3 signals | yes | yes | yes after ranking / reader gates |
| `general` | none | 0 | no | yes | yes | no; special-use only |

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

Registered issue types: `daily-radar-review`, `weekly-digest`, `reg-brief`, `claim-check`, `market-structure-note`, `infrastructure-radar`, `source-dossier`, `special-issue`.

Reader sections: `issue-panel`, `executive-brief`, `main-editorial-essay`, `key-signals`, `community-radar`, `buying-material-culture-radar`, `finance-consumer-environment`, `horizon-notes`, `signal-vs-noise`, `risks-and-limits`, `decisions-with-criteria`, `change-in-worldview`.

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

Conclusion: generated artifacts feed Today, Radar and Streams. Rubric pages are reader-visible but update primarily when published dispatch metadata changes, not directly from raw Daily Radar signals.

## Operational Classification

Fully operational after source expansion:

- `finance`
- `crypto-finance`
- `ai`
- `tech-hardware-software`
- `dj-audio-creative`
- `science-discovery`

Operational but still weak:

- `gear-style-edc`: broader specialized coverage now exists, but no active official source and no current retained radar item until the next ingestion proves density.
- `moscow-city`: active public-media source remains, but official city/transport candidates failed probe and the stream still lacks active official confirmation.

Decorative / special-use:

- `general`: intentionally no active sources and not a normal Daily Radar source category.

## Risks

- New active sources were probed successfully, but their actual signal quality and noise profile will only be visible after the next Daily Radar run.
- `moscow-city` remains the weakest stream because official city and transport endpoints failed probing.
- `gear-style-edc` still lacks active official-source coverage; specialized media signals must not be treated as confirmation.
- EU/US regulator feeds for `crypto-finance` are broad; strict keyword gates are present, but live noise should be reviewed after first ingestion.
- Vendor official blogs in AI/audio/tech are primary sources for their own claims, not independent verification.
- Fixture build proves rendering, not live ranking selection.

## Recommended Next Fixes

1. Find a stable official Moscow city / transport / culture RSS or API endpoint that returns parseable public data without 403/477.
2. Add one active official or retailer/brand source for `gear-style-edc` only after probe success and strict keyword gates.
3. Review the first Daily Radar run after this change for noise from OpenAI, Google AI, Cloudflare, Google Security, EBA and ESMA.
4. Consider source health thresholds that auto-degrade newly added feeds if fetch errors or low-density runs repeat.
5. Add a generated source freshness panel to stream pages so readers can see when a stream is underfed.

## Validation Summary

Run after the source expansion:

- `python3 tools/validate_feeds.py`
- `python3 tools/validate_official_candidates.py`
- `python3 tools/validate_source_lifecycle.py`

Final required validation must be run after the full site build.
