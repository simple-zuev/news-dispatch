# Live Quality Review — News Dispatch

Date: 2026-07-01

Status: live Daily Radar / Today quality review after source expansion #131/#132.
This report is validation-only. It does not publish content, does not change the
Daily Radar branch policy, and does not edit generated signals.

## Run Summary

- `bash scripts/ops/local-agent-ready-check.sh`: passed.
- `python3 tools/build_site.py --ranking-mode live --media-mode live`: generated
  live ranking, reader policy and `site/today.html`, then failed at the final
  repository privacy scan.
- `python3 tools/validate_reader_output.py`: passed.
- `python3 tools/validate_render_visibility.py`: passed.
- `git diff --check`: passed.

Privacy gate failure:

- `site/daily-radar-ranking-latest.json`
- `site/reader-policy-latest.json`
- `validation/daily-radar-ranking-latest.json`
- `validation/reader-policy-latest.json`

The matched title was `Protecting Cookies with Device Bound Session Credentials`.
This looks like a false positive from a public Google Security Blog title, but
the live build correctly stopped because the machine gate failed.

## Signal Count By Stream

Live ranking input contained 200 items.

| Stream | Live ranking items | Selected by ranking | Reader-safe by policy | Rendered in Today digest |
|---|---:|---:|---:|---:|
| `ai` | 111 | 1 | 2 | 1 |
| `tech-hardware-software` | 40 | 3 | 0 | 0 |
| `crypto-finance` | 29 | 0 | 0 | 0 |
| `science-discovery` | 10 | 3 | 0 | 0 |
| `finance` | 9 | 4 | 7 | 2 |
| `gear-style-edc` | 1 | 0 | 0 | 0 |
| `moscow-city` | 0 | 0 | 0 | 0 |
| `dj-audio-creative` | 0 | 0 | 0 | 0 |

Older retained radar/stream pages still show six streams with retained signals
from the latest generated signal artifact: `ai`, `crypto-finance`, `finance`,
`moscow-city`, `science-discovery`, and `tech-hardware-software`. The live Today
ranking, however, only produced digest content from `ai` and `finance`.

## Top Sources By Retained Signals

Here "retained" means selected by the live ranking step.

| Source | Stream | Class | Selected items | Reader-safe in Today | Assessment |
|---|---|---|---:|---:|---|
| Tom's Hardware | `tech-hardware-software` | `specialized_media` | 3 | 0 | Useful hardware signals, but selected examples include retro/product-like items and remain review-only. |
| ScienceDaily | `science-discovery` | `research_media` | 3 | 0 | Produces readable science items, but selected titles are broad and partly sensational; keep as weak/review-only. |
| Коммерсантъ | `finance` | `public_media` | 2 | 2 | Currently the strongest Today contributor. Useful for Russian finance context. |
| Банк России | `finance` | `official_source` | 2 | 0 | High-trust source, but selected items stayed review-only; policy/source-class handling should be checked. |
| MIT Technology Review | `ai` | `public_media` | 1 | 1 | Useful narrative AI source, but not enough to balance AI stream volume. |

## Source Quality Findings

### arXiv cs.AI

`arxiv-cs-ai` produced 32 live ranking items. None were selected into Today.
One item was blocked by a generic language pattern because the paper title
included `Long-Horizon`, which looks like a financial long/short pattern to the
policy scanner.

Assessment: arXiv cs.AI is too noisy as an uncapped live feed. It is valuable as
early research coverage, but should be capped, sampled, and always framed as
preprint/review-only unless a separate high-signal research selector promotes it.

### Moscow

`moscow-city` produced no live ranking items. The stream page still has one older
M24 signal from the generated radar artifact, but live Today cannot use Moscow
reliably yet.

Assessment: Moscow remains weak. Keep blocked official candidates disabled until
validated, and prefer stable official/city feeds or a stricter M24 city filter
over broad media.

### Gear / Style / EDC

`gear-style-edc` produced one live ranking item from Sneaker News: official images
of a Nike SB shoe. It was not selected and is not reader-safe.

Assessment: the stream is still underfed and currently risks product-card noise.
Sneaker/news retail feeds should be capped or downweighted unless the item has a
business, design, material, repairability, retail, or broader culture signal.

### DJ / Audio / Creative

`dj-audio-creative` produced zero live ranking items.

Assessment: the stream remains underfed. It needs validated stable feeds from
vendor release notes, audio software/plugin makers, DJ hardware makers, or
industry media before it can contribute to Today.

### Finance / Crypto / AI / Tech

- `finance` is the most useful Today stream today: 9 live items, 4 selected, 2
  rendered in Today.
- `crypto-finance` is high-volume and high-interest: 29 live items, including
  MiCA, FCA, ESMA, SEC and market-structure topics, but none reached Today. This
  is a ranking/reader-policy opportunity, not a source shortage.
- `ai` is overfed: 111 live items, dominated by OpenAI News and arXiv cs.AI.
  Today only used one MIT Technology Review item.
- `tech-hardware-software` has strong official/security volume, but selected
  Today candidates came from Tom's Hardware while official Google/Apple/NVIDIA
  items were not rendered in Today. The stream is high-signal but needs better
  selection and privacy-scan handling.

## Noisy Sources

