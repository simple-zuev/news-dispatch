#!/usr/bin/env python3
"""Regression checks for shared public story clustering."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from reader_text import public_items_same_story, public_story_similarity  # noqa: E402


def item(title: str, source: str, stream: str = "moscow-city", url: str = "") -> dict[str, object]:
    return {
        "title": title,
        "source_original_title": title,
        "feed_id": source,
        "routed_stream": stream,
        "url": url or f"https://example.com/{source}/{abs(hash(title))}",
    }


def test_cross_source_duplicates_are_clustered() -> None:
    assert public_items_same_story(
        item("Акции Газпрома обновили исторический минимум", "rbc", "finance"),
        item("Акции «Газпрома» обновили исторический минимум", "kommersant", "finance"),
    )
    assert public_items_same_story(
        item("Palit officially announces RTX 3060 Infinity 2 OC", "tomshardware", "tech-hardware-software"),
        item("Palit представила GeForce RTX 3060 Infinity 2 OC", "3dnews", "tech-hardware-software"),
    )
    assert public_items_same_story(
        item("Собянин: завершена проходка тоннеля от Новомосковской до Сосенок", "agency"),
        item("Собянин: завершена проходка тоннеля между Новомосковской и Сосенками", "m24"),
    )


def test_related_but_distinct_city_events_stay_separate() -> None:
    borisovo = item("Эскалатор на станции метро Борисово закроют на ремонт 16 июля", "agency")
    frunzenskaya = item("Эскалатор на станции метро Фрунзенская закроют на ремонт 16 июля", "m24")
    assert public_story_similarity(borisovo, frunzenskaya) == 0.0
    assert not public_items_same_story(borisovo, frunzenskaya)


def test_same_publisher_related_updates_are_not_merged() -> None:
    first = item("OpenAI advances independent research on AI alignment", "openai", "ai")
    second = item("OpenAI advances science and math with GPT 5.2", "openai", "ai")
    assert not public_items_same_story(first, second)


def test_identical_specific_reader_titles_are_one_story() -> None:
    first = item("First source wording", "publisher", "tech-hardware-software")
    second = item("Second source wording", "publisher", "tech-hardware-software")
    first["reader_title_ru"] = "AMD Ryzen 7 7700X3D доступен только в Newegg за $329"
    second["reader_title_ru"] = "AMD Ryzen 7 7700X3D доступен только в Newegg за $329"
    assert public_items_same_story(first, second)


def test_identical_reader_titles_in_different_streams_stay_separate() -> None:
    first = item("First wording", "publisher-one", "finance")
    second = item("Second wording", "publisher-two", "ai")
    first["reader_title_ru"] = "Компания представила новую платформу"
    second["reader_title_ru"] = "Компания представила новую платформу"
    assert not public_items_same_story(first, second)


def test_identical_url_is_always_one_story() -> None:
    url = "https://example.com/story"
    assert public_items_same_story(item("First wording", "one", url=url), item("Second wording", "two", url=url))


def main() -> int:
    test_cross_source_duplicates_are_clustered()
    test_related_but_distinct_city_events_stay_separate()
    test_same_publisher_related_updates_are_not_merged()
    test_identical_specific_reader_titles_are_one_story()
    test_identical_reader_titles_in_different_streams_stay_separate()
    test_identical_url_is_always_one_story()
    print("public story clustering tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
