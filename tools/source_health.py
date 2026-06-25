#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDS = ROOT / "sources" / "feeds.json"
REPORT = ROOT / "validation" / "daily-radar-latest.json"
OUT = ROOT / "validation" / "source-health-latest.json"


def load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def main() -> int:
    feeds = load(FEEDS, {"feeds": []}).get("feeds", [])
    report = load(REPORT, {})
    bad = {str(item).split(":", 1)[0] for item in report.get("fetch_errors", [])}
    rows = []
    for feed in feeds:
        if not isinstance(feed, dict):
            continue
        feed_id = str(feed.get("id", ""))
        enabled = feed.get("enabled", True) is not False
        rows.append({
            "id": feed_id,
            "title": feed.get("title", feed_id),
            "stream": feed.get("stream", "general"),
            "enabled": enabled,
            "status": "disabled" if not enabled else "error" if feed_id in bad else "ok",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"feeds": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
