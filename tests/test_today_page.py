#!/usr/bin/env python3
"""Regression checks for the Today Radar page builder."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_today_page.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_today_page", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_today_page = importlib.util.module_from_spec(spec)
sys.modules["build_today_page"] = build_today_page
spec.loader.exec_module(build_today_page)


def sample_report() -> dict:
    return {
        "date": "2026-06-28",
        "fetch_errors": [],
        "items": [
            {
                "selected": True,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "regulator",
                "source_type": "official",
                "configured_stream": "crypto-finance",
                "routed_stream": "crypto-finance",
                "feed_title": "Example Regulator",
                "title": "Central bank updates digital asset rules",
                "url": "https://example.com/item",
                "final_score": 1.25,
                "relevance_score": 0.82,
                "include_hits": ["central bank", "digital asset"],
                "translation_required": True,
            },
            {
                "selected": False,
                "source_rule_status": "rejected_by_exclude_keywords",
                "configured_stream": "finance",
                "title": "Sports item",
                "final_score": 0.0,
                "relevance_score": 0.0,
            },
        ],
    }


def test_render_includes_required_links_and_boundary() -> None:
    html = build_today_page.render(sample_report())
    assert "daily-radar-ranking-latest.json" in html
    assert "radar/index.html" in html
    assert "dispatches.html" in html
    assert "Граница интерпретации" in html
    assert "не инвестиционная" in html


def test_render_includes_analytical_card_structure() -> None:
    html = build_today_page.render(sample_report())
    assert "Central bank updates digital asset rules" in html
    assert "Example Regulator" in html
    assert "score 1.25" in html
    assert "relevance 0.82" in html
    assert "Тезис:" in html
    assert "Аргумент:" in html
    assert "Следствие/риск:" in html
    assert "Уровень подтверждения:" in html
    assert "Что отслеживать дальше:" in html
    assert "Неопределённость:" in html


def test_card_stays_non_directive() -> None:
    html = build_today_page.render(sample_report())
    assert "не прогнозом и не инструкцией к действию" in html
    assert "не рекомендация" in html
    assert "Требуется сверка первоисточника" in html


def main() -> int:
    test_render_includes_required_links_and_boundary()
    test_render_includes_analytical_card_structure()
    test_card_stays_non_directive()
    print("today page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
