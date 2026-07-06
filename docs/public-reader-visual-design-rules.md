# Public Reader Visual Design Rules

PR target: #147

Source of truth:

- `docs/public-reader-product-spec.md`
- `docs/public-reader-wireframes.md`

This document defines visual rules for the public reader before further
implementation. It does not authorize renderer, CSS, test, source, workflow,
dispatch or generated-site changes.

## 1. Design principles

Text-first:

- The reader must work when every article has no image.
- Titles, excerpts, time, rubric and source carry the hierarchy.
- Media can support a story, but it cannot become the structure of the page.

News-first:

- The first content block on the homepage is `Latest news`.
- `/news/` and `/news/<stream>/` start with chronological reader items.
- `/today/` starts with the main selected story.
- Product explanation, source transparency and digests are secondary to current
  reader content.

No system explanations:

- Public pages must not describe automation, gates, ranking, validation,
  workflow state, branch names, PR numbers, run IDs or diagnostic files.
- Public copy must be reader-facing and Russian-first.
- Source confidence may be visible, but it must be expressed in plain reader
  language.

No fake media:

- Do not use decorative image blocks to imply unavailable reporting.
- Do not invent documentary images, screenshots, charts or thumbnails.
- Do not use gradients as media stand-ins.

Compact, readable, calm:

- Layouts should feel like a serious editorial reader, not a dashboard or
  marketing page.
- Use restrained color, clear type scale, quiet borders and predictable spacing.
- Cards are allowed only when they improve scanning; nested cards are forbidden.

## 2. Color tokens

Tokens define intent, not implementation names. Future CSS may map these to
custom properties.

| Token | Value | Use |
| --- | --- | --- |
| `background` | `#f7f7f4` | Page background. Warm off-white, never a gradient. |
| `surface` | `#ffffff` | Item rows, digest cards and source cards. |
| `surface_alt` | `#f1f1ec` | Quiet secondary surfaces such as empty states. |
| `text` | `#161616` | Primary text and headlines. |
| `muted_text` | `#62625d` | Metadata, source labels and secondary notes. |
| `border` | `#d8d8cf` | Row separators, card borders and section rules. |
| `accent` | `#1d5f73` | Primary links, active navigation and restrained emphasis. |
| `accent_hover` | `#134b5b` | Link hover and focus emphasis. |
| `focus` | `#b35c1e` | Keyboard focus ring or explicit active state. |
| `warning_bg` | `#fff4d6` | Public safety or uncertainty labels only. |
| `warning_text` | `#6f4a00` | Text on warning labels. |
| `safety_bg` | `#eef6ee` | Confirmed/source-supported claim labels. |
| `safety_text` | `#28612d` | Text on safety labels. |

Stream markers:

| Stream | Marker |
| --- | --- |
| AI | `#4868a8` |
| Finance | `#28705f` |
| Crypto finance | `#8a5b18` |
| Moscow | `#8a3f48` |
| Science | `#5b5f9f` |
| Gear | `#606060` |

Stream markers must be small accents: a left rule, dot, compact label border or
metadata chip. They must not become full-card backgrounds.

Warning and safety labels:

- Use warning labels for weak signals, source-reported claims and uncertainty.
- Use safety labels for confirmed, official or well-supported material.
- Labels must be short and reader-facing.
- Labels must not expose internal states such as `selected`, `reader_safe`,
  `validation`, `probe`, `pass`, `fail` or `gate`.

Forbidden colors and patterns:

- Purple, blue-purple or neon gradients.
- Full-card gradients.
- Hero gradients.
- Repeated color blocks that simulate unavailable media.
- Bright red alert styling for normal editorial uncertainty.
- Dark dashboard palettes.
- One-hue palette variations that make all sections feel the same.

## 3. Typography

Font stack:

```css
font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
  "Helvetica Neue", Arial, sans-serif;
```

Base rules:

- Body text uses `16px` on desktop and `16px` on mobile.
- Do not scale type with viewport width.
- Letter spacing is `0`.
- Use font weight before color or decoration for hierarchy.
- Keep line length readable: 65 to 78 characters for long text blocks.

Desktop type scale:

| Role | Size | Line height | Weight |
| --- | --- | --- | --- |
| H1 page title | `34px` | `1.15` | `700` |
| H2 section title | `24px` | `1.25` | `700` |
| H3 card or subsection title | `19px` | `1.3` | `650` |
| Feed title | `20px` | `1.3` | `650` |
| Today main title | `24px` | `1.25` | `700` |
| Digest title | `21px` | `1.3` | `650` |
| Excerpt | `16px` | `1.55` | `400` |
| Metadata | `13px` | `1.35` | `500` |
| Navigation | `14px` | `1.2` | `600` |
| Rubric pill | `13px` | `1.2` | `600` |

