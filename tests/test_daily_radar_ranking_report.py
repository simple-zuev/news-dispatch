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


def test_arxiv_selection_score_is_downweighted() -> None:
    evidence = ranking_report.source_rule_evidence(
        feed(id="arxiv-cs-ai", stream="ai", source_class="research_media"),
        "LLM agent benchmark improves evaluation",
        "A preprint describes agent evaluation.",
    )
    score, adjustments = ranking_report.selection_score(
        feed(id="arxiv-cs-ai", stream="ai", source_class="research_media"),
        "LLM agent benchmark improves evaluation",
        evidence,
        10.0,
    )
    assert score < 10.0
    assert "research_preprint_downweighted" in adjustments


def test_product_card_selection_score_is_downweighted() -> None:
    edc_feed = feed(
        id="sneaker-news",
        stream="gear-style-edc",
        source_class="specialized_media",
        include_keywords=("nike", "sneaker"),
        exclude_keywords=(),
        boost_keywords=(),
        min_relevance_score=0.3,
    )
    evidence = ranking_report.source_rule_evidence(
        edc_feed,
        'Official Images Of The Nike SB Tennis Classic "Club 58"',
        "",
    )
    score, adjustments = ranking_report.selection_score(
        edc_feed,
        'Official Images Of The Nike SB Tennis Classic "Club 58"',
        evidence,
        10.0,
    )
    assert score < 5.0
    assert "product_card_downweighted" in adjustments


def test_source_caps_limit_overfed_sources() -> None:
    rows = [{"feed_id": "openai-news", "selection_score": 1.0, "title": str(index)} for index in range(25)]
    rows.extend({"feed_id": "fca-news", "selection_score": 1.0, "title": str(index)} for index in range(3))
    kept, diagnostics = ranking_report.apply_source_caps(rows, max_rows=50)
    assert sum(1 for row in kept if row["feed_id"] == "openai-news") == ranking_report.SOURCE_ROW_CAPS["openai-news"]
    assert diagnostics["capped_rows"]["openai-news"] == 5


def test_pure_crypto_price_target_is_labeled_and_downweighted() -> None:
    crypto_feed = feed(
        id="coindesk",
        stream="crypto-finance",
        source_class="specialized_media",
        include_keywords=("bitcoin", "ether"),
        exclude_keywords=(),
        boost_keywords=(),
        min_relevance_score=0.35,
    )
    title = "Citi slashes 12-month bitcoin, ether targets"
    evidence = ranking_report.source_rule_evidence(crypto_feed, title, "")
    score, adjustments = ranking_report.selection_score(crypto_feed, title, evidence, 10.0)
    assert score < 10.0
    assert "third_party_market_forecast_labeled" in adjustments
    assert "market_forecast_downweighted" in adjustments


def test_crypto_regulatory_forecast_context_stays_high_priority() -> None:
    crypto_feed = feed(
        id="fca-news",
        stream="crypto-finance",
        source_class="official_source",
        include_keywords=("stablecoin", "rules"),
        exclude_keywords=(),
        boost_keywords=("stablecoin",),
        min_relevance_score=0.35,
    )
    title = "FCA raises stablecoin market outlook as systemic rules take effect"
    evidence = ranking_report.source_rule_evidence(crypto_feed, title, "")
    score, adjustments = ranking_report.selection_score(crypto_feed, title, evidence, 10.0)
    assert score > 10.0
    assert "third_party_market_forecast_labeled" in adjustments
    assert "market_forecast_downweighted" not in adjustments
    assert "crypto_regulatory_signal_boost" in adjustments


def main() -> int:
    test_source_rule_evidence_explains_acceptance()
    test_source_rule_evidence_explains_rejection()
    test_arxiv_selection_score_is_downweighted()
    test_product_card_selection_score_is_downweighted()
    test_source_caps_limit_overfed_sources()
    test_pure_crypto_price_target_is_labeled_and_downweighted()
    test_crypto_regulatory_forecast_context_stays_high_priority()
    print("daily radar ranking report tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
