# Public Reader Product Spec

PR target: #145

## 1. Product goal

News Dispatch should be a public Russian-first reader for understanding what
changed across selected topic areas.

The public product must show news immediately. A reader opening the site should
see current, understandable items before any explanation of the product,
publication process or internal checks.

The product structure is:

- news feeds: broad chronological lists by rubric;
- Today: a short selected overview across the most important current items;
- digests: separate analytical issues with synthesis and context;
- sources: transparency pages about public sources and their editorial role;
- internal diagnostics: private or repository-only operational artifacts, not
  public reader pages.

The public UI must never explain internal mechanics such as ranking pipelines,
validation files, automation states, gate names, source lifecycle internals or
debugging reports.

## 2. User jobs

Primary reader jobs:

- Check what changed today without reading a long essay.
- Scan a rubric chronologically and open only relevant items.
- Understand why a selected item matters.
- Read a deeper analytical issue when a topic deserves synthesis.
- Verify where information came from.
- Distinguish confirmed facts, source-reported claims, weak signals and
  editorial interpretation.
- Avoid promotional, advisory or internal-system language.

Secondary reader jobs:

- Browse older items by rubric.
- Move from a short item to its source.
- Move from a news item to a related digest.
- Understand source confidence without seeing operational diagnostics.

## 3. Sitemap

Target public sitemap:

```text
/
/today/
/news/
/news/<rubric>/
/digests/
/digests/<slug>/
/sources/
/sources/<source-slug>/
/about/
/rss.xml
```

Non-public or non-reader paths:

```text
/validation/*
/signals/*
/data/internal/*
/debug/*
/admin/*
/drafts/*
/radar/diagnostics/*
```

If operational files are generated for machine checks, they must not be linked
from public navigation and must not be presented as reader pages.

## 4. Page roles

Homepage:

- acts as the front door;
- shows latest public news immediately;
- gives one clear route to Today;
- gives direct routes to rubric feeds and recent digests;
- does not explain automation or internal policy.

News feed pages:

- show chronological reader-safe news items by rubric;
- prioritize scan speed, timestamps, source labels and concise summaries;
- do not behave like analytical digests.

Today:

- shows a short selected overview;
- includes only the most useful current items;
- groups items by editorial importance, not by internal selection reason;
- points to source links and related feeds or digests.

Digest pages:

- publish analytical issues;
- contain synthesis, context, uncertainty, public reaction when appropriate,
  sources and watch-next sections;
- remain separate from chronological news feeds.

Source index:

- explains source coverage at a reader level;
- groups sources by rubric, type and confidence;
- avoids operational lifecycle status unless translated into plain reader
  language.

Source detail pages:

- identify the public source;
- explain why it is useful;
- state what kind of claims it can support;
- link to recent reader items using that source.

About page:

- explains editorial intent, public-safety standards and no-advertising policy;
- stays short and reader-facing.

## 5. Homepage wireframe

```text
+------------------------------------------------------------+
| Masthead                                      Today  News   |
|                                                 Digests RSS |
+------------------------------------------------------------+
| Latest news                                                |
| [timestamp] [rubric] Headline                              |
| Short reader summary.                                      |
| Source label                                 Read / Source |
|                                                            |
| [timestamp] [rubric] Headline                              |
| Short reader summary.                                      |
| Source label                                 Read / Source |
+------------------------------------------------------------+
| Today                                                      |
| 3-7 selected current items with why-it-matters text.        |
| Link: open Today                                           |
+------------------------------------------------------------+
| Rubrics                                                    |
| AI | Finance | Crypto finance | Moscow | Science | Gear    |
+------------------------------------------------------------+
| Latest digests                                             |
| Digest title, date, short thesis, rubric                   |
+------------------------------------------------------------+
```

Homepage rules:

- The first content block after navigation is latest public news.
- No first-screen hero that only describes the product.
- No validation status panel.
- No raw JSON, YAML, file names or internal run labels.
- Rubric navigation must be visible without requiring the reader to understand
  repository structure.

## 6. News feed wireframe

```text
+------------------------------------------------------------+
| News / <Rubric>                                            |
| Short rubric label, not an internal stream explanation.     |
+------------------------------------------------------------+
| Sort: newest first                         RSS for rubric   |
+------------------------------------------------------------+
| [time] Headline                                             |
| Summary in 1-3 sentences.                                  |
| Why it matters: one concise sentence.                       |
| Source: readable source name             Open source        |
| Tags / confidence label                                      |
+------------------------------------------------------------+
| [time] Headline                                             |
| Summary...                                                  |
+------------------------------------------------------------+
| Pagination / older items                                    |
+------------------------------------------------------------+
```

