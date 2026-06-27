#!/usr/bin/env python3
"""Validate public-safe front matter for News Dispatch dispatch files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from stream_registry import allowed_stream_slugs

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
RUBRICS_PATH = ROOT / "data" / "rubrics.json"

REQUIRED_KEYS = {
    "title",
    "date",
    "period",
    "stream",
    "type",
    "language",
    "status",
    "review_level",
    "publication_scope",
    "public_safe",
    "private_context_used",
    "contains_personal_data",
    "contains_internal_company_data",
    "contains_confidential_strategy",
    "contains_nonpublic_sources",
    "contains_investment_advice",
    "contains_legal_advice",
    "source_mode",
    "summary",
    "tags",
    "sources",
    "privacy_review",
    "editorial_review",
}

ALLOWED_REVIEW_LEVELS = {
    "standard_public_review",
    "strict_publication_review",
}

ALLOWED_STATUSES = {"draft", "published"}
ALLOWED_LANGUAGES = {"ru", "en"}
ALLOWED_LEGACY_TYPES = {"daily", "weekly", "special", "brief", "draft"}

MUST_BE_FALSE = {
    "private_context_used",
    "contains_personal_data",
    "contains_internal_company_data",
    "contains_confidential_strategy",
    "contains_nonpublic_sources",
    "contains_investment_advice",
    "contains_legal_advice",
}

TAXONOMY_KEYS = {
    "primary_rubric",
    "rubrics",
    "issue_type",
    "publication_mode",
    "claim_types",
    "confidence",
    "evidence_status",
    "verification_gap",
}


def clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def load_taxonomy() -> dict[str, set[str]]:
    if not RUBRICS_PATH.exists():
        return {"rubrics": set(), "issue_types": set(), "claim_types": set(), "confidence_levels": set(), "publication_modes": set()}
    data = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
    return {
        "rubrics": {item["slug"] for item in data.get("rubrics", []) if item.get("slug")},
        "issue_types": {item["slug"] for item in data.get("issue_types", []) if item.get("slug")},
        "claim_types": set(data.get("claim_types", [])),
        "confidence_levels": set(data.get("confidence_levels", [])),
        "publication_modes": set(data.get("publication_modes", [])),
    }


def as_text(meta: dict[str, object], key: str) -> str:
    value = meta.get(key)
    if isinstance(value, list):
        return ""
    return str(value) if value is not None else ""


def as_list(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def parse_front_matter(text: str) -> tuple[dict[str, object], list[str]]:
    if not text.startswith("---\n"):
        return {}, ["missing front matter delimiter"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, ["missing closing front matter delimiter"]

    raw = text[4:end]
    meta: dict[str, object] = {}
    errors: list[str] = []
    current_key: str | None = None

    for line_no, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  -"):
            if current_key is None:
                errors.append(f"line {line_no}: list item without key")
                continue
            if not isinstance(meta.get(current_key), list):
                meta[current_key] = []
            item = clean_value(line.split("-", 1)[1])
            if item:
                meta[current_key].append(item)
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: invalid front matter line")
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        raw_value = value.strip()
        if raw_value in {"", "[]"}:
            meta[current_key] = []
        else:
            meta[current_key] = clean_value(raw_value)

    return meta, errors


def validate_taxonomy(path: Path, meta: dict[str, object], taxonomy: dict[str, set[str]]) -> list[str]:
    rel = path.relative_to(ROOT)
    findings: list[str] = []
    if not (TAXONOMY_KEYS & set(meta)):
        return findings

    missing = sorted(TAXONOMY_KEYS - set(meta))
    if missing:
        findings.append(f"{rel}: incomplete taxonomy metadata, missing keys: {', '.join(missing)}")

    primary_rubric = as_text(meta, "primary_rubric")
    rubrics = as_list(meta, "rubrics")
    issue_type = as_text(meta, "issue_type")
    confidence = as_text(meta, "confidence")
    publication_mode = as_text(meta, "publication_mode")
    claim_types = as_list(meta, "claim_types")

    if primary_rubric and primary_rubric not in taxonomy["rubrics"]:
        findings.append(f"{rel}: unknown primary_rubric {primary_rubric!r}")
    if primary_rubric and rubrics and primary_rubric not in rubrics:
        findings.append(f"{rel}: primary_rubric must be included in rubrics")
    for rubric in rubrics:
        if rubric not in taxonomy["rubrics"]:
            findings.append(f"{rel}: unknown rubric {rubric!r}")
    if issue_type and issue_type not in taxonomy["issue_types"]:
        findings.append(f"{rel}: unknown issue_type {issue_type!r}")
    if confidence and confidence not in taxonomy["confidence_levels"]:
        findings.append(f"{rel}: unknown confidence {confidence!r}")
    if publication_mode and publication_mode not in taxonomy["publication_modes"]:
        findings.append(f"{rel}: unknown publication_mode {publication_mode!r}")
    for claim_type in claim_types:
        if claim_type not in taxonomy["claim_types"]:
            findings.append(f"{rel}: unknown claim_type {claim_type!r}")

    if not as_text(meta, "evidence_status"):
        findings.append(f"{rel}: evidence_status must not be empty when taxonomy metadata is present")
    if not as_text(meta, "verification_gap"):
        findings.append(f"{rel}: verification_gap must not be empty when taxonomy metadata is present")

    return findings


def validate_file(path: Path, taxonomy: dict[str, set[str]]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    meta, errors = parse_front_matter(text)
    rel = path.relative_to(ROOT)
    findings: list[str] = [f"{rel}: {error}" for error in errors]

    missing = sorted(REQUIRED_KEYS - set(meta))
    if missing:
        findings.append(f"{rel}: missing keys: {', '.join(missing)}")

    if as_text(meta, "publication_scope") != "public":
        findings.append(f"{rel}: publication_scope must be public")

    if as_text(meta, "public_safe") != "true":
        findings.append(f"{rel}: public_safe must be true")

    for key in sorted(MUST_BE_FALSE):
        if as_text(meta, key) != "false":
            findings.append(f"{rel}: {key} must be false")

    if as_text(meta, "source_mode") != "public_sources_only":
        findings.append(f"{rel}: source_mode must be public_sources_only")

    if as_text(meta, "stream") not in allowed_stream_slugs():
        findings.append(f"{rel}: unknown stream {as_text(meta, 'stream')!r}")

    if as_text(meta, "review_level") not in ALLOWED_REVIEW_LEVELS:
        findings.append(f"{rel}: unknown review_level {as_text(meta, 'review_level')!r}")

    if as_text(meta, "language") not in ALLOWED_LANGUAGES:
        findings.append(f"{rel}: language must be ru or en")

    if as_text(meta, "status") not in ALLOWED_STATUSES:
        findings.append(f"{rel}: status must be draft or published")

    if as_text(meta, "type") not in ALLOWED_LEGACY_TYPES:
        findings.append(f"{rel}: unknown legacy type {as_text(meta, 'type')!r}")

    findings.extend(validate_taxonomy(path, meta, taxonomy))
    return findings


def main() -> int:
    files = sorted(DISPATCH_DIR.rglob("*.md"))
    if not files:
        print("No dispatches found.")
        return 1

    taxonomy = load_taxonomy()
    findings: list[str] = []
    for path in files:
        findings.extend(validate_file(path, taxonomy))

    if findings:
        print("Front matter validation failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(f"Front matter validation passed for {len(files)} dispatch file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
