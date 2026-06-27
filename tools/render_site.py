#!/usr/bin/env python3
"""Render News Dispatch Markdown files into a small static site.

No external dependencies. This renderer is intentionally conservative:
- reads public-safe published Markdown dispatches from dispatches/**/*.md;
- writes HTML pages to site/dispatches/;
- writes a dynamic homepage, dispatch archive, stream pages and rubric pages;
- writes RSS and sitemap files;
- does not fetch remote resources;
- does not inject tracking scripts.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path

from core import DISPATCH_DIR, ROOT, SITE_DIR, coalesce, parse_front_matter_file
from stream_registry import streams as registry_streams

OUTPUT_DIR = SITE_DIR / "dispatches"
STREAM_DIR = SITE_DIR / "streams"
RUBRIC_DIR = SITE_DIR / "rubrics"
RUBRICS_PATH = ROOT / "data" / "rubrics.json"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"


@dataclass(frozen=True)
class StreamInfo:
    slug: str
    title: str
    review_label: str
    description: str
    strict: bool = False

    @property
    def relative_url(self) -> str:
        return f"streams/{self.slug}.html"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.relative_url}"


@dataclass(frozen=True)
class RubricInfo:
    slug: str
    title: str
    description: str

    @property
    def relative_url(self) -> str:
        return f"rubrics/{self.slug}.html"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.relative_url}"


def load_streams() -> list[StreamInfo]:
    items: list[StreamInfo] = []
    for stream in registry_streams():
        items.append(
            StreamInfo(
                slug=str(stream["slug"]),
                title=str(stream["title"]),
                review_label=str(stream.get("label", "Редакционная проверка")),
                description=str(stream.get("description", "")),
                strict=bool(stream.get("strict", False)),
            )
        )
    return items


def load_rubrics() -> list[RubricInfo]:
    if not RUBRICS_PATH.exists():
        return []
    data = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
    items: list[RubricInfo] = []
    for rubric in data.get("rubrics", []):
        slug = str(rubric.get("slug", "")).strip()
        if not slug:
            continue
        items.append(
            RubricInfo(
                slug=slug,
                title=str(rubric.get("title", slug)),
                description=str(rubric.get("description", "")),
            )
        )
    return items


STREAMS = load_streams()
RUBRICS = load_rubrics()
STREAM_BY_SLUG = {stream.slug: stream for stream in STREAMS}
RUBRIC_BY_SLUG = {rubric.slug: rubric for rubric in RUBRICS}


@dataclass
class Dispatch:
    source_path: Path
    title: str
    date: str
    stream: str
    summary: str
    body: str
    output_name: str
    primary_rubric: str = ""
    issue_type: str = ""
    publication_mode: str = ""

    @property
    def url(self) -> str:
        return f"{BASE_URL}/dispatches/{self.output_name}"

    @property
    def relative_url(self) -> str:
        return f"dispatches/{self.output_name}"


def output_slug(path: Path) -> str:
    """Preserve the historical render-site URL mapping."""
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def load_dispatch(path: Path) -> Dispatch | None:
    doc = parse_front_matter_file(path)
    if doc.errors:
        return None
    meta = doc.metadata
    if coalesce(meta.get("status"), default="draft") != "published":
        return None
    title = coalesce(meta.get("title"), default=path.stem.replace("-", " ").title())
    return Dispatch(
        source_path=path,
        title=title,
        date=coalesce(meta.get("date")),
        stream=coalesce(meta.get("stream"), default="general"),
        summary=coalesce(meta.get("summary")),
        body=doc.body.strip(),
        output_name=f"{output_slug(path)}.html",
        primary_rubric=coalesce(meta.get("primary_rubric")),
        issue_type=coalesce(meta.get("issue_type")),
        publication_mode=coalesce(meta.get("publication_mode")),
    )


def ordered_dispatches(dispatches: list[Dispatch]) -> list[Dispatch]:
    return sorted(dispatches, key=lambda item: (item.date, item.title), reverse=True)


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def render_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    out = ["<table>", "<thead><tr>"]
    out.extend(f"<th>{inline_markup(cell)}</th>" for cell in header)
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            out.extend(f"<td>{inline_markup(cell)}</td>" for cell in row)
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "\n".join(out)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph)
            out.append(f"<p>{inline_markup(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            out.append("<ul>")
            out.extend(f"<li>{inline_markup(item)}</li>" for item in list_items)
            out.append("</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(render_table(table_lines))
            table_lines = []

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        flush_table()

        if stripped.startswith("### "):
            flush_paragraph()
            flush_list()
            out.append(f"<h3>{inline_markup(stripped[4:].strip())}</h3>")
        elif stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            out.append(f"<h2>{inline_markup(stripped[3:].strip())}</h2>")
        elif stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            out.append(f"<h1>{inline_markup(stripped[2:].strip())}</h1>")
        elif stripped.startswith("- "):
            flush_paragraph()
            list_items.append(stripped[2:].strip())
        else:
            paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    flush_table()
    return "\n".join(out)


def head(title: str, description: str, css_href: str = "styles/main.css") -> str:
    return f"""<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="alternate" type="application/rss+xml" title="News Dispatch RSS" href="{BASE_URL}/rss.xml">
  <link rel="stylesheet" href="{css_href}">