News feed rules:

- Chronological order is the default.
- Items are broad by rubric and may include many source types.
- The page is not a dashboard and not a review queue.
- Empty rubrics should show a quiet empty state and links to other rubrics, not
  operational failure details.

## 7. Today wireframe

```text
+------------------------------------------------------------+
| Today                                                      |
| Date and short editorial lead.                             |
+------------------------------------------------------------+
| Main story                                                 |
| Headline                                                   |
| 2-4 sentence explanation.                                  |
| Why it matters                                             |
| Source / related feed / related digest                     |
+------------------------------------------------------------+
| Other important items                                      |
| 1. Headline - why it matters - source                      |
| 2. Headline - why it matters - source                      |
| 3. Headline - why it matters - source                      |
+------------------------------------------------------------+
| Watch next                                                 |
| Short list of public developments to monitor.              |
+------------------------------------------------------------+
| Sources used today                                         |
| Reader-readable source list.                               |
+------------------------------------------------------------+
```

Today rules:

- Today is a short selected overview, not a dump of every feed item.
- Today may be generated autonomously when public safety and quality checks pass,
  but the public page must not describe those checks as product content.
- If there is not enough safe current content, Today should show a small
  reader-facing fallback: no forced filler, no internal failure report.
- Today items should link outward to source material and inward to relevant
  rubric feeds or digests.

## 8. Digest wireframe

```text
+------------------------------------------------------------+
| Digest title                                               |
| Date, rubric, issue type, confidence label                  |
+------------------------------------------------------------+
| Lead                                                       |
| What this issue explains and why now.                      |
+------------------------------------------------------------+
| Main points                                                |
| - Point                                                    |
| - Point                                                    |
| - Point                                                    |
+------------------------------------------------------------+
| What happened                                              |
| Factual source-backed summary.                             |
+------------------------------------------------------------+
| Why it matters                                             |
| Editorial analysis with clear limits.                      |
+------------------------------------------------------------+
| Public reaction / weak signals, when appropriate           |
| Clearly marked and separated.                              |
+------------------------------------------------------------+
| What to watch next                                         |
+------------------------------------------------------------+
| Sources and media                                          |
+------------------------------------------------------------+
```

Digest rules:

- A digest is an analytical issue, not a chronological feed page.
- A digest must have a clear thesis or synthesis reason.
- Weak signals and public reaction must be separated from confirmed facts.
- Finance, regulation, legal, compliance and crypto-finance topics require
  especially cautious wording and source support.

## 9. Source page wireframe

Source index:

```text
+------------------------------------------------------------+
| Sources                                                    |
| Short transparency statement.                              |
+------------------------------------------------------------+
| By rubric                                                  |
| AI: source cards                                           |
| Finance: source cards                                      |
| Moscow: source cards                                       |
+------------------------------------------------------------+
| Source card                                                |
| Name                                                       |
| Type: official / media / specialist / community            |
| Useful for: short plain-language explanation               |
| Recent items                                               |
+------------------------------------------------------------+
```

Source detail:

```text
+------------------------------------------------------------+
| Source name                                                |
| Type, language, public URL                                 |
+------------------------------------------------------------+
| Why this source is used                                    |
| What it is good for                                        |
| What it is not enough to prove by itself                   |
+------------------------------------------------------------+
| Recent reader items from this source                       |
+------------------------------------------------------------+
```

Source page rules:

- Explain transparency, not internals.
- Use plain source confidence labels.
- Do not expose raw lifecycle states, ranking scores, probe errors, stack traces
  or feed maintenance notes.

## 10. Content model for news item

Required reader-facing fields:

- `id`
- `published_at`
- `updated_at`, optional
- `rubric`
- `title`
- `summary`
- `why_it_matters`
- `source_name`
- `source_url`
- `source_type`
- `claim_type`
- `confidence_label`
- `language`
- `tags`
- `related_digest`, optional
- `media`, optional

Editorial-only fields may exist in source data, but must not render publicly:

- ranking score;
- validation state;
- feed probe details;
- automation run ID;
- internal selection reason;
- private notes;
- debug paths.

Reader rendering requirements:

- show title, time, rubric, summary, source and confidence;
- keep source-reported claims visibly attributable;
- avoid advice language;
- avoid unsupported causal claims;
- hide implementation metadata.

