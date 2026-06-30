#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from core import ROOT, ensure_list, parse_front_matter, parse_front_matter_file, repo_path

DOC = ROOT / "docs" / "synthesis-quality-gate.md"
AUTO_DISPATCHES = ROOT / "validation" / "auto-dispatches"
CANDIDATE = ROOT / "validation" / "candidate-dispatch-latest.md"
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"

REQUIRED_DOC_PHRASES = [
    "minimum quality requirements",
    "validation/auto-dispatches/",
    "validation/candidate-dispatch-latest.md",
    "does not approve publication",
    "status: \"draft\"",
    "publication_mode: \"draft_only\"",
    "verification_gap",
    "confidence",
    "claim_types",
    "privacy_review: \"auto_passed_public_sources_only\"",
    "editorial_review: \"automatic_draft_needs_human_review\"",
    "## Лид",
    "## Главное",
    "## Что произошло",
    "## Почему это важно",
    "## Аналитическая рамка",
    "## Реестр подтверждения",
    "## Что проверять дальше",
    "## Статус",
    "Semantic topic routing, primary-source enrichment and final editorial synthesis are separate layers.",
]

REQUIRED_META = {
    "status": "draft",
    "publication_mode": "draft_only",
    "privacy_review": "auto_passed_public_sources_only",
    "editorial_review": "automatic_draft_needs_human_review",
}

REQUIRED_PRESENT = [
    "verification_gap",
    "confidence",
    "claim_types",
]

FORBIDDEN_META = {
    "status": "published",
    "publication_mode": "published",
}

FORBIDDEN_TRUE = [
    "contains_investment_advice",
    "contains_legal_advice",
    "contains_paid_promotion",
]

REQUIRED_SECTIONS = [
    "Лид",
    "Главное",
    "Что произошло",
    "Почему это важно",
    "Аналитическая рамка",
    "Реестр подтверждения",
    "Что проверять дальше",
    "Статус",
]


def as_text(value: Any) -> str:
    return str(value or "").strip()


def validate_doc(errors: list[str]) -> None:
    if not DOC.exists():
        errors.append("missing docs/synthesis-quality-gate.md")
        return

    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in text:
            errors.append(f"{repo_path(DOC)}: missing required phrase: {phrase}")


def current_auto_drafts() -> list[Path]:
    if not AUTO_DISPATCHES.exists():
        return []
    return sorted(AUTO_DISPATCHES.glob("*/*-auto-radar-draft.md"))


def validate_auto_draft(path: Path, errors: list[str]) -> None:
    doc = parse_front_matter_file(path)
    label = repo_path(path)
    if doc.errors:
        for error in doc.errors:
            errors.append(f"{label}: invalid front matter: {error}")
        return

    metadata = doc.metadata
    for key, expected in REQUIRED_META.items():
        actual = as_text(metadata.get(key))
        if actual != expected:
            errors.append(f"{label}: expected {key}: {expected!r}, got {actual!r}")

    for key in REQUIRED_PRESENT:
        value = metadata.get(key)
        if key == "claim_types":
            if not ensure_list(value):
                errors.append(f"{label}: missing non-empty claim_types")
        elif not as_text(value):
            errors.append(f"{label}: missing non-empty {key}")

    for key, forbidden in FORBIDDEN_META.items():
        actual = as_text(metadata.get(key)).lower()
        if actual == forbidden:
            errors.append(f"{label}: forbidden {key}: {forbidden!r}")

    for key in FORBIDDEN_TRUE:
        if metadata.get(key) is True:
            errors.append(f"{label}: forbidden {key}: true")

    headings = {line[3:].strip() for line in doc.body.splitlines() if line.startswith("## ")}
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"{label}: missing required section: ## {section}")


def validate_auto_drafts(errors: list[str]) -> None:
    drafts = current_auto_drafts()
    if not drafts:
        errors.append("no current auto-radar drafts found under validation/auto-dispatches/*/")
        return
    for path in drafts:
        validate_auto_draft(path, errors)


def validate_candidate(errors: list[str]) -> None:
    if not CANDIDATE.exists():
        errors.append("missing validation/candidate-dispatch-latest.md")
        return

    text = CANDIDATE.read_text(encoding="utf-8")
    lower = text.lower()
    label = repo_path(CANDIDATE)
    for phrase in ("candidate only", "not published"):
        if phrase not in lower:
            errors.append(f"{label}: missing candidate-only disclaimer phrase: {phrase}")

    if text.startswith("---\n"):
        doc = parse_front_matter(text)
        metadata = doc.metadata
        if as_text(metadata.get("status")).lower() == "published":
            errors.append(f"{label}: forbidden status: 'published'")
        if as_text(metadata.get("publication_mode")).lower() == "published":
            errors.append(f"{label}: forbidden publication_mode: 'published'")

    forbidden_tokens = [
        'status: "published"',
        "status: published",
        'publication_mode: "published"',
        "publication_mode: published",
    ]
    for token in forbidden_tokens:
        if token in lower:
            errors.append(f"{label}: candidate artifact must not contain {token!r}")


def validate_workflow(errors: list[str]) -> None:
    if not WORKFLOW.exists():
        errors.append("missing .github/workflows/validate.yml")
        return

    workflow = WORKFLOW.read_text(encoding="utf-8")
    expected = "python tools/validate_synthesis_quality_gate.py"
    if expected not in workflow:
        errors.append("validate workflow must run synthesis quality gate validator")


def main() -> int:
    errors: list[str] = []
    validate_doc(errors)
    validate_auto_drafts(errors)
    validate_candidate(errors)
    validate_workflow(errors)

    if errors:
        print("Synthesis quality gate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Synthesis quality gate validation: OK ({len(current_auto_drafts())} current auto-radar draft(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
