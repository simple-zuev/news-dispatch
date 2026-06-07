#!/usr/bin/env python3
"""Build a static source-health report for News Dispatch feeds."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "sources" / "feeds.json"
REPORT_PATH = ROOT / "data" / "hourly-radar-latest.json"
OUTPUT_JSON = ROOT / "data" / "source-health.json"
OUTPUT_HTML = ROOT / "site" / "radar" / "source-health.html"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def feed_errors(report: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    for raw in report.get("fetch_errors", []):
        text = str(raw)
        if ":" in text:
            feed_id, message = text.split(":", 1)
            errors[feed_id.strip()] = message.strip()
    return errors


def item_counts(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", ""))
        if source:
            counts[source] = counts.get(source, 0) + 1
    return counts


def build_statuses() -> list[dict[str, Any]]:
    feed_data = load_json(FEEDS_PATH, {"feeds": []})
    report = load_json(REPORT_PATH, {})
    errors = feed_errors(report)
    counts = item_counts(report)
    statuses: list[dict[str, Any]] = []
    for feed in feed_data.get("feeds", []):
        if not isinstance(feed, dict):
            continue
        feed_id = str(feed.get("id", ""))
        title = str(feed.get("title", feed_id))
        error = errors.get(feed_id, "")
        statuses.append(
            {
                "id": feed_id,
                "title": title,
                "stream": str(feed.get("stream", "general")),
                "url": str(feed.get("url", "")),
                "priority": feed.get("priority", ""),
                "status": "error" if error else "ok",
                "error": error,
                "latest_selected_count": counts.get(title, 0),
            }
        )
    return statuses


def write_json(statuses: list[dict[str, Any]]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "feeds": statuses,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def status_card(feed: dict[str, Any]) -> str:
    status = str(feed.get("status", "unknown"))
    label = "Ошибка" if status == "error" else "OK"
    error = str(feed.get("error", ""))
    details = error if error else f"Выбрано сигналов в последнем запуске: {feed.get('latest_selected_count', 0)}"
    return f"""<article class=\"source-card radar-card source-health-{html.escape(status)}\">
  <p class=\"label\">{html.escape(label)} · {html.escape(str(feed.get('stream', '')))}</p>
  <h3><a href=\"{html.escape(str(feed.get('url', '')), quote=True)}\">{html.escape(str(feed.get('title', 'Источник')))}</a></h3>
  <p>{html.escape(details)}</p>
  <p class=\"radar-meta\">id: {html.escape(str(feed.get('id', '')))} · priority: {html.escape(str(feed.get('priority', '')))}</p>
</article>"""


def write_html(statuses: list[dict[str, Any]]) -> None:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    ok_count = sum(1 for feed in statuses if feed.get("status") == "ok")
    error_count = sum(1 for feed in statuses if feed.get("status") == "error")
    cards = "".join(status_card(feed) for feed in statuses)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = f"""<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>News Dispatch — Source Health</title><meta name=\"description\" content=\"Состояние источников News Dispatch.\"><link rel=\"stylesheet\" href=\"../styles/main.css\"><link rel=\"stylesheet\" href=\"../styles/reader.css\"><link rel=\"stylesheet\" href=\"../styles/radar.css\"></head><body><header class=\"masthead compact radar-hero\"><a class=\"backlink\" href=\"index.html\">Live Radar</a><p class=\"eyebrow\">Source Health</p><h1>Состояние источников</h1><p class=\"lede\">Техническая карта RSS/Atom-источников: что работает, что падает, какие источники дали сигналы в последнем запуске.</p><p class=\"radar-status\">Обновлено: {html.escape(updated)} · OK: {ok_count} · ошибки: {error_count}</p></header><main class=\"radar-layout\"><section class=\"reader-grid radar-grid\">{cards}</section></main></body></html>"""
    OUTPUT_HTML.write_text(text, encoding="utf-8")


def main() -> int:
    statuses = build_statuses()
    write_json(statuses)
    write_html(statuses)
    print(f"Source health report generated for {len(statuses)} feed(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
