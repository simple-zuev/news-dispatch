# Public Reader Wireframes

PR target: #146

Source of truth: `docs/public-reader-product-spec.md`.

This document defines low-fidelity reader wireframes only. It does not authorize
renderer, CSS, test, source, workflow, dispatch or generated-site changes.

## Product frame

The public reader has four visible product surfaces:

- Today: a short selected overview;
- News: broad chronological feeds by rubric;
- Digests: separate analytical issues;
- Sources: transparency about public sources.

Internal diagnostics are not reader pages. Public UI must show news immediately
and must not explain automation, gates, ranking, probes or validation files.

## Shared content blocks

Every news-like item must be composed from these exact reader blocks when the
data exists:

- `title`: Russian reader title.
- `source`: readable source name.
- `time`: publication or discovery time.
- `excerpt`: 1-3 sentence summary.
- `original title`: source-language original title, collapsed or secondary.
- `source link`: direct link to the public source.
- `rubric navigation`: visible links to Today, News, Digests, Sources and
  public rubrics.

Required item order:

```text
time + rubric
title
excerpt
source
original title, if useful
source link
```

Never make the source link the whole item. Never replace the excerpt with raw
URL text.

## Shared page hierarchy

Above the fold:

- masthead and primary navigation;
- page title only when it helps orientation;
- current news or selected reader items;
- source and time metadata for visible items.

Secondary:

- rubric navigation;
- Today cross-links;
- latest digests;
- source context;
- pagination or older links.

Hidden or collapsed:

- original titles when they are long or not Russian;
- source notes longer than one line;
- old items after the first page;
- full source transparency detail;
- no internal diagnostics under any collapsed panel.

## 1. Homepage

Purpose: front door that shows current public news first.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
|                                      Sources RSS            |
+------------------------------------------------------------+
| Latest news                                                |
| [10:40] [AI] Russian reader title                          |
| Excerpt: what happened and why it matters in plain language |
| Source: readable source name            Open source         |
| Original: original title, if useful                        |
|                                                            |
| [10:15] [Finance] Russian reader title                     |
| Excerpt                                                    |
| Source                                      Open source     |
+------------------------------------------------------------+
| Today                                                      |
| Main selected item title                                   |
| 2 sentence overview.                                       |
| Open Today                                                 |
+------------------------------------------------------------+
| Rubrics                                                    |
| AI | Finance | Crypto finance | Moscow | Science | Gear    |
+------------------------------------------------------------+
| Latest digests                                             |
| Digest title - date - short thesis                         |
+------------------------------------------------------------+
```

Above the fold:

- masthead;
- primary navigation;
- `Latest news`;
- at least two news items with title, source, time and excerpt.

Secondary:

- Today preview;
- rubric navigation;
- latest digests;
- RSS utility link.

Hidden or collapsed:

- long original titles;
- older latest-news items;
- source explanations.

Acceptance checklist:

- Latest public news appears before product explanation.
- Visible items include title, source, time, excerpt and source link.
- Rubric navigation is visible on the page.
- No gradient placeholder, fake media, service text or diagnostic status.
- Today is a preview, not a replacement for latest news.

## 2. `/news/`

Purpose: all public news, newest first, with rubric filtering.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| News                                                       |
| Rubrics: All AI Finance Crypto Moscow Science Gear         |
+------------------------------------------------------------+
| [time] [rubric] Title                                      |
| Excerpt                                                    |
| Source: name                            Open source        |
| Original: source title, collapsed if long                  |
+------------------------------------------------------------+
| [time] [rubric] Title                                      |
| Excerpt                                                    |
| Source                                  Open source        |
+------------------------------------------------------------+
| Older news / pagination                                     |
+------------------------------------------------------------+
```

Above the fold:

- title `News`;
- rubric navigation;
- first chronological news items.

Secondary:

- pagination;
- links to Today and digests;
- source type or confidence label.

Hidden or collapsed:

- original title when it crowds the list;
- older pages;
- detailed source notes.

Acceptance checklist:

- The page is a chronological feed, not a dashboard.
- Every visible item has time, title, excerpt, source and source link.
- Rubric navigation is usable without knowing internal stream names.
- No link-only rows.
- No internal ranking, selection or validation language.

## 3. `/news/<stream>/`

Purpose: one rubric feed, newest first.

