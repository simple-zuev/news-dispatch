#!/usr/bin/env python3
"""Render News Dispatch Markdown files into a small static site.

No external dependencies. This renderer is intentionally conservative:
- reads public-safe Markdown dispatches from dispatches/**/*.md;
- writes HTML pages to site/dispatches/;
- writes a dispatch index;
- does not fetch remote resources;
- does not inject tracking scripts.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = SITE_DIR / "dispatches"


@dataclass
class Dispatch:
    source_path: Path
    title: str
    date: str
    stream: str
    summary: str
    body: str
    output_name: str


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


def page_template(dispatch: Dispatch, body_html: str) -> str:
    safe_title = html.escape(dispatch.title)
    safe_summary = html.escape(dispatch.summary)
    safe_stream = html.escape(dispatch.stream)
    safe_date = html.escape(dispatch.date)
    return f"""<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{safe_title}</title>
  <meta name=\"description\" content=\"{safe_summary}\">
  <link rel=\"stylesheet\" href=\"../styles/main.css\">
</head>
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


def index_template(dispatches: list[Dispatch]) -> str:
    cards = []
    for dispatch in sorted(dispatches, key=lambda item: (item.date, item.title), reverse=True):
        cards.append(
            f"""<article class=\"card\">
  <p class=\"label\">{html.escape(dispatch.stream)} · {html.escape(dispatch.date)}</p>
  <h3><a href=\"dispatches/{html.escape(dispatch.output_name)}\">{html.escape(dispatch.title)}</a></h3>
  <p>{html.escape(dispatch.summary)}</p>
</article>"""
        )
    return f"""<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>News Dispatch — Dispatches</title>
  <meta name=\"description\" content=\"Public-safe dispatch archive.\">
  <link rel=\"stylesheet\" href=\"styles/main.css\">
</head>
<body>
  <header class=\"masthead compact\">
    <p class=\"eyebrow\">Archive</p>
    <h1>Dispatches</h1>
    <p class=\"lede\">Обезличенный архив public-safe выпусков.</p>
  </header>
  <main>
    <section class=\"grid\">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def render() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dispatches = [load_dispatch(path) for path in sorted(DISPATCH_DIR.rglob("*.md"))]
    for dispatch in dispatches:
        body_html = markdown_to_html(dispatch.body)
        (OUTPUT_DIR / dispatch.output_name).write_text(page_template(dispatch, body_html), encoding="utf-8")
    (SITE_DIR / "dispatches.html").write_text(index_template(dispatches), encoding="utf-8")


if __name__ == "__main__":
    render()
    print("Rendered News Dispatch site.")