</head>"""


def dispatch_stream_title(dispatch: Dispatch) -> str:
    stream = STREAM_BY_SLUG.get(dispatch.stream)
    return stream.title if stream else dispatch.stream


def rubric_title(slug: str) -> str:
    rubric = RUBRIC_BY_SLUG.get(slug)
    return rubric.title if rubric else slug


def dispatch_meta_label(dispatch: Dispatch) -> str:
    parts = [dispatch_stream_title(dispatch), dispatch.date]
    if dispatch.primary_rubric:
        parts.append(rubric_title(dispatch.primary_rubric))
    if dispatch.issue_type:
        parts.append(dispatch.issue_type)
    if dispatch.publication_mode and dispatch.publication_mode != "published":
        parts.append(dispatch.publication_mode)
    return " · ".join(part for part in parts if part)


def dispatch_card(dispatch: Dispatch, prefix: str = "") -> str:
    return f"""<article class="card">
  <p class="label">{html.escape(dispatch_meta_label(dispatch))}</p>
  <h3><a href="{prefix}{html.escape(dispatch.relative_url)}">{html.escape(dispatch.title)}</a></h3>
  <p>{html.escape(dispatch.summary)}</p>
</article>"""


def stream_card(stream: StreamInfo, prefix: str = "", count: int | None = None) -> str:
    count_label = "" if count is None else f" · {count} выпусков"
    strict_class = " strict" if stream.strict else ""
    return f"""<article class="card{strict_class}">
  <p class="label">{html.escape(stream.review_label)}{html.escape(count_label)}</p>
  <h3><a href="{prefix}{html.escape(stream.relative_url)}">{html.escape(stream.title)}</a></h3>
  <p>{html.escape(stream.description)}</p>
</article>"""


def rubric_card(rubric: RubricInfo, prefix: str = "", count: int | None = None) -> str:
    count_label = "" if count is None else f" · {count} выпусков"
    return f"""<article class="card">
  <p class="label">Аналитическая рубрика{html.escape(count_label)}</p>
  <h3><a href="{prefix}{html.escape(rubric.relative_url)}">{html.escape(rubric.title)}</a></h3>
  <p>{html.escape(rubric.description)}</p>
</article>"""


def page_template(dispatch: Dispatch, body_html: str) -> str:
    safe_title = html.escape(dispatch.title)
    safe_summary = html.escape(dispatch.summary)
    safe_meta = html.escape(dispatch_meta_label(dispatch))
    return f"""<!doctype html>
<html lang="ru">
{head(dispatch.title, dispatch.summary, css_href="../styles/main.css")}
<body class="dispatch-page">
  <header class="article-hero">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">{safe_meta}</p>
    <h1>{safe_title}</h1>
    <p class="lede">{safe_summary}</p>
  </header>
  <main class="article-body">
    {body_html}
  </main>
