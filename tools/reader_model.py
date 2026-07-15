#!/usr/bin/env python3
"""Typed public-reader model contract.

This module is intentionally introduced beside the current renderers first.  It
creates a strict public-only contract from ranking rows without changing public
HTML output.  Later renderer refactors should consume this model directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

PUBLIC_RENDER_KEYS = (
    "title",
    "excerpt",
    "summary",
    "why_it_matters",
    "meta",
    "time",
    "published_at",
    "story_key",
    "source",
    "stream",
    "reliability",
    "url",
    "original_title",
)

FORBIDDEN_PUBLIC_KEYS = {
    "feed_id",
    "item_key",
    "selected",
    "selection_reason",
    "selection_score",
    "final_score",
    "relevance_score",
    "min_relevance_score",
    "source_rule_status",
    "validation",
    "threshold",
    "coverage",
    "reader_safe",
}


@dataclass(frozen=True)
class PublicReaderItem:
    """Public-only reader item used by homepage/news/today renderers.

    It deliberately excludes ranking, filtering, and validation internals.  The
    model keeps only fields that may be rendered to a public page.
    """

    title: str
    excerpt: str
    summary: str
    why_it_matters: str
    meta: str
    time: str
    published_at: str
    story_key: str
    source: str
    stream: str
    reliability: str
    url: str
    original_title: str = ""

    def to_render_dict(self) -> dict[str, str]:
        """Return the legacy renderer shape while preserving the public contract."""
        payload = {
            "title": self.title,
            "excerpt": self.excerpt,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "meta": self.meta,
            "time": self.time,
            "published_at": self.published_at,
            "story_key": self.story_key,
            "source": self.source,
            "stream": self.stream,
            "reliability": self.reliability,
            "url": self.url,
            "original_title": self.original_title,
        }
        assert_public_render_dict(payload)
        return payload


def assert_public_render_dict(payload: Mapping[str, str]) -> None:
    """Fail if a public render payload leaks non-public diagnostic fields."""
    keys = set(payload)
    extra = keys - set(PUBLIC_RENDER_KEYS)
    forbidden = keys & FORBIDDEN_PUBLIC_KEYS
    if extra or forbidden:
        problems = []
        if extra:
            problems.append(f"unexpected public keys: {sorted(extra)}")
        if forbidden:
            problems.append(f"forbidden public keys: {sorted(forbidden)}")
        raise ValueError("; ".join(problems))


def from_ranking_item(item: Mapping[str, Any], stream: object | None = None) -> PublicReaderItem:
    """Build a public reader model from a ranking row.

    Importing reader_text lazily avoids coupling the typed contract to the text
    helper module at import time and lets existing renderers migrate gradually.
    """
    from reader_text import (  # pylint: disable=import-outside-toplevel
        format_public_time_ru,
        public_excerpt_ru,
        public_meta_ru,
        public_reliability_label,
        public_source_name,
        public_story_key,
        public_stream_name,
        public_text,
        public_title_ru,
        public_why_it_matters_ru,
        source_original_title,
    )

    row = dict(item)
    original = public_text(source_original_title(row)).strip()
    title = public_title_ru(row)
    excerpt = public_excerpt_ru(row)
    return PublicReaderItem(
        title=title,
        excerpt=excerpt,
        summary=excerpt,
        why_it_matters=public_why_it_matters_ru(row, stream),
        meta=public_meta_ru(row, stream),
        time=format_public_time_ru(row.get("published") or row.get("date")),
        published_at=str(row.get("published") or row.get("date") or "").strip(),
        story_key=public_story_key(row, stream),
        source=public_source_name(row),
        stream=public_stream_name(row, stream),
        reliability=public_reliability_label(row),
        url=str(row.get("url") or "").strip(),
        original_title=original if original != title else "",
    )
