#!/usr/bin/env python3
"""Validate reader-facing published dispatches.

This is a guardrail, not a full fact-checker.
It blocks common publication failures:
- published content without sources;
- mismatched source/media front-matter lists;
- private/internal phrasing;
- raw URL dumps in article body;
- English headings in Russian articles;
- obvious advertising language;
- rumors mixed into articles without the required section;
- pre-publication radar/candidate artifacts leaked into published dispatches.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"

INTERNAL_PATTERNS = [
    r"(?i)our product",
    r"(?i)our company",
    r"(?i)our team",
    r"(?i)internal roadmap",
    r"(?i)internal metric",
    r"(?i)private vendor",
    r"(?i)customer data",
    r"наш продукт",
    r"наша компания",
    r"наша команда",
    r"внутренн(ий|яя|ие)",
    r"дорожная карта",
    r"клиентские данные",
]

AD_PATTERNS = [
    r"лучший выбор",
    r"обязательно брать",
    r"топ за свои деньги",
    r"идеальный вариант",
    r"must-have",
    r"безальтернативно",
    r"точно стоит купить",
    r"всем подходит",
]

TECHNICAL_PUBLIC_PATTERNS = [
    r"public-safe",
    r"source_mode",
    r"review_level",
    r"front matter",
    r"publication_scope",
    r"private_context_used",
]

PREPUBLICATION_PATTERNS = [
    r"pre-publication",
    r"candidate dispatch",
    r"reviewed radar",
    r"not a published dispatch",
    r"daily radar signals",
    r"source-reported RSS/Atom appearance",
    r"needs grouping, context check and impact assessment",
]

REQUIRED_SECTIONS = [
    "## Лид",
    "## Главное",
    "## Что произошло",
    "## Почему это важно",
    "## Анализ",
    "## Медиа и материалы",
    "## Источники",
    "## Что наблюдать дальше",
    "## Итог",
]

URL_RE = re.compile(r"https?://\S+")
EN_HEADING_RE = re.compile(r"^#{1,3}\s+[A-Za-z][A-Za-z0-9 ,:;/'\-–—]+$", re.MULTILINE)


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, object] = {}
    list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            meta.setdefault(list_key, [])
            assert isinstance(meta[list_key], list)
            meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value == "":
            list_key = key
            meta[key] = []
        else:
            list_key = None
            meta[key] = value
    return meta, body


def list_value(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def is_published(meta: dict[str, object]) -> bool:
    return meta.get("status") == "published"


def require_parallel_lengths(rel: Path, errors: list[str], anchor_key: str, related_keys: list[str], meta: dict[str, object], allow_empty: bool) -> None:
    anchor = list_value(meta, anchor_key)
    if not anchor and not allow_empty:
        errors.append(f"{rel}: published dispatch requires {anchor_key}")
        return
    if not anchor:
        return
    for key in related_keys:
        values = list_value(meta, key)
        if len(values) != len(anchor):
            errors.append(f"{rel}: {key} length must match {anchor_key} length ({len(values)} != {len(anchor)})")


def validate_published(path: Path, meta: dict[str, object], body: str) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(ROOT)

    if meta.get("public_safe") != "true":
        errors.append(f"{rel}: public_safe must be true")
    if meta.get("publication_scope") != "public":
        errors.append(f"{rel}: publication_scope must be public")
    if meta.get("private_context_used") != "false":
        errors.append(f"{rel}: private_context_used must be false")
    if meta.get("contains_personal_data") != "false":
        errors.append(f"{rel}: contains_personal_data must be false")
    if meta.get("contains_internal_company_data") != "false":
        errors.append(f"{rel}: contains_internal_company_data must be false")
    if meta.get("contains_confidential_strategy") != "false":
        errors.append(f"{rel}: contains_confidential_strategy must be false")
    if meta.get("contains_nonpublic_sources") != "false":
        errors.append(f"{rel}: contains_nonpublic_sources must be false")
    if meta.get("contains_investment_advice") != "false":
        errors.append(f"{rel}: contains_investment_advice must be false")
    if meta.get("contains_legal_advice") != "false":
        errors.append(f"{rel}: contains_legal_advice must be false")

    summary = str(meta.get("summary", "")).strip()
    if len(summary) < 40:
        errors.append(f"{rel}: summary is too short or missing")

    require_parallel_lengths(
        rel,
        errors,
        "sources",
        ["source_titles", "source_types", "source_notes"],
        meta,
        allow_empty=False,
    )
    require_parallel_lengths(
        rel,
        errors,
        "media",
        ["media_titles", "media_types", "media_notes"],
        meta,
        allow_empty=True,
    )

    for section in REQUIRED_SECTIONS:
        if section not in body:
            errors.append(f"{rel}: missing section {section}")

    # Raw URL in article body is allowed only inside explicit source/media sections.
    body_without_allowed_sections = body.split("## Источники")[0].split("## Медиа и материалы")[0]
    if URL_RE.search(body_without_allowed_sections):
        errors.append(f"{rel}: raw URL found in reader body before source/media sections")

    if str(meta.get("language", "")) == "ru" and EN_HEADING_RE.search(body):
        errors.append(f"{rel}: English heading found in Russian article")

    for pattern in INTERNAL_PATTERNS:
        if re.search(pattern, body):
            errors.append(f"{rel}: internal/private phrase matched: {pattern}")
    for pattern in AD_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            errors.append(f"{rel}: advertising phrase matched: {pattern}")
    for pattern in TECHNICAL_PUBLIC_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            errors.append(f"{rel}: technical/publication phrase leaked into body: {pattern}")
    for pattern in PREPUBLICATION_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            errors.append(f"{rel}: pre-publication artifact phrase leaked into published body: {pattern}")

    rumor_words = ["слух", "инсайд", "утечк", "неподтверж"]
    has_rumor_language = any(word in body.lower() for word in rumor_words)
    if has_rumor_language and "## Слухи и мнения" not in body:
        errors.append(f"{rel}: rumor language requires section ## Слухи и мнения")

    if "## Мнение людей" not in body:
        errors.append(f"{rel}: missing section ## Мнение людей")

    return errors


def main() -> int:
    errors: list[str] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if is_published(meta):
            errors.extend(validate_published(path, meta, body))
    if errors:
        print("Published content validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Published content validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
