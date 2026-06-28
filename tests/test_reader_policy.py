#!/usr/bin/env python3
"""Regression checks for reader-facing policy gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_reader_policy.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_reader_policy", MODULE_PATH)
assert spec is not None and spec.loader is not None
reader_policy = importlib.util.module_from_spec(spec)
sys.modules["build_reader_policy"] = reader_policy
spec.loader.exec_module(reader_policy)


def base_item(title: str = "Central bank publishes liquidity update") -> dict[str, object]:
    return {
        "selected": True,
        "source_rule_status": "accepted_by_source_rules",
        "source_class": "public_media",
        "configured_stream": "finance",
        "routed_stream": "finance",
        "feed_id": "fixture-source",
        "feed_title": "Fixture Source",
        "title": title,
        "url": "https://example.com/item",
        "final_score": 0.9,
        "relevance_score": 0.8,
        "include_hits": ["central bank", "liquidity"],
    }


def test_safe_item_is_reader_safe() -> None:
    decision = reader_policy.decision_for_item(base_item())
    assert decision["decision"] == "reader_safe"
    assert decision["reasons"] == ["passed reader policy gate"]


def test_direct_trading_language_is_blocked() -> None:
    item = base_item("Analyst says buy this asset after liquidity update")
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "blocked"
    assert decision["block_hits"]


def test_unconfirmed_language_is_review_only() -> None:
    item = base_item("Unconfirmed report about new AI model release")
    item["routed_stream"] = "ai"
    item["configured_stream"] = "ai"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "review_only"
    assert decision["review_hits"]


def test_unknown_source_class_is_review_only() -> None:
    item = base_item()
    item["source_class"] = "unknown"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "review_only"
    assert any("source class" in reason for reason in decision["reasons"])


def test_report_counts_and_reader_allowed_flag() -> None:
    safe = base_item("Central bank publishes liquidity update")
    blocked = base_item("Market note says sell this asset")
    review = base_item("Rumor about infrastructure change")
    report = reader_policy.build_policy_report({"date": "2026-06-29", "items": [safe, blocked, review]})
    assert report["counts"]["reader_safe"] == 1
    assert report["counts"]["blocked"] == 1
    assert report["counts"]["review_only"] == 1
    assert report["reader_output_allowed"] is False


def main() -> int:
    test_safe_item_is_reader_safe()
    test_direct_trading_language_is_blocked()
    test_unconfirmed_language_is_review_only()
    test_unknown_source_class_is_review_only()
    test_report_counts_and_reader_allowed_flag()
    print("reader policy tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
