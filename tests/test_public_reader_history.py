#!/usr/bin/env python3
"""Regression checks for bounded public reader history."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_public_reader_history import (  # noqa: E402
    HISTORY_SCHEMA_VERSION,
    SELECTION_MODE,
    build_history,
    policy_key,
)


def item(key: str, published: str, *, title: str | None = None) -> dict[str, object]:
    return {
        "item_key": key,
        "feed_id": "source",
        "feed_title": "Source",
        "routed_stream": "science-discovery",
        "source_class": "official",
        "source_type": "official",
        "title": title or key,
        "source_original_title": title or key,
        "source_excerpt": "Public source excerpt.",
        "url": f"https://example.com/{key}",
        "published": published,
        "source_rule_status": "accepted_by_source_rules",
        "selected": True,
        "final_score": 9.5,
        "selection_reason": "internal-only",
    }


def test_history_merges_current_and_previous_with_fourteen_day_limit() -> None:
    current = item("current", "2026-07-17T09:00:00+00:00")
    recent = item("recent", "2026-07-05T09:00:00+00:00")
    old = item("old", "2026-07-02T08:00:00+00:00")
    report = build_history(
        {"date": "2026-07-17", "items": [current]},
        {"decisions": [{"item_key": policy_key(current), "decision": "reader_safe"}]},
        {
            "schema_version": HISTORY_SCHEMA_VERSION,
            "selection_mode": SELECTION_MODE,
            "date": "2026-07-16",
            "observation_dates": ["2026-07-05", "2026-07-16"],
            "items": [recent, old],
        },
    )
    assert [row["title"] for row in report["items"]] == ["current", "recent"]
    assert report["retention_days"] == 14
    assert report["observation_dates"] == ["2026-07-05", "2026-07-16", "2026-07-17"]


def test_history_keeps_only_reader_safe_current_rows() -> None:
    safe = item("safe", "2026-07-17T09:00:00+00:00")
    blocked = item("blocked", "2026-07-17T08:00:00+00:00")
    report = build_history(
        {"date": "2026-07-17", "items": [safe, blocked]},
        {"decisions": [{"item_key": policy_key(safe), "decision": "reader_safe"}]},
        {},
    )
    assert [row["title"] for row in report["items"]] == ["safe"]


def test_history_fails_closed_when_policy_has_no_safe_decisions() -> None:
    row = item("unreviewed", "2026-07-17T09:00:00+00:00")
    report = build_history({"date": "2026-07-17", "items": [row]}, {"decisions": []}, {})
    assert report["items"] == []


def test_history_keeps_only_balanced_selected_rows() -> None:
    selected = item("selected", "2026-07-17T09:00:00+00:00")
    unselected = item("unselected", "2026-07-17T08:00:00+00:00")
    unselected["selected"] = False
    report = build_history(
        {"date": "2026-07-17", "items": [selected, unselected]},
        {
            "decisions": [
                {"item_key": policy_key(selected), "decision": "reader_safe"},
                {"item_key": policy_key(unselected), "decision": "reader_safe"},
            ]
        },
        {},
    )
    assert [row["title"] for row in report["items"]] == ["selected"]


def test_history_v2_drops_legacy_unbalanced_cache() -> None:
    selected = item("selected", "2026-07-17T09:00:00+00:00")
    legacy = item("legacy", "2026-07-16T09:00:00+00:00")
    report = build_history(
        {"date": "2026-07-17", "items": [selected]},
        {"decisions": [{"item_key": policy_key(selected), "decision": "reader_safe"}]},
        {"date": "2026-07-16", "items": [legacy]},
    )
    assert [row["title"] for row in report["items"]] == ["selected"]
    assert report["schema_version"] == HISTORY_SCHEMA_VERSION
    assert report["selection_mode"] == SELECTION_MODE
    assert report["current_selected_count"] == 1
    assert report["legacy_cache_reset"] is True
    assert report["observation_dates"] == ["2026-07-17"]


def test_history_drops_ranking_diagnostics() -> None:
    safe = item("safe", "2026-07-17T09:00:00+00:00")
    report = build_history(
        {"date": "2026-07-17", "items": [safe]},
        {"decisions": [{"item_key": policy_key(safe), "decision": "reader_safe"}]},
        {},
    )
    row = report["items"][0]
    assert "item_key" not in row
    assert "final_score" not in row
    assert "relevance_score" not in row
    assert "source_rule_status" not in row
    assert "selection_reason" not in row


def main() -> int:
    test_history_merges_current_and_previous_with_fourteen_day_limit()
    test_history_keeps_only_reader_safe_current_rows()
    test_history_fails_closed_when_policy_has_no_safe_decisions()
    test_history_keeps_only_balanced_selected_rows()
    test_history_v2_drops_legacy_unbalanced_cache()
    test_history_drops_ranking_diagnostics()
    print("public reader history tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
