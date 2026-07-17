#!/usr/bin/env python3
"""Regression tests for the live public-reader freshness gate."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_public_reader_freshness.py"

sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("validate_public_reader_freshness", MODULE_PATH)
assert spec is not None and spec.loader is not None
freshness = importlib.util.module_from_spec(spec)
sys.modules["validate_public_reader_freshness"] = freshness
spec.loader.exec_module(freshness)


def item(index: int, published: datetime, *, stream: str | None = None, source: str | None = None) -> dict:
    return {
        "feed_id": source or f"source-{index}",
        "feed_title": source or f"Source {index}",
        "source_class": "official_source",
        "source_type": "official",
        "configured_stream": stream or f"stream-{index % 4}",
        "routed_stream": stream or f"stream-{index % 4}",
        "source_rule_status": "accepted_by_source_rules",
        "title": f"Reader item {index}",
        "source_excerpt": f"Substantive public excerpt for reader item {index}.",
        "url": f"https://example.test/{index}",
        "published": published.isoformat(),
        "final_score": 12,
        "relevance_score": 0.8,
    }


def policy_for(items: list[dict]) -> dict:
    return {
        "decisions": [
            {"item_key": freshness.item_key(row), "decision": "reader_safe"}
            for row in items
        ]
    }


def run(items: list[dict], reference: datetime) -> dict:
    return freshness.validate(
        {"items": items, "fetch_errors": []},
        policy_for(items),
        reference=reference,
        max_age_hours=36,
        max_newest_age_hours=12,
        min_items=8,
        min_streams=4,
        min_sources=5,
        max_source_share=0.35,
    )


def test_healthy_reader_inventory_passes() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    items = [item(index, reference - timedelta(hours=index + 1)) for index in range(8)]
    report = run(items, reference)
    assert report["passed"] is True
    assert report["observed"]["fresh_items"] == 8
    assert report["observed"]["fresh_streams"] == 4
    assert report["observed"]["fresh_sources"] == 8


def test_stale_inventory_fails() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    items = [item(index, reference - timedelta(hours=40 + index)) for index in range(8)]
    report = run(items, reference)
    assert report["passed"] is False
    assert "newest reader item is missing" in report["issues"]


def test_single_source_inventory_fails_diversity_gate() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    items = [
        item(index, reference - timedelta(hours=index + 1), source="single-source")
        for index in range(8)
    ]
    report = run(items, reference)
    assert report["passed"] is False
    assert "fresh reader sources below minimum: 1 < 5" in report["issues"]


def test_review_only_items_do_not_count() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    items = [item(index, reference - timedelta(hours=index + 1)) for index in range(8)]
    policy = policy_for(items)
    policy["decisions"][0]["decision"] = "review_only"
    report = freshness.validate(
        {"items": items},
        policy,
        reference=reference,
        max_age_hours=36,
        max_newest_age_hours=12,
        min_items=8,
        min_streams=4,
        min_sources=5,
        max_source_share=0.35,
    )
    assert report["passed"] is False
    assert "fresh reader items below minimum: 7 < 8" in report["issues"]


def test_missing_reader_policy_fails_closed() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    items = [item(index, reference - timedelta(hours=index + 1)) for index in range(8)]
    report = freshness.validate(
        {"items": items},
        {"decisions": []},
        reference=reference,
        max_age_hours=36,
        max_newest_age_hours=12,
        min_items=8,
        min_streams=4,
        min_sources=5,
        max_source_share=0.35,
    )
    assert report["passed"] is False
    assert "fresh reader items below minimum: 0 < 8" in report["issues"]


def test_dominant_source_share_fails() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    sources = ["dominant"] * 4 + ["source-4", "source-5", "source-6", "source-7"]
    items = [
        item(index, reference - timedelta(hours=index + 1), source=source)
        for index, source in enumerate(sources)
    ]
    report = run(items, reference)
    assert report["passed"] is False
    assert "dominant source share is too high" in str(report["issues"])


def main() -> int:
    test_healthy_reader_inventory_passes()
    test_stale_inventory_fails()
    test_single_source_inventory_fails_diversity_gate()
    test_review_only_items_do_not_count()
    test_missing_reader_policy_fails_closed()
    test_dominant_source_share_fails()
    print("public reader freshness tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
