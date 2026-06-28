#!/usr/bin/env python3
"""Build a reader-facing policy gate report for Today Radar items.

The gate classifies ranking items before reader output:
- reader_safe: eligible for automated reader-facing rendering.
- review_only: keep in operational/audit artifacts, not reader-facing by default.
- blocked: do not render in reader-facing output.

This tool does not call external services and does not change source files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from core import VALIDATION_DIR, repo_path, write_json

RANKING_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
REPORT_PATH = VALIDATION_DIR / "reader-policy-latest.json"

KNOWN_STREAMS = {
    "finance",
    "crypto-finance",
    "ai",
    "tech-hardware-software",
    "gear-style-edc",
    "moscow-city",
    "dj-audio-creative",
    "science-discovery",
}

TRUSTED_SOURCE_CLASSES = {
    "official",
    "regulator",
    "company",
    "public_media",
    "industry_media",
    "research",
    "exchange",
}

BLOCK_PATTERNS = [
    r"\b(buy|sell|hold)\b",
    r"\b(long|short)\b",
    r"\bprice target\b",
    r"\bwill rise\b",
    r"\bwill fall\b",
    r"покупать",
    r"продавать",
    r"держать позицию",
    r"целевая цена",
    r"точный прогноз",
    r"гарантированно",
]

REVIEW_PATTERNS = [
    r"\brumou?r\b",
    r"\bunconfirmed\b",
    r"\bleak\b",
    r"инсайд",
    r"слух",
    r"неподтвержден",
    r"неподтверждён",
]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def stream_slug(item: dict[str, Any]) -> str:
    return str(item.get("routed_stream") or item.get("configured_stream") or "")


def item_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "description", "feed_title", "feed_id"):
        value = item.get(key)
        if value:
            parts.append(str(value))
    for key in ("include_hits", "boost_hits", "stream_keyword_hits"):
        value = item.get(key)
        if isinstance(value, list):
            parts.extend(str(part) for part in value)
    return " ".join(parts).lower()


def pattern_hits(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def item_key(item: dict[str, Any]) -> str:
    stable = "|".join([
        str(item.get("feed_id") or ""),
        str(item.get("url") or ""),
        str(item.get("title") or ""),
    ])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def decision_for_item(item: dict[str, Any]) -> dict[str, Any]:
    text = item_text(item)
    stream = stream_slug(item)
    source_class = str(item.get("source_class") or "")
    rule_status = str(item.get("source_rule_status") or "")
    relevance = numeric(item.get("relevance_score"), 0.0)
    final_score = numeric(item.get("final_score"), 0.0)
    block_hits = pattern_hits(BLOCK_PATTERNS, text)
    review_hits = pattern_hits(REVIEW_PATTERNS, text)
    reasons: list[str] = []
    decision = "reader_safe"

    if block_hits:
        decision = "blocked"
        reasons.append("blocked language pattern present")

    if rule_status != "accepted_by_source_rules":
        if decision != "blocked":
            decision = "review_only"
        reasons.append("source rules did not accept item")

    if stream not in KNOWN_STREAMS:
        if decision != "blocked":
            decision = "review_only"
        reasons.append("unknown stream")

    if source_class not in TRUSTED_SOURCE_CLASSES:
        if decision != "blocked":
            decision = "review_only"
        reasons.append("source class not trusted for automated reader output")

    if relevance < 0.3 or final_score < 0.3:
        if decision != "blocked":
            decision = "review_only"
        reasons.append("score below reader threshold")

    if review_hits:
        if decision != "blocked":
            decision = "review_only"
        reasons.append("unconfirmed-signal language present")

    if not reasons:
        reasons.append("passed reader policy gate")

    return {
        "item_key": item_key(item),
        "decision": decision,
        "reasons": reasons,
        "stream": stream,
        "source_class": source_class,
        "source_rule_status": rule_status,
        "final_score": final_score,
        "relevance_score": relevance,
        "title": str(item.get("title") or ""),
        "url": str(item.get("url") or ""),
        "block_hits": block_hits,
        "review_hits": review_hits,
    }


def build_policy_report(ranking: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in ranking.get("items", []) if isinstance(item, dict)]
    decisions = [decision_for_item(item) for item in items]
    counts = {
        "reader_safe": sum(1 for item in decisions if item["decision"] == "reader_safe"),
        "review_only": sum(1 for item in decisions if item["decision"] == "review_only"),
        "blocked": sum(1 for item in decisions if item["decision"] == "blocked"),
    }
    return {
        "date": str(ranking.get("date") or date.today().isoformat()),
        "report_date": date.today().isoformat(),
        "report_type": "reader_policy_gate",
        "source": repo_path(RANKING_PATH),
        "reader_output_allowed": counts["blocked"] == 0 and counts["reader_safe"] > 0,
        "counts": counts,
        "decisions": decisions,
        "policy_note": "Items marked reader_safe are eligible for automated reader-facing rendering. review_only and blocked items remain out of reader output by default.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", default=str(RANKING_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    ranking = load_json(Path(args.ranking), {"items": []})
    report = build_policy_report(ranking)
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        output = Path(args.output)
        write_json(output, report)
        print(f"wrote {repo_path(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
