#!/usr/bin/env python3
"""Regression checks for Today Radar reader policy enforcement."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TODAY_PATH = TOOLS / "build_today_page.py"
POLICY_PATH = TOOLS / "build_reader_policy.py"

sys.path.insert(0, str(TOOLS))
policy_spec = importlib.util.spec_from_file_location("build_reader_policy", POLICY_PATH)
assert policy_spec is not None and policy_spec.loader is not None
reader_policy = importlib.util.module_from_spec(policy_spec)
sys.modules["build_reader_policy"] = reader_policy
policy_spec.loader.exec_module(reader_policy)

today_spec = importlib.util.spec_from_file_location("build_today_page", TODAY_PATH)
assert today_spec is not None and today_spec.loader is not None
build_today_page = importlib.util.module_from_spec(today_spec)
sys.modules["build_today_page"] = build_today_page
today_spec.loader.exec_module(build_today_page)


def item(title: str, source_class: str = "public_media") -> dict[str, object]:
    return {
        "selected": True,
        "source_rule_status": "accepted_by_source_rules",
        "source_class": source_class,
        "source_type": "media",
        "configured_stream": "finance",
        "routed_stream": "finance",
        "feed_id": "fixture-source",
        "feed_title": "Fixture Source",
        "title": title,
        "url": "https://example.com/" + title.lower().replace(" ", "-"),
        "final_score": 0.9,
        "relevance_score": 0.8,
        "include_hits": ["central bank", "liquidity"],
    }


def fixture_report() -> dict[str, object]:
    return {
        "date": "2026-06-29",
        "fetch_errors": [],
        "items": [
            item("Safe central bank liquidity signal"),
            item("Analyst says buy this asset"),
            item("Rumor about infrastructure change"),
        ],
    }


def test_today_radar_renders_only_reader_safe_items() -> None:
    report = fixture_report()
    policy = reader_policy.build_policy_report(report)
    html = build_today_page.render(report, policy)
    assert "Safe central bank liquidity signal" in html
    assert "Analyst says buy this asset" not in html
    assert "Rumor about infrastructure change" not in html
    assert "Reader policy gate" in html
    assert "Today Radar рендерит только reader_safe items" in html


def test_today_radar_empty_state_when_no_reader_safe_items() -> None:
    report = {
        "date": "2026-06-29",
        "fetch_errors": [],
        "items": [item("Analyst says sell this asset")],
    }
    policy = reader_policy.build_policy_report(report)
    html = build_today_page.render(report, policy)
    assert "Нет сигналов для публичного отображения" in html
    assert "Analyst says sell this asset" not in html


def main() -> int:
    test_today_radar_renders_only_reader_safe_items()
    test_today_radar_empty_state_when_no_reader_safe_items()
    print("today reader policy tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
