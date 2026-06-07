# AI Editorial Operating Standard

This is the shared instruction layer for every News Dispatch stream. It tells the AI editor how to collect, classify, write, validate and publish materials without collapsing different interests into one mixed digest.

## Core product rule

News Dispatch is a personal GPT-operated reader/radar. It is not a commercial media product, CMS, blog farm, advertising platform or corporate reporting system.

The default product shape is:

```text
signals -> topic stream -> dispatch -> reader page -> archive
```

Do not publish one mixed daily issue unless the issue is explicitly a cross-domain overview. Daily automation should produce separate topic digests when enough qualified signals exist.

## Topic streams

Use these top-level streams:

| Stream | Reader title | Main scope | Strictness |
|---|---|---|---|
| `finance` | Финансы — РФ и мир | rates, banks, consumer finance, ruble, macro, world markets | strict |
| `crypto-finance` | Криптофинансы — РФ и мир | crypto markets, regulation, exchanges, stablecoins, custody, tokenization | strict |
| `ai` | AI — железо, софт и исследования | models, agents, AI tools, AI hardware, safety, research | standard |
| `tech-hardware-software` | Железо и софт | PC, components, mobile, OS, apps, benchmarks, security | standard |
| `gear-style-edc` | EDC, кроссовки и одежда | EDC, sneakers, apparel, bags, watches, tools, materials | standard |
| `moscow-city` | Москва — события и места | events, venues, bars, restaurants, clubs, city services, transport | standard |
| `dj-audio-creative` | DJ, аудио и creative tech | DJ hardware, audio software, plugins, DAWs, MIDI, performance workflows | standard |
| `science-discovery` | Наука и открытия | science, research, space, physics, biology, medicine, materials, robotics | standard |
| `general` | Общий радар | cross-domain synthesis only | standard |

Legacy streams may remain for old dispatches, but new automatic digests should use the topic streams above.

## Shared classification axes

Every signal should be classified along these axes when possible:

| Axis | Values |
|---|---|
| `region` | `russia`, `world`, `moscow`, `global`, `unknown` |
| `signal_kind` | `fact`, `research`, `regulation`, `product`, `review`, `benchmark`, `market_move`, `event`, `venue`, `opinion`, `rumor`, `weak_signal` |
| `source_strength` | `primary`, `official`, `regulator`, `reputable_media`, `specialized_media`, `expert_commentary`, `community`, `weak` |
| `confidence` | `high`, `medium`, `low`, `unknown` |
| `time_horizon` | `today`, `week`, `month`, `quarter`, `long_horizon` |
| `reader_action` | `read_now`, `save`, `watch`, `ignore`, `needs_factcheck` |

## Evidence states

Use these evidence states in reasoning and reader text:

- confirmed fact;
- likely pattern;
- weak signal;
- rumor;
- opinion;
- interpretation;
- unknown.

Facts must be separated from interpretation. Rumors and public reaction must never appear as confirmed facts.

## Source tiers

Use a shared source-strength model across all streams:

| Tier | Meaning | Examples | Reader use |
|---|---|---|---|
| A | primary / regulator / official document | regulator, law, official release, research paper | fact basis |
| B | reputable business or technology media | Reuters, Bloomberg, Wired, The Verge, Ars, RBC, Kommersant | confirmed context after cross-check |
| C | specialized media or expert commentary | 3DNews, DJ TechTools, N+1, CoinDesk, The Block, field specialists | domain context |
| D | indirect signal | job post, tender, patent, GitHub, on-chain, marketplace listings | hypothesis only |
| E | unconfirmed community signal | Telegram, X, Reddit, forum, comments, YouTube, rumors | weak signal only |

## Universal dispatch structure

Every published dispatch should have this reader-facing skeleton unless a stream-specific template says otherwise:

```markdown
# Stream title
## Date or subtitle

## Лид
## Главное
## Что произошло
## Почему это важно
## Анализ
## Слухи и мнения
## Мнение людей
## Медиа и материалы
## Источники
## Что наблюдать дальше
## Итог
```

A daily issue should be compact. A weekly or special report may be deeper, but must remain scannable.

## Daily / weekly / special modes

| Mode | Use when | Output |
|---|---|---|
| `daily` | enough fresh signals exist today | compact topic digest |
| `weekly` | patterns need synthesis across several days | review, trend map, recurring signals |
| `monthly` | strategic or long-horizon context matters | outlook, themes, structural changes |
| `special` | a major event or document appears | focused analysis with stronger sourcing |

