#!/usr/bin/env python3
"""Block weak or accidental material from the public Digests collection."""

from __future__ import annotations

from pathlib import Path

from core import DISPATCH_DIR, ROOT, parse_front_matter_file
from digest_policy import digest_quality_findings


def validate(dispatch_dir: Path = DISPATCH_DIR) -> list[str]:
    findings: list[str] = []
    for path in sorted(dispatch_dir.rglob("*.md")):
        document = parse_front_matter_file(path)
        if document.errors:
            continue
        collection = str(document.metadata.get("reader_collection") or "").strip()
        if not collection:
            continue
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for finding in digest_quality_findings(document.metadata, document.body):
            findings.append(f"{rel}: {finding}")
    return findings


def main() -> int:
    findings = validate()
    if findings:
        print(f"Public digest validation failed: {len(findings)} finding(s)")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Public digest validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
