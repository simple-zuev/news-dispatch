#!/usr/bin/env python3
"""Regression tests for reader title quality edge cases."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "reader_text.py"

sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("reader_text", MODULE_PATH)
assert spec is not None and spec.loader is not None
reader_text = importlib.util.module_from_spec(spec)
sys.modules["reader_text"] = reader_text
spec.loader.exec_module(reader_text)


def security_item() -> dict[str, object]:
    return {
        "feed_title": "Google Security Blog",
        "feed_id": "google-security-blog",
        "configured_stream": "tech-hardware-software",
        "routed_stream": "tech-hardware-software",
        "source_class": "official",
        "source_type": "official",
        "title": "New memory safety protections for Android",
        "source_original_title": "New memory safety protections for Android",
        "source_excerpt": "Security and cryptography updates for Android developers.",
        "url": "https://security.googleblog.com/2026/07/android-memory-safety.html",
        "published": "2026-07-09T08:58:00+00:00",
        "selected": True,
    }


def test_security_blog_is_not_treated_as_sec_regulator_signal() -> None:
    item = security_item()
    assert reader_text.russian_topic(item) == "безопасность и технологическая инфраструктура"
    title = reader_text.public_title_ru(item)
    assert title == "Google Security Blog: New memory safety protections for Android"
    assert "регуляторика и надзор" not in title.lower()


def test_sec_regulator_token_still_maps_to_regulatory_topic() -> None:
    item = {
        "feed_title": "SEC",
        "configured_stream": "finance",
        "routed_stream": "finance",
        "source_class": "regulator",
        "title": "SEC market statistics update",
        "source_original_title": "SEC market statistics update",
        "url": "https://www.sec.gov/news/stats",
    }
    assert reader_text.russian_topic(item) == "статистика рынка SEC"
    assert reader_text.public_title_ru(item) == "SEC обновила статистику рынка"


def test_source_topic_fallback_uses_original_title_when_available() -> None:
    item = security_item()
    item["reader_title_ru"] = "Google Security Blog: безопасность и технологическая инфраструктура"
    title = reader_text.public_title_ru(item)
    assert title == "Google Security Blog: New memory safety protections for Android"


def main() -> int:
    test_security_blog_is_not_treated_as_sec_regulator_signal()
    test_sec_regulator_token_still_maps_to_regulatory_topic()
    test_source_topic_fallback_uses_original_title_when_available()
    print("reader title quality tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
