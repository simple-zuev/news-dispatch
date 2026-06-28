#!/usr/bin/env python3
"""Apply source-health status to the source lifecycle registry.

Default mode is dry-run. Use --apply to write the proposed lifecycle file.
This tool does not edit sources/feeds.json.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from core import ROOT, VALIDATION_DIR, repo_path, write_json
from validate_source_lifecycle import LIFECYCLE_PATH, validate_lifecycle

HEALTH_PATH = VALIDATION_DIR / "source-health-latest.json"
REPORT_PATH = VALIDATION_DIR / "source-health-lifecycle-latest.json"
TERMINAL_STATES = {"suspended", "rejected"}
WATCH_STATES = {"active", "probation", "degraded"}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def today() -> str:
    return date.today().isoformat()


def policy_thresholds(lifecycle: dict[str, Any]) -> tuple[int, int]:
    policy = lifecycle.get("policy", {}) if isinstance(lifecycle.get("policy"), dict) else {}
    degrade_at = max(1, int_value(policy.get("degrade_failure_count"), 3))
    suspend_at = max(degrade_at, int_value(policy.get("suspend_failure_count"), 5))
    return degrade_at, suspend_at


def health_by_id(health: dict[str, Any]) -> dict[str, dict[str, Any]]:
    feeds = health.get("feeds", [])
    if not isinstance(feeds, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in feeds:
        if not isinstance(row, dict):
            continue
        feed_id = str(row.get("id") or "")
        if feed_id:
            rows[feed_id] = row
    return rows


def update_row(row: dict[str, Any], health_row: dict[str, Any], degrade_at: int, suspend_at: int) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = copy.deepcopy(row)
    source_id = str(updated.get("source_id") or "")
    current_state = str(updated.get("state") or "")
    status = str(health_row.get("status") or "unknown")
    previous_failure_count = int_value(updated.get("failure_count"), 0)
    previous_success_count = int_value(updated.get("success_count"), 0)
    action = "preserved"
    reason = "state preserved"

    updated["last_seen"] = today()
    updated["last_health_status"] = status
    updated["last_policy_decision"] = today()

    if current_state in TERMINAL_STATES:
        reason = "terminal lifecycle state preserved"
    elif current_state not in WATCH_STATES:
        reason = "state is not monitored by health lifecycle updater"
    elif status == "ok":
        updated["failure_count"] = 0
        updated["success_count"] = previous_success_count + 1
        action = "health_ok"
        reason = "source health is ok"
    else:
        failure_count = previous_failure_count + 1
        updated["failure_count"] = failure_count
        if failure_count >= suspend_at:
            updated["state"] = "suspended"
            updated["state_reason"] = f"health status {status}; failure_count reached {failure_count}"
            action = "set_suspended"
            reason = updated["state_reason"]
        elif failure_count >= degrade_at:
            updated["state"] = "degraded"
            updated["state_reason"] = f"health status {status}; failure_count reached {failure_count}"
            action = "set_degraded"
            reason = updated["state_reason"]
        else:
            updated["state_reason"] = updated.get("state_reason") or f"health status {status}"
            action = "failure_count_incremented"
            reason = f"health status {status}; failure_count is {failure_count}"

    decision = {
        "source_id": source_id,
        "previous_state": current_state,
        "proposed_state": updated.get("state"),
        "status": status,
        "action": action,
        "reason": reason,
        "failure_count": updated.get("failure_count", 0),
        "success_count": updated.get("success_count", 0),
    }
    return updated, decision


def apply_health(health: dict[str, Any], lifecycle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    proposed = copy.deepcopy(lifecycle)
    sources = proposed.get("sources", [])
    if not isinstance(sources, list):
        proposed["sources"] = []
        sources = proposed["sources"]

    degrade_at, suspend_at = policy_thresholds(proposed)
    health_rows = health_by_id(health)
    decisions: list[dict[str, Any]] = []
    matched = 0

    for index, row in enumerate(sources):
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "")
        health_row = health_rows.get(source_id)
        if not health_row:
            decisions.append({
                "source_id": source_id,
                "action": "not_matched",
                "reason": "no source-health row matched source_id",
            })
            continue
        updated, decision = update_row(row, health_row, degrade_at, suspend_at)
        sources[index] = updated
        decisions.append(decision)
        matched += 1

    errors = validate_lifecycle(proposed)
    report = {
        "date": today(),
        "report_type": "source_health_lifecycle",
        "source": repo_path(HEALTH_PATH),
        "lifecycle": repo_path(LIFECYCLE_PATH),
        "dry_run_default": True,
        "degrade_failure_count": degrade_at,
        "suspend_failure_count": suspend_at,
        "matched_count": matched,
        "decision_count": len(decisions),
        "decisions": decisions,
        "validation_errors": errors,
        "summary": {
            "set_degraded": sum(1 for item in decisions if item.get("action") == "set_degraded"),
            "set_suspended": sum(1 for item in decisions if item.get("action") == "set_suspended"),
            "health_ok": sum(1 for item in decisions if item.get("action") == "health_ok"),
            "not_matched": sum(1 for item in decisions if item.get("action") == "not_matched"),
        },
    }
    return proposed, report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health", default=str(HEALTH_PATH))
    parser.add_argument("--lifecycle", default=str(LIFECYCLE_PATH))
    parser.add_argument("--output", default=str(LIFECYCLE_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--apply", action="store_true", help="Write proposed lifecycle output. Default is dry-run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    health = load_json(Path(args.health), {"feeds": []})
    lifecycle = load_json(Path(args.lifecycle), {"version": 1, "states": [], "policy": {}, "sources": []})
    proposed, report = apply_health(health, lifecycle)

    if report["validation_errors"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    write_json(Path(args.report), report)
    if args.apply:
        write_json(Path(args.output), proposed)
        print(f"wrote {repo_path(Path(args.output))} and {repo_path(Path(args.report))}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
