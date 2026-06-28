#!/usr/bin/env python3
"""Regression tests for conservative Daily Radar filtering."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "filter_daily_signals.py"

spec = importlib.util.spec_from_file_location("filter_daily_signals", MODULE_PATH)
assert spec is not None and spec.loader is not None
filter_daily_signals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filter_daily_signals)


def reason(title: str, stream: str) -> str | None:
    return filter_daily_signals.deny_reason_for_signal(title=title, stream=stream)


def test_money_amount_is_not_discount_in_finance_streams() -> None:
    assert reason("Securitize expects to raise $400m ahead of public debut", "crypto-finance") is None
    assert reason("Binance posts over $400m in weekly net outflows as MiCA deadline nears", "crypto-finance") is None
    assert reason("Bank raises €500m in senior bonds", "finance") is None


def test_explicit_deal_language_still_filters() -> None:
    assert reason("Record-low price on a laptop deal for Prime Day", "tech-hardware-software") == "deal_or_discount"
    assert reason("Sneaker sale now just $89 for Prime Day", "gear-style-edc") == "deal_or_discount"


def test_non_price_quality_filters_still_work() -> None:
    assert reason("Full product review of a new gaming laptop", "tech-hardware-software") == "review_or_buying_guide"
    assert reason("Mahershala Ali goes full action hero in teaser trailer for new movie", "gear-style-edc") == "entertainment_not_gear"


def main() -> int:
    test_money_amount_is_not_discount_in_finance_streams()
    test_explicit_deal_language_still_filters()
    test_non_price_quality_filters_still_work()
    print("filter_daily_signals regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
