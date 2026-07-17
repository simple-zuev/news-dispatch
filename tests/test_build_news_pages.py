#!/usr/bin/env python3
"""Regression checks for public news feeds and digest index pages."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_news_pages.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_news_pages", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_news_pages = importlib.util.module_from_spec(spec)
sys.modules["build_news_pages"] = build_news_pages
spec.loader.exec_module(build_news_pages)

from public_html_scan import assert_public_html_clean


def ranking_item(
    key: str,
    *,
    stream: str = "crypto-finance",
    title: str = "FCA and the Bank of England publish stablecoin rules",
    source: str = "FCA",
    selected: bool = False,
    status: str = "accepted_by_source_rules",
    relevance: float = 0.82,
    minimum: float = 0.45,
    reader_excerpt: str | None = "Регулятор сообщил о публичном обновлении правил: в фокусе надзор, хранение активов и требования к стейблкоинам.",
) -> dict[str, object]:
    item: dict[str, object] = {
        "item_key": key,
        "feed_id": source.lower(),
        "feed_title": source,
        "configured_stream": stream,
        "routed_stream": stream,
        "source_class": "regulator",
        "source_type": "official",
        "language": "en",
        "title": title,
        "url": f"https://example.com/{key}",
        "source_excerpt": "The regulator published a public update describing supervision, custody and stablecoin requirements for market participants.",
        "source_excerpt_language": "en",
        "source_original_title": title,
        "source_original_url": f"https://example.com/{key}",
        "reader_source_line_ru": f"{source} · Криптофинансы · 12:00 · регулятор",
        "published": "2026-07-02T09:00:00+00:00",
        "relevance_score": relevance,
        "min_relevance_score": minimum,
        "source_rule_status": status,
        "selected": selected,
        "selection_score": 12.0,
        "final_score": 12.0,
    }
    if reader_excerpt is not None:
        item["reader_excerpt_ru"] = reader_excerpt
    return item


def sample_report() -> dict[str, object]:
    return {
        "date": "2026-07-02",
        "items": [
            ranking_item("overview-item", selected=True, title="EU regulator updates crypto market supervision"),
            ranking_item("feed-only-item", selected=False, title="Taiwan regulator publishes crypto custody rules"),
            ranking_item(
                "rejected-item",
                stream="finance",
                title="Sports celebrity buys watch",
                status="rejected_by_exclude_keywords",
                relevance=0.0,
            ),
        ],
    }


def sample_policy() -> dict[str, object]:
    return {
        "decisions": [
            {"item_key": "overview-item", "decision": "reader_safe"},
            {"item_key": "feed-only-item", "decision": "reader_safe"},
            {"item_key": "rejected-item", "decision": "reader_safe"},
        ]
    }


def hashed_policy_for_report(report: dict[str, object]) -> dict[str, object]:
    return {
        "decisions": [
            {"item_key": build_news_pages.policy_item_key(item), "decision": "reader_safe"}
            for item in report["items"]
            if isinstance(item, dict)
        ]
    }


def assert_public_clean(html: str) -> None:
    assert_public_html_clean(html)


def test_public_time_formatter_uses_reader_dates() -> None:
    today = datetime.now(build_news_pages.PUBLIC_TZ).date()
    assert build_news_pages.format_public_time_ru(f"{today.isoformat()}T10:10:12+03:00") == "Сегодня, 10:10"
    assert build_news_pages.format_public_time_ru("2026-06-28T00:00:00+00:00") == "28 июня, 03:00"
    assert build_news_pages.format_public_time_ru("2026-06-28") == "28 июня"
    assert build_news_pages.format_public_time_ru("2026-07-06") == "6 июля"


def test_public_news_meta_is_reader_facing() -> None:
    item = ranking_item("meta-item", source="Financial Conduct Authority")
    meta = build_news_pages.public_news_meta(item)
    assert meta == "Financial Conduct Authority · Криптофинансы · 2 июля, 12:00 · регулятор"
    assert_public_clean(meta)


def test_feed_items_include_non_selected_safe_items() -> None:
    grouped = build_news_pages.feed_items(sample_report(), sample_policy())
    titles = [row["title"] for row in grouped["crypto-finance"]]
    assert "EU regulator updates crypto market supervision" in titles
    assert "Taiwan regulator publishes crypto custody rules" in titles
    assert grouped["finance"] == []


def test_feed_items_accept_reader_policy_hash_keys() -> None:
    report = sample_report()
    grouped = build_news_pages.feed_items(report, hashed_policy_for_report(report))
    titles = [row["title"] for row in grouped["crypto-finance"]]
    assert "Taiwan regulator publishes crypto custody rules" in titles


def test_news_stream_page_is_reader_first_and_public_clean() -> None:
    grouped = build_news_pages.feed_items(sample_report(), sample_policy())
    html = build_news_pages.news_stream_page("crypto-finance", grouped["crypto-finance"])
    assert "Криптофинансы" in html
    assert "reader_excerpt_ru" not in html
    assert "Регулятор сообщил о публичном обновлении правил" in html
    assert "Оригинал" in html
    assert "Открыть источник" in html
    assert '../sources/index.html' in html
    assert "radar/index.html" not in html
    assert "news-stream-marker" in html
    assert "news-item--text" in html
    assert "stream-visual" not in html
    assert "FCA · Криптофинансы · 2 июля, 12:00 · регулятор" in html
    assert "2026-07-02 09:00:00 UTC" not in html
    assert "Тезис" not in html
    assert "Почему важно" in html
    assert "Что отслеживать" not in html
    assert_public_clean(html)


def test_news_stream_omits_non_useful_fallback_excerpt() -> None:
    rows = [
        ranking_item(
            "no-useful-excerpt",
            title="FCA publishes crypto custody update",
            reader_excerpt=None,
        )
    ]
    html = build_news_pages.news_stream_page("crypto-finance", rows)
    assert "news-excerpt" in html
    assert "По сообщению FCA, опубликовано изменение правил" in html
    assert "The regulator published a public update" not in html
    assert "Источник описывает тему" not in html
    assert "Подробности и формулировки сохранены" not in html
    assert "Короткое сообщение источника" not in html


def test_news_stream_uses_source_excerpt_after_generated_fallback() -> None:
    rows = [
        ranking_item(
            "generated-fallback-with-source-excerpt",
            title="FCA publishes crypto custody update",
            reader_excerpt=(
                "Источник описывает тему «FCA publishes crypto custody update». "
                "Подробности и формулировки сохранены в оригинале источника."
            ),
        )
    ]
    html = build_news_pages.news_stream_page("crypto-finance", rows)
    assert "По сообщению FCA, опубликовано изменение правил" in html
    assert "The regulator published a public update" not in html
    assert "Источник описывает тему" not in html
    assert "Подробности и формулировки сохранены" not in html


def test_feed_deduplicates_identical_reader_story_titles() -> None:
    first = ranking_item("same-story-one", title="Apple announces new AI tools", source="Apple")
    second = ranking_item("same-story-two", title="Apple announces new AI tools", source="Apple")
    grouped = build_news_pages.feed_items(
        {"date": "2026-07-02", "items": [first, second]},
        {"decisions": [{"item_key": "same-story-one", "decision": "reader_safe"}, {"item_key": "same-story-two", "decision": "reader_safe"}]},
    )
    assert len(grouped["crypto-finance"]) == 1


def test_feed_deduplicates_cross_source_story_wording() -> None:
    first = ranking_item(
        "gazprom-rbc",
        stream="finance",
        title="Акции Газпрома обновили исторический минимум",
        source="РБК",
    )
    second = ranking_item(
        "gazprom-kommersant",
        stream="finance",
        title="Акции «Газпрома» обновили исторический минимум",
        source="Коммерсантъ",
    )
    grouped = build_news_pages.feed_items(
        {"date": "2026-07-02", "items": [first, second]},
        {
            "decisions": [
                {"item_key": "gazprom-rbc", "decision": "reader_safe"},
                {"item_key": "gazprom-kommersant", "decision": "reader_safe"},
            ]
        },
    )
    assert len(grouped["finance"]) == 1


def test_feed_keeps_distinct_events_with_similar_templates() -> None:
    first = ranking_item(
        "borisovo",
        stream="moscow-city",
        title="Эскалатор на станции метро Борисово закроют на ремонт 16 июля",
        source="Агентство Москва",
    )
    second = ranking_item(
        "frunzenskaya",
        stream="moscow-city",
        title="Эскалатор на станции метро Фрунзенская закроют на ремонт 16 июля",
        source="Москва 24",
    )
    grouped = build_news_pages.feed_items(
        {"date": "2026-07-02", "items": [first, second]},
        {
            "decisions": [
                {"item_key": "borisovo", "decision": "reader_safe"},
                {"item_key": "frunzenskaya", "decision": "reader_safe"},
            ]
        },
    )
    assert len(grouped["moscow-city"]) == 2


def test_generic_fallback_title_is_not_repeated_on_stream_page() -> None:
    rows = [
        ranking_item("one", title="FCA and the Bank of England set out approach to joint regulation of systemic stablecoin issuers"),
        ranking_item("two", title="ESMA publishes MiCA supervisory briefing", source="ESMA"),
        ranking_item("three", title="Taiwan legislature passes crypto and stablecoin regulations", source="Taiwan News"),
    ]
    html = build_news_pages.news_stream_page("crypto-finance", rows)
    assert "Источник сообщает: Криптофинансы — регуляторика и надзор" not in html
    assert "FCA и Банк Англии описали подход к системным стейблкоинам" in html
    assert "Европейские правила MiCA" in html


def test_public_original_title_sanitizes_security_terms() -> None:
    report = {
        "date": "2026-07-02",
        "items": [
            ranking_item(
                "security-item",
                stream="tech-hardware-software",
                title="Protecting Cookies with Device Bound Session Credentials",
                source="Google Security Blog",
            )
        ]
    }
    grouped = build_news_pages.feed_items(report, sample_policy() | {"decisions": [{"item_key": "security-item", "decision": "reader_safe"}]})
    html = build_news_pages.news_stream_page("tech-hardware-software", grouped["tech-hardware-software"])
    assert "Credentials" not in html
    assert "Session" not in html
    assert "учётные данные" in html


def test_news_feed_excludes_items_older_than_seven_days() -> None:
    current = ranking_item("current")
    old = ranking_item("old")
    old["published"] = "2026-06-20T09:00:00+00:00"
    grouped = build_news_pages.feed_items(
        {"date": "2026-07-02", "items": [current, old]},
        {"decisions": [{"item_key": "current", "decision": "reader_safe"}, {"item_key": "old", "decision": "reader_safe"}]},
    )
    assert [item["item_key"] for item in grouped["crypto-finance"]] == ["current"]


def test_news_empty_state_is_simple_russian_copy() -> None:
    html = build_news_pages.news_stream_page("moscow-city", [])
    assert "Сегодня новых материалов по теме нет." in html
    assert "Активные источники" not in html
    assert "source lifecycle" not in html
    assert_public_clean(html)


def test_news_and_digest_pages_are_written_to_configured_output() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        old_news_dir = build_news_pages.NEWS_DIR
        old_digests_dir = build_news_pages.DIGESTS_DIR
        old_ranking_path = build_news_pages.RANKING_PATH
        old_policy_path = build_news_pages.POLICY_PATH
        try:
            build_news_pages.NEWS_DIR = tmpdir / "news"
            build_news_pages.DIGESTS_DIR = tmpdir / "digests"
            build_news_pages.RANKING_PATH = tmpdir / "daily-radar-ranking-latest.json"
            build_news_pages.POLICY_PATH = tmpdir / "reader-policy-latest.json"
            build_news_pages.RANKING_PATH.write_text(json.dumps(sample_report(), ensure_ascii=False), encoding="utf-8")
            build_news_pages.POLICY_PATH.write_text(json.dumps(sample_policy(), ensure_ascii=False), encoding="utf-8")

            build_news_pages.build()

            assert (build_news_pages.NEWS_DIR / "index.html").exists()
            for stream in build_news_pages.STREAM_ORDER:
                assert (build_news_pages.NEWS_DIR / f"{stream}.html").exists()
            assert (build_news_pages.DIGESTS_DIR / "index.html").exists()
            index_html = (build_news_pages.NEWS_DIR / "index.html").read_text(encoding="utf-8")
            stream_html = (build_news_pages.NEWS_DIR / "crypto-finance.html").read_text(encoding="utf-8")
            digest_html = (build_news_pages.DIGESTS_DIR / "index.html").read_text(encoding="utf-8")
            assert "Новости" in index_html
            assert "Темы новостей" in index_html
            assert "Рубрики анализа" not in index_html
            assert "news-index-row" in index_html
            assert "stream-visual" not in index_html
            assert "Последние материалы" in index_html
            assert "news-item--text" in stream_html
            assert "Открыть источник" in stream_html
            assert "stream-visual" not in stream_html
            assert "Дайджесты" in digest_html
            assert "digest-list-card" in digest_html
            assert "Открыть выпуск" in digest_html
            assert "stream-visual" not in digest_html
            assert "stream-visual--tile" not in digest_html
            assert "PUBLIC-SAFE EDITORIAL BRIEFING SYSTEM" not in digest_html
            assert "Publication boundary" not in digest_html
            assert "Большие дайджесты" not in digest_html
            assert_public_clean(index_html)
            assert_public_clean(stream_html)
            assert_public_clean(digest_html)
        finally:
            build_news_pages.NEWS_DIR = old_news_dir
            build_news_pages.DIGESTS_DIR = old_digests_dir
            build_news_pages.RANKING_PATH = old_ranking_path
            build_news_pages.POLICY_PATH = old_policy_path


def main() -> int:
    test_public_time_formatter_uses_reader_dates()
    test_public_news_meta_is_reader_facing()
    test_feed_items_include_non_selected_safe_items()
    test_feed_items_accept_reader_policy_hash_keys()
    test_news_stream_page_is_reader_first_and_public_clean()
    test_news_stream_omits_non_useful_fallback_excerpt()
    test_news_stream_uses_source_excerpt_after_generated_fallback()
    test_feed_deduplicates_identical_reader_story_titles()
    test_feed_deduplicates_cross_source_story_wording()
    test_feed_keeps_distinct_events_with_similar_templates()
    test_generic_fallback_title_is_not_repeated_on_stream_page()
    test_public_original_title_sanitizes_security_terms()
    test_news_feed_excludes_items_older_than_seven_days()
    test_news_empty_state_is_simple_russian_copy()
    test_news_and_digest_pages_are_written_to_configured_output()
    print("news feed page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
