#!/usr/bin/env python3
"""Build live hourly radar pages from public RSS/Atom signals."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import date
from pathlib import Path

from daily_radar import fetch_items, group_by_stream, load_config, load_seen, save_seen, select_items, write_signal
from stream_registry import stream_by_slug, stream_title, streams

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = ROOT / "data" / "hourly-radar-seen.json"
REPORT_PATH = ROOT / "data" / "hourly-radar-latest.json"
RADAR_DIR = ROOT / "site" / "radar"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"


def log(message: str) -> None:
    print(f"[hourly-radar] {message}")


def card(item) -> str:
    source = html.escape(item.feed.title)
    title = html.escape(item.title)
    url = html.escape(item.url, quote=True)
    stream = html.escape(stream_title(item.stream))
    summary = html.escape(item.summary or "Сводка в RSS/Atom не указана.")
    timestamp = html.escape(item.published.strftime("%Y-%m-%d %H:%M UTC"))
    return f"""<article class=\"source-card radar-card\">
  <p class=\"label\">{stream} · {source} · {timestamp}</p>
  <h3><a href=\"{url}\">{title}</a></h3>
  <p>{summary}</p>
</article>"""


def head(title: str, description: str) -> str:
    return f"""<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>{html.escape(title)}</title><meta name=\"description\" content=\"{html.escape(description)}\"><link rel=\"stylesheet\" href=\"../styles/main.css\"><link rel=\"stylesheet\" href=\"../styles/reader.css\"></head>"""


def render_index(groups: dict[str, list]) -> None:
    stream_map = stream_by_slug()
    blocks: list[str] = []
    for stream in streams():
        slug = str(stream["slug"])
        items = groups.get(slug, [])
        preview = "".join(card(item) for item in items[:3]) or "<p>За последний запуск новых сигналов нет.</p>"
        blocks.append(
            f"""<section class=\"reader-section-block\"><h2><a href=\"{html.escape(slug)}.html\">{html.escape(str(stream['title']))}</a></h2><p>{html.escape(str(stream['description']))}</p><div class=\"reader-grid\">{preview}</div></section>"""
        )
    text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — Live Radar', 'Ежечасный радар по тематическим потокам.')}<body><header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">News Dispatch</a><p class=\"eyebrow\">Live Radar</p><h1>Ежечасный радар</h1><p class=\"lede\">Свежие публичные сигналы по зонам интереса. Это не аналитический выпуск, а быстрая карта того, что появилось в источниках.</p><nav class=\"hero-actions\" aria-label=\"Навигация\"><a href=\"../streams/index.html\">Потоки</a><a href=\"../dispatches.html\">Выпуски</a></nav></header><main>{''.join(blocks)}</main></body></html>"""
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    (RADAR_DIR / "index.html").write_text(text, encoding="utf-8")


def render_stream_pages(groups: dict[str, list]) -> None:
    for stream in streams():
        slug = str(stream["slug"])
        items = groups.get(slug, [])
        content = "".join(card(item) for item in items) or "<p>За последний запуск новых сигналов нет.</p>"
        text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — ' + str(stream['title']), str(stream['description']))}<body><header class=\"masthead compact\"><a class=\"backlink\" href=\"index.html\">Live Radar</a><p class=\"eyebrow\">{html.escape(str(stream['label']))}</p><h1>{html.escape(str(stream['title']))}</h1><p class=\"lede\">{html.escape(str(stream['description']))}</p></header><main><section class=\"reader-grid\">{content}</section></main></body></html>"""
        RADAR_DIR.mkdir(parents=True, exist_ok=True)
        (RADAR_DIR / f"{slug}.html").write_text(text, encoding="utf-8")


def write_report(day: date, selected: list, fetch_errors: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "date": day.isoformat(),
        "selected_count": len(selected),
        "fetch_errors": fetch_errors,
        "items": [
            {
                "stream": item.stream,
                "source": item.feed.title,
                "title": item.title,
                "url": item.url,
                "published": item.published.isoformat(),
                "score": item.score,
            }
            for item in selected
        ],
    }
    REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date) if args.date else date.today()
    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int(args.max_items or defaults.get("hourly_max_items", 36))
    per_source = int(args.per_source or defaults.get("per_source", 3))
    lookback = int(args.lookback_hours or defaults.get("hourly_lookback_hours", 8))
    raw_items, fetch_errors = fetch_items(feeds, timeout=args.timeout)
    seen = set() if args.no_state else load_seen(STATE_PATH)
    selected = select_items(raw_items, seen, max_items=max_items, per_source=per_source, lookback_hours=lookback)
    groups = group_by_stream(selected)
    if selected:
        for item in selected:
            write_signal(day, item, dry_run=args.dry_run)
        save_seen(STATE_PATH, seen, [item.key for item in selected], dry_run=args.dry_run or args.no_state)
    if not args.dry_run:
        render_index(groups)
        render_stream_pages(groups)
        write_report(day, selected, fetch_errors)
    log(f"selected {len(selected)} signal(s); feed warnings={len(fetch_errors)}")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return build(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
