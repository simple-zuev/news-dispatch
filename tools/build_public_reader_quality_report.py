#!/usr/bin/env python3
"""Build a bounded seven-day editorial quality report for the public reader."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from reader_text import (
    has_cyrillic,
    is_generic_reader_summary,
    parse_public_datetime,
    public_excerpt_ru,
    public_items_same_story,
    public_title_ru,
    stream_slug,
)

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "validation" / "public-reader-history-latest.json"
FEEDS_PATH = ROOT / "sources" / "feeds.json"
JSON_PATH = ROOT / "validation" / "public-reader-quality-latest.json"
MARKDOWN_PATH = ROOT / "validation" / "public-reader-quality-latest.md"
WINDOW_DAYS = 7
TARGET_SOURCES_PER_STREAM = 8


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_reference(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.now(timezone.utc)
    if len(text) == 10:
        return datetime.combine(datetime.fromisoformat(text).date(), time.max, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def item_datetime(item: dict[str, Any]) -> datetime | None:
    parsed, _has_time = parse_public_datetime(item.get("published") or item.get("date"))
    return parsed.astimezone(timezone.utc) if parsed else None


def successful_observation_dates(history: dict[str, Any], reference: datetime, window_days: int) -> list[str]:
    raw_values = history.get("observation_dates")
    if not isinstance(raw_values, list):
        return []
    earliest = reference.date() - timedelta(days=window_days - 1)
    dates = set()
    for value in raw_values:
        try:
            observed = datetime.fromisoformat(str(value).strip()[:10]).date()
        except ValueError:
            continue
        if earliest <= observed <= reference.date():
            dates.add(observed)
    return [value.isoformat() for value in sorted(dates)]


def window_items(
    history: dict[str, Any],
    *,
    reference: datetime,
    window_days: int,
) -> list[dict[str, Any]]:
    earliest = reference - timedelta(days=window_days)
    rows: list[dict[str, Any]] = []
    for item in history.get("items", []):
        if not isinstance(item, dict):
            continue
        published = item_datetime(item)
        if published is not None and earliest <= published <= reference + timedelta(hours=6):
            rows.append(item)
    return sorted(rows, key=lambda row: item_datetime(row) or earliest, reverse=True)


def configured_sources(feeds: dict[str, Any]) -> Counter[str]:
    publishers: dict[str, set[str]] = defaultdict(set)
    for feed in feeds.get("feeds", []):
        if not isinstance(feed, dict) or feed.get("enabled", True) is False:
            continue
        stream = str(feed.get("stream") or "")
        if not stream or stream == "general":
            continue
        publisher = str(feed.get("publisher_id") or feed.get("id") or "")
        if publisher:
            publishers[stream].add(publisher)
    return Counter({stream: len(values) for stream, values in publishers.items()})


def duplicate_rows(rows: list[dict[str, Any]]) -> int:
    unique: list[dict[str, Any]] = []
    duplicates = 0
    for row in rows:
        if any(public_items_same_story(row, previous) for previous in unique):
            duplicates += 1
        else:
            unique.append(row)
    return duplicates


def ratio(value: int, total: int) -> float:
    return round(value / total, 4) if total else 0.0


def build_report(
    history: dict[str, Any],
    feeds: dict[str, Any],
    *,
    reference: datetime,
    window_days: int = WINDOW_DAYS,
    target_sources: int = TARGET_SOURCES_PER_STREAM,
) -> dict[str, Any]:
    rows = window_items(history, reference=reference, window_days=window_days)
    inventory = configured_sources(feeds)
    item_streams = Counter(stream_slug(row) or "unknown" for row in rows)
    item_sources = Counter(
        str(row.get("publisher_id") or row.get("feed_id") or row.get("feed_title") or "unknown")
        for row in rows
    )
    stream_sources: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        stream_sources[stream_slug(row) or "unknown"].add(
            str(row.get("publisher_id") or row.get("feed_id") or row.get("feed_title") or "unknown")
        )

    dated = [published for row in rows if (published := item_datetime(row)) is not None]
    item_days = len({published.date().isoformat() for published in dated})
    build_dates = successful_observation_dates(history, reference, window_days)
    if build_dates:
        first_observed = datetime.fromisoformat(build_dates[0]).date()
        last_observed = datetime.fromisoformat(build_dates[-1]).date()
        observation_span_days = (last_observed - first_observed).days + 1
        observation_days = len(build_dates)
    else:
        observation_span_days = (max(dated).date() - min(dated).date()).days + 1 if dated else 0
        observation_days = item_days
    duplicate_count = duplicate_rows(rows)
    russian_titles = sum(1 for row in rows if has_cyrillic(public_title_ru(row)))
    useful_summaries = 0
    for row in rows:
        summary = public_excerpt_ru(row)
        if summary and has_cyrillic(summary) and not is_generic_reader_summary(summary):
            useful_summaries += 1

    dominant_source, dominant_count = item_sources.most_common(1)[0] if item_sources else ("", 0)
    dominant_share = ratio(dominant_count, len(rows))
    dominant_stream, dominant_stream_count = item_streams.most_common(1)[0] if item_streams else ("", 0)
    dominant_stream_share = ratio(dominant_stream_count, len(rows))
    coverage_gaps = {
        stream: target_sources - count
        for stream, count in sorted(inventory.items())
        if count < target_sources
    }
    missing_streams = sorted(stream for stream in inventory if item_streams.get(stream, 0) == 0)
    low_output_streams = sorted(
        stream for stream in inventory if 0 < item_streams.get(stream, 0) < 3
    ) if observation_span_days >= window_days else []
    mature_sample = observation_span_days >= min(window_days, 3) and len(rows) >= 8

    alerts: list[dict[str, str]] = []
    if not rows:
        alerts.append({"severity": "critical", "code": "empty_window", "message": "No reader-safe items in the reporting window."})
    if coverage_gaps:
        alerts.append({"severity": "advisory", "code": "source_coverage", "message": "Some streams remain below the configured source target."})
    if mature_sample and duplicate_count / len(rows) > 0.12:
        alerts.append({"severity": "advisory", "code": "duplicate_share", "message": "Related-story duplication exceeds 12%."})
    if mature_sample and dominant_share > 0.25:
        alerts.append({"severity": "advisory", "code": "source_concentration", "message": "One source supplies more than 25% of reader items."})
    if mature_sample and dominant_stream_share > 0.32:
        alerts.append({"severity": "advisory", "code": "stream_concentration", "message": "One stream supplies more than 32% of reader items."})
    if mature_sample and russian_titles / len(rows) < 0.9:
        alerts.append({"severity": "advisory", "code": "russian_title_coverage", "message": "Russian reader-title coverage is below 90%."})
    if mature_sample and useful_summaries / len(rows) < 0.95:
        alerts.append({"severity": "advisory", "code": "summary_coverage", "message": "Useful Russian summary coverage is below 95%."})
    if observation_span_days >= window_days and missing_streams:
        alerts.append({"severity": "advisory", "code": "missing_streams", "message": "Some configured streams produced no reader-safe items in seven days."})
    if low_output_streams:
        alerts.append({"severity": "advisory", "code": "low_stream_output", "message": "Some streams produced fewer than three reader-safe items in seven days."})

    if not rows:
        status = "attention"
    elif observation_span_days < window_days:
        status = "collecting"
    elif alerts:
        status = "attention"
    else:
        status = "healthy"

    return {
        "report_type": "public_reader_seven_day_quality",
        "generated_at": reference.isoformat(),
        "status": status,
        "window_days": window_days,
        "target_sources_per_stream": target_sources,
        "alerts": alerts,
        "coverage_gaps": coverage_gaps,
        "missing_streams": missing_streams,
        "low_output_streams": low_output_streams,
        "observed": {
            "items": len(rows),
            "calendar_days_with_items": item_days,
            "successful_observation_days": observation_days,
            "observation_span_days": observation_span_days,
            "streams": len(item_streams),
            "sources": len(item_sources),
            "duplicate_rows": duplicate_count,
            "duplicate_share": ratio(duplicate_count, len(rows)),
            "dominant_source": dominant_source,
            "dominant_source_share": dominant_share,
            "dominant_stream": dominant_stream,
            "dominant_stream_share": dominant_stream_share,
            "russian_title_coverage": ratio(russian_titles, len(rows)),
            "useful_summary_coverage": ratio(useful_summaries, len(rows)),
        },
        "configured_sources_by_stream": dict(sorted(inventory.items())),
        "reader_items_by_stream": dict(sorted(item_streams.items())),
        "reader_sources_by_stream": {stream: len(sources) for stream, sources in sorted(stream_sources.items())},
        "top_sources": dict(item_sources.most_common(10)),
    }


def markdown(report: dict[str, Any]) -> str:
    observed = report["observed"]
    configured = report["configured_sources_by_stream"]
    items = report["reader_items_by_stream"]
    sources = report["reader_sources_by_stream"]
    rows = [
        "# Public Reader 7-Day Quality Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Window: {report['window_days']} days",
        f"- Reader-safe items: {observed['items']}",
        f"- Observation span: {observed['observation_span_days']} days",
        f"- Sources represented: {observed['sources']}",
        f"- Duplicate share: {observed['duplicate_share']:.1%}",
        f"- Dominant source share: {observed['dominant_source_share']:.1%}",
        f"- Dominant stream share: {observed['dominant_stream_share']:.1%}",
        f"- Russian title coverage: {observed['russian_title_coverage']:.1%}",
        f"- Useful summary coverage: {observed['useful_summary_coverage']:.1%}",
        "",
        "## Stream balance",
        "",
        "| Stream | Configured sources | Reader items | Reader sources |",
        "| --- | ---: | ---: | ---: |",
    ]
    for stream in sorted(configured):
        rows.append(f"| {stream} | {configured[stream]} | {items.get(stream, 0)} | {sources.get(stream, 0)} |")
    rows.extend(["", "## Alerts", ""])
    if report["alerts"]:
        rows.extend(f"- [{alert['severity']}] {alert['message']}" for alert in report["alerts"])
    else:
        rows.append("- none")
    return "\n".join(rows) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--feeds", type=Path, default=FEEDS_PATH)
    parser.add_argument("--json-output", type=Path, default=JSON_PATH)
    parser.add_argument("--markdown-output", type=Path, default=MARKDOWN_PATH)
    parser.add_argument("--reference-time", default="")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    history = load_json(args.history)
    reference = parse_reference(args.reference_time or history.get("date"))
    report = build_report(
        history,
        load_json(args.feeds),
        reference=reference,
        window_days=args.window_days,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown(report), encoding="utf-8")
    print(
        "Public reader quality report: "
        f"{report['status']}, {report['observed']['items']} item(s), "
        f"{len(report['alerts'])} alert(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
