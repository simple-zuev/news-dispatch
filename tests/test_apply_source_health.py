#!/usr/bin/env python3
"""Regression checks for source-health lifecycle updates."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "apply_source_health.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("apply_source_health", MODULE_PATH)
assert spec is not None and spec.loader is not None
health_tool = importlib.util.module_from_spec(spec)
sys.modules["apply_source_health"] = health_tool
spec.loader.exec_module(health_tool)


def base_lifecycle() -> dict[str, object]:
    return {
        "version": 1,
        "states": ["discovered", "probation", "active", "degraded", "suspended", "rejected"],
        "policy": {
            "promotion_min_success_count": 3,
            "promotion_max_failure_count": 1,
            "degrade_failure_count": 2,
            "suspend_failure_count": 4,
            "max_new_probation_sources_per_run": 3,
            "probation_ingestion_limit_per_source": 1,
            "required_policy_gates": ["feed_parseable"],
        },
        "sources": [],
    }


def source_row(source_id: str, state: str = "active", failure_count: int = 0) -> dict[str, object]:
    return {
        "source_id": source_id,
        "feed_url": f"https://example.com/{source_id}.xml",
        "stream": "ai",
        "state": state,
        "state_reason": "test source",
        "first_seen": "2026-06-29",
        "last_seen": "2026-06-29",
        "last_policy_decision": "2026-06-29",
        "last_density_score": 0.5,
        "promotion_attempts": 0,
        "failure_count": failure_count,
        "success_count": 0,
    }


def health_row(source_id: str, status: str) -> dict[str, object]:
    return {
        "id": source_id,
        "title": source_id,
        "stream": "ai",
        "enabled": True,
        "status": status,
    }


def test_ok_status_resets_failure_count() -> None:
    lifecycle = base_lifecycle()
    lifecycle["sources"] = [source_row("source-ok", state="active", failure_count=2)]
    proposed, report = health_tool.apply_health({"feeds": [health_row("source-ok", "ok")]}, lifecycle)
    assert report["validation_errors"] == []
    row = proposed["sources"][0]
    assert row["state"] == "active"
    assert row["failure_count"] == 0
    assert row["success_count"] == 1
    assert report["summary"]["health_ok"] == 1


def test_error_status_sets_degraded_at_threshold() -> None:
    lifecycle = base_lifecycle()
    lifecycle["sources"] = [source_row("source-watch", state="active", failure_count=1)]
    proposed, report = health_tool.apply_health({"feeds": [health_row("source-watch", "error")]}, lifecycle)
    assert report["validation_errors"] == []
    row = proposed["sources"][0]
    assert row["state"] == "degraded"
    assert row["failure_count"] == 2
    assert report["summary"]["set_degraded"] == 1


def test_error_status_sets_suspended_at_threshold() -> None:
    lifecycle = base_lifecycle()
    lifecycle["sources"] = [source_row("source-stop", state="degraded", failure_count=3)]
    proposed, report = health_tool.apply_health({"feeds": [health_row("source-stop", "error")]}, lifecycle)
    assert report["validation_errors"] == []
    row = proposed["sources"][0]
    assert row["state"] == "suspended"
    assert row["failure_count"] == 4
    assert report["summary"]["set_suspended"] == 1


def test_terminal_state_is_preserved() -> None:
    lifecycle = base_lifecycle()
    lifecycle["sources"] = [source_row("source-final", state="rejected", failure_count=9)]
    proposed, report = health_tool.apply_health({"feeds": [health_row("source-final", "ok")]}, lifecycle)
    assert report["validation_errors"] == []
    row = proposed["sources"][0]
    assert row["state"] == "rejected"
    assert row["failure_count"] == 9
    assert report["decisions"][0]["action"] == "preserved"


def test_unmatched_source_is_reported_without_state_change() -> None:
    lifecycle = base_lifecycle()
    lifecycle["sources"] = [source_row("source-missing", state="active", failure_count=0)]
    proposed, report = health_tool.apply_health({"feeds": []}, lifecycle)
    assert report["validation_errors"] == []
    assert proposed["sources"][0]["state"] == "active"
    assert report["summary"]["not_matched"] == 1


def main() -> int:
    test_ok_status_resets_failure_count()
    test_error_status_sets_degraded_at_threshold()
    test_error_status_sets_suspended_at_threshold()
    test_terminal_state_is_preserved()
    test_unmatched_source_is_reported_without_state_change()
    print("source health lifecycle tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
