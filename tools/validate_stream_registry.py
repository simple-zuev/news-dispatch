#!/usr/bin/env python3
"""Validate the shared topic stream registry and feed mappings."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAMS_PATH = ROOT / "data" / "streams.json"
FEEDS_PATH = ROOT / "sources" / "feeds.json"

REQUIRED_STREAM_KEYS = {
    "slug",
    "title",
    "label",
    "description",
    "strict",
    "review_level",
    "min_publish_items",
    "regions",
    "keywords",
}

ALLOWED_REVIEW_LEVELS = {"standard_public_review", "strict_publication_review"}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_streams(data: dict[str, object]) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    raw_streams = data.get("streams", [])
    if not isinstance(raw_streams, list) or not raw_streams:
        return set(), ["data/streams.json: streams must be a non-empty list"]
    slugs: set[str] = set()
    for index, item in enumerate(raw_streams):
        if not isinstance(item, dict):
            errors.append(f"data/streams.json: stream #{index} must be an object")
            continue
        missing = REQUIRED_STREAM_KEYS - set(item)
        slug = str(item.get("slug", f"#{index}"))
        if missing:
            errors.append(f"data/streams.json: stream {slug}: missing keys: {', '.join(sorted(missing))}")
        if slug in slugs:
            errors.append(f"data/streams.json: duplicate stream slug {slug}")
        slugs.add(slug)
        if item.get("review_level") not in ALLOWED_REVIEW_LEVELS:
            errors.append(f"data/streams.json: stream {slug}: invalid review_level")
        if not isinstance(item.get("regions"), list):
            errors.append(f"data/streams.json: stream {slug}: regions must be a list")
        if not isinstance(item.get("keywords"), list):
            errors.append(f"data/streams.json: stream {slug}: keywords must be a list")
        try:
            min_items = int(item.get("min_publish_items", 0))
            if min_items < 1:
                errors.append(f"data/streams.json: stream {slug}: min_publish_items must be >= 1")
        except (TypeError, ValueError):
            errors.append(f"data/streams.json: stream {slug}: min_publish_items must be an integer")
    legacy = data.get("legacy_streams", {})
    if not isinstance(legacy, dict):
        errors.append("data/streams.json: legacy_streams must be an object")
    else:
        for legacy_slug, targets in legacy.items():
            if not isinstance(targets, list) or not targets:
                errors.append(f"data/streams.json: legacy stream {legacy_slug}: targets must be a non-empty list")
                continue
            for target in targets:
                if str(target) not in slugs:
                    errors.append(f"data/streams.json: legacy stream {legacy_slug}: unknown target {target}")
    return slugs, errors


def validate_feeds(feed_data: dict[str, object], allowed_streams: set[str]) -> list[str]:
    errors: list[str] = []
    feeds = feed_data.get("feeds", [])
    if not isinstance(feeds, list) or not feeds:
        return ["sources/feeds.json: feeds must be a non-empty list"]
    ids: set[str] = set()
    for index, feed in enumerate(feeds):
        if not isinstance(feed, dict):
            errors.append(f"sources/feeds.json: feed #{index} must be an object")
            continue
        feed_id = str(feed.get("id", f"#{index}"))
        if feed_id in ids:
            errors.append(f"sources/feeds.json: duplicate feed id {feed_id}")
        ids.add(feed_id)
        for key in ("id", "title", "url", "stream", "source_type", "source_class", "priority", "tags"):
            if key not in feed:
                errors.append(f"sources/feeds.json: feed {feed_id}: missing {key}")
        stream = str(feed.get("stream", ""))
        if stream not in allowed_streams:
            errors.append(f"sources/feeds.json: feed {feed_id}: unknown stream {stream}")
        if not str(feed.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"sources/feeds.json: feed {feed_id}: url must be http(s)")
        if not isinstance(feed.get("tags", []), list):
            errors.append(f"sources/feeds.json: feed {feed_id}: tags must be a list")
        try:
            priority = float(feed.get("priority", 0))
            if not 0 <= priority <= 1:
                errors.append(f"sources/feeds.json: feed {feed_id}: priority must be between 0 and 1")
        except (TypeError, ValueError):
            errors.append(f"sources/feeds.json: feed {feed_id}: priority must be numeric")
    return errors


def main() -> int:
    errors: list[str] = []
    streams_data = load_json(STREAMS_PATH)
    slugs, stream_errors = validate_streams(streams_data)
    errors.extend(stream_errors)
    errors.extend(validate_feeds(load_json(FEEDS_PATH), slugs))
    if errors:
        print("Stream registry validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Stream registry validation passed for {len(slugs)} stream(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
