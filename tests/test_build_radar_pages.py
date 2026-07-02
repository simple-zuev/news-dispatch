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


def test_empty_stream_page_uses_simple_reader_copy() -> None:
    stream = {
        "slug": "moscow-city",
        "title": "Москва",
        "description": "Городская инфраструктура и сервисы.",
    }
    status = build_radar_pages.source_status_by_stream().get("moscow-city", {})
    html = build_radar_pages.stream_page(stream, [], status)

    assert "Сегодня новых материалов по теме нет." in html
    assert "Активные источники:" not in html
    assert "Отключённые источники:" not in html
    assert "техническая пустота покрытия" not in html
    assert "порог релевантности" not in html


def test_signal_card_v2_shows_reader_context_and_boundaries() -> None:
    html = build_radar_pages.signal_card(
        {
            "title": "Central bank updates digital asset rules",
            "date": "2026-06-30",
            "source": "Example Regulator: Central bank updates digital asset rules",
            "source_type": "Официальный источник",
            "source_class": "official_source",
            "status": "draft",
            "stream": "crypto-finance",
            "summary": "Example Regulator опубликовал материал в публичной RSS/Atom-ленте.",
            "raw_title_only": "yes",
            "confirmation_level": "Подтверждён факт публикации первичным или официальным источником; последствия и интерпретации требуют проверки.",
            "reader_context": "Контекст для читателя: сигнал относится к теме «Криптофинансы».",
            "next_check": "Проверить первичный документ.",
            "url": "https://example.com/signal",
        }
    )

    assert "Сигнал · не опубликовано · не материал" in html
    assert "<h3><a href=\"https://example.com/signal\">Источник сообщает: Криптофинансы</a></h3>" in html
    assert "Оригинал:" in html
    assert "Central bank updates digital asset rules" in html
    assert "Example Regulator · официальный источник · Официальный источник" in html
    assert "Криптофинансы" in html
    assert "Подтверждение" in html
    assert "Почему важно" in html
    assert "Что проверить" in html
    assert "Сигнал не является опубликованным материалом" in html


def test_public_stream_labels_are_exact() -> None:
    expected = {
        "finance": "Финансы",
        "crypto-finance": "Криптофинансы",
        "ai": "ИИ",
        "tech-hardware-software": "Железо и софт",
        "gear-style-edc": "EDC / стиль / вещи",
        "moscow-city": "Москва",
        "dj-audio-creative": "DJ / аудио / креатив",
        "science-discovery": "Наука",
        "general": "Спецвыпуски",
    }
    for slug, title in expected.items():
        assert build_radar_pages.stream_title(slug) == title


def main() -> int:
    test_source_status_detects_active_moscow_source()
    test_empty_stream_page_uses_simple_reader_copy()
    test_signal_card_v2_shows_reader_context_and_boundaries()
    test_public_stream_labels_are_exact()
    print("radar page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