## 11. Content model for Today item

Required reader-facing fields:

- `id`
- `date`
- `rank`
- `title`
- `summary`
- `why_selected`
- `why_it_matters`
- `rubric`
- `source_name`
- `source_url`
- `claim_type`
- `confidence_label`
- `watch_next`, optional
- `related_news_item`, optional
- `related_digest`, optional

Today rendering requirements:

- show the strongest selected items first;
- keep `why_selected` editorial and reader-facing, not mechanical;
- cap the page to a short overview;
- avoid duplicate items from the same story cluster;
- include direct source access for every material claim.

## 12. Media policy

Media should help understanding. It must not be decorative filler.

Allowed media:

- source-provided images with usable metadata;
- official charts, documents, screenshots or embeds when rights permit;
- generated diagrams or charts based on structured public data;
- local fallback previews only when source metadata is unavailable and the
  fallback does not mislead.

Required media metadata:

- title;
- source;
- source URL;
- image or media origin;
- rights status;
- alt text;
- reason for inclusion.

Forbidden media use:

- random image search as article decoration;
- stock-like hero images unrelated to the item;
- unattributed images;
- misleading crops;
- promotional vendor imagery unless the article is explicitly about that vendor
  and attribution is clear;
- media that implies endorsement.

## 13. Visual design rules

Public pages should feel like a serious editorial reader:

- Russian-first interface copy;
- latest content visible before explanation;
- strong typographic hierarchy;
- restrained color palette;
- compact metadata labels;
- readable line length;
- clear source and confidence labels;
- cards only where they improve scanning;
- no nested cards;
- no raw operational panels;
- mobile layouts tested for readable wrapping.

Navigation rules:

- primary navigation: Today, News, Digests, Sources;
- rubric navigation must use reader names, not internal stream names;
- RSS is a utility link, not a primary reader action;
- diagnostics, drafts and validation pages must not appear in public navigation.

## 14. Forbidden public UI patterns

The public UI must not include:

- dashboards for internal automation;
- validation status blocks;
- ranking score explanations;
- source probe error tables;
- raw feed URLs as primary content;
- YAML, JSON or front matter;
- "selected by algorithm" explanations;
- "machine gate passed" banners;
- debug file paths;
- internal branch, PR or workflow names;
- draft queues;
- admin-like controls;
- empty landing pages that describe the product before showing news;
- hero sections that delay current news;
- broad mixed feeds that collapse Today, news and digests into one format.

## 15. Acceptance criteria

Product acceptance:

- The homepage shows current public news immediately.
- Today is visibly a short selected overview.
- News feeds are chronological lists by rubric.
- Digests are separate analytical issues.
- Sources are transparency pages, not diagnostics.
- Internal diagnostics are not linked as public reader pages.
- Public UI does not explain automation mechanics.
- Every material news or Today item has a readable source.
- Weak or source-reported claims are clearly labeled.
- No page encourages investment, legal, compliance or purchasing decisions
  without limits and evidence.

Implementation acceptance:

- Public navigation exposes only reader pages.
- Generated diagnostics remain private, repository-only or unlinked.
- Renderer changes preserve the product separation above.
- CSS changes preserve immediate news visibility and mobile readability.
- Tests or validators catch diagnostic leakage into public pages.
- Existing dispatch publication gates remain intact.

## 16. Implementation phases

Phase 1: Product structure freeze

- Adopt this spec as the public reader target.
- Stop UI changes that mix diagnostics with reader pages.
- Map current generated pages to the target sitemap.
- Identify public pages that should be removed, renamed or hidden in a later PR.

Phase 2: Data and content contracts

- Define stable reader models for news items and Today items.
- Decide which operational fields are allowed to influence selection but never
  render publicly.
- Add tests for public metadata leakage.

Phase 3: Navigation and page separation

- Update public navigation to Today, News, Digests and Sources.
- Keep internal diagnostics out of navigation and sitemap output.
- Ensure homepage starts with latest news.

Phase 4: Reader page rendering

- Implement news feed pages by rubric.
- Implement the short Today overview.
- Keep digests as analytical issue pages.
- Implement source index and source detail pages as transparency surfaces.

Phase 5: Visual polish and validation

- Apply editorial visual hierarchy after page roles are correct.
- Test mobile and desktop layouts.
- Add validators for immediate-news visibility, diagnostic leakage and source
  presence.
- Review public pages as a reader, not as an operator.
