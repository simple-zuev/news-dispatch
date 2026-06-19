#!/usr/bin/env python3
"""Run Daily Radar in a guarded signal-collection mode."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "sources" / "feeds.json"
DAILY_RADAR_PATH = ROOT / "tools" / "daily_radar.py"

DISABLED_FEEDS = {
    "the-verge-ai",
}

ORIGINAL_CLASSIFY = '''def classify(feed: Feed, title: str, summary: str) -> str:
    haystack = f"{title} {summary} {' '.join(feed.tags)}".lower()
    scores = {stream: sum(1 for word in words if word in haystack) for stream, words in KEYWORDS.items()}
    if not scores:
        return feed.stream
    best_stream, best_score = max(scores.items(), key=lambda pair: pair[1])
    return best_stream if best_score > 0 else feed.stream
'''

SAFE_CLASSIFY = '''def classify(feed: Feed, title: str, summary: str) -> str:
    return feed.stream
'''


def disable_broad_feeds() -> None:
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    changed = False
    for feed in data.get("feeds", []):
        if feed.get("id") in DISABLED_FEEDS:
            feed["enabled"] = False
            changed = True
    if changed:
        FEEDS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Disabled broad Daily Radar feeds: {', '.join(sorted(DISABLED_FEEDS))}")


def force_feed_owned_routing() -> None:
    text = DAILY_RADAR_PATH.read_text(encoding="utf-8")
    if SAFE_CLASSIFY in text:
        return
    if ORIGINAL_CLASSIFY not in text:
        raise SystemExit("Expected daily_radar classify() implementation not found.")
    DAILY_RADAR_PATH.write_text(text.replace(ORIGINAL_CLASSIFY, SAFE_CLASSIFY, 1), encoding="utf-8")
    print("Forced feed-owned stream routing for Daily Radar.")


def run(command: list[str]) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    disable_broad_feeds()
    force_feed_owned_routing()
    run([sys.executable, "tools/daily_radar.py"])
    run([sys.executable, "tools/filter_daily_signals.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
