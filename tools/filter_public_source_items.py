#!/usr/bin/env python3
"""Remove non-article public source rows before reader policy and rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PATH = ROOT / "validation" / "daily-radar-ranking-latest.json"
SITE_PATH = ROOT / "site" / "daily-radar-ranking-latest.json"
COMMENT_FEED_MARKERS = (
    "/comments/default",
    "/feeds/comments",
)


def url_text(item: dict[str, Any]) -> str:
    fields = (
        item.get("url"),
        item.get("source_original_url"),
        item.get("link"),
        item.get("source_url"),
    )
    return " ".join(str(field or "") for field in fields).lower()


def should_remove(item: dict[str, Any]) -> bool:
    text = url_text(item)
    return any(marker in text for marker in COMMENT_FEED_MARKERS)


def filter_report(report: dict[str, Any]) -> int:
    items = report.get("items", [])
    if not isinstance(items, list):
        return 0
    kept: list[Any] = []
    removed = 0
    for item in items:
        if isinstance(item, dict) and should_remove(item):
            removed += 1
            continue
        kept.append(item)
    report["items"] = kept
    report["selected_keys_count"] = sum(
        1 for item in kept if isinstance(item, dict) and item.get("selected")
    )
    diagnostics = report.setdefault("public_source_filter", {})
    if isinstance(diagnostics, dict):
        diagnostics["removed_comment_feed_items"] = removed
    return removed


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not VALIDATION_PATH.exists():
        print("Public source filter: ranking report is absent.")
        return 0
    report = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        print("Public source filter: ranking report is not an object.")
        return 0
    removed = filter_report(report)
    write_report(VALIDATION_PATH, report)
    if SITE_PATH.exists():
        write_report(SITE_PATH, report)
    print(f"Public source filter: removed {removed} comment-feed item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
