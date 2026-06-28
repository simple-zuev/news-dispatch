#!/usr/bin/env python3
"""Regression checks for radar stream pages."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_radar_pages.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_radar_pages", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_radar_pages = importlib.util.module_from_spec(spec)
sys.modules["build_radar_pages"] = build_radar_pages
spec.loader.exec_module(build_radar_pages)


def test_source_status_detects_disabled_moscow_feeds() -> None:
    status = build_radar_pages.source_status_by_stream()
    moscow = status.get("moscow-city", {})
    assert len(moscow.get("active", [])) == 0
    assert len(moscow.get("disabled", [])) >= 2


def test_empty_stream_page_explains_why_it_is_empty() -> None:
    stream = {
        "slug": "moscow-city",
        "title": "Москва",
        "description": "Городская инфраструктура и сервисы.",
    }
    status = build_radar_pages.source_status_by_stream().get("moscow-city", {})
    html = build_radar_pages.stream_page(stream, [], status)
    assert "Почему рубрика пустая" in html
    assert "Активные источники: 0" in html
    assert "Отключённые источники:" in html
    assert "Все известные источники рубрики сейчас отключены" in html
    assert "Это диагностическое состояние" in html


def main() -> int:
    test_source_status_detects_disabled_moscow_feeds()
    test_empty_stream_page_explains_why_it_is_empty()
    print("radar page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
