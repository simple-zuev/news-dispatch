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
    assert title == (
        "Google Security Blog сообщает об изменениях в технологиях и безопасности: "
        "New memory safety protections for Android"
    )
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


def test_source_topic_fallback_stays_reader_facing_and_russian() -> None:
    item = security_item()
    item["reader_title_ru"] = "Google Security Blog: безопасность и технологическая инфраструктура"
    title = reader_text.public_title_ru(item)
    assert title == (
        "Google Security Blog сообщает об изменениях в технологиях и безопасности: "
        "New memory safety protections for Android"
    )


def test_unresolved_security_source_topic_gets_clean_public_title() -> None:
    item = security_item()
    item["title"] = "Google Security Blog: регуляторика и надзор"
    item["source_original_title"] = "Google Security Blog: регуляторика и надзор"
    item["reader_title_ru"] = "Google Security Blog: регуляторика и надзор"
    title = reader_text.public_title_ru(item)
    assert title == "Google описывает безопасность и технологическую инфраструктуру"
    assert "регуляторика и надзор" not in title.lower()


def test_english_title_keeps_original_words_instead_of_mixing_languages() -> None:
    item = {
        "feed_title": "OpenAI News",
        "configured_stream": "ai",
        "routed_stream": "ai",
        "title": "Previewing a next-generation model",
        "source_original_title": "Previewing a next-generation model",
        "reader_title_ru": "OpenAI News представил материал о развитии ИИ",
    }
    title = reader_text.public_title_ru(item)
    assert title.startswith("OpenAI News представил материал о развитии ИИ:")
    assert "Previewing a next-generation model" in title
    assert "next-generation модель" not in title

    item["title"] = "MOVE token turmoil"
    item["source_original_title"] = "MOVE token turmoil"
    title = reader_text.public_title_ru(item)
    assert "MOVE token turmoil" in title
    assert "MOVE токены turmoil" not in title


def main() -> int:
    test_security_blog_is_not_treated_as_sec_regulator_signal()
    test_sec_regulator_token_still_maps_to_regulatory_topic()
    test_source_topic_fallback_stays_reader_facing_and_russian()
    test_unresolved_security_source_topic_gets_clean_public_title()
    test_english_title_keeps_original_words_instead_of_mixing_languages()
    print("reader title quality tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
