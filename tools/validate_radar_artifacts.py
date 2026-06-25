#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "validation/daily-radar-latest.json",
    "validation/daily-radar-filter-summary.json",
    "validation/source-health-latest.json",
    "validation/reviewed-radar-latest.md",
    "validation/candidate-dispatch-latest.md",
]


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            errors.append(f"missing artifact: {rel}")
    if not errors:
        radar = load_json("validation/daily-radar-latest.json")
        if not isinstance(radar.get("generated", []), list):
            errors.append("daily-radar-latest.json generated must be a list")
        source_health = load_json("validation/source-health-latest.json")
        feeds = source_health.get("feeds", [])
        if source_health.get("total") != len(feeds):
            errors.append("source-health total must equal feed count")
        reviewed = (ROOT / "validation/reviewed-radar-latest.md").read_text(encoding="utf-8")
        candidate = (ROOT / "validation/candidate-dispatch-latest.md").read_text(encoding="utf-8")
        if "Status: pre-publication review artifact." not in reviewed:
            errors.append("reviewed radar missing pre-publication status")
        if "Status: candidate only. Not published." not in candidate:
            errors.append("candidate dispatch missing candidate-only status")
    if errors:
        print("Radar artifact validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Radar artifact validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
