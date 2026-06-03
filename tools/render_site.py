#!/usr/bin/env python3
"""Render News Dispatch Markdown files into a small static site.

No external dependencies. This renderer is intentionally conservative:
- reads public-safe Markdown dispatches from dispatches/**/*.md;
- writes HTML pages to site/dispatches/;
- writes a dynamic homepage, dispatch archive, and stream pages;
- writes RSS and sitemap files;
- does not fetch remote resources;
- does not inject tracking scripts.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = SITE_DIR / "dispatches"
STREAM_DIR = SITE_DIR / "streams"
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


STREAMS: list[StreamInfo] = [
    StreamInfo(
        "general",
        "General Dispatch",
        "Editorial review",
        "Multi-domain analysis across technology, finance, gear, culture, cities, science, and adjacent fields.",
    ),
    StreamInfo(
        "digital-assets-infrastructure",
        "Digital Assets Infrastructure",
        "Strict review",
        "Public-source analysis of regulation, restrictions, technology, market structure, public competitors, vendor landscape, security, trust, and infrastructure resilience.",
        strict=True,
    ),
    StreamInfo(
        "work",
        "Work Dispatch",
        "Strict review",
        "Public market and product signals, AI, UX, operating models, and organizational implications without internal company or product data.",
        strict=True,
    ),
    StreamInfo(
        "finance",
        "Finance Dispatch",
        "Strict review",
        "Rates, banking products, consumer economics, liquidity, subscriptions, and large-purchase context in educational framing.",
        strict=True,
    ),
    StreamInfo(
        "home-environment",
        "Home & Environment",
        "Strict review",
        "Home, smart home, energy, safety, infrastructure patterns, comfort, and practical systems.",
        strict=True,
    ),
    StreamInfo(
        "gear",
        "Gear & Material Culture",
        "Editorial review",
        "EDC, bags, watches, tools, apparel, materials, repairability, ownership, and everyday-use criteria.",
    ),
    StreamInfo(
        "city-culture",
        "City & Culture",
        "Editorial review",
        "City life, culture, media, events, urban services, and lifestyle signals.",
    ),
    StreamInfo(
        "audio-creative",
        "Audio & Creative Tech",
        "Editorial review",
        "DJ gear, audio, MIDI, music production, performance interfaces, and creator tools.",
    ),
    StreamInfo(
        "horizon",
        "Horizon Notes",
        "Editorial review",
        "Science, systems, materials, robotics, biotech, cognition, HCI, and futures.",
    ),
]

STREAM_BY_SLUG = {stream.slug: stream for stream in STREAMS}


@dataclass
class Dispatch:
    source_path: Path
    title: str
    date: str
    stream: str
    summary: str
    body: str
    output_name: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/dispatches/{self.output_name}"

    @property
    def relative_url(self) -> str:
        return f"dispatches/{self.output_name}"


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("-"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, body


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def load_dispatch(path: Path) -> Dispatch:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    title = meta.get("title") or path.stem.replace("-", " ").title()
    return Dispatch(
        source_path=path,
        title=title,
        date=meta.get("date", ""),
        stream=meta.get("stream", "general"),
        summary=meta.get("summary", ""),
        body=body.strip(),
        output_name=f"{slugify(path)}.html",
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
        else:
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
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <meta name=\"description\" content=\"{html.escape(description)}\">
  <link rel=\"alternate\" type=\"application/rss+xml\" title=\"News Dispatch RSS\" href=\"{BASE_URL}/rss.xml\">
  <link rel=\"stylesheet\" href=\"{css_href}\">
</head>"""


def dispatch_card(dispatch: Dispatch, prefix: str = "") -> str:
    return f"""<article class=\"card\">
  <p class=\"label\">{html.escape(dispatch.stream)} · {html.escape(dispatch.date)}</p>
  <h3><a href=\"{prefix}{html.escape(dispatch.relative_url)}\">{html.escape(dispatch.title)}</a></h3>
  <p>{html.escape(dispatch.summary)}</p>
</article>"""


def stream_card(stream: StreamInfo, prefix: str = "", count: int | None = None) -> str:
    count_label = "" if count is None else f" · {count} dispatches"
    strict_class = " strict" if stream.strict else ""
    return f"""<article class=\"card{strict_class}\">
  <p class=\"label\">{html.escape(stream.review_label)}{html.escape(count_label)}</p>
  <h3><a href=\"{prefix}{html.escape(stream.relative_url)}\">{html.escape(stream.title)}</a></h3>
  <p>{html.escape(stream.description)}</p>
</article>"""


def page_template(dispatch: Dispatch, body_html: str) -> str:
    safe_title = html.escape(dispatch.title)
    safe_summary = html.escape(dispatch.summary)
    safe_stream = html.escape(dispatch.stream)
    safe_date = html.escape(dispatch.date)
    return f"""<!doctype html>
<html lang=\"ru\">
{head(dispatch.title, dispatch.summary, css_href="../styles/main.css")}
<body class=\"dispatch-page\">
  <header class=\"article-hero\">
    <a class=\"backlink\" href=\"../index.html\">News Dispatch</a>
    <p class=\"eyebrow\">{safe_stream} · {safe_date}</p>
    <h1>{safe_title}</h1>
    <p class=\"lede\">{safe_summary}</p>
  </header>
  <main class=\"article-body\">
    {body_html}
  </main>
</body>
</html>
"""


