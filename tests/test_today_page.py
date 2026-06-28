#!/usr/bin/env python3
"""Regression checks for the Today Radar entry page."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODAY = ROOT / "site" / "today.html"


def test_today_page_has_required_links() -> None:
    text = TODAY.read_text(encoding="utf-8")
    assert "daily-radar-ranking-latest.json" in text
    assert "radar/index.html" in text
    assert "dispatches.html" in text


def test_today_page_marks_interpretation_boundary() -> None:
    text = TODAY.read_text(encoding="utf-8")
    assert "Граница интерпретации" in text
    assert "не инвестиционная" in text
    assert "не заменяет аналитический выпуск" in text


def main() -> int:
    test_today_page_has_required_links()
    test_today_page_marks_interpretation_boundary()
    print("today page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
