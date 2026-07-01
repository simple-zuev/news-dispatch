# Coverage Audit — News Dispatch

Date: 2026-07-01

Status: source coverage expanded through live discovery v2 and audited. This file does not publish content, does not edit generated signals, and does not change Daily Radar branch policy.

## Scope and Inputs

This audit checks whether registered News Dispatch streams, rubrics and reader surfaces are connected to source feeds and generated artifacts after live source discovery v2.

Inputs inspected:

- `data/streams.json`
- `data/rubrics.json`
- `sources/feeds.json`
- `sources/feed-candidates.json`
- `sources/official-candidates.json`
- `validation/source-discovery-v2-latest.md`
- `signals/`
- `validation/daily-radar-latest.json`
- `validation/daily-radar-ranking-latest.json`
- `validation/reader-policy-latest.json`
- `validation/reviewed-radar-latest.md`
- `validation/auto-dispatch-latest.json`
- `.github/workflows/daily-radar.yml`
- `.github/workflows/pages.yml`
- `docs/daily-radar-automation-branch-policy.md`

Important date note:

- Latest generated Daily Radar artifact date: `2026-06-30`.
- Latest signal directory date found locally: `2026-06-30`.
- Fixture Today ranking date from the requested build: `2026-06-28`.
- New feeds will affect recent-signal and Today coverage only after the next Daily Radar ingestion run.
- Production Pages workflow uses live ranking, not fixture ranking.

## Source Coverage

| Stream | Active / total | Active source classes | Active official / high-trust | Coverage status |
|---|---:|---|---:|---|
| `finance` | 5 / 5 | `official_source` x3, `public_media` x2 | 3 | strong |
| `crypto-finance` | 7 / 7 | `official_source` x4, `specialized_media` x3 | 4 | strong |
| `ai` | 6 / 7 | `official_source` x4, `public_media` x1, `research_media` x1 | 5 | strong, one noisy broad feed disabled |
| `tech-hardware-software` | 9 / 9 | `official_source` x6, `public_media` x1, `specialized_media` x2 | 6 | strong |
| `gear-style-edc` | 4 / 4 | `specialized_media` x4 | 0 | broader, still no active official source |
| `moscow-city` | 2 / 4 | `public_media` x2 | 0 | improved but still weak; no active official source |
| `dj-audio-creative` | 6 / 6 | `official_source` x2, `specialized_media` x4 | 2 | strong enough for Daily Radar ingestion |
| `science-discovery` | 5 / 6 | `official_source` x2, `research_media` x1, `specialized_media` x2 | 3 | strong |
| `general` | 0 / 0 | none | 0 | special-use only; intentionally not a catch-all feed |

Repository total: 44 / 48 active sources.

## Active Sources Added in Discovery v2

| Stream | Source | Class | Reliability tier | Why it matters |
|---|---|---|---|---|
| `finance` | `ecb-press` | `official_source` | A | Official euro-area monetary policy, digital euro, payment and collateral signals. |
| `crypto-finance` | `fca-news` | `official_source` | A | Official UK crypto, stablecoin and financial-crime regulatory signals. |
| `ai` | `arxiv-cs-ai` | `research_media` | C | Early AI research/preprint signals with strict preprint labeling. |
| `tech-hardware-software` | `github-security-blog` | `official_source` | A | Official GitHub security, advisory and supply-chain signals. |
| `tech-hardware-software` | `kernel-releases` | `official_source` | A | Primary Linux kernel release cadence signals. |
| `moscow-city` | `moskvichmag` | `public_media` | B | Adds a second active Moscow city/culture/business source while official feeds remain blocked. |
| `gear-style-edc` | `carryology` | `specialized_media` | C | Adds focused carry, bag, materials and EDC design coverage. |
| `science-discovery` | `esa-space-science` | `official_source` | A | Adds official European space-science mission coverage. |

## Disabled / Candidate Sources

Existing disabled live feeds:

| Stream | Source | Class | Reason |
|---|---|---|---|
| `ai` | `the-verge-ai` | `public_media` | Broad feed produced cross-topic noise; disabled until per-section filtering exists. |
| `moscow-city` | `mos-ru-news` | `official_source` | Repeated timeout / blocked access; still not re-enabled. |
| `moscow-city` | `the-village` | `public_media` | Repeated timeout; needs stable replacement or recovery. |
| `science-discovery` | `nature-news` | `research_media` | XML parse errors; NASA, ESA and Phys.org now provide replacement coverage. |

Candidate / held sources are recorded in `sources/feed-candidates.json` and detailed in `validation/source-discovery-v2-latest.md`. Key holds:

