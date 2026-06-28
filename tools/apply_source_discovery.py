#!/usr/bin/env python3
"""Apply source-discovery candidates to the source lifecycle registry.

Default mode is dry-run. Use --apply to write the proposed lifecycle file.
This tool does not edit sources/feeds.json and does not activate sources.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from core import ROOT, VALIDATION_DIR, repo_path, write_json
from validate_source_lifecycle import LIFECYCLE_PATH, validate_lifecycle

DISCOVERY_PATH = VALIDATION_DIR / "source-discovery-latest.json"
REPORT_PATH = VALIDATION_DIR / "source-lifecycle-apply-latest.json"
PROTECTED_STATES = {"active", "suspended", "rejected"}
ELIGIBLE_STATUSES = {"passed_probe"}
KNOWN_REVIEW_STATUSES = {"broad_feed_review_required", "low_item_count"}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def source_id_for(feed_url: str) -> str:
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:12]
    return f"auto-{digest}"


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def today() -> str:
    return date.today().isoformat()


def existing_by_feed(lifecycle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = lifecycle.get("sources", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("feed_url", "")): row for row in rows if isinstance(row, dict) and row.get("feed_url")}


def has_deny_hits(item: dict[str, Any]) -> bool:
    value = item.get("deny_term_hits", [])
    return isinstance(value, list) and bool(value)


def candidate_state(item: dict[str, Any], probation_slots_left: int) -> tuple[str, str, bool]:
    status = str(item.get("candidate_status") or "")
    score = numeric(item.get("score"), 0.0)
    ratio = numeric(item.get("sample_match_ratio"), 0.0)
    min_ratio = numeric(item.get("min_sample_ratio"), 0.2)

    if status in ELIGIBLE_STATUSES and not has_deny_hits(item) and score >= 0.55 and ratio >= min_ratio:
        if probation_slots_left > 0:
            return "probation", "candidate passed discovery policy gates", True
        return "discovered", "candidate passed gates but probation limit is exhausted", False

    if status in KNOWN_REVIEW_STATUSES:
        return "discovered", "candidate needs more evidence before probation", False

    return "discovered", "candidate recorded for audit only", False


def telemetry_from_item(item: dict[str, Any]) -> dict[str, Any]:
    probe = item.get("probe", {}) if isinstance(item.get("probe"), dict) else {}
    return {
        "last_seen": today(),
        "last_health_status": "ok" if probe.get("ok") else str(probe.get("error") or "unknown"),
        "last_density_score": numeric(item.get("sample_match_ratio"), 0.0),
        "last_policy_decision": today(),
    }


def new_source_row(item: dict[str, Any], state: str, reason: str) -> dict[str, Any]:
    feed_url = str(item.get("feed_url") or "").strip()
    stream = str(item.get("stream") or "").strip()
    row = {
        "source_id": source_id_for(feed_url),
        "feed_url": feed_url,
        "source_page_url": str(item.get("source_page_url") or ""),
        "source_page_title": str(item.get("source_page_title") or ""),
        "stream": stream,
        "state": state,
        "state_reason": reason,
        "first_seen": today(),
        "promotion_attempts": 0,
        "failure_count": 0,
        "success_count": 1 if state == "probation" else 0,
        "last_discovery_status": str(item.get("candidate_status") or ""),
        "last_discovery_score": numeric(item.get("score"), 0.0),
    }
    row.update(telemetry_from_item(item))
    return row


def update_existing_source(row: dict[str, Any], item: dict[str, Any], proposed_state: str, reason: str) -> dict[str, Any]:
    updated = copy.deepcopy(row)
    current_state = str(updated.get("state") or "")
    updated.update(telemetry_from_item(item))
    updated["last_discovery_status"] = str(item.get("candidate_status") or "")
    updated["last_discovery_score"] = numeric(item.get("score"), 0.0)

    if current_state in PROTECTED_STATES:
        updated["state_reason"] = updated.get("state_reason") or "protected lifecycle state preserved"
        return updated

    if current_state == "discovered" and proposed_state == "probation":
        updated["state"] = "probation"
        updated["state_reason"] = reason
        updated["promotion_attempts"] = int_value(updated.get("promotion_attempts"), 0) + 1
        updated["success_count"] = int_value(updated.get("success_count"), 0) + 1
        return updated

    if current_state == "probation" and proposed_state == "probation":
        updated["state_reason"] = reason
        updated["success_count"] = int_value(updated.get("success_count"), 0) + 1
        return updated

    updated["state_reason"] = updated.get("state_reason") or reason
    return updated


def apply_discovery(discovery: dict[str, Any], lifecycle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    proposed = copy.deepcopy(lifecycle)
    proposed.setdefault("sources", [])
    sources = proposed["sources"]
    policy = proposed.get("policy", {}) if isinstance(proposed.get("policy"), dict) else {}
    slots_left = int_value(policy.get("max_new_probation_sources_per_run"), 3)
    by_feed = existing_by_feed(proposed)
    decisions: list[dict[str, Any]] = []

    for item in discovery.get("items", []):
        if not isinstance(item, dict):
            continue
        feed_url = str(item.get("feed_url") or "").strip()
        stream = str(item.get("stream") or "").strip()
        if not feed_url or not stream:
            decisions.append({"action": "skipped", "reason": "missing feed_url or stream"})
            continue

        state, reason, uses_slot = candidate_state(item, slots_left)
        existing = by_feed.get(feed_url)
        if existing:
            updated = update_existing_source(existing, item, state, reason)
            existing.clear()
            existing.update(updated)
            action = "updated_existing"
        else:
            row = new_source_row(item, state, reason)
            sources.append(row)
            by_feed[feed_url] = row
            action = "added_new"
            if uses_slot:
                slots_left -= 1

        decisions.append({
            "action": action,
            "feed_url": feed_url,
            "stream": stream,
            "proposed_state": state,
            "reason": reason,
            "candidate_status": str(item.get("candidate_status") or ""),
            "score": numeric(item.get("score"), 0.0),
            "sample_match_ratio": numeric(item.get("sample_match_ratio"), 0.0),
        })

    errors = validate_lifecycle(proposed)
    report = {
        "date": today(),
        "report_type": "source_lifecycle_apply",
        "discovery_report_type": discovery.get("report_type", ""),
        "dry_run_default": True,
        "decisions": decisions,
        "validation_errors": errors,
        "summary": {
            "decision_count": len(decisions),
            "added_new": sum(1 for item in decisions if item.get("action") == "added_new"),
            "updated_existing": sum(1 for item in decisions if item.get("action") == "updated_existing"),
            "remaining_probation_slots": slots_left,
        },
    }
    return proposed, report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", default=str(DISCOVERY_PATH))
    parser.add_argument("--lifecycle", default=str(LIFECYCLE_PATH))
    parser.add_argument("--output", default=str(LIFECYCLE_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--apply", action="store_true", help="Write proposed lifecycle output. Default is dry-run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    discovery = load_json(Path(args.discovery), {"items": []})
    lifecycle = load_json(Path(args.lifecycle), {"version": 1, "states": [], "policy": {}, "sources": []})
    proposed, report = apply_discovery(discovery, lifecycle)

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
