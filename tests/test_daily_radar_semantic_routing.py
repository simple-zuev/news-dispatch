#!/usr/bin/env python3
"""Regression tests for conservative Daily Radar semantic routing and source rules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "daily_radar.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("daily_radar", MODULE_PATH)
assert spec is not None and spec.loader is not None
daily_radar = importlib.util.module_from_spec(spec)
sys.modules["daily_radar"] = daily_radar
spec.loader.exec_module(daily_radar)


def feed(stream: str, **kwargs):
    defaults = {
        "id": "test-feed",
        "title": "Test Feed",
        "url": "https://example.com/feed.xml",
        "stream": stream,
        "source_type": "Тестовый источник",
        "source_class": "public_media",
        "priority": 0.5,
        "tags": (),
    }
    defaults.update(kwargs)
    return daily_radar.Feed(**defaults)


def route(stream: str, title: str, summary: str = "") -> str:
    return daily_radar.classify(feed(stream), title, summary)


def test_ai_story_from_broad_tech_feed_routes_to_ai() -> None:
    assert route(
        "tech-hardware-software",
        "AI coding agents can be tricked into installing malware via clean GitHub repositories",
        "Mozilla 0din team shows how Claude Code can be exploited by its own helpfulness.",
    ) == "ai"


def test_hardware_story_stays_in_tech() -> None:
    assert route(
        "tech-hardware-software",
        "China's Loongson launches homegrown 16-core server CPU built on LoongArch",
        "New processor and server hardware details were published.",
    ) == "tech-hardware-software"


def test_crypto_story_from_finance_feed_routes_to_crypto_finance() -> None:
    assert route(
        "finance",
        "Bitcoin ETF issuers report new weekly inflows as crypto market structure changes",
        "The story focuses on crypto market infrastructure, bitcoin and exchange traded products.",
    ) == "crypto-finance"


def test_finance_story_without_crypto_terms_stays_finance() -> None:
    assert route(
        "finance",
        "Central bank keeps the key rate unchanged as inflation slows",
        "Banks, deposits and credit markets remain the main context.",
    ) == "finance"


def test_crypto_regulation_story_from_ai_feed_routes_to_crypto_finance() -> None:
    assert route(
        "ai",
        "Dubai set for crypto firm influx as MiCA deadline pushes companies to relocate",
        "Regulatory regimes and market structure are driving digital asset company moves.",
    ) == "crypto-finance"


def test_crypto_enforcement_story_from_ai_feed_routes_to_crypto_finance() -> None:
    assert route(
        "ai",
        "Self-exiled billionaire sentenced to 30 years for fraud involving crypto investors",
        "The court case covers crypto fraud and enforcement against investor abuse.",
    ) == "crypto-finance"


def test_prediction_market_court_order_from_ai_feed_routes_to_crypto_finance() -> None:
    assert route(
        "ai",
        "Kalshi hit with restraining order blocking sports prediction markets in Michigan",
        "The court order concerns prediction market access and regulated contracts.",
    ) == "crypto-finance"


def test_sneaker_story_from_ai_feed_routes_to_gear_style_edc() -> None:
    assert route(
        "ai",
        "Nike extends the laces on this SE Air Max 95",
        "The release focuses on sneakers, footwear design and consumer style.",
    ) == "gear-style-edc"


def test_science_research_story_from_ai_feed_routes_to_science_discovery() -> None:
    assert route(
        "ai",
        "Alzheimer's research identifies new evidence in long-running treatment study",
        "Researchers published scientific findings for peer reviewed follow-up.",
    ) == "science-discovery"


def test_homo_naledi_story_from_ai_feed_routes_to_science_discovery() -> None:
    assert route(
        "ai",
        "Homo naledi research reshapes debate over ancient burial behavior",
        "Scientific findings from researchers are the main context.",
    ) == "science-discovery"


def test_apple_security_story_from_ai_feed_routes_to_tech_hardware_software() -> None:
    assert route(
        "ai",
        "Apple security update fixes iOS vulnerability",
        "The software update affects iPhone and macOS users.",
    ) == "tech-hardware-software"


def test_leaked_hardware_story_from_ai_feed_routes_to_tech_hardware_software() -> None:
    assert route(
        "ai",
        "Leaked hardware images show Apple's next iPhone chassis",
        "The images focus on hardware design and device changes.",
    ) == "tech-hardware-software"


def test_source_rule_exclude_zeroes_relevance() -> None:
    configured = feed(
        "finance",
        include_keywords=("bank", "market"),
        exclude_keywords=("sports", "football"),
        min_relevance_score=0.45,
    )
    assert daily_radar.relevance_score(configured, "Sports league match report", "football coach update") == 0.0


def test_source_rule_include_and_boost_raise_relevance() -> None:
    configured = feed(
        "finance",
        include_keywords=("bank", "market"),
        boost_keywords=("central bank",),
        min_relevance_score=0.45,
    )
    assert daily_radar.relevance_score(configured, "Central bank keeps market rate unchanged", "bank liquidity remains key") >= 0.45


def main() -> int:
    test_ai_story_from_broad_tech_feed_routes_to_ai()
    test_hardware_story_stays_in_tech()
    test_crypto_story_from_finance_feed_routes_to_crypto_finance()
    test_finance_story_without_crypto_terms_stays_finance()
    test_crypto_regulation_story_from_ai_feed_routes_to_crypto_finance()
    test_crypto_enforcement_story_from_ai_feed_routes_to_crypto_finance()
    test_prediction_market_court_order_from_ai_feed_routes_to_crypto_finance()
    test_sneaker_story_from_ai_feed_routes_to_gear_style_edc()
    test_science_research_story_from_ai_feed_routes_to_science_discovery()
    test_homo_naledi_story_from_ai_feed_routes_to_science_discovery()
    test_apple_security_story_from_ai_feed_routes_to_tech_hardware_software()
    test_leaked_hardware_story_from_ai_feed_routes_to_tech_hardware_software()
    test_source_rule_exclude_zeroes_relevance()
    test_source_rule_include_and_boost_raise_relevance()
    print("daily_radar semantic routing tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