- `moscow-city`: official `mos.ru` and Moscow Transport endpoints still failed probe; this remains the largest coverage gap.
- `gear-style-edc`: Gear Patrol and Dezeen failed XML parsing; GearJunkie was parseable but too broad.
- `crypto-finance`: FATF, FinCEN and Coinbase endpoints failed; Kraken was parseable but too noisy for active ingestion.
- `tech-hardware-software`: MSRC endpoint failed XML parsing.
- `science-discovery`: EurekAlert was blocked; arXiv astro-ph was parseable but high volume and left as candidate.

## Reader Connectivity

| Stream | Source coverage | Recent local signals on latest day | In Daily Radar output | In `site/radar/` | In `site/streams/` | Today can use it |
|---|---|---:|---|---|---|---|
| `finance` | strong | 15 | yes, 7 signals | yes | yes | yes after ranking / reader gates |
| `crypto-finance` | strong | 15 | yes, 6 signals | yes | yes | yes; fixture selected 1 reader-safe item |
| `ai` | strong | 2 | yes, 1 signal | yes | yes | yes after ranking / reader gates |
| `tech-hardware-software` | strong | 7 | yes, 4 signals | yes | yes | yes after ranking / reader gates |
| `gear-style-edc` | moderate | 1 | no current retained radar item | yes | yes | source-ready, but needs next ingestion/ranking |
| `moscow-city` | moderate/weak | 1 | yes, 1 signal | yes | yes | yes, but official confirmation is weak |
| `dj-audio-creative` | strong | 0 | no current retained radar item | yes | yes | source-ready, but needs next ingestion/ranking |
| `science-discovery` | strong | 5 | yes, 3 signals | yes | yes | yes after ranking / reader gates |
| `general` | none | 0 | no | yes | yes | no; special-use only |

## Registered Rubrics and Reader Taxonomy

Registered rubrics:

| Rubric | Title | Connected status |
|---|---|---|
| `reg-watch` | Регуляторный контур | rendered in `site/rubrics/`; used by published dispatches |
| `market-structure` | Структура рынка | rendered in `site/rubrics/`; used by published dispatches |
| `infrastructure` | Инфраструктура | rendered in `site/rubrics/`; used by published dispatches |
| `product-platform` | Продукт и платформа | rendered in `site/rubrics/`; sparse published archive |
| `security-abuse` | Безопасность и злоупотребления | rendered in `site/rubrics/`; sparse published archive |
| `research-evidence` | Исследования и доказательная база | rendered in `site/rubrics/`; sparse published archive |
| `consumer-use` | Пользовательская практика | rendered in `site/rubrics/`; sparse published archive |
| `city-culture` | Город и культура | rendered in `site/rubrics/`; sparse published archive |
| `weak-signals` | Слабые сигналы | rendered in `site/rubrics/`; sparse published archive |

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
8. `tools/build_site.py` renders Today, Radar, Streams and Rubrics from current source/radar/dispatch artifacts.

Conclusion: generated artifacts feed Today, Radar and Streams. Rubric pages are reader-visible but update primarily when published dispatch metadata changes, not directly from raw Daily Radar signals.

## Operational Classification

Fully operational after discovery v2:

- `finance`
- `crypto-finance`
- `ai`
- `tech-hardware-software`
- `dj-audio-creative`
- `science-discovery`

Operational but still weak:

- `gear-style-edc`: broader specialized coverage exists, but no active official source and no current retained radar item until the next ingestion proves density.
- `moscow-city`: active city-media coverage improved, but official city/transport endpoints still failed probe.

Decorative / special-use:

- `general`: intentionally no active sources and not a normal Daily Radar source category.

## Risks

- New active sources were probe-validated, but their actual signal quality and noise profile will only be visible after the next Daily Radar run.
- `arxiv-cs-ai` is high volume; keyword gates must be watched closely.
- `moscow-city` remains the weakest stream because official city and transport endpoints failed probing.
- `gear-style-edc` still lacks active official-source coverage; specialized media signals must not be treated as confirmation.
- Vendor, exchange and official blogs are primary sources for their own claims, not independent verification.
- Fixture build proves rendering, not live ranking selection.

## Recommended Next Fixes

1. Find a stable official Moscow city / transport / culture RSS or API endpoint that returns parseable public data without 403/477.
2. Review first Daily Radar output after adding `arxiv-cs-ai`, `ecb-press`, `fca-news`, `github-security-blog`, `kernel-releases`, `moskvichmag`, `carryology` and `esa-space-science`.
3. Add source-health auto-degrade behavior for newly added feeds if fetch errors or low-density runs repeat.
4. Add a generated source freshness panel to stream pages so readers can see when a stream is underfed.

## Validation Summary

Source-specific validation already run after discovery v2:

- `python3 tools/validate_feeds.py`
- `python3 tools/validate_official_candidates.py`

Final required validation must be run after the full site build.
