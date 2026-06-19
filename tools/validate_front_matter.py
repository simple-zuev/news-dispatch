#!/usr/bin/env python3
"""Validate public-safe front matter for News Dispatch dispatch files."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from stream_registry import allowed_stream_slugs

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"

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

ALLOWED_STATUSES = {"draft", "published"}
ALLOWED_TYPES = {"daily", "weekly", "monthly", "issue", "signal", "sample"}
ALLOWED_REVIEW_LEVELS = {
    "standard_public_review",
    "strict_publication_review",
}
MUST_BE_FALSE = {
    "private_context_used",
    "contains_personal_data",
    "contains_internal_company_data",
    "contains_confidential_strategy",
    "contains_nonpublic_sources",
    "contains_investment_advice",
    "contains_legal_advice",
}

SOURCE_PARALLEL_KEYS = ["source_titles", "source_types", "source_notes"]
MEDIA_PARALLEL_KEYS = ["media_titles", "media_types", "media_notes"]
VISUAL_PARALLEL_KEYS = ["visual_titles", "visual_types"]


def parse_front_matter(text: str) -> tuple[dict[str, Any], list[str]]:
    if not text.startswith("---\n"):
        return {}, ["missing front matter delimiter"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, ["missing closing front matter delimiter"]

    raw = text[4:end]
    meta: dict[str, Any] = {}
    errors: list[str] = []
    current_key: str | None = None

    for line_no, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  -"):
            if current_key is None:
                errors.append(f"line {line_no}: list item without key")
                continue
            meta.setdefault(current_key, [])
            if not isinstance(meta[current_key], list):
                errors.append(f"line {line_no}: list item under scalar key {current_key}")
                continue
            meta[current_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if line.startswith(" "):
            errors.append(f"line {line_no}: unsupported indentation")
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: invalid front matter line")
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip().strip('"')
        meta[current_key] = [] if value == "" else value

    return meta, errors


def list_value(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def scalar(meta: dict[str, Any], key: str) -> str:
    value = meta.get(key, "")
    if isinstance(value, list):
        return ""
    return str(value)


def validate_parallel_lists(path: Path, meta: dict[str, Any], findings: list[str]) -> None:
    rel = path.relative_to(ROOT)
    sources = list_value(meta, "sources")
    if scalar(meta, "status") == "published" and not sources:
        findings.append(f"{rel}: published dispatch requires at least one source")
    if sources:
        for key in SOURCE_PARALLEL_KEYS:
            values = list_value(meta, key)
            if len(values) != len(sources):
                findings.append(f"{rel}: {key} length must match sources length ({len(values)} != {len(sources)})")

    media = list_value(meta, "media")
    if media:
        for key in MEDIA_PARALLEL_KEYS:
            values = list_value(meta, key)
            if len(values) != len(media):
                findings.append(f"{rel}: {key} length must match media length ({len(values)} != {len(media)})")

    visuals = list_value(meta, "visuals")
    if visuals:
        for key in VISUAL_PARALLEL_KEYS:
            values = list_value(meta, key)
            if len(values) != len(visuals):
                findings.append(f"{rel}: {key} length must match visuals length ({len(values)} != {len(visuals)})")


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    meta, errors = parse_front_matter(text)
    rel = path.relative_to(ROOT)
    findings: list[str] = [f"{rel}: {error}" for error in errors]

    missing = sorted(REQUIRED_KEYS - set(meta))
    if missing:
        findings.append(f"{rel}: missing keys: {', '.join(missing)}")

    if scalar(meta, "status") not in ALLOWED_STATUSES:
        findings.append(f"{rel}: status must be draft or published")

    if scalar(meta, "type") not in ALLOWED_TYPES:
        findings.append(f"{rel}: unknown type {scalar(meta, 'type')!r}")

    if scalar(meta, "publication_scope") != "public":
        findings.append(f"{rel}: publication_scope must be public")

    if scalar(meta, "public_safe") != "true":
        findings.append(f"{rel}: public_safe must be true")

    for key in sorted(MUST_BE_FALSE):
        if scalar(meta, key) != "false":
            findings.append(f"{rel}: {key} must be false")

    if scalar(meta, "source_mode") != "public_sources_only":
        findings.append(f"{rel}: source_mode must be public_sources_only")

    if scalar(meta, "stream") not in allowed_stream_slugs():
        findings.append(f"{rel}: unknown stream {scalar(meta, 'stream')!r}")

    if scalar(meta, "review_level") not in ALLOWED_REVIEW_LEVELS:
        findings.append(f"{rel}: unknown review_level {scalar(meta, 'review_level')!r}")

    if scalar(meta, "language") not in {"ru", "en"}:
        findings.append(f"{rel}: language must be ru or en")

    if scalar(meta, "status") == "published" and len(scalar(meta, "summary").strip()) < 40:
        findings.append(f"{rel}: published dispatch summary is too short")

    validate_parallel_lists(path, meta, findings)
    return findings


def main() -> int:
    files = sorted(DISPATCH_DIR.rglob("*.md"))
    if not files:
        print("No dispatches found.")
        return 1

    findings: list[str] = []
    for path in files:
        findings.extend(validate_file(path))

    if findings:
        print("Front matter validation failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(f"Front matter validation passed for {len(files)} dispatch file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
