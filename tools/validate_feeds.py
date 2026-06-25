#!/usr/bin/env python3
"""Validate public RSS/Atom feed configuration for News Dispatch."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from stream_registry import stream_slugs

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "sources" / "feeds.json"

REQUIRED_KEYS = {
    "id",
    "title",
    "url",
    "stream",
    "source_type",
    "source_class",
    "priority",
    "tags",
}

ALLOWED_SOURCE_CLASSES = {
    "official_source",
    "public_media",
    "specialized_media",
    "research_media",
}


def validate() -> list[str]:
    errors: list[str] = []
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    feeds = data.get("feeds", [])
    if not isinstance(feeds, list) or not feeds:
        return ["sources/feeds.json: feeds must be a non-empty list"]

    allowed_streams = stream_slugs()
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()

    for index, feed in enumerate(feeds):
        prefix = f"sources/feeds.json feeds[{index}]"
        if not isinstance(feed, dict):
            errors.append(f"{prefix}: feed must be an object")
            continue

        missing = sorted(REQUIRED_KEYS - set(feed))
        if missing:
            errors.append(f"{prefix}: missing keys: {', '.join(missing)}")

        feed_id = str(feed.get("id", "")).strip()
        if not feed_id:
            errors.append(f"{prefix}: id is empty")
        elif feed_id in seen_ids:
            errors.append(f"{prefix}: duplicate id {feed_id!r}")
        seen_ids.add(feed_id)

        url = str(feed.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{prefix}: invalid url {url!r}")
        elif url in seen_urls:
            errors.append(f"{prefix}: duplicate url {url!r}")
        seen_urls.add(url)

        stream = str(feed.get("stream", "")).strip()
        if stream not in allowed_streams:
            errors.append(f"{prefix}: unknown stream {stream!r}")

        source_class = str(feed.get("source_class", "")).strip()
        if source_class not in ALLOWED_SOURCE_CLASSES:
            errors.append(f"{prefix}: unknown source_class {source_class!r}")

        try:
            priority = float(feed.get("priority"))
        except (TypeError, ValueError):
            errors.append(f"{prefix}: priority must be numeric")
        else:
            if not 0 <= priority <= 1:
                errors.append(f"{prefix}: priority must be between 0 and 1")

        tags = feed.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            errors.append(f"{prefix}: tags must be a list of non-empty strings")

        if feed.get("enabled", True) is False and not str(feed.get("disabled_reason", "")).strip():
            errors.append(f"{prefix}: disabled feeds require disabled_reason")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Feed validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Feed validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
