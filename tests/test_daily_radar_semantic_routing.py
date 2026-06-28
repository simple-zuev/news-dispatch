#!/usr/bin/env python3
"""Regression tests for conservative Daily Radar semantic routing."""

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


def feed(stream: str):
    return daily_radar.Feed(
        id="test-feed",
        title="Test Feed",
        url="https://example.com/feed.xml",
        stream=stream,
        source_type="Тестовый источник",
        source_class="public_media",
        priority=0.5,
        tags=(),
    )


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


def main() -> int:
    test_ai_story_from_broad_tech_feed_routes_to_ai()
    test_hardware_story_stays_in_tech()
    test_crypto_story_from_finance_feed_routes_to_crypto_finance()
    test_finance_story_without_crypto_terms_stays_finance()
    print("daily_radar semantic routing tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
