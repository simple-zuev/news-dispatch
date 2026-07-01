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


def test_official_source_class_is_reader_safe() -> None:
    item = base_item("FCA sets stablecoin rules")
    item["source_class"] = "official_source"
    item["configured_stream"] = "crypto-finance"
    item["routed_stream"] = "crypto-finance"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "reader_safe"


def test_arxiv_preprint_is_review_only_not_confirmed_analysis() -> None:
    item = base_item("Agent benchmark for LLM systems")
    item["source_class"] = "research_media"
    item["source_type"] = "Препринты / исследовательская лента"
    item["feed_id"] = "arxiv-cs-ai"
    item["configured_stream"] = "ai"
    item["routed_stream"] = "ai"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "review_only"
    assert any("preprint" in reason for reason in decision["reasons"])


def test_product_card_edc_signal_is_review_only() -> None:
    item = base_item('Official Images Of The Nike SB Tennis Classic "Club 58"')
    item["source_class"] = "specialized_media"
    item["configured_stream"] = "gear-style-edc"
    item["routed_stream"] = "gear-style-edc"
    item["include_hits"] = ["nike", "sneaker"]
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "review_only"
    assert any("product-card" in reason for reason in decision["reasons"])


def test_crypto_forecast_headline_is_labeled_not_blocked() -> None:
    item = base_item("Citi slashes 12-month bitcoin, ether targets")
    item["configured_stream"] = "crypto-finance"
    item["routed_stream"] = "crypto-finance"
    item["feed_id"] = "coindesk"
    item["market_signal_type"] = "third_party_forecast"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "reader_safe"
    assert "third_party_market_forecast" in decision["safety_labels"]
    assert decision["market_signal_type"] == "third_party_forecast"


def test_market_statistics_are_not_labeled_as_forecast_only_because_proceeds_rose() -> None:
    item = base_item("SEC Publishes Updated Market Statistics, Highlighting Increase in IPOs and Proceeds Raised")
    item["source_class"] = "official_source"
    item["configured_stream"] = "crypto-finance"
    item["routed_stream"] = "crypto-finance"
    item["feed_id"] = "crypto-finance-sec-press-releases"
    decision = reader_policy.decision_for_item(item)
    assert decision["decision"] == "reader_safe"
    assert "third_party_market_forecast" not in decision["safety_labels"]
    assert decision["market_signal_type"] == "source_reported"


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
    test_official_source_class_is_reader_safe()
    test_arxiv_preprint_is_review_only_not_confirmed_analysis()
    test_product_card_edc_signal_is_review_only()
    test_crypto_forecast_headline_is_labeled_not_blocked()
    test_market_statistics_are_not_labeled_as_forecast_only_because_proceeds_rose()
    test_report_counts_and_reader_allowed_flag()
    print("reader policy tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
