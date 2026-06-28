#!/usr/bin/env python3
"""Build a probation-only feed view from the source lifecycle registry.

This tool does not edit sources/feeds.json and does not enable ingestion. It only
writes a validation artifact that shows how probation sources would be represented
as constrained feed candidates.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from core import VALIDATION_DIR, repo_path, write_json
from validate_source_lifecycle import LIFECYCLE_PATH, load_lifecycle, validate_lifecycle

REPORT_PATH = VALIDATION_DIR / "probation-feeds-latest.json"


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def probation_limit(lifecycle: dict[str, Any]) -> int:
    policy = lifecycle.get("policy", {}) if isinstance(lifecycle.get("policy"), dict) else {}
    return max(1, int_value(policy.get("probation_ingestion_limit_per_source"), 1))


def probation_rows(lifecycle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = lifecycle.get("sources", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("state") == "probation"]


def feed_view(row: dict[str, Any], per_source: int) -> dict[str, Any]:
    source_id = str(row.get("source_id") or "")
    title = str(row.get("source_page_title") or source_id or row.get("feed_url") or "Probation source")
    return {
        "id": f"probation-{source_id}",
        "title": title,
        "url": str(row.get("feed_url") or ""),
        "stream": str(row.get("stream") or ""),
        "source_type": "Probation source",
        "source_class": "probation_source",
        "enabled": False,
        "probation": True,
        "per_source": per_source,
        "min_relevance_score": 0.55,
        "source_lifecycle_state": str(row.get("state") or ""),
        "source_lifecycle_reason": str(row.get("state_reason") or ""),
        "last_density_score": numeric(row.get("last_density_score"), 0.0),
        "last_discovery_score": numeric(row.get("last_discovery_score"), 0.0),
        "last_health_status": str(row.get("last_health_status") or ""),
        "tags": ["probation", str(row.get("stream") or "")],
    }


def build_report(lifecycle: dict[str, Any]) -> dict[str, Any]:
    per_source = probation_limit(lifecycle)
    rows = probation_rows(lifecycle)
    feeds = [feed_view(row, per_source) for row in rows]
    feeds = sorted(feeds, key=lambda row: (row.get("stream", ""), row.get("id", "")))
    return {
        "date": date.today().isoformat(),
        "report_type": "probation_feed_view",
        "source": repo_path(LIFECYCLE_PATH),
        "probation_count": len(feeds),
        "ingestion_enabled": False,
        "feeds": feeds,
        "policy_note": "This artifact is a read-only probation view. It does not edit sources/feeds.json and does not enable ingestion.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle", default=str(LIFECYCLE_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    lifecycle_path = Path(args.lifecycle)
    lifecycle = load_lifecycle(lifecycle_path)
    errors = validate_lifecycle(lifecycle)
    if errors:
        print("source lifecycle validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    report = build_report(lifecycle)
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        output = Path(args.output)
        write_json(output, report)
        print(f"wrote {repo_path(output)} with {report['probation_count']} probation feed(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
