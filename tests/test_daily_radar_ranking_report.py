#!/usr/bin/env python3
"""Regression checks for Daily Radar ranking report helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_daily_radar_ranking_report.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("ranking_report", MODULE_PATH)
assert spec is not None and spec.loader is not None
ranking_report = importlib.util.module_from_spec(spec)
sys.modules["ranking_report"] = ranking_report
spec.loader.exec_module(ranking_report)


def feed(**kwargs):
    defaults = {
        "id": "test-feed",
        "title": "Test Feed",
        "url": "https://example.com/feed.xml",
        "stream": "finance",
        "source_type": "Test Source",
        "source_class": "public_media",
        "priority": 0.5,
        "tags": (),
        "include_keywords": ("bank", "market"),
        "exclude_keywords": ("sports",),
        "boost_keywords": ("central bank",),
        "penalty_keywords": ("entertainment",),
        "min_relevance_score": 0.45,
        "language": "en",
        "translation_required": True,
    }
    defaults.update(kwargs)
    return ranking_report.daily_radar.Feed(**defaults)


def test_source_rule_evidence_explains_acceptance() -> None:
    evidence = ranking_report.source_rule_evidence(
        feed(),
        "Central bank keeps market rate unchanged",
        "Bank liquidity remains important.",
    )
    assert evidence["source_rule_status"] == "accepted_by_source_rules"
    assert "market" in evidence["include_hits"]
    assert "central bank" in evidence["boost_hits"]
    assert evidence["relevance_score"] >= evidence["min_relevance_score"]


def test_source_rule_evidence_explains_rejection() -> None:
    evidence = ranking_report.source_rule_evidence(
        feed(),
        "Sports match report",
        "A coach commented on the football match.",
    )
    assert evidence["source_rule_status"] == "rejected_by_exclude_keywords"
    assert evidence["relevance_score"] == 0.0
    assert "sports" in evidence["exclude_hits"]


def main() -> int:
    test_source_rule_evidence_explains_acceptance()
    test_source_rule_evidence_explains_rejection()
    print("daily radar ranking report tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
