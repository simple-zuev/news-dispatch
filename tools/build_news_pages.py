#!/usr/bin/env python3
"""Build public news feeds and digest indexes.

News feeds are broad chronological lists of accepted public-source items. They
are intentionally separate from Today selection and from analytical digests.
"""

from __future__ import annotations

import html
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from build_today_page import (
    GENERAL_SPECIAL_USE_STREAM,
    public_href,
)
from core import DISPATCH_DIR, ROOT, SITE_DIR, coalesce, parse_front_matter_file
from digest_policy import digest_issue_title, is_public_digest
from reader_shell import public_nav, public_skip_link
from reader_text import (
    PUBLIC_TZ,
    build_public_item,
    format_public_time_ru,
    public_meta_ru,
    public_excerpt_ru,
    public_items_same_story,
    public_item_is_fresh,
    stream_label,
)
from render_site import output_slug

RANKING_PATH = ROOT / "validation" / "daily-radar-ranking-latest.json"
POLICY_PATH = ROOT / "validation" / "reader-policy-latest.json"
HISTORY_PATH = ROOT / "validation" / "public-reader-history-latest.json"
NEWS_DIR = SITE_DIR / "news"
DIGESTS_DIR = SITE_DIR / "digests"
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

def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def numeric(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def item_stream(item: dict[str, Any]) -> str:
    return str(item.get("routed_stream") or item.get("configured_stream") or "").strip()


def item_time(item: dict[str, Any]) -> str:
    return format_public_time_ru(item.get("published") or item.get("date"))


def item_sort_key(item: dict[str, Any]) -> str:
    return str(item.get("published") or item.get("date") or "")


def item_key(item: dict[str, Any]) -> str:
    explicit = str(item.get("item_key") or "").strip()
    if explicit:
        return explicit
    return "|".join([str(item.get("feed_id") or ""), str(item.get("title") or ""), str(item.get("url") or "")])


def policy_item_key(item: dict[str, Any]) -> str:
    stable = "|".join([
        str(item.get("feed_id") or ""),
        str(item.get("url") or ""),
        str(item.get("title") or ""),
    ])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def reader_safe_keys(policy: dict[str, Any]) -> set[str]:
    decisions = policy.get("decisions", [])
    keys: set[str] = set()
    if not isinstance(decisions, list):
        return keys
    for row in decisions:
        if not isinstance(row, dict):
            continue
        if row.get("decision") == "reader_safe" and row.get("item_key"):
            keys.add(str(row["item_key"]))
    return keys


def accepted_by_policy(item: dict[str, Any], safe_keys: set[str]) -> bool:
    if str(item.get("source_rule_status") or "") != "accepted_by_source_rules":
        return False
    relevance = numeric(item.get("relevance_score"))
    minimum = numeric(item.get("min_relevance_score"), 0.0)
    if relevance < minimum:
        return False
    if safe_keys:
        return item_key(item) in safe_keys or policy_item_key(item) in safe_keys
    return True


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    clusters: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=item_sort_key, reverse=True):
        url_key = str(item.get("url") or "").strip().lower()
        if url_key and url_key in seen_urls:
            continue
        if url_key:
            seen_urls.add(url_key)
        for cluster in clusters:
            if public_items_same_story(item, cluster[0]):
                cluster.append(item)
                break
        else:
            clusters.append([item])

    result: list[dict[str, Any]] = []
    for cluster in clusters:
        representative = dict(cluster[0])
        related = cluster[1:]
        if related:
            representative["_public_related_items"] = related
        result.append(representative)
    return result


