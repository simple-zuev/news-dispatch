#!/usr/bin/env python3
"""Build live hourly radar pages from public RSS/Atom signals."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from daily_radar import fetch_items, load_config, load_seen, save_seen, select_items, write_signal
from stream_registry import stream_title, streams

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = ROOT / "data" / "hourly-radar-seen.json"
REPORT_PATH = ROOT / "data" / "hourly-radar-latest.json"
LOG_PATH = ROOT / "data" / "hourly-radar-log.json"
RADAR_DIR = ROOT / "site" / "radar"
MAX_LOG_ITEMS = 300


def log(message: str) -> None:
    print(f"[hourly-radar] {message}")


def record_from_item(item) -> dict[str, Any]:
    return {
        "key": item.key,
        "stream": item.stream,
        "stream_title": stream_title(item.stream),
        "source": item.feed.title,
        "source_type": item.feed.source_type,
        "source_class": item.feed.source_class,
        "title": item.title,
        "url": item.url,
        "summary": item.summary or "Сводка в RSS/Atom не указана.",
        "published": item.published.isoformat(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "score": item.score,
    }


def load_log() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    try:
        data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = data.get("items", [])
    return [item for item in items if isinstance(item, dict)]


def save_log(records: list[dict[str, Any]]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps({"items": records[:MAX_LOG_ITEMS]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_records(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in [*new, *old]:
        key = str(record.get("key") or record.get("url") or record.get("title"))
        if key and key not in merged:
            merged[key] = record
    return sorted(merged.values(), key=lambda item: str(item.get("published", "")), reverse=True)[:MAX_LOG_ITEMS]


def group_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(str(record.get("stream", "general")), []).append(record)
    return groups


def card(record: dict[str, Any]) -> str:
    source = html.escape(str(record.get("source", "Источник")))
    source_type = html.escape(str(record.get("source_type", "Источник")))
    title = html.escape(str(record.get("title", "Сигнал")))
    url = html.escape(str(record.get("url", "#")), quote=True)
    stream = html.escape(str(record.get("stream_title", stream_title(str(record.get("stream", "general"))))))
    summary = html.escape(str(record.get("summary", "Сводка в RSS/Atom не указана.")))
    published = str(record.get("published", ""))
    timestamp = html.escape(published.replace("T", " ").replace("+00:00", " UTC")[:20])
    return f"""<article class=\"source-card radar-card\">
  <p class=\"label radar-label\">{stream} · {source} · {timestamp}</p>
  <h3><a href=\"{url}\">{title}</a></h3>
  <p>{summary}</p>
  <p class=\"radar-meta\">{source_type} · сигнал из публичной RSS/Atom-ленты · требует проверки первоисточника</p>
</article>"""


def head(title: str, description: str) -> str:
    return f"""<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>{html.escape(title)}</title><meta name=\"description\" content=\"{html.escape(description)}\"><link rel=\"stylesheet\" href=\"../styles/main.css\"><link rel=\"stylesheet\" href=\"../styles/reader.css\"><link rel=\"stylesheet\" href=\"../styles/radar.css\"></head>"""


def render_index(groups: dict[str, list[dict[str, Any]]], new_count: int) -> None:
    blocks: list[str] = []
    for stream in streams():
        slug = str(stream["slug"])
        items = groups.get(slug, [])
        preview = "".join(card(item) for item in items[:3]) or "<p class=\"radar-empty\">Свежих сигналов в этом потоке пока нет.</p>"
        blocks.append(
            f"""<section class=\"reader-section-block radar-stream-block\"><h2><a href=\"{html.escape(slug)}.html\">{html.escape(str(stream['title']))}</a></h2><p>{html.escape(str(stream['description']))}</p><div class=\"reader-grid radar-grid\">{preview}</div></section>"""
        )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — Live Radar', 'Ежечасный радар по тематическим потокам.')}<body><header class=\"masthead compact radar-hero\"><a class=\"backlink\" href=\"../index.html\">News Dispatch</a><p class=\"eyebrow\">Live Radar</p><h1>Ежечасный радар</h1><p class=\"lede\">Свежие публичные сигналы по зонам интереса. Это не аналитический выпуск, а быстрая карта того, что появилось в источниках.</p><nav class=\"hero-actions\" aria-label=\"Навигация\"><a href=\"../streams/index.html\">Потоки</a><a href=\"../dispatches.html\">Выпуски</a><a href=\"source-health.html\">Источники</a><a href=\"../rss.xml\">RSS</a></nav><p class=\"radar-status\">Обновлено: {html.escape(updated)} · новых сигналов в запуске: {new_count}</p></header><main class=\"radar-layout\">{''.join(blocks)}</main></body></html>"""
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    (RADAR_DIR / "index.html").write_text(text, encoding="utf-8")


