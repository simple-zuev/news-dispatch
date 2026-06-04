#!/usr/bin/env python3
"""Validate public-safe front matter for News Dispatch dispatch files.

The validator checks only committed dispatches under `dispatches/**/*.md`.
It does not inspect templates or policy files.
"""

from __future__ import annotations

import sys
from pathlib import Path

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

ALLOWED_STREAMS = {
    "general",
    "work",
    "finance",
    "digital-assets-infrastructure",
    "home-environment",
    "gear",
    "city-culture",
    "audio-creative",
    "horizon",
}

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


def parse_front_matter(text: str) -> tuple[dict[str, str], list[str]]:
    if not text.startswith("---\n"):
        return {}, ["missing front matter delimiter"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, ["missing closing front matter delimiter"]

    raw = text[4:end]
    meta: dict[str, str] = {}
    errors: list[str] = []
    current_key: str | None = None

    for line_no, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  -"):
            if current_key is None:
                errors.append(f"line {line_no}: list item without key")
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: invalid front matter line")
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        meta[current_key] = value.strip().strip('"')

    return meta, errors


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    meta, errors = parse_front_matter(text)
    findings: list[str] = [f"{path.relative_to(ROOT)}: {error}" for error in errors]

    missing = sorted(REQUIRED_KEYS - set(meta))
    if missing:
        findings.append(f"{path.relative_to(ROOT)}: missing keys: {', '.join(missing)}")

    if meta.get("publication_scope") != "public":
        findings.append(f"{path.relative_to(ROOT)}: publication_scope must be public")

    if meta.get("public_safe") != "true":
        findings.append(f"{path.relative_to(ROOT)}: public_safe must be true")

    for key in sorted(MUST_BE_FALSE):
        if meta.get(key) != "false":
            findings.append(f"{path.relative_to(ROOT)}: {key} must be false")

    if meta.get("source_mode") != "public_sources_only":
        findings.append(f"{path.relative_to(ROOT)}: source_mode must be public_sources_only")

    if meta.get("stream") not in ALLOWED_STREAMS:
        findings.append(f"{path.relative_to(ROOT)}: unknown stream {meta.get('stream')!r}")

    if meta.get("review_level") not in ALLOWED_REVIEW_LEVELS:
        findings.append(f"{path.relative_to(ROOT)}: unknown review_level {meta.get('review_level')!r}")

    if meta.get("language") not in {"ru", "en"}:
        findings.append(f"{path.relative_to(ROOT)}: language must be ru or en")

    if not text.strip().endswith("."):
        # Non-blocking style check would be better later; keep validator strict only for metadata.
        pass

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
