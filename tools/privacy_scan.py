#!/usr/bin/env python3
"""Basic public-safety scanner for News Dispatch.

This is not a complete DLP system. It is a lightweight guardrail for obvious leaks
in publishable content and site output.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {".git", ".github", "node_modules", "public", "dist", "build"}
TEXT_EXTENSIONS = {".md", ".yml", ".yaml", ".json", ".txt", ".html", ".css", ".js", ".ts", ".xml"}

# Automated scanning focuses on areas that may later be published.
# Policy and style files intentionally contain prohibited examples and are reviewed manually.
SCAN_PREFIXES = (
    "dispatches/",
    "issues/",
    "site/",
    "validation/",
    "streams/",
)

POLICY_LIKE_FILES = {
    "README.md",
}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("possible_secret_keyword", re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|private[_-]?key|oauth|cookie|bearer)")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("ipv4_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("email_address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("phone_like", re.compile(r"(?<!\d)(?:\+?7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")),
    ("private_context_phrase", re.compile(r"(?i)(our product|our company|our team|internal roadmap|internal metric|private vendor|contractor shortlist|customer data|partner notes)")),
    ("russian_private_context_phrase", re.compile(r"(?i)(наш продукт|наша компания|наша команда|внутренн(ий|яя|ие)|роадмап|дорожная карта|метрики|подрядчик|партнер|клиентские данные)")),
]

ALLOWLIST_PATTERNS = [
    re.compile(r"example\.com", re.IGNORECASE),
    re.compile(r"YYYY-MM-DD", re.IGNORECASE),
    re.compile(r"127\.0\.0\.1"),
    re.compile(r"0\.0\.0\.0"),
]


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if path.name in POLICY_LIKE_FILES and rel.startswith("streams/"):
        return False
    if not rel.startswith(SCAN_PREFIXES):
        return False
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    return True


def is_allowlisted(line: str) -> bool:
    return any(pattern.search(line) for pattern in ALLOWLIST_PATTERNS)


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        if is_allowlisted(line):
            continue
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{path.relative_to(ROOT)}:{line_no}: {name}: {line.strip()[:220]}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and should_scan(path):
            findings.extend(scan_file(path))

    if findings:
        print("Privacy scan failed. Review findings:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Privacy scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
