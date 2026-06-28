#!/usr/bin/env python3
"""Regression checks for autonomous source lifecycle registry."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_source_lifecycle.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("validate_source_lifecycle", MODULE_PATH)
assert spec is not None and spec.loader is not None
lifecycle = importlib.util.module_from_spec(spec)
sys.modules["validate_source_lifecycle"] = lifecycle
spec.loader.exec_module(lifecycle)


def base_policy() -> dict[str, object]:
    return {
        "promotion_min_success_count": 3,
        "promotion_max_failure_count": 1,
        "degrade_failure_count": 3,
        "suspend_failure_count": 5,
        "max_new_probation_sources_per_run": 3,
        "probation_ingestion_limit_per_source": 1,
        "required_policy_gates": ["feed_parseable"],
    }


def test_lifecycle_file_validates() -> None:
    data = lifecycle.load_lifecycle(ROOT / "sources" / "source-lifecycle.json")
    assert lifecycle.validate_lifecycle(data) == []


def test_lifecycle_states_cover_autopilot_model() -> None:
    data = lifecycle.load_lifecycle(ROOT / "sources" / "source-lifecycle.json")
    states = set(data["states"])
    assert lifecycle.ALLOWED_STATES <= states
    for state in ["discovered", "probation", "active", "degraded", "suspended", "rejected"]:
        assert state in data["state_model"]


def test_valid_source_row_passes() -> None:
    row = {
        "source_id": "example-ai",
        "feed_url": "https://example.com/rss.xml",
        "stream": "ai",
        "state": "probation",
        "state_reason": "candidate passed discovery scoring",
        "first_seen": "2026-06-29",
        "last_seen": "2026-06-29",
        "last_health_status": "ok",
        "last_density_score": 0.42,
        "last_policy_decision": "2026-06-29",
        "promotion_attempts": 1,
        "failure_count": 0,
        "success_count": 1,
    }
    data = {
        "version": 1,
        "states": sorted(lifecycle.ALLOWED_STATES),
        "policy": base_policy(),
        "sources": [row],
    }
    assert lifecycle.validate_lifecycle(data) == []


def test_invalid_source_row_reports_errors() -> None:
    row = {
        "source_id": "example-ai",
        "feed_url": "",
        "stream": "missing-stream",
        "state": "review",
        "state_reason": "",
        "last_density_score": 1.5,
        "promotion_attempts": -1,
    }
    data = {
        "version": 1,
        "states": sorted(lifecycle.ALLOWED_STATES),
        "policy": base_policy(),
        "sources": [row, dict(row)],
    }
    errors = lifecycle.validate_lifecycle(data)
    joined = "\n".join(errors)
    assert "feed_url" in joined
    assert "unknown stream" in joined
    assert "invalid state" in joined
    assert "state_reason" in joined
    assert "last_density_score" in joined
    assert "promotion_attempts" in joined
    assert "duplicate source_id" in joined


def main() -> int:
    test_lifecycle_file_validates()
    test_lifecycle_states_cover_autopilot_model()
    test_valid_source_row_passes()
    test_invalid_source_row_reports_errors()
    print("source lifecycle tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
