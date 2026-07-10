#!/usr/bin/env python3
"""Build the public source transparency page."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from build_news_pages import (
    accepted_by_policy,
    item_sort_key,
    load_json,
    policy_item_key,
    reader_safe_keys,
)
from build_today_page import public_href
from core import ROOT, SITE_DIR
from reader_shell import public_nav
from reader_text import build_public_item, source_type_label, stream_label

SOURCES_PATH = ROOT / "sources" / "feeds.json"
RANKING_PATH = ROOT / "validation" / "daily-radar-ranking-latest.json"
POLICY_PATH = ROOT / "validation" / "reader-policy-latest.json"
OUTPUT_DIR = SITE_DIR / "sources"
OUTPUT_PATH = OUTPUT_DIR / "index.html"

STREAM_ORDER = [
    "finance",
    "crypto-finance",
    "ai",
    "tech-hardware-software",
    "gear-style-edc",
    "moscow-city",
    "dj-audio-creative",
    "science-discovery",
    "general",
]

SOURCE_ROLE_BY_CLASS = {
    "official_source": "первичные заявления, решения и документы",
    "official": "первичные заявления, решения и документы",
    "regulator": "первичные заявления регулятора",
    "public_media": "публичная хроника и быстрый контекст",
    "business_media": "деловой контекст и рыночная хроника",
    "specialized_media": "профильные новости и ранние сигналы",
    "industry_media": "отраслевая хроника и детали рынка",
    "research_media": "исследования и научный контекст",
}

RELIABILITY_BY_TIER = {
    "A": "высокая: первичный или официальный источник",
    "B": "средняя: профильный публичный источник",
    "C": "ограниченная: ранний или специализированный сигнал",
}

RELIABILITY_BY_CLASS = {
    "official_source": "высокая: первичный источник",
    "official": "высокая: первичный источник",
    "regulator": "высокая: первичный источник",
    "research_media": "ограниченная: выводы требуют сверки",
    "public_media": "редакционная: публичная лента",
    "business_media": "редакционная: деловая публичная лента",
    "specialized_media": "редакционная: профильная публичная лента",
    "industry_media": "редакционная: отраслевая публичная лента",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def load_sources(path: Path = SOURCES_PATH) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    rows = data.get("feeds", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("enabled", True) is not False]


def source_key(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("title") or "").strip()


def source_role(row: dict[str, Any]) -> str:
    source_class = str(row.get("source_class") or "").strip()
    return SOURCE_ROLE_BY_CLASS.get(source_class, "публичные сообщения по теме")


def reliability_label(row: dict[str, Any]) -> str:
    tier = str(row.get("reliability_tier") or "").strip().upper()
    if tier in RELIABILITY_BY_TIER:
        return RELIABILITY_BY_TIER[tier]
    source_class = str(row.get("source_class") or "").strip()
    return RELIABILITY_BY_CLASS.get(source_class, "редакционная: публичный источник")


def recent_items_by_source(report: dict[str, Any], policy: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    safe_keys = reader_safe_keys(policy)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for item in sorted(report.get("items", []), key=item_sort_key, reverse=True):
        if not isinstance(item, dict):
            continue
        if not accepted_by_policy(item, safe_keys):
            continue
        feed_id = str(item.get("feed_id") or "").strip()
        if not feed_id:
            continue
        key = (feed_id, str(item.get("url") or item.get("title") or policy_item_key(item)))
        if key in seen:
            continue
        seen.add(key)
        grouped[feed_id].append(item)
    return grouped


def recent_items_html(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[:2]:
        public_item = build_public_item(item)
        title = public_item["title"]
        url = str(item.get("url") or "").strip()
        if url:
            rows.append(f'<a href="{esc(public_href(url))}">{esc(title)}</a>')
        else:
            rows.append(esc(title))
    if not rows:
        return ""
    return f'<p class="source-recent">Недавнее: {"; ".join(rows)}</p>'


def source_row(row: dict[str, Any], recent_lookup: dict[str, list[dict[str, Any]]]) -> str:
    stream = str(row.get("stream") or "").strip()
    title = str(row.get("title") or row.get("id") or "Публичный источник").strip()
    source_type = source_type_label(row.get("source_type"))
    reliability = reliability_label(row)
    role = source_role(row)
    recent = recent_items_html(recent_lookup.get(source_key(row), []))
    return f"""<article class="source-row">
  <span class="news-stream-marker stream-dot--{esc(stream)}" aria-hidden="true"></span>
  <div class="source-row-body">
    <p class="source-meta">Рубрика: {esc(stream_label(stream))} · Тип: {esc(source_type)} · Надёжность: {esc(reliability)}</p>
    <h3>{esc(title)}</h3>
    <p class="source-role">Роль: {esc(role)}.</p>
    {recent}
  </div>
</article>"""


def rubric_nav(streams: list[str]) -> str:
    links = [
        f'<a class="home-rubric-pill" href="#{esc(stream)}">{esc(stream_label(stream))}</a>'
        for stream in streams
    ]
    return "\n".join(links)


def source_sections(rows: list[dict[str, Any]], recent_lookup: dict[str, list[dict[str, Any]]]) -> str:
    by_stream: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stream[str(row.get("stream") or "").strip()].append(row)
    sections = []
    ordered = [stream for stream in STREAM_ORDER if by_stream.get(stream)]
    for stream in ordered:
        cards = "\n".join(source_row(row, recent_lookup) for row in sorted(by_stream[stream], key=lambda item: str(item.get("title") or "")))
        sections.append(
            f"""<section class="sources-group" id="{esc(stream)}">
  <div class="news-index-heading"><h2>{esc(stream_label(stream))}</h2><p>{len(by_stream[stream])} источн.</p></div>
  <div class="sources-list">{cards}</div>
</section>"""
        )
    return "\n".join(sections)


def page_html(rows: list[dict[str, Any]], recent_lookup: dict[str, list[dict[str, Any]]]) -> str:
    streams = [stream for stream in STREAM_ORDER if any(str(row.get("stream") or "").strip() == stream for row in rows)]
    sections = source_sections(rows, recent_lookup)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Источники — News Dispatch</title>
  <meta name="description" content="Публичные источники News Dispatch по рубрикам.">
  <link rel="stylesheet" href="../styles/main.css">
</head>
<body>
  <header class="masthead compact sources-header">
    <a class="backlink" href="../index.html">News Dispatch</a>
    {public_nav("../", current="sources")}
    <h1>Источники</h1>
    <p class="lede">Публичные источники, из которых собираются читательские ленты. Здесь показаны роль источника, рубрика и понятный уровень доверия без служебных деталей.</p>
  </header>
  <main class="sources-page">
    <section class="sources-rubrics" aria-label="Рубрики">
      <div class="news-index-heading"><h2>Рубрики</h2><p>{len(rows)} источн.</p></div>
      <div class="home-rubric-list">{rubric_nav(streams)}</div>
    </section>
    {sections}
  </main>
</body>
</html>"""


def build() -> None:
    sources = load_sources()
    recent_lookup = recent_items_by_source(load_json(RANKING_PATH), load_json(POLICY_PATH))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(page_html(sources, recent_lookup), encoding="utf-8")


def main() -> int:
    build()
    print(f"Built {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