| Source | Evidence | Recommendation |
|---|---|---|
| OpenAI News | 74 AI ranking items, zero selected into Today. | Cap per source/day and apply stronger recency or release-type filtering. |
| arXiv cs.AI | 32 AI ranking items, zero selected; one false policy block. | Cap, preprint-label, and require topic gates before ranking high. |
| Google Security Blog | 21 items across tech/AI; triggered privacy false positive via `Cookies`. | Keep, but fix scanner context and cap archive-like bursts. |
| Tom's Hardware | 3 selected tech items, all review-only; includes retro/product-like content. | Downweight consumer novelty/product-card topics unless infrastructure/security impact is clear. |
| ScienceDaily | 3 selected science items, all review-only; broad/sensational topics. | Keep review-only and downweight health/alien/asteroid headlines without primary confirmation. |
| Sneaker News | 1 EDC item, not selected; pure product-card signal. | Downweight or require design/business/material context. |
| Hypebeast | Fetch parse error during live build. | Keep disabled/candidate until stable parsing is proven. |

## Underfed Streams

| Stream | Current state | Recommendation |
|---|---|---|
| `moscow-city` | 0 live ranking items; one older retained M24 signal on stream page. | Keep weak label; add/promote only validated official/city feeds or strict city-filtered media. |
| `gear-style-edc` | 1 live item, product-card-like, not reader-safe. | Add higher-signal design/retail/material/repairability sources; cap pure product feeds. |
| `dj-audio-creative` | 0 live items. | Prioritize validated vendor release feeds and stable industry media feeds. |
| `crypto-finance` | 29 live items but 0 Today items. | Not underfed, but under-selected; tune ranking to surface official/regulatory crypto items safely. |

## Sources To Cap Or Downweight

- `openai-news`: cap daily volume and avoid archive flood.
- `arxiv-cs-ai`: cap hard; keep as preprint/review-only by default.
- `google-security-blog`: cap bursts and fix privacy false-positive context.
- `tomshardware`: downweight retro, product-card and novelty hardware unless
  there is infrastructure, supply-chain, security, or market relevance.
- `science-daily`: downweight broad science headlines without primary-source
  confirmation.
- `sneaker-news`: downweight unless there is design, business, retail, material
  or market context.

## Sources To Promote Or Protect

- `kommersant-finance`: already useful for Today finance; keep.
- `cbr-news`: high-trust finance source; investigate why selected official items
  stayed review-only despite being official.
- `fca-news`, `esma-news`, `crypto-finance-sec-press-releases`: preserve and
  consider ranking boosts for official crypto/regulatory items so crypto can
  appear in Today without relying on market-media summaries.
- `google-security-blog`, `apple-newsroom-tech`, `nvidia-blog-tech`: keep as
  high-signal tech sources, but improve selection so official security/platform
  items beat lower-value product-media items.
- `m24-news` / Moscow city media: keep as limited Moscow coverage, but do not
  treat it as enough to make Moscow fully operational.

## Sources To Remain Candidate Or Disabled

Keep the following outside active ingestion until probes are stable and
source-specific rules are defined:

- Moscow blocked/unstable candidates: `mskagency-candidate`, `mos-ru-news-reprobe`,
  `transport-mos-news-candidate`, `moslenta-candidate`, broad Interfax Moscow.
- Gear/design unstable or noisy candidates: `gearpatrol-candidate`,
  `gearjunkie-candidate`, `dezeen-candidate`.
- DJ/audio unstable candidates: `resident-advisor-candidate`,
  `soundonsound-candidate`, `kvr-audio-candidate`.
- Finance/crypto blocked candidates: BIS, IMF, World Bank, FATF, FinCEN,
  Coinbase where the tested endpoints are blocked, HTML-only, stale, too noisy
  or not parseable.

## Today Quality

Today is readable as a page and contains the autonomous digest sections:

- `Главное за период`
- `События с наибольшим эффектом`
- `Регуляторика и правовой контур`
- `Инфраструктура и участники рынка`
- `Продуктовые и организационные импликации`
- `Радар слабых сигналов`
- `Что проверять дальше`
- `Источники и уровень надёжности`

However, Today is not yet reliable enough for actual zero-touch daily use after
this live run:

- The final build failed the privacy gate.
- The rendered digest used only 3 items: 2 finance and 1 AI.
- Crypto, Moscow, EDC, DJ/audio, tech and science did not appear as reader-safe
  Today content despite several of them having raw live signal volume.
- The digest is structurally useful, but too narrow and too dependent on
  public-media finance items.

Today useful: **no, not for actual daily use after this live run**.

## Recommended Next Fixes

1. Fix the privacy scanner false positive for public article titles such as
   `Protecting Cookies with Device Bound Session Credentials` without weakening
   real secret detection.
2. Add per-source daily caps for `openai-news`, `arxiv-cs-ai`,
   `google-security-blog`, `tomshardware`, `science-daily`, and product-card
   lifestyle feeds.
3. Add a stronger official-source ranking path so CBR, FCA, ESMA, SEC, Google
   Security, Apple and NVIDIA official items can outrank lower-value media
   summaries when safe.
4. Keep arXiv cs.AI active only with preprint labels, hard caps and topic gates.
5. Strengthen Moscow with validated official/city endpoints or strict M24
   filtering; do not mark blocked Moscow candidates active.
6. Rework EDC source rules to reject pure product cards unless they carry a
   design, material, business, retail, repairability or market signal.
7. Add validated DJ/audio release-note and industry feeds before expecting the
   stream to appear in Today.
8. Tune crypto ranking so official/regulatory MiCA, FCA, ESMA and SEC items can
   appear in Today as source-reported regulatory signals.
