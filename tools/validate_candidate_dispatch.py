#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "validation" / "candidate-dispatch-latest.md"

REQUIRED = [
    "Status: candidate only. Not published.",
    "Do not move to dispatches/ without editorial review.",
]

FORBIDDEN = [
    "status: published",
    "publication_scope: public",
]


def main() -> int:
    if not CANDIDATE.exists():
        print("Candidate dispatch artifact not found; skipping.")
        return 0
    text = CANDIDATE.read_text(encoding="utf-8")
    errors: list[str] = []
    for item in REQUIRED:
        if item not in text:
            errors.append(f"missing required disclaimer: {item}")
    lower = text.lower()
    for item in FORBIDDEN:
        if item in lower:
            errors.append(f"candidate artifact must not contain: {item}")
    if errors:
        print("Candidate dispatch validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Candidate dispatch validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
