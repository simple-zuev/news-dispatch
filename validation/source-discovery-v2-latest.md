# Source Discovery v2 — News Dispatch

Date: 2026-07-01

Status: live source discovery and local probe validation. This file is a validation/report artifact; it does not publish content and does not change Daily Radar workflow.

## Method

- Used current web discovery and direct official endpoint discovery.
- Used existing bookmarks only as seeds, not as source truth.
- Promoted active sources only when `tools/probe_feed_candidates.py` returned parseable RSS/Atom.
- Kept failed, blocked, stale, unstable or noisy sources in candidate tracking instead of active ingestion.
- Kept `general` special-use only.

## Active Sources Added

| Stream | Source | URL | Endpoint | Class | Tier | Freshness evidence | Expected signal type | Noise risk | Validation | Reason |
|---|---|---|---|---|---|---|---|---|---|---|
| `finance` | European Central Bank | https://www.ecb.europa.eu/ | https://www.ecb.europa.eu/rss/press.html | `official_source` | A | Probe: HTTP 200, RSS, 15 items | official policy/payment infrastructure release | speeches/interviews can be low-action | active | Adds euro-area central-bank, digital euro and payments coverage. |
| `crypto-finance` | Financial Conduct Authority | https://www.fca.org.uk/ | https://www.fca.org.uk/news/rss.xml | `official_source` | A | Probe: HTTP 200, RSS, 20 items | official crypto/stablecoin/financial-crime regulatory release | broad FCA consumer/wholesale regulation | active | Adds UK crypto, stablecoin, AML and market-regulation coverage. |
| `ai` | arXiv cs.AI | https://arxiv.org/ | https://rss.arxiv.org/rss/cs.AI | `research_media` | C | Probe: HTTP 200, RSS, 356 items | research preprint signal | very high volume; preprints are not confirmation | active | Adds early AI research coverage with strict preprint framing and keyword gates. |
| `tech-hardware-software` | GitHub Security Blog | https://github.blog/security/ | https://github.blog/security/feed/ | `official_source` | A | Probe: HTTP 200, RSS, 10 items | official security/advisory/supply-chain release | product framing from platform owner | active | Adds official GitHub security, advisory and supply-chain signals. |
| `tech-hardware-software` | kernel.org releases | https://www.kernel.org/ | https://www.kernel.org/feeds/kdist.xml | `official_source` | A | Probe: HTTP 200, RSS, 10 items | official kernel release signal | release-only; no impact analysis by itself | active | Adds primary Linux kernel release cadence signals. |
| `moscow-city` | Москвич Mag | https://moskvichmag.ru/ | https://moskvichmag.ru/feed/ | `public_media` | B | Probe: HTTP 200, RSS, 11 items | city culture/business/urban-life signal | lifestyle and commercial noise | active | Adds a second active Moscow city source while official endpoints remain blocked. |
| `gear-style-edc` | Carryology | https://www.carryology.com/ | https://www.carryology.com/feed/ | `specialized_media` | C | Probe: HTTP 200, RSS, 10 items | carry, bags, material and design signal | reviews and brand enthusiasm | active | Adds focused carry/bag/material coverage missing from sneaker/watch sources. |
| `science-discovery` | ESA Space Science | https://www.esa.int/ | https://www.esa.int/rssfeed/Our_Activities/Space_Science | `official_source` | A | Probe: HTTP 200, RSS, 15 items | official space-science release | agency release is not independent peer review | active | Adds official European space-science mission coverage. |

## Held / Disabled / Candidate Findings