def render_stream_pages(groups: dict[str, list[dict[str, Any]]]) -> None:
    for stream in streams():
        slug = str(stream["slug"])
        items = groups.get(slug, [])
        content = "".join(card(item) for item in items[:60]) or "<p class=\"radar-empty\">Свежих сигналов в этом потоке пока нет.</p>"
        text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — ' + str(stream['title']), str(stream['description']))}<body><header class=\"masthead compact radar-hero\"><a class=\"backlink\" href=\"index.html\">Live Radar</a><p class=\"eyebrow\">{html.escape(str(stream['label']))}</p><h1>{html.escape(str(stream['title']))}</h1><p class=\"lede\">{html.escape(str(stream['description']))}</p><nav class=\"hero-actions\" aria-label=\"Навигация\"><a href=\"source-health.html\">Источники</a><a href=\"../streams/{html.escape(slug)}.html\">Выпуски потока</a></nav></header><main class=\"radar-layout\"><section class=\"reader-grid radar-grid\">{content}</section></main></body></html>"""
        RADAR_DIR.mkdir(parents=True, exist_ok=True)
        (RADAR_DIR / f"{slug}.html").write_text(text, encoding="utf-8")


def render_pages(records: list[dict[str, Any]], new_count: int) -> None:
    groups = group_records(records)
    render_index(groups, new_count)
    render_stream_pages(groups)


def write_report(day: date, selected: list, fetch_errors: list[str], records: list[dict[str, Any]]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "date": day.isoformat(),
        "selected_count": len(selected),
        "stored_count": len(records),
        "fetch_errors": fetch_errors,
        "items": [record_from_item(item) for item in selected],
    }
    REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date) if args.date else date.today()
    existing_records = load_log()
    if args.render_only:
        if not args.dry_run:
            render_pages(existing_records, 0)
        log(f"rendered radar pages from {len(existing_records)} stored signal(s)")
        return 0

    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int(args.max_items or defaults.get("hourly_max_items", 36))
    per_source = int(args.per_source or defaults.get("per_source", 3))
    lookback = int(args.lookback_hours or defaults.get("hourly_lookback_hours", 8))
    raw_items, fetch_errors = fetch_items(feeds, timeout=args.timeout)
    seen = set() if args.no_state else load_seen(STATE_PATH)
    selected = select_items(raw_items, seen, max_items=max_items, per_source=per_source, lookback_hours=lookback)
    new_records = [record_from_item(item) for item in selected]
    records = merge_records(existing_records, new_records)
    if selected:
        for item in selected:
            write_signal(day, item, dry_run=args.dry_run)
        save_seen(STATE_PATH, seen, [item.key for item in selected], dry_run=args.dry_run or args.no_state)
    if not args.dry_run:
        save_log(records)
        render_pages(records, len(selected))
        write_report(day, selected, fetch_errors, records)
    log(f"selected {len(selected)} signal(s); stored {len(records)}; feed warnings={len(fetch_errors)}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=os.getenv("HOURLY_RADAR_DATE", ""))
    parser.add_argument("--max-items", type=int, default=int(os.getenv("HOURLY_RADAR_MAX_ITEMS", "0")))
    parser.add_argument("--per-source", type=int, default=int(os.getenv("HOURLY_RADAR_PER_SOURCE", "0")))
    parser.add_argument("--lookback-hours", type=int, default=int(os.getenv("HOURLY_RADAR_LOOKBACK_HOURS", "0")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("HOURLY_RADAR_TIMEOUT", "20")))
    parser.add_argument("--dry-run", action="store_true", default=os.getenv("HOURLY_RADAR_DRY_RUN", "") == "1")
    parser.add_argument("--no-state", action="store_true", default=os.getenv("HOURLY_RADAR_NO_STATE", "") == "1")
    parser.add_argument("--render-only", action="store_true", default=os.getenv("HOURLY_RADAR_RENDER_ONLY", "") == "1")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return build(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
