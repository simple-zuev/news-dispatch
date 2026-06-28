#!/usr/bin/env python3
"""Coverage checks for stream source configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAMS_PATH = ROOT / "data" / "streams.json"
SOURCES_PATH = ROOT / "sources" / "feeds.json"

EXEMPT_STREAMS = {
    "general",  # Cross-domain special stream, not a primary source category.
}

TEMPORARILY_PAUSED_STREAMS: set[str] = set()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def active_source_counts() -> dict[str, int]:
    result: dict[str, int] = {}
    for feed in load_json(SOURCES_PATH).get("feeds", []):
        stream = str(feed.get("stream") or "")
        if not stream:
            continue
        if feed.get("enabled") is False:
            result.setdefault(stream, 0)
            continue
        result[stream] = result.get(stream, 0) + 1
    return result


def public_streams() -> list[str]:
    return [str(stream["slug"]) for stream in load_json(STREAMS_PATH).get("streams", [])]


def test_primary_public_streams_have_active_sources_or_explicit_pause() -> None:
    counts = active_source_counts()
    missing = []
    for slug in public_streams():
        if slug in EXEMPT_STREAMS or slug in TEMPORARILY_PAUSED_STREAMS:
            continue
        if counts.get(slug, 0) < 1:
            missing.append(slug)
    assert not missing, "Streams without active source coverage: " + ", ".join(sorted(missing))


def test_paused_streams_are_explicit_and_visible() -> None:
    counts = active_source_counts()
    for slug in TEMPORARILY_PAUSED_STREAMS:
        assert counts.get(slug, 0) == 0, f"{slug} should be removed from TEMPORARILY_PAUSED_STREAMS after adding an active source"


def main() -> int:
    test_primary_public_streams_have_active_sources_or_explicit_pause()
    test_paused_streams_are_explicit_and_visible()
    print("source coverage tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
