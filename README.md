# News Dispatch

**News Dispatch** — public-safe editorial radar for multi-domain analytical dispatches.

## Recent Improvements (Июнь 2026)

- Выделен общий модуль `tools/core.py` с утилитами (slugify, front-matter parser, logging и т.д.)
- Создан `tools/synthesize_dispatch.py` — инструмент для AI-синтеза аналитических диспатчей из сигналов
- Подготовлена основа для LLM-интеграции (Grok / другие модели)
- Код стал чище и модульнее

Следующие этапы: улучшение daily_radar, render_site и workflows.

The project turns public external signals into structured analytical material:

```text
public signal -> source check -> context -> mechanism -> second-order effects -> criteria -> published dispatch
```

It is not a raw news feed, personal notebook, private research dump, internal product memo, investment newsletter, or operational work log.

## Current status

The project is now a working GitHub Pages/static-site MVP with an automated signal radar and publication guardrails.

Implemented:

- canonical stream registry in `data/streams.json`;
- public-safe editorial, source, privacy, security and publishing rules;
- Markdown dispatch format with strict front matter;
- static renderer for published dispatches;
- reader-facing enhancement layer: archive, stream pages, RSS, sitemap, media/source cards, Open Graph metadata and reader sections;
- automated Daily Radar signal collection from public RSS/Atom feeds;
- signal filtering and validation reports;
- reviewed radar and candidate-dispatch validation artifacts;
- GitHub Actions workflows for signal collection, validation and Pages deployment.

The main unfinished layer is editorial synthesis: turning collected signals into verified topic-first dispatches.

## Publication boundary

Everything committed to this repository must be safe for public disclosure.

This includes Git history, branches, pull requests, issues, comments, file names, commit messages, generated reports, deleted files and metadata.

Do not commit:

- private prompts or private calibration notes;
- internal company, product, client, partner, vendor, contractor, roadmap, metric, compliance or security context;
- personal data, account data, private financial data, medical data or employment-sensitive data;
- infrastructure details, private URLs, hostnames, IP addresses, tokens, cookies, keys or credentials;
- screenshots with private UI or metadata.

Personal or organizational context may influence topic selection and weighting, but it must not appear in the published text.

## Editorial model

News Dispatch is an analytical publication system, not a clipping service.

Each significant item should separate:

- fact;
- release;
- research;
- review;
- benchmark;
- user/community signal;
- rumor or unconfirmed signal;
- forecast;
- marketing claim;
- editorial inference.

For high-impact topics, especially finance, crypto-finance, regulation, AML/CFT, sanctions, taxation, cybersecurity and compliance, use primary sources whenever possible and avoid legal, tax, compliance or investment advice.

The operational editorial workflow is documented in `docs/editorial-workflow.md`. Candidate promotion uses `templates/promotion-checklist.md`.

## Canonical streams

Active streams are defined in `data/streams.json`.

Current streams:

- `finance` — финансы РФ и мир;
- `crypto-finance` — криптофинансы РФ и мир;
- `ai` — AI, железо, софт и исследования;
- `tech-hardware-software` — железо и софт;
- `gear-style-edc` — EDC, кроссовки и одежда;
- `moscow-city` — Москва, события и места;
- `dj-audio-creative` — DJ, аудио и creative tech;
- `science-discovery` — наука и открытия;
- `general` — only for cross-domain special issues.

Legacy stream names may remain for historical compatibility, but new navigation and publication logic must use `data/streams.json`.

## Workflows

### Daily Radar Signals

Purpose: collect public RSS/Atom signals and update radar state.

It writes signal-layer and validation artifacts only:

- `signals/`;
- `data/daily-radar-seen.json`;
- `validation/daily-radar-latest.json`;
- `validation/daily-radar-filter-summary.json`;
- `validation/source-health-latest.json`;
- `validation/reviewed-radar-latest.md`;
- `validation/candidate-dispatch-latest.md`.

It must not publish analytical conclusions by itself. Draft dispatch files are not a user-facing deliverable.

### Validate News Dispatch

Purpose: verify repository quality on PRs and pushes to `main`.

It checks Python syntax, front matter, published-content rules, static rendering, reader output and public-safety scanning.

### Deploy News Dispatch Pages

Purpose: build and deploy the public site.

Only dispatches with `status: "published"` are exposed on GitHub Pages. Signals and draft material are not published as finished dispatches.

## Publication workflow

```text
public signal
-> signal capture
-> source/context check
-> reviewed radar
-> candidate dispatch artifact
-> promotion checklist
-> editorial synthesis
-> privacy/public-safety check
-> published dispatch
-> static site deployment
```

Minimal rule: Daily Radar can tell what appeared in public sources. A dispatch can state what it means only after editorial review.

## Repository structure

```text
news-dispatch/
  README.md
  PUBLICATION_BOUNDARY.md
  PRIVACY.md
  EDITORIAL_STANDARD.md
  SOURCE_POLICY.md
  STYLE_GUIDE.md
  PUBLISHING.md
  SECURITY.md

  docs/
    editorial-workflow.md
    radar-quality-audit-2026-06-25.md

  data/
    streams.json
    taxonomy.yml
    daily-radar-seen.json

  sources/
    feeds.json

  dispatches/
    <stream>/*.md

  signals/
    YYYY-MM-DD/<stream>/*.md

  media/
    registry.json
    registry.generated.json

  templates/
    dispatch.md
    privacy-check.md
    promotion-checklist.md

  tools/
    *.py

  validation/
    *.json
    reviewed-radar-latest.md
    candidate-dispatch-latest.md

  site/
    generated static site
```

## Quality target

A good issue is short but not shallow. It distinguishes signal from noise, fact from inference, source report from verified claim, and public evidence from community sentiment. It explains mechanisms, second-order effects, uncertainty, and what should be checked next.
