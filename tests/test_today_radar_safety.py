#!/usr/bin/env python3
"""Safety regression checks for Today Radar analytical cards."""

from __future__ import annotations

import importlib.util
import re
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

FORBIDDEN_PATTERNS = [
    r"\b(buy|sell|hold)\b",
    r"\b(long|short)\b",
    r"\bprice target\b",
    r"\bwill rise\b",
    r"\bwill fall\b",
    r"покупать",
    r"продавать",
    r"держать позицию",
    r"целевая цена",
    r"точный прогноз",
    r"гарантированно",
]


def fixture_report() -> dict:
    return {
        "date": "2026-06-28",
        "fetch_errors": [],
        "items": [
            {
                "selected": True,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "public_media",
                "source_type": "media",
                "configured_stream": "finance",
                "routed_stream": "finance",
                "feed_title": "Fixture Source",
                "title": "Markets react to central bank liquidity signal",
                "url": "https://example.com/signal",
                "published": "2026-06-28T09:00:00+00:00",
                "reader_excerpt_ru": "Перед выводами нужно открыть первичный материал и проверить контекст сообщения источника.",
                "final_score": 1.10,
                "relevance_score": 0.76,
                "include_hits": ["central bank", "liquidity"],
                "translation_required": False,
            }
        ],
    }


def rendered() -> str:
    return build_today_page.render(fixture_report()).lower()


def test_today_radar_avoids_direct_trading_language() -> None:
    html = rendered()
    for pattern in FORBIDDEN_PATTERNS:
        assert re.search(pattern, html, re.IGNORECASE) is None, pattern


def test_today_radar_keeps_source_signal_boundary() -> None:
    html = rendered()
    assert "главное за сегодня" in html
    assert "ежедневное ручное решение не требуется" not in html
    assert "не инвестиционная" in html
    assert "сообщения источников не являются готовым выводом" in html
    assert "прогнозы и оценки участников рынка подписаны как оценки" in html


def test_today_radar_uses_monitoring_not_commands() -> None:
    html = rendered()
    assert "открыть первичный материал" in html
    assert "проверить контекст" in html
    assert "открыть источник" in html


def main() -> int:
    test_today_radar_avoids_direct_trading_language()
    test_today_radar_keeps_source_signal_boundary()
    test_today_radar_uses_monitoring_not_commands()
    print("today radar safety tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