</body>
</html>
"""


def homepage_template(dispatches: list[Dispatch]) -> str:
    latest = ordered_dispatches(dispatches)[:6]
    latest_cards = "\n".join(dispatch_card(dispatch) for dispatch in latest)
    stream_cards = "\n".join(stream_card(stream) for stream in STREAMS[:8])
    rubric_counts = rubric_counts_for(dispatches)
    rubric_cards = "\n".join(rubric_card(rubric, count=rubric_counts.get(rubric.slug, 0)) for rubric in RUBRICS[:6])
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch", "Личный reader/radar по технологиям, рынкам, AI, финансам, Москве, вещам, аудио и науке.")}
<body>
  <header class="masthead">
    <p class="eyebrow">Персональный reader/radar</p>
    <h1>News Dispatch</h1>
    <p class="lede">Личный статический радар по зонам интереса: live-сигналы в течение дня, тематические полки и аналитические выпуски, когда есть что синтезировать.</p>
    <p class="hero-actions"><a href="radar/index.html">Live Radar</a><a href="dispatches.html">Архив выпусков</a><a href="streams/index.html">Потоки</a><a href="rubrics/index.html">Рубрики</a><a href="rss.xml">RSS</a></p>
  </header>

  <main>
    <section class="panel">
      <h2>Последние выпуски</h2>
      <p>Итоговые материалы и тематические synthesis-выпуски.</p>
    </section>

    <section class="grid latest-grid" aria-label="Latest dispatches">
      {latest_cards}
    </section>

    <section class="panel">
      <h2>Рубрики</h2>
      <p>Аналитические линзы поверх потоков: регулирование, инфраструктура, market structure, research evidence и weak signals.</p>
    </section>

    <section class="grid" aria-label="Dispatch rubrics">
      {rubric_cards}
    </section>

    <section class="panel">
      <h2>Потоки</h2>
      <p>Темы разделены на самостоятельные reader-полки.</p>
    </section>

    <section class="grid" aria-label="Dispatch streams">
      {stream_cards}
    </section>
  </main>
</body>
</html>
"""


def archive_template(dispatches: list[Dispatch]) -> str:
    cards = "\n".join(dispatch_card(dispatch) for dispatch in ordered_dispatches(dispatches))
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Выпуски", "Архив выпусков.")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="index.html">News Dispatch</a>
    <p class="eyebrow">Архив</p>
    <h1>Выпуски</h1>
    <p class="lede">Архив опубликованных материалов.</p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def stream_index_template(dispatches: list[Dispatch]) -> str:
    counts = {stream.slug: 0 for stream in STREAMS}
    for dispatch in dispatches:
        counts[dispatch.stream] = counts.get(dispatch.stream, 0) + 1
    cards = "\n".join(stream_card(stream, prefix="../", count=counts.get(stream.slug, 0)) for stream in STREAMS)
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Потоки", "Тематические потоки.", css_href="../styles/main.css")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">Потоки</p>
    <h1>Потоки</h1>
    <p class="lede">Темы, форматы и направления reader/radar.</p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def stream_page_template(stream: StreamInfo, dispatches: list[Dispatch]) -> str:
    stream_dispatches = [dispatch for dispatch in ordered_dispatches(dispatches) if dispatch.stream == stream.slug]
    cards = "\n".join(dispatch_card(dispatch, prefix="../") for dispatch in stream_dispatches)
    empty = "" if cards else "<p>В этом потоке пока нет выпусков.</p>"
    return f"""<!doctype html>
<html lang="ru">
{head(f"News Dispatch — {stream.title}", stream.description, css_href="../styles/main.css")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">{html.escape(stream.review_label)}</p>
    <h1>{html.escape(stream.title)}</h1>
    <p class="lede">{html.escape(stream.description)}</p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
    {empty}
  </main>
</body>
</html>
"""


def rubric_counts_for(dispatches: list[Dispatch]) -> dict[str, int]:
    counts = {rubric.slug: 0 for rubric in RUBRICS}
    for dispatch in dispatches:
        if dispatch.primary_rubric:
            counts[dispatch.primary_rubric] = counts.get(dispatch.primary_rubric, 0) + 1
    return counts


