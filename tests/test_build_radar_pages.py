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


def test_source_status_detects_active_moscow_source() -> None:
    status = build_radar_pages.source_status_by_stream()
    moscow = status.get("moscow-city", {})
    active = moscow.get("active", [])
    disabled = moscow.get("disabled", [])

    assert len(active) >= 1
    assert any(source.get("id") == "m24-moscow-news" for source in active)
    assert len(disabled) >= 2


def test_empty_stream_page_explains_active_source_without_generated_signals() -> None:
    stream = {
        "slug": "moscow-city",
        "title": "Москва",
        "description": "Городская инфраструктура и сервисы.",
    }
    status = build_radar_pages.source_status_by_stream().get("moscow-city", {})
    html = build_radar_pages.stream_page(stream, [], status)

    assert "Почему рубрика пустая" in html
    assert "Активные источники:" in html
    assert "Отключённые источники:" in html
    assert "Активные источники есть, но в последнем Daily Radar run" in html
    assert "Это диагностическое состояние" in html


def main() -> int:
    test_source_status_detects_active_moscow_source()
    test_empty_stream_page_explains_active_source_without_generated_signals()
    print("radar page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