Mobile type scale:

| Role | Size | Line height | Weight |
| --- | --- | --- | --- |
| H1 page title | `26px` | `1.2` | `700` |
| H2 section title | `21px` | `1.25` | `700` |
| H3 card or subsection title | `18px` | `1.3` | `650` |
| Feed title | `19px` | `1.3` | `650` |
| Today main title | `22px` | `1.25` | `700` |
| Digest title | `19px` | `1.3` | `650` |
| Excerpt | `16px` | `1.5` | `400` |
| Metadata | `12px` | `1.35` | `500` |
| Navigation | `14px` | `1.2` | `600` |
| Rubric pill | `12px` | `1.2` | `600` |

Typography guardrails:

- Feed rows must not rely on tiny metadata alone; the title and excerpt must
  remain readable.
- Metadata may wrap, but it must not overlap the title, source link or excerpt.
- Long source titles and original titles should collapse or move below primary
  content.

## 4. Layout grid

Desktop page shell:

- Max content width: `1120px`.
- Page margins: `32px` minimum on desktop.
- Main content starts immediately below masthead spacing, not after a hero.
- Use a single editorial column for feeds and Today content.

Homepage columns:

- Desktop: two-column layout after the masthead.
- Primary column: latest news, `minmax(0, 2fr)`.
- Secondary column: Today preview, rubrics, latest digests, `minmax(280px, 1fr)`.
- Latest news remains first in DOM and first visually.
- At widths below `860px`, collapse to one column with latest news first.

Feed width:

- `/news/` and `/news/<stream>/` content width: `760px` to `820px`.
- Optional secondary links may sit below the feed, not as a competing sidebar.
- Feed rows are full-width within the feed column.

Today width:

- `/today/` content width: `720px` to `800px`.
- The main story can use a slightly larger surface, but not a hero panel.
- Other selected items remain compact rows.

Digest width:

- Digest index: `860px` maximum for list content.
- Digest detail: `720px` maximum for article reading.

Sources width:

- Source index: `920px` maximum.
- Source detail: `760px` maximum.

Mobile behavior:

- One column at all widths below `860px`.
- Page margins: `16px`.
- Horizontal scrolling is allowed only for compact rubric navigation.
- Navigation must not push real news out of the first mobile screen.
- No fixed-height media slots.

## 5. Components

Header:

- Contains site name and primary navigation: Today, News, Digests, Sources.
- RSS may appear as a utility link.
- Header height should stay compact: `56px` to `72px` on desktop, `52px` to
  `64px` on mobile.
- Do not add status badges, validation labels, run metadata or admin controls.

Latest news row:

- Order: time and rubric, title, excerpt, source, original title if useful,
  source link.
- Use a thin border or quiet surface boundary between rows.
- Source link must be visible but must not turn the entire row into a link.
- Rows must be readable without media.

Stream feed row:

- Same content order as latest news row.
- Add a small stream marker or rubric pill.
- Include confidence or claim label only when it is meaningful to the reader.
- Do not show internal stream routing explanations.

Today highlight:

- Used for the main story on `/today/` and the compact Today preview on the
  homepage.
- Contains title, 2 to 4 sentence explanation, why-it-matters text and source.
- May use a slightly stronger border or background, but no large hero treatment.
- Must not describe why an algorithm selected the item.

Today selected item:

- Compact row for other important items.
- Contains rubric, title, excerpt, source and link.
- `why it matters` is editorial context, not mechanical selection language.
- Avoid repeated items from the same story cluster.

Digest card:

- Contains title, date, rubric, issue type, thesis excerpt and source summary.
- Looks distinct from news rows through structure, not decoration.
- Must not be a placeholder analytical card.
- Must not link draft, validation or issue-prep artifacts.

Source row:

- Contains source name, type, reader role, recent reader items and source page
  link.
- Raw feed URLs are not primary content.
- Source confidence must be translated into plain language.
- No lifecycle state, probe error, score or maintenance note.

Rubric pill:

- Compact text label with optional small stream marker.
- Uses reader-facing rubric names, not internal slugs.
- Active state may use border, underline or accent text.
- Do not use oversized button-like pills that dominate feed content.

Empty state:

