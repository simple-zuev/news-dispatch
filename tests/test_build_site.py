#!/usr/bin/env python3
"""Regression tests for the canonical static site build orchestrator."""

from __future__ import annotations

import importlib.util
import sys
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


def test_homepage_template_is_today_first_and_public_clean() -> None:
    html = render_site.homepage_template([], {})
    lower = html.lower()
    assert "<h1>Главное за сегодня</h1>" in html
    assert "today.html" in html
    assert "drafts.html" not in html
    assert "Статус обновления" not in html
    for term in ["selected", "reader_safe", "source_rule_status", "validation", "draft-only", "review-only", "generated", "prompt", "json", "score=", "final_score", "selection_score", "fetch warnings", "gate"]:
        assert term not in lower


def test_public_stream_labels_are_exact_on_homepage_cards() -> None:
    html = render_site.homepage_template([], {})
    for title in [
        "Финансы",
        "Криптофинансы",
        "ИИ",
        "Железо и софт",
        "EDC / стиль / вещи",
        "Москва",
        "DJ / аудио / креатив",
        "Наука",
    ]:
        assert title in html


def main() -> int:
    test_default_modes_are_deterministic()
    test_pages_modes_are_explicit()
    test_offline_ranking_fixture_contract()
    test_homepage_template_is_today_first_and_public_clean()
    test_public_stream_labels_are_exact_on_homepage_cards()
    print("build_site regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