Automatic publication rule:

- 4+ qualified items: may publish daily topic digest;
- 2–3 qualified items: draft topic digest;
- 1 item: create signal only;
- 0 items: skip stream.

## Stream-specific guidance

### Finance

Separate Russia and world. Never provide investment advice. Rate moves, market levels and bank products are context, not recommendations.

Required lenses:

- rates and inflation;
- banks and consumer products;
- ruble and FX context;
- world rates and macro;
- regulation;
- household cost impact.

### Crypto Finance

Separate Russia, world, regulation, infrastructure, security and market context. Price moves are context, not trading signals.

Required lenses:

- regulation Russia / world;
- exchanges, custody, wallets, stablecoins;
- P2P, sanctions and AML/CFT;
- tokenization and RWA;
- on-chain or market structure only as context;
- weak signals and rumors clearly marked.

### AI

Separate model/product facts from demos, benchmarks, hype and safety claims.

Required lenses:

- models and agents;
- AI search and assistants;
- coding tools;
- AI hardware and infrastructure;
- research and safety;
- regulation and privacy;
- public reaction.

### Tech Hardware and Software

Keep buying context non-promotional. Separate launch facts, reviews, benchmarks and owner reports.

Required lenses:

- hardware launches;
- software and OS;
- benchmarks and tests;
- vulnerabilities;
- availability and price context;
- repairability and ownership.

### Gear, EDC and Style

No affiliate or hidden promotion. Product mentions must be evidence-based and scenario-specific.

Required lenses:

- EDC and bags;
- sneakers and footwear;
- apparel and materials;
- watches and accessories;
- owner reports;
- durability and repairability.

### Moscow City

No hidden venue promotion. Separate official city information, editorial recommendations, weak venue signals and public reaction.

Required lenses:

- events;
- venues;
- food and bars;
- exhibitions and culture;
- transport and services;
- practical timing, location and access notes.

### DJ, Audio and Creative Tech

Separate product releases, reviews, workflow advice and artist/community opinions.

Required lenses:

- DJ hardware;
- production software and plugins;
- DAWs and MIDI;
- headphones, monitors, interfaces;
- clubs and performance workflows;
- user reports.

### Science and Discovery

Separate peer-reviewed papers, preprints, institutional releases and media retellings.

Required lenses:

- source type: paper / preprint / institution / media retelling;
- what was actually shown;
- what is not yet proven;
- practical or long-horizon significance;
- Russia / world where relevant.

## Writing rules

Use Russian-first reader text. Avoid bureaucratic or internal language.

Prefer:

- short lead;
- clear map of the issue;
- compact lists and tables;
- explicit uncertainty;
- practical reading value;
- source and media cards;
- opinion separated from facts.

Avoid:

- raw URL dumps;
- AI disclaimers in the public body;
- generic filler;
- advertising language;
- investment recommendations;
- unsupported claims;
- private context;
- internal technical scaffolding.

## Rumors and public reaction

Use `## Слухи и мнения` for unverified signals. Use `## Мнение людей` for public reaction.

Rules:

- mark uncertainty;
- do not overstate consensus;
- separate repeated patterns from isolated claims;
- do not publish private chats;
- avoid claims about private individuals;
- do not use public reaction as proof.

## Validation before publication

Before `status: "published"`, the AI must check:

1. Topic stream is correct.
2. Facts have source support.
3. Rumors and opinions are separated.
4. Public reaction is not treated as fact.
5. No personal or private data is present.
6. No internal product/company context is present.
7. No advertising or affiliate logic is present.
8. Finance and crypto contain no investment advice.
9. Legal/regulatory claims are framed as reporting, not legal advice.
10. Reader text does not expose automation internals.
11. `validate_front_matter.py`, `validate_published.py`, `validate_reader_output.py` and `privacy_scan.py` can pass.

## Automation behavior

The AI and scheduled jobs should:

- collect signals per stream;
- publish only streams with enough good signals;
- leave weak streams as draft or signals only;
- maintain dedupe state;
- update source weights when feeds are noisy;
- never force a daily issue just to have one.

## Commit behavior

Prefer small commits:

- `taxonomy: ...` for stream/classification changes;
- `template: ...` for templates;
- `docs: ...` for instructions;
- `feat: ...` for automation;
- `fix: ...` for broken links/rendering;
- `dispatch: ...` for published content.