def feed_items(
    report: dict[str, Any],
    policy: dict[str, Any],
    retained_items: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    safe_keys = reader_safe_keys(policy)
    reference = report.get("date")
    grouped: dict[str, list[dict[str, Any]]] = {stream: [] for stream in STREAM_ORDER}
    candidates = [(item, safe_keys, False) for item in report.get("items", [])]
    candidates.extend((item, set(), True) for item in (retained_items or []))
    for item, item_safe_keys, retained in candidates:
        if not isinstance(item, dict):
            continue
        stream = item_stream(item)
        if stream not in grouped:
            continue
        if not retained and (
            item.get("selected") is not True
            or not accepted_by_policy(item, item_safe_keys)
        ):
            continue
        if not public_item_is_fresh(item, reference, max_age_hours=24 * 14):
            continue
        if not public_excerpt_ru(item):
            continue
        grouped[stream].append(item)
    return {stream: dedupe_items(rows) for stream, rows in grouped.items()}


def public_news_meta(item: dict[str, Any]) -> str:
    return public_meta_ru(item, item_stream(item))


def source_link(item: dict[str, Any], text: str, css_class: str = "") -> str:
    url = str(item.get("url") or "").strip()
    if not url:
        return esc(text)
    class_attr = f' class="{esc(css_class)}"' if css_class else ""
    return f'<a{class_attr} href="{esc(public_href(url))}">{esc(text)}</a>'


def related_sources_line(item: dict[str, Any]) -> str:
    related = item.get("_public_related_items")
    if not isinstance(related, list):
        return ""
    primary_source = str(item.get("feed_title") or item.get("feed_id") or "").strip()
    links: list[str] = []
    seen_sources = {primary_source}
    for row in related:
        if not isinstance(row, dict):
            continue
        source = str(row.get("feed_title") or row.get("feed_id") or "Публичный источник").strip()
        if source in seen_sources:
            continue
        seen_sources.add(source)
        links.append(source_link(row, source, "reader-action-link"))
        if len(links) == 3:
            break
    if not links:
        return ""
    return f'\n    <p class="news-related-sources">Другие источники: {"; ".join(links)}</p>'


def feed_item_card(item: dict[str, Any]) -> str:
    public_item = build_public_item(item, stream=item_stream(item))
    title = public_item["title"]
    original = public_item["original_title"]
    excerpt = public_item["excerpt"]
    excerpt_line = f'\n    <p class="news-excerpt">{esc(excerpt)}</p>' if excerpt else ""
    why = public_item["why_it_matters"]
    why_line = f'\n    <p class="news-why"><strong>Почему важно:</strong> {esc(why)}</p>' if why else ""
    meta = public_item["meta"]
    original_line = ""
    if original and original != title:
        original_line = f'\n    <details class="news-original"><summary>Оригинал</summary><p>{esc(original)}</p></details>'
    related_line = related_sources_line(item)
    slug = item_stream(item)
    return f"""<article class="news-item news-item--text">
  <span class="news-stream-marker stream-dot--{esc(slug)}" aria-hidden="true"></span>
  <div class="news-item-body">
    <p class="news-meta">{esc(meta)}</p>
    <h3>{source_link(item, title, "reader-title-link")}</h3>{excerpt_line}{why_line}
    <p class="news-source-link">{source_link(item, "Открыть источник", "reader-action-link")}</p>{original_line}{related_line}
  </div>
</article>"""


def empty_feed_card() -> str:
    return """<article class="news-item empty-state">
  <p class="label">Нет новых материалов</p>
  <h3>Сегодня новых материалов по теме нет.</h3>
</article>"""


def top_nav(prefix: str = "", current: str = "news") -> str:
    return public_nav(prefix, current=current)


def head(title: str, description: str, css_href: str = "../styles/main.css") -> str:
    return f"""<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="stylesheet" href="{esc(css_href)}">
</head>"""


def stream_overview_row(stream: str, rows: list[dict[str, Any]]) -> str:
    count = len(rows)
    latest = item_time(rows[0]) if rows else "нет новых материалов"
    return f"""<article class="news-index-row">
  <span class="news-stream-marker stream-dot--{esc(stream)}" aria-hidden="true"></span>
  <h2><a href="{esc(stream)}.html">{esc(stream_label(stream))}</a></h2>
  <p><span>{count} материалов</span><span>последнее: {esc(latest)}</span></p>
</article>"""


def news_index(grouped: dict[str, list[dict[str, Any]]]) -> str:
    rows = "\n".join(stream_overview_row(stream, grouped.get(stream, [])) for stream in STREAM_ORDER)
    total = sum(len(rows) for rows in grouped.values())
    latest_rows = dedupe_items([row for rows in grouped.values() for row in rows])[:20]
    latest_cards = "\n".join(feed_item_card(item) for item in latest_rows)
    return f"""<!doctype html>
<html lang="ru">
{head("Новости — News Dispatch", "Хронологические ленты публичных источников.", css_href="../styles/main.css")}
<body>
  {public_skip_link()}
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    {top_nav("../")}
    <h1>Новости</h1>
  </header>
  <main id="main-content">
    <section class="news-index-heading"><h2>Последние материалы</h2><a href="#top">К началу</a></section>
    <section class="news-list news-list--preview">{latest_cards or empty_feed_card()}</section>
    <section class="news-index-summary" aria-label="Темы новостей">
      <div class="news-index-heading"><h2>Темы новостей</h2><p>Всего: {total} материалов</p></div>
      <div class="news-index-list">{rows}</div>
    </section>
  </main>
</body>
</html>"""


def news_stream_page(stream: str, rows: list[dict[str, Any]]) -> str:
    limited_rows = rows[:50]
    days: dict[str, list[dict[str, Any]]] = {}
    for item in limited_rows:
        day = str(item.get("published") or item.get("date") or "")[:10]
        days.setdefault(day or "unknown", []).append(item)
    day_links = "".join(
        f'<a href="#day-{esc(day)}">{esc(format_public_time_ru(day) if day != "unknown" else "Без даты")}</a>'
        for day in days
    )
    archive_nav = f'<nav class="news-archive-nav" aria-label="Дни архива">{day_links}</nav>' if len(days) > 1 else ""
    day_sections = "\n".join(
        f'<section class="news-day-group" id="day-{esc(day)}"><h2>{esc(format_public_time_ru(day) if day != "unknown" else "Без даты")}</h2>'
        + "\n".join(feed_item_card(item) for item in day_rows)
        + "</section>"
        for day, day_rows in days.items()
    )
    cards = day_sections or empty_feed_card()
    return f"""<!doctype html>
<html lang="ru">
{head(f"{stream_label(stream)} — лента новостей", f"Хронологическая лента: {stream_label(stream)}.")}
<body>
  {public_skip_link()}
  <header class="masthead compact">
    <a class="backlink" href="index.html">Ленты новостей</a>
    {top_nav("../")}
    <h1>{esc(stream_label(stream))}</h1>
    <p class="lede">Материалы за последние 14 дней, новейшие сверху. Показано до 50 строк.</p>
  </header>
  <main id="main-content">
    {archive_nav}
    <section class="news-list news-list--archive">{cards}</section>
  </main>
</body>
</html>"""


def collect_digests() -> list[dict[str, str]]:
    digests: list[dict[str, str]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        doc = parse_front_matter_file(path)
        if doc.errors or not is_public_digest(doc.metadata, doc.body):
            continue
        stream = coalesce(doc.metadata.get("stream"), default=GENERAL_SPECIAL_USE_STREAM)
        digests.append(
            {
                "title": coalesce(doc.metadata.get("title"), default=path.stem.replace("-", " ")),
                "date": coalesce(doc.metadata.get("date")),
                "stream": stream,
                "stream_title": stream_label(stream),
                "issue_title": digest_issue_title(doc.metadata),
                "thesis": coalesce(doc.metadata.get("digest_thesis")),
                "reader_value": coalesce(doc.metadata.get("reader_value")),
                "url": f"../dispatches/{output_slug(path)}.html",
            }
        )
    return sorted(digests, key=lambda item: (item["date"], item["title"]), reverse=True)


def digest_card(item: dict[str, str]) -> str:
    return f"""<article class="digest-list-card">
  <p class="news-meta">{esc(item["date"])} · {esc(item["stream_title"])} · {esc(item["issue_title"])}</p>
  <h3><a href="{esc(item["url"])}">{esc(item["title"])}</a></h3>
  <p class="digest-thesis"><strong>Главный вывод:</strong> {esc(item["thesis"])}</p>
  <p class="digest-reader-value"><strong>Зачем читать:</strong> {esc(item["reader_value"])}</p>
  <p class="news-source-link"><a href="{esc(item["url"])}">Открыть выпуск</a></p>
</article>"""


def digests_index(digests: list[dict[str, str]]) -> str:
    cards = "\n".join(digest_card(item) for item in digests) or """<article class="digest-list-card empty-state">
  <p class="label">Нет дайджестов</p>
  <h3>Дайджесты пока не опубликованы.</h3>
</article>"""
    return f"""<!doctype html>
<html lang="ru">
{head("Дайджесты — News Dispatch", "Аналитические выпуски News Dispatch.", css_href="../styles/main.css")}
<body>
  {public_skip_link()}
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    {top_nav("../", current="digests")}
    <h1>Дайджесты</h1>
  </header>
  <main id="main-content"><section class="news-list digest-list">{cards}</section></main>
</body>
</html>"""


def build() -> None:
    report = load_json(RANKING_PATH)
    policy = load_json(POLICY_PATH)
    history = load_json(HISTORY_PATH)
    retained_items = [item for item in history.get("items", []) if isinstance(item, dict)]
    grouped = feed_items(report, policy, retained_items)
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    (NEWS_DIR / "index.html").write_text(news_index(grouped), encoding="utf-8")
    for stream in STREAM_ORDER:
        (NEWS_DIR / f"{stream}.html").write_text(news_stream_page(stream, grouped.get(stream, [])), encoding="utf-8")
    (DIGESTS_DIR / "index.html").write_text(digests_index(collect_digests()), encoding="utf-8")


def main() -> int:
    build()
    print("Built news feeds and digest index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
