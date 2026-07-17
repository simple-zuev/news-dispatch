#!/usr/bin/env python3
"""Block publication when the live public reader is stale or too sparse."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_reader_policy import item_key
from reader_text import parse_public_datetime, public_excerpt_ru

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = ROOT / "validation"
RANKING_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
POLICY_PATH = VALIDATION_DIR / "reader-policy-latest.json"
REPORT_PATH = VALIDATION_DIR / "public-reader-freshness-latest.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def reader_safe_keys(policy: dict[str, Any]) -> set[str]:
    decisions = policy.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    return {
        str(decision.get("item_key"))
        for decision in decisions
        if isinstance(decision, dict)
        and decision.get("decision") == "reader_safe"
        and decision.get("item_key")
    }


def item_datetime(item: dict[str, Any]) -> datetime | None:
    parsed, _has_time = parse_public_datetime(item.get("published") or item.get("date"))
    if parsed is None:
        return None
    return parsed.astimezone(timezone.utc)


def eligible_items(
    ranking: dict[str, Any],
    policy: dict[str, Any],
    *,
    reference: datetime,
    max_age_hours: float,
) -> list[dict[str, Any]]:
    safe_keys = reader_safe_keys(policy)
    if not safe_keys:
        return []
    rows = ranking.get("items", [])
    if not isinstance(rows, list):
        return []

    eligible: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        if item.get("source_rule_status") != "accepted_by_source_rules":
            continue
        if safe_keys and item_key(item) not in safe_keys:
            continue
        if not public_excerpt_ru(item):
            continue
        published = item_datetime(item)
        if published is None:
            continue
        age_hours = (reference - published).total_seconds() / 3600
        if -6 <= age_hours <= max_age_hours:
            eligible.append(item)
    return eligible


def validate(
    ranking: dict[str, Any],
    policy: dict[str, Any],
    *,
    reference: datetime,
    max_age_hours: float,
    max_newest_age_hours: float,
    min_items: int,
    min_streams: int,
    min_sources: int,
    max_source_share: float,
) -> dict[str, Any]:
    rows = eligible_items(ranking, policy, reference=reference, max_age_hours=max_age_hours)
    streams = {
        str(item.get("routed_stream") or item.get("configured_stream") or "")
        for item in rows
        if item.get("routed_stream") or item.get("configured_stream")
    }
    sources = {
        str(item.get("feed_id") or item.get("feed_title") or "")
        for item in rows
        if item.get("feed_id") or item.get("feed_title")
    }
    source_counts = Counter(
        str(item.get("feed_id") or item.get("feed_title") or "")
        for item in rows
        if item.get("feed_id") or item.get("feed_title")
    )
    dominant_source, dominant_count = source_counts.most_common(1)[0] if source_counts else ("", 0)
    dominant_share = dominant_count / len(rows) if rows else 0.0
    published = [value for item in rows if (value := item_datetime(item)) is not None]
    newest = max(published) if published else None
    newest_age_hours = (reference - newest).total_seconds() / 3600 if newest else None

    issues: list[str] = []
    if len(rows) < min_items:
        issues.append(f"fresh reader items below minimum: {len(rows)} < {min_items}")
    if len(streams) < min_streams:
        issues.append(f"fresh reader streams below minimum: {len(streams)} < {min_streams}")
    if len(sources) < min_sources:
        issues.append(f"fresh reader sources below minimum: {len(sources)} < {min_sources}")
    if dominant_share > max_source_share:
        issues.append(
            f"dominant source share is too high: {dominant_source} "
            f"{dominant_share:.1%} > {max_source_share:.1%}"
        )
    if newest_age_hours is None:
        issues.append("newest reader item is missing")
    elif newest_age_hours > max_newest_age_hours:
        issues.append(
            f"newest reader item is stale: {newest_age_hours:.1f}h > {max_newest_age_hours:.1f}h"
        )

    return {
        "report_type": "public_reader_freshness",
        "generated_at": reference.astimezone(timezone.utc).isoformat(),
        "passed": not issues,
        "issues": issues,
        "limits": {
            "max_age_hours": max_age_hours,
            "max_newest_age_hours": max_newest_age_hours,
            "min_items": min_items,
            "min_streams": min_streams,
            "min_sources": min_sources,
            "max_source_share": max_source_share,
        },
        "observed": {
            "fresh_items": len(rows),
            "fresh_streams": len(streams),
            "fresh_sources": len(sources),
            "dominant_source": dominant_source,
            "dominant_source_share": round(dominant_share, 4),
            "newest_item_at": newest.isoformat() if newest else "",
            "newest_item_age_hours": round(newest_age_hours, 2) if newest_age_hours is not None else None,
            "fetch_errors": len(ranking.get("fetch_errors", []))
            if isinstance(ranking.get("fetch_errors"), list)
            else 0,
        },
    }


def parse_reference(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", default=str(RANKING_PATH))
    parser.add_argument("--policy", default=str(POLICY_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--reference-time", default="")
    parser.add_argument("--max-age-hours", type=float, default=36)
    parser.add_argument("--max-newest-age-hours", type=float, default=12)
    parser.add_argument("--min-items", type=int, default=8)
    parser.add_argument("--min-streams", type=int, default=4)
    parser.add_argument("--min-sources", type=int, default=5)
    parser.add_argument("--max-source-share", type=float, default=0.35)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = validate(
        load_json(Path(args.ranking)),
        load_json(Path(args.policy)),
        reference=parse_reference(args.reference_time),
        max_age_hours=args.max_age_hours,
        max_newest_age_hours=args.max_newest_age_hours,
        min_items=args.min_items,
        min_streams=args.min_streams,
        min_sources=args.min_sources,
        max_source_share=args.max_source_share,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        print(f"Public reader freshness failed: {len(report['issues'])} issue(s)")
        return 1
    observed = report["observed"]
    print(
        "Public reader freshness passed: "
        f"{observed['fresh_items']} item(s), "
        f"{observed['fresh_streams']} stream(s), "
        f"{observed['fresh_sources']} source(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