def homepage_template(dispatches: list[Dispatch]) -> str:
    latest = ordered_dispatches(dispatches)[:6]
    latest_cards = "\n".join(dispatch_card(dispatch) for dispatch in latest)
    stream_cards = "\n".join(stream_card(stream) for stream in STREAMS[:8])
    return f"""<!doctype html>
<html lang=\"ru\">
{head("News Dispatch", "Public-safe editorial dispatches across technology, finance, culture, gear, infrastructure, and science.")}
<body>
  <header class=\"masthead\">
    <p class=\"eyebrow\">Public-safe editorial briefing system</p>
    <h1>News Dispatch</h1>
    <p class=\"lede\">Аналитический хаб для обезличенных выпусков о технологиях, рынках, инфраструктуре, вещах, городе, культуре и научном горизонте.</p>
    <p class=\"hero-actions\"><a href=\"dispatches.html\">Open dispatch archive</a><a href=\"streams/index.html\">Streams</a><a href=\"rss.xml\">RSS</a></p>
  </header>

  <main>
    <section class=\"panel\">
      <h2>Latest dispatches</h2>
      <p>Последние public-safe выпуски, собранные из Markdown-архива.</p>
    </section>

    <section class=\"grid latest-grid\" aria-label=\"Latest dispatches\">
      {latest_cards}
    </section>

    <section class=\"panel\">
      <h2>Streams</h2>
      <p>Потоки помогают разделять разные типы аналитики, review level и источниковую модель.</p>
    </section>

    <section class=\"grid\" aria-label=\"Dispatch streams\">
      {stream_cards}
    </section>

    <section class=\"panel boundary\">
      <h2>Publication boundary</h2>
      <p>Everything committed to the repository is treated as public. Private context may calibrate selection, but never appears as disclosure.</p>
    </section>
  </main>
</body>
</html>
"""


def archive_template(dispatches: list[Dispatch]) -> str:
    cards = "\n".join(dispatch_card(dispatch) for dispatch in ordered_dispatches(dispatches))
    return f"""<!doctype html>
<html lang=\"ru\">
{head("News Dispatch — Dispatches", "Public-safe dispatch archive.")}
<body>
  <header class=\"masthead compact\">
    <a class=\"backlink\" href=\"index.html\">News Dispatch</a>
    <p class=\"eyebrow\">Archive</p>
    <h1>Dispatches</h1>
    <p class=\"lede\">Обезличенный архив public-safe выпусков.</p>
  </header>
  <main>
    <section class=\"grid\">
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
<html lang=\"ru\">
{head("News Dispatch — Streams", "Editorial stream index.", css_href="../styles/main.css")}
<body>
  <header class=\"masthead compact\">
    <a class=\"backlink\" href=\"../index.html\">News Dispatch</a>
    <p class=\"eyebrow\">Streams</p>
    <h1>Streams</h1>
    <p class=\"lede\">Потоки разделяют темы, уровни проверки и правила публикации.</p>
  </header>
  <main>
    <section class=\"grid\">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def stream_page_template(stream: StreamInfo, dispatches: list[Dispatch]) -> str:
    stream_dispatches = [dispatch for dispatch in ordered_dispatches(dispatches) if dispatch.stream == stream.slug]
    cards = "\n".join(dispatch_card(dispatch, prefix="../") for dispatch in stream_dispatches)
    empty = "" if cards else "<p>No dispatches in this stream yet.</p>"
    return f"""<!doctype html>
<html lang=\"ru\">
{head(f"News Dispatch — {stream.title}", stream.description, css_href="../styles/main.css")}
<body>
  <header class=\"masthead compact\">
    <a class=\"backlink\" href=\"../index.html\">News Dispatch</a>
    <p class=\"eyebrow\">{html.escape(stream.review_label)}</p>
    <h1>{html.escape(stream.title)}</h1>
    <p class=\"lede\">{html.escape(stream.description)}</p>
  </header>
  <main>
    <section class=\"grid\">
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
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
  <channel>
    <title>News Dispatch</title>
    <link>{BASE_URL}/</link>
    <description>Public-safe editorial dispatches.</description>
    <language>ru</language>
{chr(10).join(items)}
  </channel>
</rss>
"""


def sitemap_template(dispatches: list[Dispatch]) -> str:
    urls = [f"{BASE_URL}/", f"{BASE_URL}/dispatches.html", f"{BASE_URL}/rss.xml", f"{BASE_URL}/sitemap.xml", f"{BASE_URL}/streams/index.html"]
    urls.extend(stream.url for stream in STREAMS)
    urls.extend(dispatch.url for dispatch in ordered_dispatches(dispatches))
    entries = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in urls)
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
{entries}
</urlset>
"""


def render() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_DIR.mkdir(parents=True, exist_ok=True)
    dispatches = [load_dispatch(path) for path in sorted(DISPATCH_DIR.rglob("*.md"))]
    for dispatch in dispatches:
        body_html = markdown_to_html(dispatch.body)
        (OUTPUT_DIR / dispatch.output_name).write_text(page_template(dispatch, body_html), encoding="utf-8")
    for stream in STREAMS:
        (STREAM_DIR / f"{stream.slug}.html").write_text(stream_page_template(stream, dispatches), encoding="utf-8")
    (STREAM_DIR / "index.html").write_text(stream_index_template(dispatches), encoding="utf-8")
    (SITE_DIR / "index.html").write_text(homepage_template(dispatches), encoding="utf-8")
    (SITE_DIR / "dispatches.html").write_text(archive_template(dispatches), encoding="utf-8")
    (SITE_DIR / "rss.xml").write_text(rss_template(dispatches), encoding="utf-8")
    (SITE_DIR / "sitemap.xml").write_text(sitemap_template(dispatches), encoding="utf-8")


if __name__ == "__main__":
    render()
    print("Rendered News Dispatch site.")
