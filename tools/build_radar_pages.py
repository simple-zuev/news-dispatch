#!/usr/bin/env python3
"""Build static radar pages from validation/daily-radar-latest.json."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from core import ROOT
from stream_registry import streams as registry_streams

SITE_DIR = ROOT / "site"
RADAR_DIR = SITE_DIR / "radar"
RADAR_PATH = ROOT / "validation" / "daily-radar-latest.json"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    raw = text[4:end]
    meta: dict[str, Any] = {}
    list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            meta.setdefault(list_key, [])
            assert isinstance(meta[list_key], list)
            meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value == "":
            list_key = key
            meta[key] = []
        else:
            list_key = None
            meta[key] = value
    return meta


def first_value(meta: dict[str, Any], key: str, default: str = "") -> str:
    value = meta.get(key, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value or default)


def stream_data() -> list[dict[str, Any]]:
    rows = []
    for item in registry_streams():
        rows.append({
            "slug": str(item["slug"]),
            "title": str(item["title"]),
            "description": str(item.get("description", "")),
            "label": str(item.get("label", "Редакционная проверка")),
        })
    return rows


def radar_items() -> dict[str, list[dict[str, str]]]:
    data = load_json(RADAR_PATH)
    result: dict[str, list[dict[str, str]]] = {}
    for group in data.get("generated", []):
        if not isinstance(group, dict):
            continue
        stream = str(group.get("stream", "")).strip()
        if not stream:
            continue
        result.setdefault(stream, [])
        for path_text in group.get("signals", []):
            path = ROOT / str(path_text)
            if not path.exists():
                continue
            meta = parse_front_matter(path.read_text(encoding="utf-8"))
            result[stream].append({
                "title": first_value(meta, "title", path.stem.replace("-", " ")),
                "date": first_value(meta, "date"),
                "source": first_value(meta, "source_titles", first_value(meta, "sources", "Публичный источник")),
                "url": first_value(meta, "sources"),
                "source_class": first_value(meta, "source_class", "public_source"),
            })
    for rows in result.values():
        rows.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
    return result


def head(title: str, description: str) -> str:
    return f"""<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <meta name=\"description\" content=\"{html.escape(description)}\">
  <link rel=\"stylesheet\" href=\"../styles/main.css\">
</head>"""


def signal_card(row: dict[str, str]) -> str:
    source = row.get("source") or "Публичный источник"
    label = " · ".join(part for part in [row.get("date", ""), row.get("source_class", ""), source] if part)
    link = row.get("url", "")
    title = row.get("title", "Сигнал")
    title_html = html.escape(title)
    if link:
        heading = f'<h3><a href="{html.escape(link, quote=True)}">{title_html}</a></h3>'
    else:
        heading = f"<h3>{title_html}</h3>"
    return f"""<article class=\"card signal-card\">
  <p class=\"label\">Сигнал · {html.escape(label)}</p>
  {heading}
  <p>Публичный сигнал для проверки. Это не опубликованный аналитический вывод.</p>
</article>"""


def stream_card(stream: dict[str, Any], count: int) -> str:
    slug = str(stream["slug"])
    title = str(stream["title"])
    description = str(stream.get("description", ""))
    return f"""<article class=\"card\">
  <p class=\"label\">{count} сигналов</p>
  <h3><a href=\"{html.escape(slug)}.html\">{html.escape(title)}</a></h3>
  <p>{html.escape(description)}</p>
</article>"""


def index_page(streams: list[dict[str, Any]], items: dict[str, list[dict[str, str]]]) -> str:
    cards = "\n".join(stream_card(stream, len(items.get(str(stream["slug"]), []))) for stream in streams)
    return f"""<!doctype html>
<html lang=\"ru\">
{head("Дайджест — Свежие сигналы", "Публичный радар сигналов по темам.")}
<body>
  <header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">Дайджест</a><p class=\"eyebrow\">Радар</p><h1>Свежие сигналы</h1><p class=\"lede\">Публичные сигналы по темам. Это сырьё для анализа, а не опубликованные выводы.</p></header>
  <main><section class=\"grid\">{cards}</section></main>
</body>
</html>
"""


def stream_page(stream: dict[str, Any], rows: list[dict[str, str]]) -> str:
    cards = "\n".join(signal_card(row) for row in rows)
    empty = "" if cards else "<p>В этой теме сейчас нет свежих сигналов.</p>"
    title = str(stream["title"])
    description = str(stream.get("description", ""))
    return f"""<!doctype html>
<html lang=\"ru\">
{head(f"Дайджест — Свежие сигналы — {title}", description)}
<body>
  <header class=\"masthead compact\"><a class=\"backlink\" href=\"index.html\">Свежие сигналы</a><p class=\"eyebrow\">Радар темы</p><h1>{html.escape(title)}</h1><p class=\"lede\">{html.escape(description)}</p></header>
  <main><section class=\"grid\">{cards}</section>{empty}</main>
</body>
</html>
"""


def main() -> int:
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    for page in RADAR_DIR.glob("*.html"):
        page.unlink()
    streams = stream_data()
    items = radar_items()
    (RADAR_DIR / "index.html").write_text(index_page(streams, items), encoding="utf-8")
    for stream in streams:
        slug = str(stream["slug"])
        (RADAR_DIR / f"{slug}.html").write_text(stream_page(stream, items.get(slug, [])), encoding="utf-8")
    print(f"Built radar pages for {len(streams)} stream(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
