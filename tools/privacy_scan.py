#!/usr/bin/env python3
"""Public-safety scanner for News Dispatch.

The scanner has two severity levels:
- hard blockers: secrets, credentials, private keys, direct personal contact data;
- soft warnings: editorial/private-context phrases that require review but should not
  stop a public Pages deploy by themselves.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".github", "node_modules", "public", "dist", "build"}
TEXT_EXTENSIONS = {".md", ".yml", ".yaml", ".json", ".txt", ".html", ".css", ".js", ".ts", ".xml"}
SCAN_PREFIXES = ("dispatches/", "signals/", "issues/", "site/", "validation/", "streams/")
POLICY_LIKE_FILES = {"README.md"}

SECRET_KEYWORDS = [
    r"api[_-]?key",
    r"access[_-]?token",
    r"refresh[_-]?token",
    r"auth[_-]?token",
    r"secret[_-]?key",
    r"client[_-]?secret",
    r"password",
    r"passwd",
    r"private[_-]?key",
    r"oauth",
    r"cookie",
    r"bearer",
]
KEYWORD_PATTERN = "(?i)(" + "|".join(SECRET_KEYWORDS) + ")"

HARD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("possible_secret_keyword", re.compile(KEYWORD_PATTERN)),
    ("private_key_block", re.compile("-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email_address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("phone_like", re.compile(r"(?<!\d)(?:\+?7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")),
]

SOFT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_context_phrase",
        re.compile(
            r"(?i)(our product|our company|our team|internal roadmap|internal metric|private vendor|contractor shortlist|customer data|partner notes)"
        ),
    ),
    (
        "russian_private_context_phrase",
        re.compile(
            r"(?i)(наш продукт|наша компания|наша команда|внутренн(ий|яя|ие) роадмап|внутренн(ий|яя|ие) метрик|клиентские данные|данные клиентов|подрядчик по проекту|партнерские заметки)"
        ),
    ),
    (
        "ipv4_address_review",
        re.compile(r"\b(?:10|172\.(?:1[6-9]|2\d|3[0-1])|192\.168)\.\d{1,3}\.\d{1,3}\b"),
    ),
]

ALLOWLIST_PATTERNS = [
    re.compile(r"example\.com", re.IGNORECASE),
    re.compile(r"YYYY-MM-DD", re.IGNORECASE),
    re.compile(r"127\.0\.0\.1"),
    re.compile(r"0\.0\.0\.0"),
    re.compile(r"метрики качества", re.IGNORECASE),
    re.compile(r"Open Graph", re.IGNORECASE),
]

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
PUBLIC_PRIVATE_KEYS_TOPIC_PATTERN = re.compile(r"\bprivate[-\s]+keys\b", re.IGNORECASE)
PRIVATE_KEY_ASSIGNMENT_PATTERN = re.compile(r"(?i)private[_-]?key\s*[:=]")
PUBLIC_SECURITY_TERMS_PATTERN = re.compile(
    r"\b(cookies?|credentials?|tokens?|sessions?|oauth|bearer|device bound|bound session)\b",
    re.IGNORECASE,
)
PUBLIC_SECURITY_CONTEXT_PATTERN = re.compile(
    r"\b(security|chrome|android|google security|protecting|mitigating|credentialless|authentication)\b",
    re.IGNORECASE,
)
PUBLIC_SECURITY_REPORT_CONTEXT_PATTERN = re.compile(
    r"\b(google security blog|public google security|matched title|public article title|privacy false positive)\b",
    re.IGNORECASE,
)
TITLE_LIKE_LINE_PATTERN = re.compile(
    r'(?i)(["\'](?:title|first_title)["\']\s*:|class=["\'](?:news-original|signal-original-title)["\']|<h[1-6]\b|<a\b|<title>|<meta\b)',
)
QUOTED_PUBLIC_SECURITY_TOPIC_PATTERN = re.compile(
    r"`[^`]*(?:cookies?|credentials?|tokens?|sessions?|oauth|bearer|device bound|bound session)[^`]*`",
    re.IGNORECASE,
)
SECRET_VALUE_CONTEXT_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|secret[_-]?key|client[_-]?secret|password|passwd|cookie|bearer)[\"']?\s*[:=]|authorization\s*:\s*bearer|set-cookie\s*:)"
)

REPO_SIGNAL_PATH_PATTERN = re.compile(
    r"(?:^|[\"'\s/])signals/\d{4}-\d{2}-\d{2}/[a-z0-9-]+/[a-f0-9]{16}-[^\"'\s]+\.md(?:[\"'\s,]|$)",
    re.IGNORECASE,
)
GENERATED_ITEM_KEY_PATTERN = re.compile(r'^\s*"item_key"\s*:\s*"[a-f0-9]{16}"\s*,?\s*$', re.IGNORECASE)


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


def is_public_private_keys_topic(line: str) -> bool:
    """Allow public coverage of private-key security incidents, not secrets.

    The scanner must block real private_key assignments and PEM private key
    blocks, but public article titles and URLs often contain the plural phrase
    "private keys" as a security topic.
    """
    if PRIVATE_KEY_ASSIGNMENT_PATTERN.search(line):
        return False
    return bool(PUBLIC_PRIVATE_KEYS_TOPIC_PATTERN.search(line))


def is_public_security_title_topic(line: str) -> bool:
    """Allow public security article titles without allowing secret values.

    Generated ranking JSON and Today pages can include titles like "Protecting
    Cookies with Device Bound Session Credentials". Those words are security
    terminology in a public-source headline, not a leaked credential. Real
    assignments, headers and secret-like key/value lines remain hard blockers.
    """
    if SECRET_VALUE_CONTEXT_PATTERN.search(line):
        return False
    if TITLE_LIKE_LINE_PATTERN.search(line):
        return bool(PUBLIC_SECURITY_TERMS_PATTERN.search(line) and PUBLIC_SECURITY_CONTEXT_PATTERN.search(line))
    if QUOTED_PUBLIC_SECURITY_TOPIC_PATTERN.search(line):
        return bool(PUBLIC_SECURITY_CONTEXT_PATTERN.search(line))
    return bool(PUBLIC_SECURITY_TERMS_PATTERN.search(line) and PUBLIC_SECURITY_REPORT_CONTEXT_PATTERN.search(line))


def should_skip_hard_pattern(path: Path, name: str, line: str) -> bool:
    """Avoid known generated-report false positives while keeping hard checks strict."""
    rel = path.relative_to(ROOT).as_posix()
    if name == "phone_like" and rel.startswith("validation/") and REPO_SIGNAL_PATH_PATTERN.search(line):
        return True
    if name == "phone_like" and (rel.startswith("validation/") or rel.startswith("site/")) and GENERATED_ITEM_KEY_PATTERN.search(line):
        return True
    if name == "possible_secret_keyword" and is_public_private_keys_topic(line):
        return True
    if name == "possible_secret_keyword" and is_public_security_title_topic(line):
        return True
    return False


def hard_scan_line(name: str, line: str) -> str:
    """Return the string to scan for a hard pattern.

    URL path fragments can contain long digit groups that look like phone numbers.
    Keep phone detection strict for visible text while removing URLs before the
    phone-like check. Other hard blockers still scan the original line.
    """
    if name == "phone_like":
        return URL_PATTERN.sub("", line)
    return line


def format_finding(path: Path, line_no: int, name: str, line: str) -> str:
    return f"{path.relative_to(ROOT)}:{line_no}: {name}: {line.strip()[:220]}"


def scan_file(path: Path) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return blockers, warnings
    for line_no, line in enumerate(text.splitlines(), start=1):
        if is_allowlisted(line):
            continue
        for name, pattern in HARD_PATTERNS:
            if should_skip_hard_pattern(path, name, line):
                continue
            if pattern.search(hard_scan_line(name, line)):
                blockers.append(format_finding(path, line_no, name, line))
        for name, pattern in SOFT_PATTERNS:
            if pattern.search(line):
                warnings.append(format_finding(path, line_no, name, line))
    return blockers, warnings


def main() -> int:
    blockers: list[str] = []
    warnings: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and should_scan(path):
            file_blockers, file_warnings = scan_file(path)
            blockers.extend(file_blockers)
            warnings.extend(file_warnings)

    if blockers:
        print("Privacy scan failed. Hard blockers:")
        for finding in blockers:
            print(f"- {finding}")
        if warnings:
            print("\nPrivacy scan warnings also found:")
            for finding in warnings:
                print(f"- {finding}")
        return 1

    if warnings:
        print("Privacy scan passed with warnings. Review when editing content:")
        for finding in warnings:
            print(f"- {finding}")
        return 0

    print("Privacy scan passed. No blockers or warnings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
