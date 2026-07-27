#!/usr/bin/env python3
"""Shared editorial contract for public analytical digests."""

from __future__ import annotations

import re
from typing import Any

from core import ensure_list

DIGEST_COLLECTION = "digests"
DIGEST_ISSUE_TYPES = {
    "weekly-digest": "Недельный дайджест",
    "market-structure-note": "Структура рынка",
    "infrastructure-radar": "Инфраструктурный радар",
    "special-issue": "Специальный выпуск",
}

REQUIRED_HEADINGS = {
    "Лид",
    "Главное",
    "Почему это важно",
    "Анализ",
    "Итог",
}
WATCH_HEADINGS = {"Что наблюдать дальше", "Что отслеживать дальше"}
GENERIC_TITLE_PATTERNS = (
    r"\bавтоматическ(?:ий|ая|ое)\b",
    r"\bdaily radar\b",
    r"\bобщий выпуск\b",
    r"\btaxonomy pilot\b",
)


def text_value(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    return "" if isinstance(value, list) else str(value or "").strip()


def digest_declared(metadata: dict[str, Any]) -> bool:
    return text_value(metadata, "reader_collection") == DIGEST_COLLECTION


def digest_issue_title(metadata: dict[str, Any]) -> str:
    issue_type = text_value(metadata, "issue_type")
    return DIGEST_ISSUE_TYPES.get(issue_type, issue_type)


def body_headings(body: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)
    }


def digest_quality_findings(metadata: dict[str, Any], body: str) -> list[str]:
    collection = text_value(metadata, "reader_collection")
    if not collection:
        return []
    if collection != DIGEST_COLLECTION:
        return [f"unknown reader_collection {collection!r}"]

    findings: list[str] = []
    if text_value(metadata, "status") != "published":
        findings.append("digest must have status published")
    if metadata.get("public_safe") is not True:
        findings.append("digest must be public_safe")

    issue_type = text_value(metadata, "issue_type")
    if issue_type not in DIGEST_ISSUE_TYPES:
        findings.append(f"digest issue_type must be one of: {', '.join(sorted(DIGEST_ISSUE_TYPES))}")

    editorial_review = text_value(metadata, "editorial_review").lower()
    if not editorial_review or editorial_review.startswith("automated"):
        findings.append("digest requires a non-automated editorial_review")

    title = text_value(metadata, "title")
    if any(re.search(pattern, title, flags=re.IGNORECASE) for pattern in GENERIC_TITLE_PATTERNS):
        findings.append("digest title must state a specific analytical subject")

    thesis = text_value(metadata, "digest_thesis")
    if len(thesis) < 80:
        findings.append("digest_thesis must provide a specific analytical conclusion")

    reader_value = text_value(metadata, "reader_value")
    if len(reader_value) < 80:
        findings.append("reader_value must explain what the reader gains")

    summary = text_value(metadata, "summary")
    if len(summary) < 80:
        findings.append("digest summary must be specific and reader-facing")

    sources = {source.strip() for source in ensure_list(metadata.get("sources")) if source.strip()}
    if len(sources) < 2:
        findings.append("digest requires at least two distinct public sources")

    headings = body_headings(body)
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        findings.append(f"digest body missing sections: {', '.join(missing_headings)}")
    if not (WATCH_HEADINGS & headings):
        findings.append("digest body missing a what-to-watch-next section")

    return findings


def is_public_digest(metadata: dict[str, Any], body: str) -> bool:
    return digest_declared(metadata) and not digest_quality_findings(metadata, body)