- Short, calm reader-facing message.
- Offer links to other rubrics, Today or digests.
- Do not show stack traces, fetch errors, probe failures, validation files or
  operational status.
- Do not fill the space with generic claims or fake cards.

## 6. Media rules

Allowed:

- Real source media with source, rights status and alt text.
- Official charts, documents, screenshots or embeds when rights permit.
- Generated charts only when based on structured public data and clearly
  labeled.
- Small neutral stream marker when no media exists.

Forbidden:

- Gradient placeholders.
- Large fallback images.
- Fake documentary images.
- Random stock-like or search-result images.
- Repeated generic thumbnails.
- Decorative illustrations that imply reporting not present in the source.
- Promotional vendor imagery unless the item is explicitly about that vendor
  and attribution is clear.

Absent media behavior:

- Layout must not reserve large empty image slots.
- Text rows remain balanced with title, excerpt and metadata.
- Digest and source cards remain complete without images.
- A stream marker may identify rubric, but it must stay small.

## 7. Spacing

Page spacing:

- Desktop page margin: `32px`.
- Tablet page margin: `24px`.
- Mobile page margin: `16px`.
- Masthead-to-content spacing: `24px` desktop, `16px` mobile.

Section spacing:

- Between major homepage sections: `32px` desktop, `24px` mobile.
- Between feed header and first row: `16px`.
- Between digest/source sections: `28px` desktop, `20px` mobile.

Row spacing:

- Feed row padding: `18px 0` desktop, `16px 0` mobile.
- Metadata-to-title gap: `6px`.
- Title-to-excerpt gap: `8px`.
- Excerpt-to-source gap: `10px`.

Card spacing:

- Card padding: `18px` desktop, `16px` mobile.
- Card border radius: `8px` maximum.
- Gap between cards: `14px` to `18px`.
- Do not place cards inside other cards.

Navigation spacing:

- Primary nav item gap: `18px` desktop.
- Mobile nav item gap: `12px`.
- Rubric pill gap: `8px`.

## 8. Forbidden UI patterns

The public reader must not use:

- Giant hero panels.
- Purple or gradient cards.
- Repeated fake visuals.
- Link-only feed rows.
- Generic filler text.
- Internal diagnostic language.
- Dashboards for automation.
- Validation status blocks.
- Ranking score explanations.
- Source probe error tables.
- Raw JSON, YAML, front matter or file paths.
- "Machine gate passed" or "selected by algorithm" banners.
- Empty landing pages that describe the product before showing news.
- Broad mixed pages that collapse Today, news, digests and sources into one
  visual format.

## 9. Visual acceptance checklist

Homepage:

- Latest public news appears before product explanation.
- At least two visible items include title, time, rubric, excerpt, source and
  source link.
- Today is a secondary preview, not a replacement for latest news.
- Rubric navigation and latest digests are visible below the news lead.
- No hero, gradient placeholder, fake media or diagnostic status.

`/news/`:

- The page is a chronological feed, newest first.
- Rubric navigation is visible and uses reader-facing names.
- Every visible row has title, time, rubric, excerpt, source and source link.
- Rows are not link-only.
- No ranking, selection, validation or workflow language.

`/news/<stream>/`:

- Visible title uses the reader rubric name, not an internal slug.
- First screen contains real news items.
- Feed rows remain chronological within the rubric.
- Related digests are secondary.
- No stream routing explanation, source-rule detail or empty filler card.

`/today/`:

- Main story appears immediately with title, date, explanation and source.
- Other selected items are compact and limited.
- `why it matters` reads as editorial context.
- Watch-next and sources-used sections are secondary.
- No pass/fail status, gate name, ranking score, run ID or algorithm language.

`/digests/`:

- Digests are visually distinct from news rows.
- Each digest card includes title, date, rubric and analytical thesis.
- Source information is present but not dominant.
- No placeholder analytical cards.
- No generated draft, validation or issue-prep artifacts are linked.

`/sources/`:

- The page explains source transparency in reader language.
- Source rows show name, type, role and recent reader items.
- Raw feed URLs are not primary content.
- No lifecycle states, probe errors, scores or maintenance notes.
- Sources do not compete with news as the first reader surface.

Mobile:

- First mobile screen shows real news or the Today main story, depending on the
  route.
- Text wraps without overlap or critical truncation.
- Source and time metadata remain visible.
- Navigation is compact but reachable.
- No fixed-height fake image blocks.
- No section spacing that turns the page into a landing page before news.