| Stream | Source | Endpoint | Class | Tier | Freshness evidence | Expected signal type | Noise risk | Validation status | Reason |
|---|---|---|---|---|---|---|---|---|---|
| `finance` | BIS | https://www.bis.org/rss/bispress.xml | `official_source` | A | Probe: HTTP 404 | central-bank coordination | none if endpoint found | disabled/rejected | Tested RSS URL was not valid. |
| `finance` | IMF | https://www.imf.org/en/News/RSS | `official_source` | A | Probe: HTTP 200, HTML root | macro/financial policy | broad macro content | candidate | Page exists but is not parseable RSS/Atom. |
| `finance` | World Bank | https://www.worldbank.org/en/news/all?format=rss | `official_source` | A | Probe: HTTP 200, XML parse error | development finance | broad development content | candidate | Endpoint reached but XML was not parseable. |
| `finance` | MOEX | https://www.moex.com/export/news.aspx?cat=100 | `official_source` | A | Final probe: HTTP 403 | exchange news | access instability | candidate | Useful official exchange source, but blocked in probe. |
| `crypto-finance` | FATF | https://www.fatf-gafi.org/en/publications/_jcr_content/root/responsivegrid/mainpar/rss.feed | `official_source` | A | Probe: HTTP 403 | AML/sanctions policy | low if endpoint works | candidate | Valuable AML source but blocked. |
| `crypto-finance` | FinCEN | https://www.fincen.gov/news-room/rss.xml | `official_source` | A | Final probe: timeout; earlier invalid-endpoint result | AML/enforcement release | access instability | candidate | High-trust AML source, but endpoint did not validate. |
| `crypto-finance` | Coinbase Blog | https://blog.coinbase.com/feed | `official_source` | B | Probe: HTTP 403 | exchange/product/legal release | product marketing | candidate | Major exchange source but blocked. |
| `crypto-finance` | Kraken Blog | https://blog.kraken.com/feed | `official_source` | B | Probe: HTTP 200, RSS, 10 items | exchange/product/legal release | token listings and trading promotion | candidate | Parseable but too noisy for active ingestion without stricter rules. |
| `ai` | Google DeepMind Blog | https://deepmind.google/discover/blog/rss.xml | `official_source` | A | Probe: HTTP 404 | AI lab research/product release | none if endpoint found | disabled/rejected | Tested RSS URL was not valid. |
| `ai` | Meta AI Blog | https://ai.meta.com/blog/rss/ | `official_source` | A | Probe: HTTP 404 | AI lab research/product release | product framing | disabled/rejected | Tested RSS URL was not valid. |
| `tech-hardware-software` | Microsoft Security Response Center Blog | https://msrc.microsoft.com/blog/feed | `official_source` | A | Final probe: timeout; earlier XML parse error | security release/advisory | access/parse instability | candidate | High-value source, but endpoint did not validate. |
| `moscow-city` | mos.ru | https://www.mos.ru/rss/news/ | `official_source` | A | Probe: HTTP 403 | official city services/culture/transport | low if accessible | candidate | Still blocked; do not re-enable. |
| `moscow-city` | Moscow Transport | https://transport.mos.ru/rss/news | `official_source` | A | Probe: HTTP 477 | official transport changes | low if accessible | candidate | Official transport source remains inaccessible. |
| `moscow-city` | Мослента | https://moslenta.ru/rss/news | `public_media` | B | Probe: HTTP 200, XML parse error | city news | broad local news | candidate | Endpoint reached but XML was not parseable. |
| `gear-style-edc` | Gear Patrol | https://www.gearpatrol.com/feed/ | `specialized_media` | C | Probe: HTTP 200, XML parse error | gear/design signal | shopping/review noise | candidate | Endpoint reached but XML was not parseable. |
| `gear-style-edc` | GearJunkie | https://gearjunkie.com/feed | `specialized_media` | C | Probe: HTTP 200, RSS, 8 items | outdoor/gear signal | too broad for EDC/design | candidate | Parseable but sample was too broad for active stream use. |
| `gear-style-edc` | Dezeen | https://www.dezeen.com/feed/ | `specialized_media` | C | Probe: HTTP 200, XML parse error | design/material signal | broad architecture/design | candidate | Endpoint reached but XML was not parseable. |
| `dj-audio-creative` | Resident Advisor | https://ra.co/xml/rss.xml | `specialized_media` | C | Probe: HTTP 404 | club-culture signal | event listings | disabled/rejected | Tested RSS URL was not valid. |
| `dj-audio-creative` | Sound On Sound | https://www.soundonsound.com/rss | `specialized_media` | C | Probe: HTTP 410 | production/audio tech | review/catalog noise | disabled/rejected | Tested RSS URL is gone. |
| `dj-audio-creative` | KVR Audio | https://www.kvraudio.com/rss/news.xml | `specialized_media` | C | Final probe: timeout; earlier invalid-endpoint result | plugin release signal | product listing noise | candidate | Tested endpoint did not validate reliably. |
| `science-discovery` | EurekAlert! | https://www.eurekalert.org/rss.xml | `research_media` | C | Final probe: HTTP 404 | research press-release signal | press-release overstatement | disabled/rejected | Tested endpoint did not validate. |
| `science-discovery` | arXiv astro-ph | https://rss.arxiv.org/rss/astro-ph | `research_media` | C | Probe: HTTP 200, RSS, 181 items | astronomy preprint signal | high volume and preprint uncertainty | candidate | Parseable, but needs topic gates before active ingestion. |

## Stream Outcome

| Stream | Active outcome | Remaining weakness |
|---|---|---|
| `finance` | Stronger: ECB added. | MOEX/BIS/IMF/World Bank endpoints still need better parseable feeds. |
| `crypto-finance` | Stronger: FCA added. | FATF/FinCEN/Coinbase unavailable; Kraken too noisy for active use. |
| `ai` | Stronger: arXiv cs.AI added with preprint gates. | DeepMind and Meta AI RSS endpoints not found. |
| `tech-hardware-software` | Stronger: GitHub Security and kernel.org added. | MSRC feed needs a parseable endpoint. |
| `moscow-city` | Better: Москвич Mag added. | Still no active official Moscow source. |
| `gear-style-edc` | Better: Carryology added. | Still no active official source; GearJunkie remains too broad. |
| `dj-audio-creative` | No new active source in v2. | Existing active set is broad enough; RA/SOS/KVR tested endpoints failed. |
| `science-discovery` | Stronger: ESA Space Science added. | EurekAlert blocked; arXiv astro-ph needs tighter gates. |
| `general` | Unchanged special-use only. | None; should not become catch-all. |

## Active / Candidate / Disabled Split

- Active added in v2: 8.
- Candidate/probation-style holds: 16.
- Disabled/rejected tested endpoints: 6.
- No probation ingestion rows were added to `sources/source-lifecycle.json`; this repo currently treats these as candidate/held records rather than probation feed ingestion unless explicitly promoted.

## Notes for Next Review

- Review the first Daily Radar output after adding arXiv cs.AI; high-volume preprint feeds can overwhelm weak keyword gates.
- Moscow still needs an official source with stable public RSS/Atom/API access.
- Exchange/vendor blogs should remain source-reported claims and not become analysis or investment guidance.
