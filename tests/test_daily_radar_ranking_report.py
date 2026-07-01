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


def ranking_row(index: int, *, stream: str, feed_id: str, score: float = 12.0, relevance: float = 0.8) -> dict:
    return {
        "item_key": f"{feed_id}-{index}",
        "feed_id": feed_id,
        "configured_stream": stream,
        "routed_stream": stream,
        "source_rule_status": "accepted_by_source_rules",
        "selection_score": score,
        "final_score": score,
        "relevance_score": relevance,
        "selected": False,
        "selection_reason": "not_selected_after_current_ranking",
        "title": f"{stream} item {index}",
    }


def test_current_selection_does_not_collapse_to_stale_reviewed_keys() -> None:
    rows: list[dict] = []
    fixture = [
        ("ai", ["openai-news", "google-ai-blog", "anthropic-news"], 70, 16.0),
        ("tech-hardware-software", ["google-security-blog", "github-security-blog", "apple-newsroom-tech"], 50, 15.0),
        ("crypto-finance", ["fca-news", "coindesk", "the-block"], 35, 14.0),
        ("finance", ["sec-market-statistics", "cbr-news", "kommersant-finance"], 25, 13.0),
        ("science-discovery", ["nasa-science", "phys-org", "science-daily"], 20, 12.0),
    ]
    for stream, sources, count, base_score in fixture:
        rows.extend(
            ranking_row(
                index,
                stream=stream,
                feed_id=sources[index % len(sources)],
                score=base_score - index * 0.01,
            )
            for index in range(count)
        )

    diagnostics = ranking_report.apply_current_selection(rows, limit=18)
    selected = [row for row in rows if row["selected"]]

    assert diagnostics["selected_count"] == 18
    assert len(selected) == 18
    assert len({row["routed_stream"] for row in selected}) >= 4
    assert sum(1 for row in selected if row["feed_id"] == "openai-news") <= 2
    assert sum(1 for row in selected if row["feed_id"] == "google-security-blog") <= 2
    assert any(row["routed_stream"] == "crypto-finance" for row in selected)


def test_weak_stream_selection_requires_relevance_threshold() -> None:
    rows = [
        ranking_row(1, stream="moscow-city", feed_id="m24-moscow-news", relevance=0.49),
        ranking_row(2, stream="dj-audio-creative", feed_id="dj-techtools", relevance=0.72),
        ranking_row(3, stream="crypto-finance", feed_id="fca-news", relevance=0.72),
    ]

    ranking_report.apply_current_selection(rows, limit=6)

    selected_streams = {row["routed_stream"] for row in rows if row["selected"]}
    assert "moscow-city" not in selected_streams
    assert "dj-audio-creative" in selected_streams
    assert "crypto-finance" in selected_streams


def test_crypto_regulatory_items_beat_forecasts_and_roundups_when_stream_is_capped() -> None:
    rows = [
        ranking_row(1, stream="crypto-finance", feed_id="coindesk", score=16.2),
        ranking_row(2, stream="crypto-finance", feed_id="coindesk", score=15.96),
        ranking_row(3, stream="crypto-finance", feed_id="cointelegraph", score=15.8),
        ranking_row(4, stream="crypto-finance", feed_id="esma-news", score=15.59),
        ranking_row(5, stream="crypto-finance", feed_id="fca-news", score=15.49),
        ranking_row(6, stream="crypto-finance", feed_id="crypto-finance-sec-press-releases", score=15.4),
        ranking_row(7, stream="crypto-finance", feed_id="cointelegraph", score=15.26),
        ranking_row(8, stream="crypto-finance", feed_id="cointelegraph", score=15.17),
    ]
    rows[0]["title"] = "Europe is rewriting its landmark crypto rulebook MiCA as hard deadline passes"
    rows[1]["title"] = "Citi slashes 12-month bitcoin, ether targets as ETF flows dry up"
    rows[1]["market_signal_type"] = "third_party_forecast"
    rows[2]["title"] = "Here’s what happened in crypto today"
    rows[3]["title"] = "ESAs publish first report on DORA major ICT-related incidents"
    rows[4]["title"] = "FCA and the Bank of England set out approach to joint regulation of systemic stablecoin issuers"
    rows[4]["source_class"] = "official_source"
    rows[5]["title"] = "SEC Publishes Updated Market Statistics, Highlighting Increase in IPOs and Proceeds Raised"
    rows[5]["source_class"] = "official_source"
    rows[6]["title"] = "French banking giant Crédit Agricole launches EURXT euro stablecoin"
    rows[7]["title"] = "Taiwan’s legislature passes crypto, stablecoin regulations"

    ranking_report.apply_current_selection(rows, limit=4)

    selected_titles = [str(row["title"]) for row in rows if row["selected"]]
    assert any("MiCA" in title for title in selected_titles)
    assert any("FCA and the Bank of England" in title for title in selected_titles)
    assert any("SEC Publishes Updated Market Statistics" in title for title in selected_titles)
    assert not any("Citi slashes" in title for title in selected_titles)
    assert not any("Here’s what happened" in title for title in selected_titles)


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
    test_current_selection_does_not_collapse_to_stale_reviewed_keys()
    test_weak_stream_selection_requires_relevance_threshold()
    test_crypto_regulatory_items_beat_forecasts_and_roundups_when_stream_is_capped()
    test_pure_crypto_price_target_is_labeled_and_downweighted()
    test_crypto_regulatory_forecast_context_stays_high_priority()
    print("daily radar ranking report tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