Public label rule: the URL may use a stream slug, but the visible page title
must use the reader rubric name.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| AI                                                         |
| Short rubric description, one reader sentence at most.      |
| Rubrics: All Finance Crypto Moscow Science Gear            |
+------------------------------------------------------------+
| [time] Title                                               |
| Excerpt                                                    |
| Source: name | confidence label         Open source        |
| Original: original title                                   |
+------------------------------------------------------------+
| [time] Title                                               |
| Excerpt                                                    |
| Source                                  Open source        |
+------------------------------------------------------------+
| Related digests                                            |
| Digest title - why it is relevant                          |
+------------------------------------------------------------+
```

Above the fold:

- rubric title;
- compact rubric navigation;
- first items for the rubric.

Secondary:

- related digests;
- source labels;
- older items.

Hidden or collapsed:

- long original titles;
- source detail;
- older pagination.

Acceptance checklist:

- The page title is reader-facing, not an internal slug.
- Items are chronological within the rubric.
- The first screen contains actual news items.
- Related digests are secondary.
- No stream routing explanations, source-rule details or empty filler cards.

## 4. `/today/`

Purpose: short selected overview of the current day.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| Today                                                      |
| Date                                                       |
+------------------------------------------------------------+
| Main story                                                 |
| Title                                                      |
| Excerpt: 2-4 sentence explanation.                         |
| Why it matters: one concise paragraph.                     |
| Source: name                            Open source        |
+------------------------------------------------------------+
| Other important items                                      |
| [rubric] Title                                             |
| Excerpt                                                    |
| Source                                  Open source        |
|                                                            |
| [rubric] Title                                             |
| Excerpt                                                    |
| Source                                  Open source        |
+------------------------------------------------------------+
| Watch next                                                 |
| Short public developments to monitor.                      |
+------------------------------------------------------------+
```

Above the fold:

- title `Today`;
- date;
- main story;
- source link for the main story.

Secondary:

- other selected items;
- watch-next list;
- sources used today;
- links to feeds and related digests.

Hidden or collapsed:

- original titles;
- long source lists;
- older Today archives.

Acceptance checklist:

- Today is short and selected, not a full feed.
- The main story appears immediately.
- Each selected item has a source, time or date, title and excerpt.
- `why it matters` is editorial, not mechanical.
- No public wording about gates, pass/fail status, ranking scores or run IDs.

## 5. `/digests/`

Purpose: index of analytical issues.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| Digests                                                    |
| Analytical issues, newest first.                           |
| Rubrics: All AI Finance Crypto Moscow Science Gear         |
+------------------------------------------------------------+
| Digest title                                               |
| Date | rubric | issue type                                 |
| Thesis excerpt                                             |
| Sources: count or key source names                         |
| Open digest                                                |
+------------------------------------------------------------+
| Digest title                                               |
| Date | rubric | issue type                                 |
| Thesis excerpt                                             |
+------------------------------------------------------------+
```

Above the fold:

- title `Digests`;
- rubric navigation;
- latest digest cards with thesis excerpts.

Secondary:

- older digests;
- stream filters;
- source count or key source names.

Hidden or collapsed:

- long source lists;
- full issue outlines;
- archival pagination.

Acceptance checklist:

- Digests are clearly distinct from news items.
- Each digest shows title, date, rubric and analytical thesis.
- The page does not look like a raw feed.
- Source information is present but not dominant.
- No generated draft, validation or issue-prep artifacts are linked.

## 6. `/digests/<stream>/`

Purpose: analytical issues for one rubric.

Public label rule: visible title is the reader rubric, not the internal stream
identifier.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| AI digests                                                 |
| Analytical issues for this rubric.                         |
| Rubrics: All Finance Crypto Moscow Science Gear            |
+------------------------------------------------------------+
| Featured digest                                            |
| Title                                                      |
| Date | issue type | confidence label                       |
| Thesis excerpt                                             |
| Open digest                                                |
+------------------------------------------------------------+
| Earlier in this rubric                                     |
| Title - date - short thesis                                |
| Title - date - short thesis                                |
+------------------------------------------------------------+
```

Above the fold:

- rubric digest title;
- latest or featured digest;
- rubric navigation.

Secondary:

- earlier digests;
- related news feed link;
- source summary.

Hidden or collapsed:

- full source lists;
- old archives;
- implementation details.

Acceptance checklist:

- The page is issue-led, not item-led.
- The latest digest has a thesis excerpt.
- There is a clear route back to the news feed for the rubric.
- No placeholder analytical cards.
- No internal issue-generation status.

## 7. `/sources/`

Purpose: source transparency, not operational diagnostics.

Low-fidelity wireframe:

```text
+------------------------------------------------------------+
| News Dispatch                         Today News Digests    |
+------------------------------------------------------------+
| Sources                                                    |
| Public sources used for reader items.                      |
+------------------------------------------------------------+
| Rubrics                                                    |
| AI | Finance | Crypto finance | Moscow | Science | Gear    |
+------------------------------------------------------------+
| Source name                                                |
| Type: official / media / specialist / community            |
| Useful for: plain-language source role                     |
| Recent items: title, title                                 |
| Open source page                                           |
+------------------------------------------------------------+
| Source name                                                |
| Type                                                       |
| Useful for                                                 |
+------------------------------------------------------------+
```

Above the fold:

- title `Sources`;
- short transparency sentence;
- rubric navigation;
- first source cards.

Secondary:

