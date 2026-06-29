#!/usr/bin/env python3
"""Build a public-safe source governance report for Daily Radar feeds."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "sources" / "feeds.json"
SOURCE_HEALTH_PATH = ROOT / "validation" / "source-health-latest.json"
REPORT_JSON = ROOT / "validation" / "source-governance-latest.json"
REPORT_MD = ROOT / "validation" / "source-governance-latest.md"

HIGH_TRUST_CLASSES = {"official_source", "research_media"}
WEAK_SIGNAL_CLASSES = {"public_media"}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def enabled(feed: dict[str, Any]) -> bool:
    return feed.get("enabled", True) is not False


def health_by_id() -> dict[str, str]:
    data = load_json(SOURCE_HEALTH_PATH, {"feeds": []})
    rows = data.get("feeds", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("id", "")): str(row.get("status", "unknown"))
        for row in rows
        if isinstance(row, dict) and row.get("id")
    }


def stream_summary(feeds: list[dict[str, Any]], health: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feed in feeds:
        grouped[str(feed.get("stream", "general"))].append(feed)

    rows: list[dict[str, Any]] = []
    for stream in sorted(grouped):
        items = grouped[stream]
        active = [feed for feed in items if enabled(feed)]
        class_counts = Counter(str(feed.get("source_class", "unknown")) for feed in items)
        enabled_class_counts = Counter(str(feed.get("source_class", "unknown")) for feed in active)
        disabled = [feed for feed in items if not enabled(feed)]
        error_count = sum(1 for feed in active if health.get(str(feed.get("id", ""))) == "error")
        rows.append({
            "stream": stream,
            "total_sources": len(items),
            "enabled_sources": len(active),
            "disabled_sources": len(disabled),
            "class_counts": dict(sorted(class_counts.items())),
            "enabled_class_counts": dict(sorted(enabled_class_counts.items())),
            "enabled_official_sources": enabled_class_counts.get("official_source", 0),
            "enabled_high_trust_sources": sum(enabled_class_counts.get(name, 0) for name in sorted(HIGH_TRUST_CLASSES)),
            "enabled_fetch_errors": error_count,
        })
    return rows


def feed_rows(feeds: list[dict[str, Any]], health: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for feed in feeds:
        feed_id = str(feed.get("id", ""))
        source_class = str(feed.get("source_class", "unknown"))
        priority = float(feed.get("priority", 0))
        feed_enabled = enabled(feed)
        keyword_count = len(feed.get("include_keywords", []) or [])
        exclude_count = len(feed.get("exclude_keywords", []) or [])
        risk_flags: list[str] = []

        if not feed_enabled:
            risk_flags.append("disabled")
        if feed_enabled and health.get(feed_id) == "error":
            risk_flags.append("fetch_error")
        if feed_enabled and source_class in WEAK_SIGNAL_CLASSES:
            risk_flags.append("public_media_needs_corroboration")
        if feed_enabled and source_class in {"public_media", "specialized_media"} and keyword_count == 0:
            risk_flags.append("missing_include_keywords")
        if feed_enabled and source_class == "public_media" and exclude_count == 0:
            risk_flags.append("missing_exclude_keywords")
        if feed_enabled and priority < 0.65:
            risk_flags.append("low_priority_enabled")

        rows.append({
            "id": feed_id,
            "title": feed.get("title", feed_id),
            "stream": feed.get("stream", "general"),
            "source_class": source_class,
            "enabled": feed_enabled,
            "health_status": health.get(feed_id, "unknown"),
            "priority": priority,
            "include_keyword_count": keyword_count,
            "exclude_keyword_count": exclude_count,
            "risk_flags": risk_flags,
            "disabled_reason": feed.get("disabled_reason", "") if not feed_enabled else "",
        })
    return rows


def recommendations(streams: list[dict[str, Any]], feeds: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for row in streams:
        stream = row["stream"]
        if row["enabled_sources"] == 0:
            notes.append(f"{stream}: add or re-enable at least one source before relying on the stream.")
        elif row["enabled_official_sources"] == 0:
            notes.append(f"{stream}: add or restore official-source coverage for stronger confirmation.")
        if row["enabled_fetch_errors"]:
            notes.append(f"{stream}: review feeds with current fetch errors before promotion decisions.")

    disabled_official = [feed["id"] for feed in feeds if feed["source_class"] == "official_source" and not feed["enabled"]]
    if disabled_official:
        notes.append("Disabled official sources require replacement or a stable fallback: " + ", ".join(sorted(disabled_official)) + ".")

    noisy = [feed["id"] for feed in feeds if "public_media_needs_corroboration" in feed["risk_flags"]]
    if noisy:
        notes.append("Public-media signals should be corroborated before editorial promotion: " + ", ".join(sorted(noisy)) + ".")

    return notes


def build_report() -> dict[str, Any]:
    feeds = load_json(FEEDS_PATH, {"feeds": []}).get("feeds", [])
    if not isinstance(feeds, list):
        feeds = []
    feed_dicts = [feed for feed in feeds if isinstance(feed, dict)]
    health = health_by_id()
    streams = stream_summary(feed_dicts, health)
    rows = feed_rows(feed_dicts, health)

    class_counts = Counter(row["source_class"] for row in rows)
    enabled_class_counts = Counter(row["source_class"] for row in rows if row["enabled"])
    disabled = [row for row in rows if not row["enabled"]]
    risk_counts = Counter(flag for row in rows for flag in row["risk_flags"])

    return {
        "status": "pre-publication source governance artifact",
        "total_sources": len(rows),
        "enabled_sources": sum(1 for row in rows if row["enabled"]),
        "disabled_sources": len(disabled),
        "class_counts": dict(sorted(class_counts.items())),
        "enabled_class_counts": dict(sorted(enabled_class_counts.items())),
        "streams": streams,
        "feeds": sorted(rows, key=lambda row: (str(row["stream"]), str(row["id"]))),
        "risk_counts": dict(sorted(risk_counts.items())),
        "recommendations": recommendations(streams, rows),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source Governance Report",
        "",
        "Status: pre-publication source governance artifact.",
        "",
        "This report summarizes source coverage, reliability flags and editorial review needs. It does not publish content and does not change feed lifecycle state.",
        "",
        "## Summary",
        "",
        f"- Total sources: {report['total_sources']}",
        f"- Enabled sources: {report['enabled_sources']}",
        f"- Disabled sources: {report['disabled_sources']}",
        "",
        "## Stream coverage",
        "",
        "| Stream | Enabled / total | Enabled official | Enabled high-trust | Fetch errors |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["streams"]:
        lines.append(
            f"| {row['stream']} | {row['enabled_sources']} / {row['total_sources']} | "
            f"{row['enabled_official_sources']} | {row['enabled_high_trust_sources']} | {row['enabled_fetch_errors']} |"
        )

    lines.extend(["", "## Risk flags", ""])
    if report["risk_counts"]:
        for name, count in report["risk_counts"].items():
            lines.append(f"- {name}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Recommendations", ""])
    if report["recommendations"]:
        for item in report["recommendations"]:
            lines.append(f"- {item}")
    else:
        lines.append("- No source governance recommendations generated.")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {REPORT_JSON.relative_to(ROOT)}")
    print(f"Wrote {REPORT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
