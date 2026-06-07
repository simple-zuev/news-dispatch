# Hourly Radar Model

News Dispatch should be optimized for checking topic areas during the day, not only for reading daily digests.

## Product decision

The primary product mode is now:

```text
hourly public signal collection -> live topic radar -> daily / weekly synthesis
```

Daily digests remain useful, but they are not the main delivery mechanism. The main reader need is to open the site during the day and see what changed across personal zones of interest.

## Layers

### 1. Hourly signals

Atomic updates collected from public sources.

Stored under:

```text
signals/YYYY-MM-DD/<stream>/
```

Each signal must remain factual and cautious:

- what appeared;
- where it appeared;
- source type;
- stream;
- confidence / source status;
- why it might matter;
- what needs verification.

### 2. Live radar pages

Reader-facing pages built from recent signals.

Target paths:

```text
site/radar/index.html
site/radar/<stream>.html
```

These pages should show recent updates grouped by stream. They are not articles and do not need article-style analysis.

### 3. Daily synthesis

A daily dispatch should be generated only when enough signals exist in a stream and there is something to synthesize.

It should answer:

- what repeated;
- what changed;
- which sources matter;
- what needs watching next.

### 4. Weekly and special reports

Weekly and special reports are deeper analysis, not raw news feeds.

## Hourly publication rule

An hourly run may publish live radar updates if:

- new public signals are found;
- deduplication passes;
- privacy scan passes;
- generated pages remain static and lightweight.

If no new signals are found, the run should not create a pointless commit.

## Daily digest rule

Daily digests should be generated from accumulated signals, not from scratch as a mixed article.

Recommended behavior:

- 4+ qualified signals in a stream: publish or draft a topic digest;
- 2–3 signals: draft only;
- 1 signal: signal only;
- 0 signals: skip stream.

## Reader experience

The homepage should link to the live radar.

The live radar should support quick scanning:

- stream cards;
- newest first;
- source label;
- timestamp;
- short summary;
- direct source link;
- no long editorial prose;
- no raw URL dumps.

## Safety

Hourly radar must not become a rumor amplifier.

Rules:

- source appearance is a fact;
- source claim is not automatically a fact;
- weak sources stay weak;
- public reaction is not proof;
- no investment advice;
- no hidden promotion;
- no private context.

## Automation

Suggested schedule:

```yaml
- cron: "17 * * * *"
```

The job should commit only if new signals or rendered radar pages changed.

## Architecture

```text
sources/feeds.json
        ↓
tools/hourly_radar.py
        ↓
signals/YYYY-MM-DD/<stream>/*.md
        ↓
data/hourly-radar-log.json
        ↓
site/radar/index.html
site/radar/<stream>.html
        ↓
privacy_scan.py
        ↓
GitHub Pages
```

## Relationship to digests

Digests become summary products:

- daily: synthesis of the day;
- weekly: trend and pattern review;
- monthly: outlook;
- special: focused analysis of a major event or document.
