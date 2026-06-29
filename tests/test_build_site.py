#!/usr/bin/env python3
"""Regression tests for the canonical static site build orchestrator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_site.py"

spec = importlib.util.spec_from_file_location("build_site", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)


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


def main() -> int:
    test_default_modes_are_deterministic()
    test_pages_modes_are_explicit()
    test_offline_ranking_fixture_contract()
    print("build_site regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
