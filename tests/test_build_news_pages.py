#!/usr/bin/env python3
"""Regression checks for public news feeds and digest index pages."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
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


FORBIDDEN_PUBLIC_TERMS = [
    "selected",
    "reader_safe",
    "source_rule_status",
    "validation",
    "draft-only",
    "review-only",
    "generated",
    "prompt",
    "json",
    "score=",
    "final_score",
    "selection_score",
    "fetch warnings",
    "gate",
    "gates",
    "lifecycle",
    "threshold",
    "coverage",
    "техническая пустота покрытия",
]


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
) -> dict[str, object]:
    return {
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
        "reader_excerpt_ru": "Регулятор сообщил о публичном обновлении правил: в фокусе надзор, хранение активов и требования к стейблкоинам.",
        "reader_source_line_ru": f"{source} · Криптофинансы · 12:00 · регулятор",
        "published": "2026-07-02T09:00:00+00:00",
        "relevance_score": relevance,
        "min_relevance_score": minimum,
        "source_rule_status": status,
        "selected": selected,
        "selection_score": 12.0,
        "final_score": 12.0,
    }


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
    lower = html.lower()
    for term in FORBIDDEN_PUBLIC_TERMS:
        assert term not in lower


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
    assert "Лента новостей" in html
    assert "reader_excerpt_ru" not in html
    assert "Регулятор сообщил о публичном обновлении правил" in html
    assert "Оригинал" in html
    assert "Открыть источник" in html
    assert "news-stream-marker" in html
    assert "news-item--text" in html
    assert "stream-visual--thumb" not in html
    assert "2026-07-02 09:00:00 UTC" not in html
    assert "FCA · Криптофинансы · 12:00 · регулятор" in html
    assert "Тезис" not in html
    assert "Почему важно" not in html
    assert_public_clean(html)


def test_generic_fallback_title_is_not_repeated_on_stream_page() -> None:
    rows = [
        ranking_item("one", title="FCA and the Bank of England set out approach to joint regulation of systemic stablecoin issuers"),
        ranking_item("two", title="ESMA publishes MiCA supervisory briefing", source="ESMA"),
        ranking_item("three", title="Taiwan legislature passes crypto and stablecoin regulations", source="Taiwan News"),
    ]
    html = build_news_pages.news_stream_page("crypto-finance", rows)
    assert html.count("Источник сообщает: Криптофинансы — регуляторика и надзор") <= 1
    assert "FCA и Банк Англии описали подход к системным стейблкоинам" in html
    assert "Европейские правила MiCA" in html


def test_public_original_title_sanitizes_security_terms() -> None:
    report = {
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
            assert "Ленты новостей" in index_html
            assert "feed-overview-grid" in index_html
            assert "stream-visual" not in index_html
            assert "Последние материалы" in index_html
            assert_public_clean(index_html)
        finally:
            build_news_pages.NEWS_DIR = old_news_dir
            build_news_pages.DIGESTS_DIR = old_digests_dir
            build_news_pages.RANKING_PATH = old_ranking_path
            build_news_pages.POLICY_PATH = old_policy_path


def main() -> int:
    test_feed_items_include_non_selected_safe_items()
    test_feed_items_accept_reader_policy_hash_keys()
    test_news_stream_page_is_reader_first_and_public_clean()
    test_generic_fallback_title_is_not_repeated_on_stream_page()
    test_public_original_title_sanitizes_security_terms()
    test_news_empty_state_is_simple_russian_copy()
    test_news_and_digest_pages_are_written_to_configured_output()
    print("news feed page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
