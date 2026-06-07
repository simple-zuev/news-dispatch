# Topic Digest Taxonomy

News Dispatch should not publish one mixed daily issue by default. The product model is a personal reader with separate topical digests and shared signal classification.

## Top-level digests

### 1. Finance

Slug: `finance`

Scope:
- Russia: rates, banks, cards, deposits, consumer credit, mortgages, inflation, ruble, regulation, major banks.
- World: rates, Fed/ECB/BOE, markets, banks, macro, consumer finance, payments, fintech regulation.

Default sections:
- Russia
- World
- Banks and consumer products
- Markets and rates
- Regulation
- What to watch

Boundary:
- No investment advice.
- Separate facts, market interpretation and opinion.

### 2. Crypto Finance

Slug: `crypto-finance`

Scope:
- Russia: crypto regulation, P2P restrictions, exchange access, taxation, banks, enforcement, digital ruble adjacency.
- World: BTC/ETH, ETFs, stablecoins, exchanges, custody, settlement, tokenization, regulation, market infrastructure.

Default sections:
- Russia
- World
- Market structure
- Regulation
- Infrastructure and security
- Weak signals and rumors
- What to watch

Boundary:
- No trading advice.
- Price moves are context, not recommendations.

### 3. AI

Slug: `ai`

Scope:
- Models, agents, assistants, search, coding tools, research, safety, regulation, enterprise adoption.
- AI hardware only when it matters for AI systems: GPUs, NPUs, AI PCs, local inference devices, data centers.

Default sections:
- Models and products
- Agents and tools
- Hardware and infrastructure
- Research and safety
- Regulation and policy
- Public reaction
- What to watch

### 4. Tech Hardware and Software

Slug: `tech-hardware-software`

Scope:
- PC hardware, mobile devices, OS, apps, games, benchmarks, chips, components, cybersecurity, consumer software.
- Similar reading mode to 3DNews, Ars Technica, The Verge, AnandTech-style coverage.

Default sections:
- Hardware
- Software and platforms
- Reviews and benchmarks
- Security
- Buying context
- What to watch

Boundary:
- Reviews and shopping context must stay non-advertising.

### 5. Gear, EDC and Style

Slug: `gear-style-edc`

Scope:
- EDC, bags, tools, watches, sneakers, outerwear, technical apparel, materials, repairability, ownership.

Default sections:
- EDC and bags
- Sneakers and footwear
- Apparel and materials
- Watches and accessories
- Reviews and owner reports
- What to watch

Boundary:
- No affiliate logic.
- Separate product facts, user opinions and style interpretation.

### 6. Moscow City

Slug: `moscow-city`

Scope:
- Events, venues, restaurants, bars, clubs, exhibitions, urban services, transport, city culture, practical Moscow context.

Default sections:
- Events
- Venues
- Food and bars
- Culture
- City services and transport
- Practical notes
- What to watch

Boundary:
- No hidden promotion.
- Clearly mark weak venue/event signals.

### 7. DJ, Audio and Creative Tech

Slug: `dj-audio-creative`

Scope:
- DJ equipment, mixers, controllers, CDJs, turntables, headphones, monitors, audio interfaces, plugins, DAWs, MIDI, performance software, clubs and creator workflows.

Default sections:
- DJ hardware
- Audio software
- Production and plugins
- Performance workflows
- Reviews and user reports
- What to watch

### 8. Science and Discovery

Slug: `science-discovery`

Scope:
- Science, research, discoveries, space, physics, biology, medicine, climate, materials, robotics, cognition, HCI, Russia and world.

Default sections:
- World research
- Russian research
- Space and physics
- Biology and medicine
- Materials and robotics
- Long-horizon signals
- What to watch

Boundary:
- Separate preprints, peer-reviewed papers, institutional releases and media retellings.

## Shared classification axes

Every signal and dispatch item should carry these axes where possible:

- `topic_stream`: top-level digest slug.
- `region`: `russia`, `world`, `moscow`, `global`, `unknown`.
- `signal_kind`: `fact`, `research`, `regulation`, `product`, `review`, `market_move`, `event`, `venue`, `opinion`, `rumor`, `weak_signal`.
- `source_strength`: `primary`, `official`, `reputable_media`, `specialized_media`, `expert_commentary`, `community`, `weak`.
- `confidence`: `high`, `medium`, `low`, `unknown`.
- `time_horizon`: `today`, `week`, `month`, `quarter`, `long_horizon`.
- `reader_action`: `read_now`, `save`, `watch`, `ignore`, `needs_factcheck`.

## Publishing model

Default behavior should be topic-first:

- one mixed homepage as dashboard only;
- separate daily/weekly digest pages by stream;
- no mixed daily dispatch unless explicitly titled as cross-domain overview;
- each digest may have Russia/World subsections where relevant.

## Automation model

Daily automation should create separate draft or published dispatches per stream when enough signals exist. If a stream has too few good signals, it should create signals only and skip a weak published digest.

Recommended threshold:

- publish stream digest: 4+ qualified items;
- draft stream digest: 2-3 qualified items;
- signals only: 1 item.