def rubric_index_template(dispatches: list[Dispatch]) -> str:
    counts = rubric_counts_for(dispatches)
    cards = "\n".join(rubric_card(rubric, prefix="../", count=counts.get(rubric.slug, 0)) for rubric in RUBRICS)
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Рубрики", "Аналитические рубрики.", css_href="../styles/main.css")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">Рубрики</p>
    <h1>Рубрики</h1>
    <p class="lede">Повторяющиеся аналитические линзы: regulation, market structure, infrastructure, product/platform, security, research, consumer use и weak signals.</p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def rubric_page_template(rubric: RubricInfo, dispatches: list[Dispatch]) -> str:
    rubric_dispatches = [dispatch for dispatch in ordered_dispatches(dispatches) if dispatch.primary_rubric == rubric.slug]
    cards = "\n".join(dispatch_card(dispatch, prefix="../") for dispatch in rubric_dispatches)
    empty = "" if cards else "<p>В этой рубрике пока нет выпусков.</p>"
    return f"""<!doctype html>
<html lang="ru">
{head(f"News Dispatch — {rubric.title}", rubric.description, css_href="../styles/main.css")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">Аналитическая рубрика</p>
    <h1>{html.escape(rubric.title)}</h1>
    <p class="lede">{html.escape(rubric.description)}</p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
    {empty}
  </main>
</body>
</html>
"""


def rss_template(dispatches: list[Dispatch]) -> str:
    items = []
    for dispatch in ordered_dispatches(dispatches)[:20]:
        items.append(
            f"""    <item>
      <title>{html.escape(dispatch.title)}</title>
      <link>{html.escape(dispatch.url)}</link>
      <guid>{html.escape(dispatch.url)}</guid>
      <pubDate>{formatdate(usegmt=True)}</pubDate>
      <description>{html.escape(dispatch.summary)}</description>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>News Dispatch</title>
    <link>{BASE_URL}/</link>
    <description>Personal reader/radar dispatches.</description>
    <language>ru</language>
{chr(10).join(items)}
  </channel>
</rss>
"""


def sitemap_template(dispatches: list[Dispatch]) -> str:
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/dispatches.html",
        f"{BASE_URL}/rss.xml",
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/streams/index.html",
        f"{BASE_URL}/rubrics/index.html",
        f"{BASE_URL}/radar/index.html",
    ]
    urls.extend(stream.url for stream in STREAMS)
    urls.extend(rubric.url for rubric in RUBRICS)
    urls.extend(f"{BASE_URL}/radar/{stream.slug}.html" for stream in STREAMS)
    urls.extend(dispatch.url for dispatch in ordered_dispatches(dispatches))
    entries = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in dict.fromkeys(urls))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""


def render() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_DIR.mkdir(parents=True, exist_ok=True)
    RUBRIC_DIR.mkdir(parents=True, exist_ok=True)

    for page in OUTPUT_DIR.glob("*.html"):
        page.unlink()
    for page in RUBRIC_DIR.glob("*.html"):
        page.unlink()

    dispatches: list[Dispatch] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        dispatch = load_dispatch(path)
        if dispatch is not None:
            dispatches.append(dispatch)

    for dispatch in dispatches:
        body_html = markdown_to_html(dispatch.body)
        (OUTPUT_DIR / dispatch.output_name).write_text(page_template(dispatch, body_html), encoding="utf-8")
    for stream in STREAMS:
        (STREAM_DIR / f"{stream.slug}.html").write_text(stream_page_template(stream, dispatches), encoding="utf-8")
    for rubric in RUBRICS:
        (RUBRIC_DIR / f"{rubric.slug}.html").write_text(rubric_page_template(rubric, dispatches), encoding="utf-8")
    (STREAM_DIR / "index.html").write_text(stream_index_template(dispatches), encoding="utf-8")
    (RUBRIC_DIR / "index.html").write_text(rubric_index_template(dispatches), encoding="utf-8")
    (SITE_DIR / "index.html").write_text(homepage_template(dispatches), encoding="utf-8")
    (SITE_DIR / "dispatches.html").write_text(archive_template(dispatches), encoding="utf-8")
    (SITE_DIR / "rss.xml").write_text(rss_template(dispatches), encoding="utf-8")
    (SITE_DIR / "sitemap.xml").write_text(sitemap_template(dispatches), encoding="utf-8")


if __name__ == "__main__":
    render()
    print("Rendered News Dispatch site.")
