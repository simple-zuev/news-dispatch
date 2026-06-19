#!/usr/bin/env python3
"""Write a machine-readable privacy scan report.

This wrapper reuses the existing scanner rules from tools/privacy_scan.py and writes
validation/privacy-report.json for audit/debugging. It intentionally does not define
scanner rules itself.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import privacy_scan

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "privacy-report.json"


def parse_finding(value: str) -> dict[str, object]:
    path, line, rule, excerpt = (value.split(":", 3) + [""] * 4)[:4]
    line_no: int | str
    try:
        line_no = int(line)
    except ValueError:
        line_no = line
    return {
        "path": path.strip(),
        "line": line_no,
        "rule": rule.strip(),
        "excerpt": excerpt.strip(),
    }


def write_report(scanned_files: int, blockers: list[str], warnings: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    status = "failed" if blockers else "passed_with_warnings" if warnings else "passed"
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "scanned_files": scanned_files,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": [parse_finding(item) for item in blockers],
        "warnings": [parse_finding(item) for item in warnings],
    }
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    blockers: list[str] = []
    warnings: list[str] = []
    scanned_files = 0
    for path in privacy_scan.ROOT.rglob("*"):
        if path.is_file() and privacy_scan.should_scan(path):
            scanned_files += 1
            file_blockers, file_warnings = privacy_scan.scan_file(path)
            blockers.extend(file_blockers)
            warnings.extend(file_warnings)

    write_report(scanned_files, blockers, warnings)

    if blockers:
        print("Privacy report failed. Blocking findings:")
        for item in blockers:
            print(f"- {item}")
        if warnings:
            print("\nWarnings also found:")
            for item in warnings:
                print(f"- {item}")
        print(f"Report written to {REPORT_PATH.relative_to(ROOT)}")
        return 1

    if warnings:
        print("Privacy report passed with warnings:")
        for item in warnings:
            print(f"- {item}")
        print(f"Report written to {REPORT_PATH.relative_to(ROOT)}")
        return 0

    print("Privacy report passed. No findings.")
    print(f"Report written to {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
