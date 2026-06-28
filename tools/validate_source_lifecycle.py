#!/usr/bin/env python3
"""Validate autonomous source lifecycle registry."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from core import ROOT, repo_path
from stream_registry import stream_slugs

LIFECYCLE_PATH = ROOT / "sources" / "source-lifecycle.json"
ALLOWED_STATES = {
    "discovered",
    "probation",
    "active",
    "degraded",
    "suspended",
    "rejected",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class LifecycleValidationError(Exception):
    """Raised when lifecycle registry validation fails."""


def load_lifecycle(path: Path = LIFECYCLE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise LifecycleValidationError(f"missing lifecycle file: {repo_path(path)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LifecycleValidationError("lifecycle root must be an object")
    return data


def require_string(row: dict[str, Any], key: str, context: str, errors: list[str]) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context}: {key} must be a non-empty string")
        return ""
    return value.strip()


def validate_non_negative_int(row: dict[str, Any], key: str, context: str, errors: list[str]) -> None:
    value = row.get(key, 0)
    if not isinstance(value, int) or value < 0:
        errors.append(f"{context}: {key} must be a non-negative integer")


def validate_optional_date(row: dict[str, Any], key: str, context: str, errors: list[str]) -> None:
    value = row.get(key, "")
    if value in ("", None):
        return
    if not isinstance(value, str) or DATE_RE.match(value) is None:
        errors.append(f"{context}: {key} must use YYYY-MM-DD")


def validate_source(row: dict[str, Any], index: int, seen_ids: set[str], streams: set[str]) -> list[str]:
    errors: list[str] = []
    context = f"sources[{index}]"

    if not isinstance(row, dict):
        return [f"{context}: source row must be an object"]

    source_id = require_string(row, "source_id", context, errors)
    if source_id:
        if source_id in seen_ids:
            errors.append(f"{context}: duplicate source_id: {source_id}")
        seen_ids.add(source_id)

    require_string(row, "feed_url", context, errors)
    stream = require_string(row, "stream", context, errors)
    if stream and stream not in streams:
        errors.append(f"{context}: unknown stream: {stream}")

    state = require_string(row, "state", context, errors)
    if state and state not in ALLOWED_STATES:
        errors.append(f"{context}: invalid state: {state}")

    require_string(row, "state_reason", context, errors)

    for key in ("first_seen", "last_seen", "last_policy_decision"):
        validate_optional_date(row, key, context, errors)

    for key in ("promotion_attempts", "failure_count", "success_count"):
        validate_non_negative_int(row, key, context, errors)

    if row.get("last_density_score", 0.0) is not None:
        try:
            value = float(row.get("last_density_score", 0.0))
            if value < 0 or value > 1:
                errors.append(f"{context}: last_density_score must be between 0 and 1")
        except (TypeError, ValueError):
            errors.append(f"{context}: last_density_score must be numeric")

    return errors


def validate_lifecycle(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("version") != 1:
        errors.append("version must be 1")

    states = data.get("states")
    if not isinstance(states, list):
        errors.append("states must be a list")
    else:
        missing = sorted(ALLOWED_STATES - {str(state) for state in states})
        extra = sorted({str(state) for state in states} - ALLOWED_STATES)
        if missing:
            errors.append("states missing: " + ", ".join(missing))
        if extra:
            errors.append("states unknown: " + ", ".join(extra))

    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        for key in (
            "promotion_min_success_count",
            "promotion_max_failure_count",
            "degrade_failure_count",
            "suspend_failure_count",
            "max_new_probation_sources_per_run",
            "probation_ingestion_limit_per_source",
        ):
            validate_non_negative_int(policy, key, "policy", errors)
        gates = policy.get("required_policy_gates", [])
        if not isinstance(gates, list) or not gates:
            errors.append("policy.required_policy_gates must be a non-empty list")

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        return errors

    seen_ids: set[str] = set()
    streams = set(stream_slugs())
    for index, row in enumerate(sources):
        errors.extend(validate_source(row, index, seen_ids, streams))

    return errors


def main() -> int:
    try:
        errors = validate_lifecycle(load_lifecycle())
    except (json.JSONDecodeError, OSError, LifecycleValidationError) as exc:
        print(f"source lifecycle validation failed: {exc}")
        return 1

    if errors:
        print("source lifecycle validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("source lifecycle validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
