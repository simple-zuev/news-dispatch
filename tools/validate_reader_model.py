#!/usr/bin/env python3
"""Validate public reader model output before HTML rendering."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_reader_policy import item_key
from core import VALIDATION_DIR, repo_path, write_json
from reader_model import FORBIDDEN_PUBLIC_KEYS, PublicReaderItem, from_ranking_item

RANKING_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
POLICY_PATH = VALIDATION_DIR / "reader-policy-latest.json"
REPORT_PATH = VALIDATION_DIR / "reader-model-latest.json"

GENERIC_TITLES = {
    "без заголовка",
    "публичный источник: регуляторика и надзор",
    "публичный источник: движение крипторынка",
}
GENERIC_SOURCE_TOPICS = {
    "регуляторика и надзор",
    "банки ставки и ликвидность",
    "безопасность и технологическая инфраструктура",
    "модели и инфраструктура ии",
    "движение крипторынка",
}
FORBIDDEN_URL_MARKERS = (
    "/comments/default",
    "/feeds/comments",
)
FORBIDDEN_PUBLIC_TEXT = (
    "source_rule_status",
    "final_score",
    "relevance_score",
    "feed_id",
    "reader_safe",
    "validation",
    "threshold",
    "coverage",
)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def norm(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"[^0-9a-zа-яё]+", " ", text).strip()


def is_generic_source_topic(title: str) -> bool:
    if ":" not in title:
        return False
    _source, topic = title.split(":", 1)
    return norm(topic) in GENERIC_SOURCE_TOPICS


def safe_decision_keys(policy: dict[str, Any]) -> set[str]:
    decisions = policy.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    keys: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        if decision.get("decision") != "reader_safe":
            continue
        key = str(decision.get("item_key") or "")
        if key:
            keys.add(key)
    return keys


def selected_items(ranking: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [item for item in ranking.get("items", []) if isinstance(item, dict)]
    safe_keys = safe_decision_keys(policy)
    if safe_keys:
        return [item for item in rows if item_key(item) in safe_keys]
    return [item for item in rows if item.get("selected")]


def validate_model(model: PublicReaderItem) -> list[str]:
    issues: list[str] = []
    payload = model.to_render_dict()
    leaked = set(payload) & FORBIDDEN_PUBLIC_KEYS
    if leaked:
        issues.append("forbidden public keys leaked: " + ", ".join(sorted(leaked)))
    title = model.title.strip()
    if not title:
        issues.append("title is empty")
    if norm(title) in GENERIC_TITLES or is_generic_source_topic(title):
        issues.append(f"title is generic: {title}")
    if not model.source.strip():
        issues.append("source is empty")
    if not model.stream.strip():
        issues.append("stream label is empty")
    if not model.reliability.strip():
        issues.append("reliability label is empty")
    if not model.url.strip():
        issues.append("url is empty")
    lowered_url = model.url.lower()
    for marker in FORBIDDEN_URL_MARKERS:
        if marker in lowered_url:
            issues.append(f"comment feed URL in model: {marker}")
    joined = " ".join(payload.values()).lower()
    for text in FORBIDDEN_PUBLIC_TEXT:
        if text in joined:
            issues.append(f"diagnostic text leaked into model: {text}")
    return issues


def validate(ranking: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    rows = selected_items(ranking, policy)
    for item in rows:
        model = from_ranking_item(item)
        item_issues = validate_model(model)
        if item_issues:
            issues.append(
                {
                    "item_key": item_key(item),
                    "title": model.title,
                    "url": model.url,
                    "issues": item_issues,
                }
            )
    return {
        "report_type": "reader_model_validation",
        "ranking": repo_path(RANKING_PATH),
        "policy": repo_path(POLICY_PATH),
        "checked_items": len(rows),
        "passed": not issues,
        "issues": issues,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", default=str(RANKING_PATH))
    parser.add_argument("--policy", default=str(POLICY_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    ranking = load_json(Path(args.ranking), {"items": []})
    policy = load_json(Path(args.policy), {"decisions": []})
    report = validate(ranking, policy)
    write_json(Path(args.output), report)
    if not report["passed"]:
        print(f"Reader model validation failed: {len(report['issues'])} item(s)")
        return 1
    print(f"Reader model validation passed: {report['checked_items']} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
