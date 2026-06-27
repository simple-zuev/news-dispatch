#!/usr/bin/env python3
"""Validate News Dispatch source governance rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RULES_PATH = ROOT / "data" / "source_rules.json"
STREAMS_PATH = ROOT / "data" / "streams.json"
RUBRICS_PATH = ROOT / "data" / "rubrics.json"

REQUIRED_SOURCE_CLASSES = {
    "official_source",
    "business_media",
    "public_media",
    "specialized_media",
    "research_media",
    "community_source",
    "marketing_source",
}

REQUIRED_PUBLICATION_MODES = {"published", "limited_publication", "draft_only", "blocked"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stream_slugs() -> set[str]:
    data = load_json(STREAMS_PATH)
    return {item["slug"] for item in data.get("streams", []) if item.get("slug")}


def rubric_taxonomy() -> dict[str, set[str]]:
    data = load_json(RUBRICS_PATH)
    return {
        "claim_types": set(data.get("claim_types", [])),
        "confidence_levels": set(data.get("confidence_levels", [])),
        "publication_modes": set(data.get("publication_modes", [])),
    }


def validate() -> list[str]:
    findings: list[str] = []
    if not SOURCE_RULES_PATH.exists():
        return ["data/source_rules.json is missing"]

    data = load_json(SOURCE_RULES_PATH)
    streams = stream_slugs()
    taxonomy = rubric_taxonomy()

    source_classes = data.get("source_classes", {})
    missing_classes = sorted(REQUIRED_SOURCE_CLASSES - set(source_classes))
    if missing_classes:
        findings.append("missing source_classes: " + ", ".join(missing_classes))

    for slug, item in sorted(source_classes.items()):
        if not item.get("tier"):
            findings.append(f"source_classes.{slug}: missing tier")
        if not item.get("role"):
            findings.append(f"source_classes.{slug}: missing role")
        ceiling = item.get("default_confidence_ceiling")
        if ceiling not in taxonomy["confidence_levels"]:
            findings.append(f"source_classes.{slug}: invalid default_confidence_ceiling {ceiling!r}")
        for claim_type in item.get("allowed_claim_types", []):
            if claim_type not in taxonomy["claim_types"]:
                findings.append(f"source_classes.{slug}: unknown claim_type {claim_type!r}")

    stream_rules = data.get("stream_rules", {})
    missing_streams = sorted(streams - set(stream_rules))
    if missing_streams:
        findings.append("missing stream_rules: " + ", ".join(missing_streams))
    unknown_streams = sorted(set(stream_rules) - streams)
    if unknown_streams:
        findings.append("unknown stream_rules: " + ", ".join(unknown_streams))

    for slug, item in sorted(stream_rules.items()):
        minimum = item.get("minimum_for_published", {})
        modes = set(minimum.get("allowed_publication_modes", []))
        if not modes:
            findings.append(f"stream_rules.{slug}: allowed_publication_modes is empty")
        unknown_modes = sorted(modes - taxonomy["publication_modes"])
        if unknown_modes:
            findings.append(f"stream_rules.{slug}: unknown publication modes: {', '.join(unknown_modes)}")
        for claim_type in minimum.get("blocked_without_primary_for_claims", []):
            if claim_type not in taxonomy["claim_types"]:
                findings.append(f"stream_rules.{slug}: unknown blocked claim_type {claim_type!r}")
        if not item.get("default_risks"):
            findings.append(f"stream_rules.{slug}: default_risks is empty")

    publication_modes = set(data.get("publication_modes", {}))
    missing_modes = sorted(REQUIRED_PUBLICATION_MODES - publication_modes)
    if missing_modes:
        findings.append("missing publication_modes descriptions: " + ", ".join(missing_modes))

    claim_rules = data.get("claim_rules", {})
    missing_claim_rules = sorted(taxonomy["claim_types"] - set(claim_rules))
    if missing_claim_rules:
        findings.append("missing claim_rules: " + ", ".join(missing_claim_rules))

    return findings


def main() -> int:
    findings = validate()
    if findings:
        print("Source rules validation failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Source rules validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
