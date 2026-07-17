#!/usr/bin/env python3
"""Regression tests for the canonical static site build orchestrator."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_site.py"
RENDER_PATH = ROOT / "tools" / "render_site.py"
SOURCES_PATH = ROOT / "tools" / "build_sources_page.py"
ENHANCE_PATH = ROOT / "tools" / "enhance_site.py"
READER_SECTIONS_PATH = ROOT / "tools" / "apply_reader_sections.py"

sys.path.insert(0, str(ROOT / "tools"))

spec = importlib.util.spec_from_file_location("build_site", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)

render_spec = importlib.util.spec_from_file_location("render_site", RENDER_PATH)
assert render_spec is not None and render_spec.loader is not None
render_site = importlib.util.module_from_spec(render_spec)
sys.modules["render_site"] = render_site
render_spec.loader.exec_module(render_site)

sources_spec = importlib.util.spec_from_file_location("build_sources_page", SOURCES_PATH)
assert sources_spec is not None and sources_spec.loader is not None
build_sources_page = importlib.util.module_from_spec(sources_spec)
sys.modules["build_sources_page"] = build_sources_page
sources_spec.loader.exec_module(build_sources_page)

enhance_spec = importlib.util.spec_from_file_location("enhance_site", ENHANCE_PATH)
assert enhance_spec is not None and enhance_spec.loader is not None
enhance_site = importlib.util.module_from_spec(enhance_spec)
sys.modules["enhance_site"] = enhance_site
enhance_spec.loader.exec_module(enhance_site)

reader_sections_spec = importlib.util.spec_from_file_location("apply_reader_sections", READER_SECTIONS_PATH)
assert reader_sections_spec is not None and reader_sections_spec.loader is not None
apply_reader_sections = importlib.util.module_from_spec(reader_sections_spec)
reader_sections_spec.loader.exec_module(apply_reader_sections)

from public_html_scan import assert_public_html_clean, assert_public_pages_clean

def test_default_modes_are_deterministic() -> None:
    args = build_site.parse_args([])
    assert args.ranking_mode == "fixture"
    assert args.media_mode == "skip"
    assert args.ranking_timeout == 8
    assert args.ranking_max_rows == 200


def test_pages_modes_are_explicit() -> None:
    args = build_site.parse_args(["--ranking-mode", "live", "--media-mode", "live"])
    assert args.ranking_mode == "live"
    assert args.media_mode == "live"


def test_offline_ranking_fixture_contract() -> None:
    fixture = build_site.OFFLINE_RANKING_FIXTURE
    assert fixture["report_type"] == "daily_radar_ranking"
    assert isinstance(fixture["items"], list)
    assert "The central bank published an update" in str(fixture["items"][0]["source_excerpt"])
    assert {item["selection_reason"] for item in fixture["items"]} == {
        "selected_top_ranked",
        "filtered_by_source_rules",
    }


def test_build_orchestrator_writes_sources_page() -> None:
    calls: list[str] = []
    original_build_ranking = build_site.build_ranking
    original_build_reader_policy = build_site.build_reader_policy
    original_run_tool = build_site.run_tool
    try:
        build_site.build_ranking = lambda args: calls.append("ranking")
        build_site.build_reader_policy = lambda: calls.append("reader-policy")
        build_site.run_tool = lambda script, *args: calls.append(script)
        build_site.build(build_site.parse_args(["--skip-validation", "--skip-privacy-scan"]))
    finally:
        build_site.build_ranking = original_build_ranking
        build_site.build_reader_policy = original_build_reader_policy
        build_site.run_tool = original_run_tool

    assert "build_sources_page.py" in calls
    assert calls.index("build_sources_page.py") > calls.index("build_news_pages.py")
    assert calls.index("build_sources_page.py") < calls.index("build_today_page.py")


def test_sources_page_is_grouped_public_transparency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        old_sources_path = build_sources_page.SOURCES_PATH
        old_ranking_path = build_sources_page.RANKING_PATH
        old_policy_path = build_sources_page.POLICY_PATH
        old_output_dir = build_sources_page.OUTPUT_DIR
        old_output_path = build_sources_page.OUTPUT_PATH
        old_enhance_site_dir = enhance_site.SITE_DIR
        try:
            build_sources_page.SOURCES_PATH = tmpdir / "feeds.json"
            build_sources_page.RANKING_PATH = tmpdir / "daily-radar-ranking-latest.json"
            build_sources_page.POLICY_PATH = tmpdir / "reader-policy-latest.json"
            build_sources_page.OUTPUT_DIR = tmpdir / "site" / "sources"
            build_sources_page.OUTPUT_PATH = build_sources_page.OUTPUT_DIR / "index.html"
            enhance_site.SITE_DIR = tmpdir / "site"
            build_sources_page.SOURCES_PATH.write_text(
                json.dumps(
                    {
                        "feeds": [
                            {
                                "id": "fca-news",
                                "title": "Financial Conduct Authority",
                                "url": "https://example.com/feed",
                                "stream": "crypto-finance",
                                "source_type": "Официальный источник / регулятор",
                                "source_class": "official_source",
                                "reliability_tier": "A",
                                "priority": 0.8,
                                "tags": ["regulation"],
                            },
                            {
                                "id": "disabled-source",
                                "title": "Disabled Source",
                                "url": "https://example.com/disabled",
                                "stream": "finance",
                                "source_type": "Деловое медиа",
                                "source_class": "public_media",
                                "enabled": False,
                                "priority": 0.2,
                                "tags": ["finance"],
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            build_sources_page.RANKING_PATH.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "item_key": "recent-fca",
                                "feed_id": "fca-news",
                                "feed_title": "Financial Conduct Authority",
                                "configured_stream": "crypto-finance",
                                "routed_stream": "crypto-finance",
                                "source_class": "official_source",
                                "source_type": "official",
                                "title": "FCA updates stablecoin custody rules",
                                "reader_title_ru": "FCA обновило правила хранения стейблкоинов",
                                "reader_excerpt_ru": "Регулятор описал требования к хранению и надзору.",
                                "url": "https://example.com/fca",
                                "published": "2026-07-02T09:00:00+00:00",
                                "source_rule_status": "accepted_by_source_rules",
                                "relevance_score": 0.9,
                                "min_relevance_score": 0.2,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            build_sources_page.POLICY_PATH.write_text(
                json.dumps({"decisions": [{"item_key": "recent-fca", "decision": "reader_safe"}]}, ensure_ascii=False),
                encoding="utf-8",
            )

            build_sources_page.build()

            assert build_sources_page.OUTPUT_PATH.exists()
            html = build_sources_page.OUTPUT_PATH.read_text(encoding="utf-8")
            assert "Источники" in html
            assert "Криптофинансы" in html
            assert "Financial Conduct Authority" in html
            assert "Тип: официальный источник / регулятор" in html
            assert "Доверие: первичный" in html
            assert "Роль: первичные заявления, решения и документы." in html
            assert "FCA обновило правила хранения стейблкоинов" in html
            assert "Disabled Source" not in html
            for term in ["source_rule_status", "validation", "threshold", "coverage", "feed_id", "final_score", "selection_score"]:
                assert term not in html.lower()
            assert_public_html_clean(html)

            enhance_site.enhance_html(build_sources_page.OUTPUT_PATH)
            enhanced_html = build_sources_page.OUTPUT_PATH.read_text(encoding="utf-8")
            assert "News Dispatch" in enhanced_html
            assert "Рубрики анализа" not in enhanced_html
            assert 'property="og:site_name" content="News Dispatch"' in enhanced_html
            assert_public_html_clean(enhanced_html)
        finally:
            build_sources_page.SOURCES_PATH = old_sources_path
            build_sources_page.RANKING_PATH = old_ranking_path
            build_sources_page.POLICY_PATH = old_policy_path
            build_sources_page.OUTPUT_DIR = old_output_dir
            build_sources_page.OUTPUT_PATH = old_output_path
            enhance_site.SITE_DIR = old_enhance_site_dir


def has_cyrillic(value: str) -> bool:
    return any("а" <= char.lower() <= "я" or char == "ё" for char in value)


def ranking_item(
    key: str,
    *,
    title: str,
    source: str,
    stream: str = "crypto-finance",
    published: str = "2026-07-02T09:00:00+00:00",
    excerpt: str = "",
    selected: bool = False,
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
        "reader_title_ru": title if has_cyrillic(title) else "",
        "url": f"https://example.com/{key}",
        "published": published,
        "source_rule_status": "accepted_by_source_rules",
        "selected": selected,
        "selection_score": 12.0 if selected else 8.0,
        "final_score": 12.0 if selected else 8.0,
    }
    if excerpt:
        item["reader_excerpt_ru"] = excerpt
    else:
        item["source_excerpt"] = "The source published a short English update without a Russian reader excerpt."
    return item


def homepage_html() -> str:
    items = [
        ranking_item(
            "latest-ai",
            title="OpenAI опубликовала заметку о безопасности агентов",
            source="OpenAI",
            stream="ai",
            published="2026-07-02T11:00:00+00:00",
            excerpt="Компания описала практики безопасности для агентных сценариев.",
            selected=True,
        ),
        ranking_item(
            "latest-finance",
            title="ЦБ обновил обзор по ликвидности банков",
            source="Банк России",
            stream="finance",
            published="2026-07-02T10:00:00+00:00",
        ),
    ]
    dispatches = [
        render_site.Dispatch(
            source_path=ROOT / "dispatches" / "sample.md",
            title="Что меняется в регулировании цифровых активов",
            date="2026-07-02",
            stream="crypto-finance",
            summary="Короткий аналитический тезис.",
            body="",
            output_name="sample.html",
        )
    ]
    original_loader = render_site.load_ranking_items
    render_site.load_ranking_items = lambda limit=None: items[:limit] if limit is not None else items
    try:
        return render_site.homepage_template(dispatches, {})
    finally:
        render_site.load_ranking_items = original_loader


def test_homepage_template_matches_public_reader_blocks() -> None:
    html = homepage_html()
    lower = html.lower()
    for block in ["home-header", "home-latest", "home-today", "home-rubrics", "home-digests", "home-sources"]:
        assert block in html
    assert html.index("home-latest") < html.index("home-today") < html.index("home-rubrics") < html.index("home-digests")
    assert "Последние новости" in html
    assert "OpenAI" in html
    assert "Открыть источник" in html
    assert html.count("OpenAI опубликовала заметку о безопасности агентов") == 1
    assert "обновлени</p>" not in html
    assert "Открыть сегодняшний обзор" in html
    assert "today.html" in html
    assert "news/index.html" in html
    assert "digests/index.html" in html
    assert "sources/index.html" in html
    assert "radar/index.html" not in html
    assert "drafts.html" not in html
    assert "Статус обновления" not in html
    assert "Как читать" not in html
    assert "Рубрики анализа" not in html
    assert "порог релевантности" not in lower
    assert "feature-card" not in html
    assert "quick-signals" not in html
    assert "stream-visual" not in html
    assert "rubric-tile" not in html
    assert "news-preview-card" not in html
    assert "featured-card" not in html
    assert "homepage-hero" not in html
    assert "техническая пустота покрытия" not in lower
    assert "Источник описывает тему" not in html
    assert "Подробности и формулировки сохранены" not in html
    assert "Источник сообщает: Криптофинансы" not in html
    assert "2026-07-02 11:00:00 UTC" not in html
    assert "2 июля, 14:00" in html
    for term in ["selected", "reader_safe", "source_rule_status", "validation", "draft-only", "review-only", "generated", "prompt", "json", "score=", "final_score", "selection_score", "fetch warnings", "gate"]:
        assert term not in lower
    assert_public_html_clean(html)


def test_public_generated_page_scan_checks_reader_pages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        site_dir = Path(tmp)
        news_dir = site_dir / "news"
        news_dir.mkdir(parents=True)
        clean_html = "<html><body><p>Fixture Regulator · Криптофинансы · 28 июня · регулятор</p></body></html>"
        for path in [
            site_dir / "index.html",
            news_dir / "index.html",
            news_dir / "crypto-finance.html",
            site_dir / "today.html",
        ]:
            path.write_text(clean_html, encoding="utf-8")
        sources_dir = site_dir / "sources"
        sources_dir.mkdir(parents=True)
        (sources_dir / "index.html").write_text(clean_html, encoding="utf-8")
        digests_dir = site_dir / "digests"
        digests_dir.mkdir(parents=True)
        (digests_dir / "index.html").write_text(clean_html, encoding="utf-8")
        assert_public_pages_clean(site_dir)

        (site_dir / "index.html").write_text("2026-07-06 14:09:58 UTC", encoding="utf-8")
        try:
            assert_public_pages_clean(site_dir)
        except AssertionError:
            pass
        else:
            raise AssertionError("public generated-page scan did not catch raw homepage metadata")

        (site_dir / "index.html").write_text(clean_html, encoding="utf-8")
        (digests_dir / "index.html").write_text("source_rule_status", encoding="utf-8")
        try:
            assert_public_pages_clean(site_dir)
        except AssertionError:
            return
        raise AssertionError("public generated-page scan did not catch raw digest metadata")


def test_public_stream_labels_are_exact_on_homepage_cards() -> None:
    html = homepage_html()
    for title in [
        "Финансы",
        "Криптофинансы",
        "ИИ",
        "Железо и софт",
        "EDC / стиль",
        "Москва",
        "DJ / аудио",
        "Наука",
    ]:
        assert title in html


def test_homepage_attributes_english_source_detail_in_russian() -> None:
    html = homepage_html()
    assert "Кратко по сообщению" in html
    assert "The source published a short English update" in html
    assert "Короткое сообщение источника" not in html
    assert "Источник описывает тему" not in html


def test_old_home_hero_css_is_removed() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    assert "homepage-hero" not in css
    assert "featured-card" not in css
    assert "font-size: clamp(2.6rem" not in css
    for forbidden in ["linear-gradient", "radial-gradient", ".stream-visual", ".visual-shape", ".visual-grid-line"]:
        assert forbidden not in css
    for selector in [
        ".home-news-row h3 a",
        ".news-item h3 a",
        ".digest-list-card h3 a",
        ".source-row h3",
        ".signal-card h3",
    ]:
        assert selector in css
    assert ".digest-list-card h3 a {\n  color: var(--ink);\n  text-decoration: none;" in css
    assert ".news-item h3 a {\n  color: inherit;\n  text-decoration: none;" in css
    assert "grid-template-columns: repeat(2, max-content);" in css
    assert ".sources-rubrics .home-rubric-list" in css


def test_public_builders_share_sources_navigation_and_skip_reader_css() -> None:
    html = homepage_html()
    assert 'class="top-nav home-nav"' in html
    assert 'href="sources/index.html"' in html
    assert "radar/index.html" not in html
    enhanced = enhance_site.enhance_html
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "news.html"
        page.write_text('<html><head><link rel="stylesheet" href="styles/main.css"></head><body></body></html>', encoding="utf-8")
        original_site_dir = enhance_site.SITE_DIR
        try:
            enhance_site.SITE_DIR = Path(tmp)
            enhanced(page)
        finally:
            enhance_site.SITE_DIR = original_site_dir
        assert "reader.css" not in page.read_text(encoding="utf-8")


def test_enhancement_keeps_the_reader_brand() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "news.html"
        page.write_text('<html><head><title>News Dispatch</title><link rel="stylesheet" href="styles/main.css"></head><body>News Dispatch · an AI crisis stopgap</body></html>', encoding="utf-8")
        original_site_dir = enhance_site.SITE_DIR
        try:
            enhance_site.SITE_DIR = Path(tmp)
            enhance_site.enhance_html(page)
        finally:
            enhance_site.SITE_DIR = original_site_dir
        text = page.read_text(encoding="utf-8")
        assert "News Dispatch" in text
        assert "Дайджест" not in text
        assert "an AI crisis stopgap" in text


def test_mobile_homepage_keeps_reader_news_visible() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    selector = ".home-news-list > .home-news-row:nth-child(n + 3)"
    assert selector not in css
    assert "@media (max-width: 360px)" in css
    assert ".home-header .home-nav" in css
    assert "grid-template-columns: repeat(2, max-content);" in css
    assert "overflow: visible;" in css
    assert "flex-wrap: wrap;" in css
    assert "white-space: nowrap;" in css
    assert "width: min(100% - 32px, 1180px);" in css
    assert "overflow-x: hidden;" not in css


def test_two_week_archive_controls_are_compact_and_mobile_safe() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    for selector in [
        ".news-archive-nav",
        ".news-day-group",
        ".news-related-sources",
        ".today-related-sources",
    ]:
        assert selector in css
    assert "scrollbar-width: none;" in css
    assert "scroll-margin-top: 12px;" in css


def test_reader_sections_accept_main_with_accessibility_id() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "dispatch.html"
        page.write_text(
            '<html><body><main class="article-body" id="main-content">'
            '<h1>Выпуск</h1><h2>Главное</h2><p>Короткий итог.</p></main></body></html>',
            encoding="utf-8",
        )
        assert apply_reader_sections.process_page(page)
        html = page.read_text(encoding="utf-8")
        assert 'id="main-content"' in html
        assert 'class="reader-map"' in html
        assert 'reader-section-main' in html


def main() -> int:
    test_default_modes_are_deterministic()
    test_pages_modes_are_explicit()
    test_offline_ranking_fixture_contract()
    test_build_orchestrator_writes_sources_page()
    test_sources_page_is_grouped_public_transparency()
    test_homepage_template_matches_public_reader_blocks()
    test_public_generated_page_scan_checks_reader_pages()
    test_public_stream_labels_are_exact_on_homepage_cards()
    test_homepage_attributes_english_source_detail_in_russian()
    test_old_home_hero_css_is_removed()
    test_public_builders_share_sources_navigation_and_skip_reader_css()
    test_enhancement_keeps_the_reader_brand()
    test_mobile_homepage_keeps_reader_news_visible()
    test_two_week_archive_controls_are_compact_and_mobile_safe()
    test_reader_sections_accept_main_with_accessibility_id()
    print("build_site regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
