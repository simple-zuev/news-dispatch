#!/usr/bin/env python3
"""Coverage checks for stream source configuration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
STREAMS_PATH = ROOT / "data" / "streams.json"
SOURCES_PATH = ROOT / "sources" / "feeds.json"

EXEMPT_STREAMS = {
    "general",  # Cross-domain special stream, not a primary source category.
}

TEMPORARILY_PAUSED_STREAMS: set[str] = set()
MIN_ACTIVE_BY_STREAM = {
    "gear-style-edc": 4,
    "moscow-city": 7,
}
DEFAULT_MIN_ACTIVE = 5


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
        minimum = MIN_ACTIVE_BY_STREAM.get(slug, DEFAULT_MIN_ACTIVE)
        if counts.get(slug, 0) < minimum:
            missing.append(slug)
    assert not missing, "Streams below minimum active source coverage: " + ", ".join(sorted(missing))


def test_moscow_stream_has_multiple_russian_publishers() -> None:
    feeds = [
        feed
        for feed in load_json(SOURCES_PATH).get("feeds", [])
        if feed.get("stream") == "moscow-city" and feed.get("enabled", True)
    ]
    assert len(feeds) >= 7
    assert all(feed.get("language") == "ru" for feed in feeds)
    assert len({str(feed.get("title")) for feed in feeds}) == len(feeds)
    publishers = {str(feed.get("publisher_id") or feed.get("id")) for feed in feeds}
    assert len(publishers) >= 6


def test_high_volume_feeds_have_explicit_caps() -> None:
    from build_daily_radar_ranking_report import SOURCE_ROW_CAPS

    assert SOURCE_ROW_CAPS["huggingface-blog"] <= 12
    assert SOURCE_ROW_CAPS["nature-news"] <= 16
    assert SOURCE_ROW_CAPS["mskagency-culture"] <= 12
    assert SOURCE_ROW_CAPS["core77-design"] <= 12
    assert SOURCE_ROW_CAPS["ria-moscow-city"] <= 12
    assert SOURCE_ROW_CAPS["big-city-moscow"] <= 10


def test_paused_streams_are_explicit_and_visible() -> None:
    counts = active_source_counts()
    for slug in TEMPORARILY_PAUSED_STREAMS:
        assert counts.get(slug, 0) == 0, f"{slug} should be removed from TEMPORARILY_PAUSED_STREAMS after adding an active source"


def main() -> int:
    test_primary_public_streams_have_active_sources_or_explicit_pause()
    test_paused_streams_are_explicit_and_visible()
    test_moscow_stream_has_multiple_russian_publishers()
    test_high_volume_feeds_have_explicit_caps()
    print("source coverage tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
