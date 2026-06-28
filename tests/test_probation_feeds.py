#!/usr/bin/env python3
"""Regression checks for probation feed view builder."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_probation_feeds.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_probation_feeds", MODULE_PATH)
assert spec is not None and spec.loader is not None
probation = importlib.util.module_from_spec(spec)
sys.modules["build_probation_feeds"] = probation
spec.loader.exec_module(probation)


def lifecycle_with_sources() -> dict[str, object]:
    return {
        "version": 1,
        "policy": {"probation_ingestion_limit_per_source": 1},
        "sources": [
            {
                "source_id": "auto-ai",
                "feed_url": "https://example.com/ai/rss.xml",
                "source_page_title": "Example AI",
                "stream": "ai",
                "state": "probation",
                "state_reason": "candidate passed discovery policy gates",
                "last_density_score": 0.42,
                "last_discovery_score": 0.8,
                "last_health_status": "ok",
            },
            {
                "source_id": "auto-finance",
                "feed_url": "https://example.com/finance/rss.xml",
                "stream": "finance",
                "state": "discovered",
                "state_reason": "candidate needs more evidence before probation",
            },
        ],
    }


def test_probation_rows_only_include_probation_state() -> None:
    rows = probation.probation_rows(lifecycle_with_sources())
    assert len(rows) == 1
    assert rows[0]["source_id"] == "auto-ai"


def test_feed_view_is_disabled_and_marked_probation() -> None:
    row = probation.probation_rows(lifecycle_with_sources())[0]
    feed = probation.feed_view(row, per_source=1)
    assert feed["id"] == "probation-auto-ai"
    assert feed["enabled"] is False
    assert feed["probation"] is True
    assert feed["stream"] == "ai"
    assert feed["url"] == "https://example.com/ai/rss.xml"
    assert feed["source_class"] == "probation_source"
    assert feed["per_source"] == 1


def test_build_report_is_read_only_probation_view() -> None:
    report = probation.build_report(lifecycle_with_sources())
    assert report["report_type"] == "probation_feed_view"
    assert report["ingestion_enabled"] is False
    assert report["probation_count"] == 1
    assert len(report["feeds"]) == 1
    assert "read-only" in report["policy_note"]


def test_empty_lifecycle_builds_empty_report() -> None:
    report = probation.build_report({"version": 1, "policy": {}, "sources": []})
    assert report["probation_count"] == 0
    assert report["feeds"] == []


def main() -> int:
    test_probation_rows_only_include_probation_state()
    test_feed_view_is_disabled_and_marked_probation()
    test_build_report_is_read_only_probation_view()
    test_empty_lifecycle_builds_empty_report()
    print("probation feed tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
