#!/usr/bin/env python3
"""Retain reader-safe news rows for a bounded two-week public archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from core import ROOT
from reader_text import public_item_is_fresh

RANKING_PATH = ROOT / "validation" / "daily-radar-ranking-latest.json"
POLICY_PATH = ROOT / "validation" / "reader-policy-latest.json"
HISTORY_PATH = ROOT / "validation" / "public-reader-history-latest.json"
RETENTION_DAYS = 14
MAX_ITEMS = 1200
HISTORY_SCHEMA_VERSION = 2
SELECTION_MODE = "balanced_reader_selection"

RETAINED_KEYS = {
    "feed_id",
    "publisher_id",
    "feed_title",
    "configured_stream",
    "routed_stream",
    "source_class",
    "source_type",
    "language",
    "translation_required",
    "title",
    "source_original_title",
    "source_excerpt",
    "source_excerpt_language",
    "reader_title_ru",
    "reader_excerpt_ru",
    "reader_source_line_ru",
    "url",
    "source_original_url",
    "published",
    "date",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def policy_key(item: dict[str, Any]) -> str:
    stable = "|".join(
        [
            str(item.get("feed_id") or ""),
            str(item.get("url") or ""),
            str(item.get("title") or ""),
        ]
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def reader_safe_keys(policy: dict[str, Any]) -> set[str]:
    return {
        str(row.get("item_key"))
        for row in policy.get("decisions", [])
        if isinstance(row, dict) and row.get("decision") == "reader_safe" and row.get("item_key")
    }


def is_reader_safe(item: dict[str, Any], safe_keys: set[str]) -> bool:
    if not safe_keys:
        return False
    if str(item.get("source_rule_status") or "") != "accepted_by_source_rules":
        return False
    explicit = str(item.get("item_key") or "")
    return explicit in safe_keys or policy_key(item) in safe_keys


def is_reader_selected(item: dict[str, Any]) -> bool:
    return item.get("selected") is True


def public_identity(item: dict[str, Any]) -> str:
    url = str(item.get("url") or item.get("source_original_url") or "").strip().lower()
    if url:
        return url
    return "|".join(
        str(item.get(key) or "").strip().lower()
        for key in ("feed_id", "title", "published")
    )


def retained_row(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item[key] for key in RETAINED_KEYS if key in item}


def build_observation_dates(
    previous: dict[str, Any],
    reference: object,
    *,
    retention_days: int,
    previous_is_compatible: bool,
) -> list[str]:
    text = str(reference or "").strip()[:10]
    try:
        reference_date = date.fromisoformat(text)
    except ValueError:
        return []
    values = previous.get("observation_dates", []) if previous_is_compatible else []
    observed: set[date] = {reference_date}
    for value in values if isinstance(values, list) else []:
        try:
            observed.add(date.fromisoformat(str(value).strip()[:10]))
        except ValueError:
            continue
    cutoff = reference_date - timedelta(days=retention_days - 1)
    return [value.isoformat() for value in sorted(observed) if cutoff <= value <= reference_date]


def build_history(
    ranking: dict[str, Any],
    policy: dict[str, Any],
    previous: dict[str, Any],
    *,
    retention_days: int = RETENTION_DAYS,
) -> dict[str, Any]:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    reference = ranking.get("date") or previous.get("date")
    safe_keys = reader_safe_keys(policy)
    current = [
        retained_row(item)
        for item in ranking.get("items", [])
        if isinstance(item, dict) and is_reader_safe(item, safe_keys) and is_reader_selected(item)
    ]
    previous_is_compatible = (
        previous.get("schema_version") == HISTORY_SCHEMA_VERSION
        and previous.get("selection_mode") == SELECTION_MODE
    )
    legacy_cache_reset = bool(previous.get("items")) and not previous_is_compatible
    observation_dates = build_observation_dates(
        previous,
        reference,
        retention_days=retention_days,
        previous_is_compatible=previous_is_compatible,
    )
    older = [item for item in previous.get("items", []) if isinstance(item, dict)] if previous_is_compatible else []
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(current + older, key=lambda row: str(row.get("published") or row.get("date") or ""), reverse=True):
        identity = public_identity(item)
        if not identity or identity in seen:
            continue
        if reference and not public_item_is_fresh(item, reference, max_age_hours=24 * retention_days):
            continue
        seen.add(identity)
        merged.append(retained_row(item))
        if len(merged) == MAX_ITEMS:
            break
    return {
        "report_type": "public_reader_history",
        "schema_version": HISTORY_SCHEMA_VERSION,
        "selection_mode": SELECTION_MODE,
        "date": reference,
        "retention_days": retention_days,
        "current_selected_count": len(current),
        "legacy_cache_reset": legacy_cache_reset,
        "observation_dates": observation_dates,
        "item_count": len(merged),
        "items": merged,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", type=Path, default=RANKING_PATH)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--retention-days", type=int, default=RETENTION_DAYS)
    parser.add_argument("--reset", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ranking = load_json(args.ranking)
    policy = load_json(args.policy)
    previous = {} if args.reset else load_json(args.history)
    try:
        report = build_history(ranking, policy, previous, retention_days=args.retention_days)
    except ValueError as exc:
        print(f"Public reader history failed: {exc}")
        return 2
    args.history.parent.mkdir(parents=True, exist_ok=True)
    args.history.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Public reader history retained {report['item_count']} item(s) for {report['retention_days']} days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
