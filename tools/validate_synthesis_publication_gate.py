#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "synthesis-publication-gate.md"
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"

REQUIRED_DOC_PHRASES = [
    "A signal is not a dispatch.",
    "validation/candidate-dispatch-latest.md",
    "validation/auto-dispatches/",
    "dispatches/",
    "Human approval is not required for routine autonomous daily publication.",
    "fact",
    "source",
    "why it matters",
    "affected actors",
    "possible effect",
    "uncertainty",
    "what to monitor next",
    "separate fact, trend, assessment, hypothesis and unconfirmed signal",
    "privacy scan",
    "source governance",
    "no investment advice",
    "Publication checklist",
    "digest withheld by automated gate",
]

def main() -> int:
    errors: list[str] = []

    if not DOC.exists():
        errors.append("missing docs/synthesis-publication-gate.md")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                errors.append(f"gate document missing required phrase: {phrase}")

        required_block = "must not be copied, moved or automatically promoted into `dispatches/` as-is"
        if required_block not in text:
            errors.append("gate document must block raw automatic promotion into dispatches/")

    if not WORKFLOW.exists():
        errors.append("missing .github/workflows/validate.yml")
    else:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        expected = "python tools/validate_synthesis_publication_gate.py"
        if expected not in workflow:
            errors.append("validate workflow must run synthesis publication gate validator")
        required_block = (
            "run: |\n"
            "          python tools/validate_daily_radar_branch_policy.py\n"
            "          python tools/validate_synthesis_publication_gate.py"
        )
        if required_block not in workflow:
            errors.append("validate workflow must run both policy validators in one multiline run block")

    if errors:
        print("Synthesis publication gate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Synthesis publication gate validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
