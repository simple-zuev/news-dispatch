#!/usr/bin/env python3
"""Shared stream registry helpers for News Dispatch tools."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STREAMS_PATH = ROOT / "data" / "streams.json"


@lru_cache(maxsize=1)
def registry() -> dict[str, Any]:
    return json.loads(STREAMS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def streams() -> list[dict[str, Any]]:
    return list(registry().get("streams", []))


@lru_cache(maxsize=1)
def stream_by_slug() -> dict[str, dict[str, Any]]:
    return {str(item["slug"]): item for item in streams()}


@lru_cache(maxsize=1)
def stream_slugs() -> set[str]:
    return set(stream_by_slug())


@lru_cache(maxsize=1)
def allowed_stream_slugs() -> set[str]:
    legacy = set(registry().get("legacy_streams", {}).keys())
    return stream_slugs() | legacy


def stream_title(slug: str) -> str:
    stream = stream_by_slug().get(slug)
    return str(stream.get("title", slug)) if stream else slug


def stream_label(slug: str) -> str:
    stream = stream_by_slug().get(slug)
    return str(stream.get("label", "Редакционная проверка")) if stream else "Редакционная проверка"


def stream_description(slug: str) -> str:
    stream = stream_by_slug().get(slug)
    return str(stream.get("description", slug)) if stream else slug


def stream_review_level(slug: str) -> str:
    stream = stream_by_slug().get(slug)
    if stream:
        return str(stream.get("review_level", "standard_public_review"))
    return "standard_public_review"


def stream_min_publish_items(slug: str, default: int = 2) -> int:
    stream = stream_by_slug().get(slug)
    if not stream:
        return default
    try:
        return int(stream.get("min_publish_items", default))
    except (TypeError, ValueError):
        return default


def stream_keywords() -> dict[str, list[str]]:
    return {str(item["slug"]): [str(word) for word in item.get("keywords", [])] for item in streams()}
