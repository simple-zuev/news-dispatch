#!/usr/bin/env python3
"""Regression tests for the seven-day public reader quality report."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_public_reader_quality_report.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_public_reader_quality_report", MODULE_PATH)
assert spec is not None and spec.loader is not None
quality = importlib.util.module_from_spec(spec)
sys.modules["build_public_reader_quality_report"] = quality
spec.loader.exec_module(quality)


def row(index: int, published: datetime, *, stream: str, source: str, title: str | None = None) -> dict:
    return {
        "feed_id": source,
        "feed_title": source,
        "configured_stream": stream,
        "routed_stream": stream,
        "source_class": "research_media",
        "source_type": "research",
        "title": title or f"Научная новость {index}",
        "reader_title_ru": title or f"Научная новость {index}",
        "reader_excerpt_ru": f"Источник опубликовал содержательное описание результата номер {index}.",
        "url": f"https://example.test/{index}",
        "published": published.isoformat(),
    }


def feeds(per_stream: int = 8) -> dict:
    return {
        "feeds": [
            {"id": f"{stream}-{index}", "stream": stream, "enabled": True}
            for stream in ("science-discovery", "gear-style-edc")
            for index in range(per_stream)
        ]
    }


def test_short_history_is_collecting() -> None:
    reference = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    history = {"items": [row(1, reference - timedelta(hours=2), stream="science-discovery", source="science-a")]}
    report = quality.build_report(history, feeds(), reference=reference)
    assert report["status"] == "collecting"
    assert report["observed"]["items"] == 1


def test_old_item_dates_do_not_mature_a_new_observation_window() -> None:
    reference = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    rows = [
        row(index, reference - timedelta(days=index), stream="science-discovery", source=f"science-{index}")
        for index in range(7)
    ]
    report = quality.build_report(
        {"observation_dates": ["2026-07-17"], "items": rows},
        feeds(),
        reference=reference,
    )
    assert report["status"] == "collecting"
    assert report["observed"]["calendar_days_with_items"] == 7
    assert report["observed"]["successful_observation_days"] == 1
    assert report["observed"]["observation_span_days"] == 1
    assert report["low_output_streams"] == []


def test_full_window_reports_duplicates_and_concentration() -> None:
    reference = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    rows = [
        row(index, reference - timedelta(days=index), stream="science-discovery", source="dominant")
        for index in range(7)
    ]
    rows.append(
        row(20, reference - timedelta(days=1), stream="science-discovery", source="second", title="Научная новость 1")
    )
    report = quality.build_report({"items": rows}, feeds(), reference=reference)
    assert report["status"] == "attention"
    assert report["observed"]["observation_span_days"] == 7
    assert report["observed"]["duplicate_rows"] == 1
    assert {alert["code"] for alert in report["alerts"]} >= {
        "duplicate_share",
        "source_concentration",
        "stream_concentration",
        "missing_streams",
    }


def test_source_inventory_gap_is_visible() -> None:
    reference = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    report = quality.build_report(
        {"items": [row(1, reference, stream="gear-style-edc", source="gear-a")]},
        feeds(per_stream=5),
        reference=reference,
    )
    assert report["coverage_gaps"] == {"gear-style-edc": 3, "science-discovery": 3}
    assert "source_coverage" in {alert["code"] for alert in report["alerts"]}


def test_full_window_reports_low_output_stream() -> None:
    reference = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    rows = [
        row(index, reference - timedelta(days=index), stream="science-discovery", source=f"science-{index}")
        for index in range(7)
    ]
    rows.append(row(20, reference, stream="gear-style-edc", source="gear-a"))
    report = quality.build_report({"items": rows}, feeds(), reference=reference)
    assert report["low_output_streams"] == ["gear-style-edc"]
    assert "low_stream_output" in {alert["code"] for alert in report["alerts"]}


def test_multiple_feeds_from_one_publisher_count_once() -> None:
    config = {
        "feeds": [
            {"id": "agency-news", "publisher_id": "agency", "stream": "moscow-city"},
            {"id": "agency-culture", "publisher_id": "agency", "stream": "moscow-city"},
            {"id": "city-independent", "stream": "moscow-city"},
        ]
    }
    assert quality.configured_sources(config)["moscow-city"] == 2


def main() -> int:
    test_short_history_is_collecting()
    test_old_item_dates_do_not_mature_a_new_observation_window()
    test_full_window_reports_duplicates_and_concentration()
    test_source_inventory_gap_is_visible()
    test_full_window_reports_low_output_stream()
    test_multiple_feeds_from_one_publisher_count_once()
    print("public reader quality report tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
