# Dispatch Contract

This document defines the stable publication contract for News Dispatch.

## Purpose

A dispatch is an analytical issue, not a raw list of links. It turns public signals into a structured reading map: facts, analysis, weak signals, public reaction, media, sources, and next observations.

The style should be analytical rather than prescriptive. The issue may describe hypotheses, potential effects, weak signals, risks, and zones to watch. It should not read like direct operational instructions.

## Pipeline

```text
Markdown dispatch
→ static render
→ site enhancement
→ media metadata enrichment
→ media preview insertion
→ reader section enhancement
→ validation
→ GitHub Pages deploy
```

Generation and deployment are separate. The daily workflow may generate content manually. The Pages workflow publishes the site.

## Front matter groups

Each public dispatch must describe:

- identity: title, date, period, stream, type, language, status;
- publication review: review level, publication scope, safety flags, review markers;
- summary and tags;
- sources and source annotations;
- media and media annotations;
- optional visuals.

Published dispatches must have a clear summary and at least one public source.

## Source contract

The source fields are parallel lists:

- `sources`
- `source_titles`
- `source_types`
- `source_notes`

For published dispatches, the lists must have matching lengths. Notes should explain why the source matters.

Recommended source types:

- Official source
- Research / preprint
- Business media
- Technology media
- Industry media
- Opinion / column
- Community signal

## Media contract

The media fields are parallel lists:

- `media`
- `media_titles`
- `media_types`
- `media_notes`

Media URLs should usually be a subset of sources or closely related public materials. Media cards are enriched from the source URL itself through page metadata. Random image search must not be used. If page metadata is unavailable, a local fallback preview may be used.

Every visual media card should expose attribution: material source, image source, preview origin, and source domain.

## Body sections

A published dispatch must contain:

```text
## Лид
## Главное
## Что произошло
## Почему это важно
## Анализ
## Медиа и материалы
## Источники
## Что наблюдать дальше
## Итог
```

Recommended additional sections:

```text
## Скрытые и косвенные сигналы
## Слухи и мнения
## Мнение людей
```

If the issue contains rumor-like language, it must include a rumor/opinion section.

## Generator requirements

Automated generators should produce valid dispatches on the first pass:

- complete front matter groups;
- non-empty sources for published output;
- matching parallel list lengths;
- media selected from key source items;
- required body sections present;
- analytical framing rather than commands;
- no raw URLs in the reader body before media/source sections;
- no technical publication metadata leaking into reader text.

## Automation policy

Scheduled generation stays disabled until the manual path is stable. The safe order is:

```text
manual render
manual daily generation
manual validation
manual commit
Pages deployment
scheduled daily generation
```
