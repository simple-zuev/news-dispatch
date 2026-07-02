#!/usr/bin/env python3
"""Regression tests for the canonical static site build orchestrator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_site.py"
RENDER_PATH = ROOT / "tools" / "render_site.py"
VISUALS_PATH = ROOT / "tools" / "newsroom_visuals.py"

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

visuals_spec = importlib.util.spec_from_file_location("newsroom_visuals", VISUALS_PATH)
assert visuals_spec is not None and visuals_spec.loader is not None
newsroom_visuals = importlib.util.module_from_spec(visuals_spec)
sys.modules["newsroom_visuals"] = newsroom_visuals
visuals_spec.loader.exec_module(newsroom_visuals)


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


def test_homepage_template_matches_simple_newsroom_blocks() -> None:
    html = render_site.homepage_template([], {})
    lower = html.lower()
    for block in [
        "newsroom-top",
        "feature-card",
        "quick-signals",
        "rubric-tiles",
        "latest-news",
        "digest-preview",
        "source-strip",
    ]:
        assert block in html
    assert "quick-signals" in html
    assert "stream-visual" in html
    assert "stream-visual--mini" not in html
    assert "today.html" in html
    assert "news/index.html" in html
    assert "digests/index.html" in html
    assert "radar/index.html" in html
    assert "drafts.html" not in html
    assert "Статус обновления" not in html
    assert "Как читать" not in html
    assert "Рубрики анализа" not in html
    assert "порог релевантности" not in lower
    assert "featured-card" not in html
    assert "homepage-hero" not in html
    assert "техническая пустота покрытия" not in lower
    assert html.index("latest-news") < html.index("rubric-tiles")
    for term in ["selected", "reader_safe", "source_rule_status", "validation", "draft-only", "review-only", "generated", "prompt", "json", "score=", "final_score", "selection_score", "fetch warnings", "gate"]:
        assert term not in lower


def test_public_stream_labels_are_exact_on_homepage_cards() -> None:
    html = render_site.homepage_template([], {})
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


def test_stream_fallback_visuals_exist_for_all_public_streams() -> None:
    for slug in newsroom_visuals.visual_streams():
        visual = newsroom_visuals.stream_visual(slug)
        assert "Иллюстрация темы" in visual
        assert f"stream-visual--{slug}" in visual


def test_tracked_static_homepage_no_longer_exposes_legacy_service_copy() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    lower = html.lower()
    assert "Ленты" in html
    assert "Дайджесты" in html
    assert "Сегодня" in html
    for term in [
        "public-safe editorial briefing system",
        "editorial model",
        "publication boundary",
        "strict review",
        "work dispatch",
        "open dispatch archive",
        "как читать",
        "validation",
        "selected",
        "reader_safe",
        "source_rule_status",
        "score=",
    ]:
        assert term not in lower


def test_old_home_hero_css_is_removed() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    assert "homepage-hero" not in css
    assert "featured-card" not in css
    assert "font-size: clamp(2.6rem" not in css


def main() -> int:
    test_default_modes_are_deterministic()
    test_pages_modes_are_explicit()
    test_offline_ranking_fixture_contract()
    test_homepage_template_matches_simple_newsroom_blocks()
    test_public_stream_labels_are_exact_on_homepage_cards()
    test_stream_fallback_visuals_exist_for_all_public_streams()
    test_tracked_static_homepage_no_longer_exposes_legacy_service_copy()
    test_old_home_hero_css_is_removed()
    print("build_site regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
