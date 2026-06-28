#!/usr/bin/env python3
"""Regression checks for applying discovery candidates to lifecycle."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "apply_source_discovery.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("apply_source_discovery", MODULE_PATH)
assert spec is not None and spec.loader is not None
apply_tool = importlib.util.module_from_spec(spec)
sys.modules["apply_source_discovery"] = apply_tool
spec.loader.exec_module(apply_tool)


def lifecycle_base() -> dict[str, object]:
    return {
        "version": 1,
        "purpose": "test lifecycle",
        "states": ["discovered", "probation", "active", "degraded", "suspended", "rejected"],
        "state_model": {
            "discovered": "candidate",
            "probation": "sampling",
            "active": "normal",
            "degraded": "watch",
            "suspended": "paused",
            "rejected": "excluded",
        },
        "policy": {
            "promotion_min_success_count": 3,
            "promotion_max_failure_count": 1,
            "degrade_failure_count": 3,
            "suspend_failure_count": 5,
            "max_new_probation_sources_per_run": 1,
            "probation_ingestion_limit_per_source": 1,
            "required_policy_gates": ["feed_parseable"],
        },
        "sources": [],
    }


def discovery_item(url: str, status: str = "passed_probe", ratio: float = 0.4) -> dict[str, object]:
    return {
        "stream": "ai",
        "source_page_url": "https://example.com",
        "source_page_title": "Example",
        "feed_url": url,
        "candidate_status": status,
        "score": 0.8,
        "sample_match_ratio": ratio,
        "min_sample_ratio": 0.2,
        "deny_term_hits": [],
        "probe": {"ok": True, "item_count": 10, "error": ""},
    }


def test_passed_probe_candidate_enters_probation() -> None:
    proposed, report = apply_tool.apply_discovery(
        {"report_type": "source_discovery", "items": [discovery_item("https://example.com/rss.xml")]},
        lifecycle_base(),
    )
    assert report["validation_errors"] == []
    assert report["summary"]["added_new"] == 1
    row = proposed["sources"][0]
    assert row["state"] == "probation"
    assert row["stream"] == "ai"
    assert row["feed_url"] == "https://example.com/rss.xml"


def test_broad_candidate_is_recorded_as_discovered() -> None:
    item = discovery_item("https://example.com/broad.xml", status="broad_feed_review_required", ratio=0.1)
    proposed, report = apply_tool.apply_discovery(
        {"report_type": "source_discovery", "items": [item]},
        lifecycle_base(),
    )
    assert report["validation_errors"] == []
    row = proposed["sources"][0]
    assert row["state"] == "discovered"
    assert "more evidence" in row["state_reason"]


def test_probation_limit_is_respected() -> None:
    discovery = {
        "report_type": "source_discovery",
        "items": [
            discovery_item("https://example.com/one.xml"),
            discovery_item("https://example.com/two.xml"),
        ],
    }
    proposed, report = apply_tool.apply_discovery(discovery, lifecycle_base())
    states = [row["state"] for row in proposed["sources"]]
    assert states.count("probation") == 1
    assert states.count("discovered") == 1
    assert report["summary"]["remaining_probation_slots"] == 0


def test_active_source_state_is_preserved() -> None:
    lifecycle = lifecycle_base()
    lifecycle["sources"] = [
        {
            "source_id": apply_tool.source_id_for("https://example.com/rss.xml"),
            "feed_url": "https://example.com/rss.xml",
            "stream": "ai",
            "state": "active",
            "state_reason": "already active",
            "first_seen": "2026-06-29",
            "last_seen": "2026-06-29",
            "last_policy_decision": "2026-06-29",
            "last_density_score": 0.5,
            "promotion_attempts": 0,
            "failure_count": 0,
            "success_count": 3,
        }
    ]
    proposed, report = apply_tool.apply_discovery(
        {"report_type": "source_discovery", "items": [discovery_item("https://example.com/rss.xml")]},
        lifecycle,
    )
    assert report["validation_errors"] == []
    assert proposed["sources"][0]["state"] == "active"
    assert proposed["sources"][0]["state_reason"] == "already active"


def main() -> int:
    test_passed_probe_candidate_enters_probation()
    test_broad_candidate_is_recorded_as_discovered()
    test_probation_limit_is_respected()
    test_active_source_state_is_preserved()
    print("apply source discovery tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
