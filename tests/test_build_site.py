#!/usr/bin/env python3
"""Regression tests for the canonical static site build orchestrator."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_site.py"
RENDER_PATH = ROOT / "tools" / "render_site.py"

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
    assert {item["selection_reason"] for item in fixture["items"]} == {
        "selected_top_ranked",
        "filtered_by_source_rules",
    }


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
    assert "today.html" in html
    assert "news/index.html" in html
    assert "digests/index.html" in html
    assert "radar/index.html" in html
    assert "sources/index.html" not in html
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
        assert_public_pages_clean(site_dir)

        (site_dir / "index.html").write_text("2026-07-06 14:09:58 UTC", encoding="utf-8")
        try:
            assert_public_pages_clean(site_dir)
        except AssertionError:
            return
        raise AssertionError("public generated-page scan did not catch raw public metadata")


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


def test_homepage_omits_missing_excerpts_instead_of_generic_filler() -> None:
    html = homepage_html()
    assert "The source published a short English update" not in html
    assert "Короткое сообщение источника" not in html
    assert "Источник описывает тему" not in html


def test_old_home_hero_css_is_removed() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    assert "homepage-hero" not in css
    assert "featured-card" not in css
    assert "font-size: clamp(2.6rem" not in css


def main() -> int:
    test_default_modes_are_deterministic()
    test_pages_modes_are_explicit()
    test_offline_ranking_fixture_contract()
    test_homepage_template_matches_public_reader_blocks()
    test_public_generated_page_scan_checks_reader_pages()
    test_public_stream_labels_are_exact_on_homepage_cards()
    test_homepage_omits_missing_excerpts_instead_of_generic_filler()
    test_old_home_hero_css_is_removed()
    print("build_site regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
