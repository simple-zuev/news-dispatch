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
    "official_source",
    "regulator",
    "company",
    "public_media",
    "specialized_media",
    "industry_media",
    "research",
    "exchange",
}

BLOCK_PATTERNS = [
    r"\b(buy|sell|hold)\b",
    r"\b(go|goes|went)\s+(long|short)\b",
    r"\b(long|short)\s+(position|trade|asset|bitcoin|btc|eth|stock|crypto|market)\b",
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

PRODUCT_CARD_PATTERNS = [
    r"\bofficial images?\b",
    r"\bwhere to buy\b",
    r"\bnow available\b",
    r"\bdrop(s|ped)?\b",
    r"\bcolorway\b",
    r"\bcollection\b",
    r"\brelease date\b",
    r"\bretail price\b",
]

EDC_RELEVANCE_PATTERNS = [
    r"\bmaterial(s)?\b",
    r"\bdesign\b",
    r"\bindustry\b",
    r"\bmarket\b",
    r"\bsupply\b",
    r"\brepair",
    r"\bsustainab",
    r"\btechnical apparel\b",
    r"\bmanufactur",
    r"\bcollaboration\b",
]

PREPRINT_SOURCE_CLASSES = {"research_media"}

MARKET_FORECAST_PATTERNS = [
    r"\bprice targets?\b",
    r"\b\d{1,2}[-\s]?month\b",
    r"\byear[-\s]?end\b",
    r"\bforecast(s|ed|ing)?\b",
    r"\bpredict(s|ed|ion|ions)?\b",
    r"\bestimat(e|es|ed|ing)\b",
    r"\boutlook\b",
    r"\banalyst(s)?\b",
    r"\bstrategist(s)?\b",
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


def is_preprint_signal(item: dict[str, Any]) -> bool:
    source_class = str(item.get("source_class") or "")
    source_type = str(item.get("source_type") or "")
    feed_id = str(item.get("feed_id") or "")
    return source_class in PREPRINT_SOURCE_CLASSES or "preprint" in source_type.lower() or feed_id.startswith("arxiv")


def is_product_card_like(item: dict[str, Any], text: str) -> bool:
    if stream_slug(item) != "gear-style-edc":
        return False
    if not pattern_hits(PRODUCT_CARD_PATTERNS, text):
        return False
    return not pattern_hits(EDC_RELEVANCE_PATTERNS, text)


def is_market_forecast_item(item: dict[str, Any], text: str) -> bool:
    if stream_slug(item) not in {"finance", "crypto-finance"}:
        return False
    return bool(pattern_hits(MARKET_FORECAST_PATTERNS, text)) or str(item.get("market_signal_type") or "") == "third_party_forecast"


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
    safety_labels: list[str] = []
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

    if is_preprint_signal(item):
        if decision != "blocked":
            decision = "review_only"
        reasons.append("research/preprint signal; not confirmed analysis")

    if is_product_card_like(item, text):
        if decision != "blocked":
            decision = "review_only"
        reasons.append("product-card retail signal without broader relevance")

    if is_market_forecast_item(item, text):
        safety_labels.append("third_party_market_forecast")

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
        "market_signal_type": "third_party_forecast" if safety_labels else str(item.get("market_signal_type") or "source_reported"),
        "safety_labels": safety_labels,
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