- recent items per source;
- source detail links;
- source type filters.

Hidden or collapsed:

- full source notes;
- recent item overflow;
- confidence explanation longer than one line.

Acceptance checklist:

- The page explains transparency in reader language.
- Source cards show name, type, role and recent reader items.
- No feed probe errors, lifecycle states, scores or maintenance notes.
- Raw feed URLs are not primary content.
- Source pages do not compete with news as the first reader surface.

## 8. Mobile homepage

Purpose: same as homepage, with news first and compact navigation.

Low-fidelity wireframe:

```text
+------------------------------+
| News Dispatch          Menu   |
+------------------------------+
| Latest news                  |
| 10:40 | AI                   |
| Title wraps to 2-3 lines     |
| Excerpt                      |
| Source name                  |
| Open source                  |
+------------------------------+
| 10:15 | Finance              |
| Title                        |
| Excerpt                      |
| Source name                  |
+------------------------------+
| Today                        |
| Main selected item           |
| Open Today                   |
+------------------------------+
| Rubrics                      |
| AI Finance Crypto Moscow     |
| Science Gear                 |
+------------------------------+
| Digests                      |
| Latest digest title          |
+------------------------------+
```

Above the fold:

- masthead with compact menu;
- `Latest news`;
- first news item with time, title, excerpt and source.

Secondary:

- second news item;
- Today preview;
- rubrics;
- digests.

Hidden or collapsed:

- full navigation menu;
- original titles;
- older latest-news items.

Acceptance checklist:

- The first mobile screen shows real news, not a hero or service explanation.
- Text wraps cleanly without overlap.
- Source and time remain visible.
- Navigation is compact but reachable.
- No fake image blocks inserted to fill space.

## 9. Mobile news feed

Purpose: scan a chronological feed on a narrow screen.

Low-fidelity wireframe:

```text
+------------------------------+
| News Dispatch          Menu   |
+------------------------------+
| News                         |
| Rubrics: All AI Finance ...  |
+------------------------------+
| 10:40 | AI                   |
| Title wraps naturally        |
| Excerpt                      |
| Source: name                 |
| Open source                  |
| Original title               |
+------------------------------+
| 10:15 | Moscow               |
| Title                        |
| Excerpt                      |
| Source                       |
+------------------------------+
| Older                        |
+------------------------------+
```

Above the fold:

- masthead;
- page title;
- horizontally wrapping or scrollable rubric navigation;
- first feed item.

Secondary:

- remaining feed items;
- pagination;
- Today and digest links.

Hidden or collapsed:

- original title for long non-Russian headlines;
- source detail;
- full rubric descriptions.

Acceptance checklist:

- Mobile feed remains chronological.
- Each item is readable without opening a detail page.
- No text overlaps or truncates critical metadata.
- Rubric navigation does not dominate the first screen.
- No system explanations or diagnostic panels.

## Visual rules

Mandatory rules:

- no gradients;
- no fake placeholder images;
- no large media without a real source asset;
- no service or explanatory text before news;
- no internal diagnostics;
- no raw JSON, YAML or file paths;
- no ranking, gate, probe, branch, PR or workflow language;
- no decorative card grids that repeat the same empty pattern;
- no media unless it has source, rights and alt metadata.

Allowed visual language:

- restrained editorial typography;
- compact metadata labels;
- whitespace that improves scanning;
- simple borders or rules;
- source and confidence labels;
- reader-facing rubric names.

## Bad examples from rejected iterations

Giant gradient placeholders:

```text
+------------------------------------------------------------+
| LARGE COLORED GRADIENT HERO                                |
| "Your intelligent radar for everything"                    |
| No news visible above the fold.                            |
+------------------------------------------------------------+
```

Why rejected: it delays current news and looks like a landing page, not a
reader.

Repeated fake cards:

```text
+----------------+ +----------------+ +----------------+
| Placeholder    | | Placeholder    | | Placeholder    |
| Lorem ipsum    | | Lorem ipsum    | | Lorem ipsum    |
+----------------+ +----------------+ +----------------+
```

Why rejected: it creates visual bulk without reader information.

System explanations:

```text
Daily Radar passed source governance and selected items after ranking.
Validation artifact: validation/daily-radar-ranking-latest.json
```

Why rejected: operational mechanics are not public reader content.

Link-only feeds:

```text
10:40 https://example.com/article
10:15 https://example.org/post
```

Why rejected: the reader gets no title, source context, excerpt or reason to
open the item.

Generic filler text:

```text
Important developments across technology and finance are reshaping the future.
Stay tuned for more insights and analysis.
```

Why rejected: it says nothing concrete and competes with real news.

## Implementation gate for future UI work

Future implementation should start only after these wireframes are approved.
The first implementation PR should map existing generated reader pages to this
document before visual polish. Visual polish must not introduce gradients, fake
images, diagnostics or explanatory-first layouts.
