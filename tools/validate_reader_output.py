#!/usr/bin/env python3
"""Validate generated reader/dashboard HTML after site post-processing."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
SITE_DIR = ROOT / "site"
MEDIA_REGISTRY = ROOT / "media" / "registry.json"

SECTION_CLASS = {
    "Лид": "reader-section-lede",
    "Главное": "reader-section-main",
    "Что произошло": "reader-section-facts",
    "Почему это важно": "reader-section-why",
    "Анализ": "reader-section-analysis",
    "Слухи и мнения": "reader-section-rumors",
    "Мнение людей": "reader-section-people",
    "Медиа и материалы": "reader-section-media",
    "Источники": "reader-section-sources",
    "Что наблюдать дальше": "reader-section-watch",
    "Итог": "reader-section-summary",
}


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


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def body_h2_titles(body: str) -> list[str]:
    return [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]


def published_dispatches() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) != "published":
            continue
        items.append(
            {
                "source_path": path,
                "output_path": SITE_DIR / "dispatches" / f"{slugify(path)}.html",
                "body": body,
                "media": list_value(meta, "media"),
            }
        )
    return items


def registry_previews() -> dict[str, str]:
    if not MEDIA_REGISTRY.exists():
        return {}
    data = json.loads(MEDIA_REGISTRY.read_text(encoding="utf-8"))
    previews: dict[str, str] = {}
    for item in data.get("items", []):
        if isinstance(item, dict) and item.get("url") and item.get("preview"):
            previews[str(item["url"])] = str(item["preview"])
    return previews


def media_card_for(text: str, url: str) -> str:
    escaped_url = html.escape(url, quote=True)
    pattern = re.compile(
        r'<article class="(?=[^"]*\bsource-card\b)(?=[^"]*\bmedia-card\b)[^"]*">.*?</article>',
        re.S,
    )
    for match in pattern.finditer(text):
        card = match.group(0)
        if escaped_url in card:
            return card
    return ""


def validate_dispatch(item: dict[str, object], previews: dict[str, str]) -> list[str]:
    errors: list[str] = []
    page = Path(item["output_path"])
    source = Path(item["source_path"])
    if not page.exists():
        return [f"{source}: generated page is missing: {page}"]
    text = page.read_text(encoding="utf-8")

    if '<main class="article-body">' not in text:
        errors.append(f"{page}: missing article-body main")
    if 'class="reader-map"' not in text:
        errors.append(f"{page}: missing reader map")
    if '<h1>' in text.split('<main class="article-body">', 1)[-1].split('</main>', 1)[0]:
        errors.append(f"{page}: body still contains duplicate h1")

    titles = body_h2_titles(str(item["body"]))
    section_titles = [title for title in titles if title in SECTION_CLASS]
    if not section_titles:
        errors.append(f"{source}: no known reader sections in body")
    for title in section_titles:
        css_class = SECTION_CLASS[title]
        if f'reader-section-block {css_class}' not in text:
            errors.append(f"{page}: missing reader section for {title!r}")
        anchor = re.sub(r"[^a-zа-я0-9-]+", "-", title.lower()).strip("-")
        del anchor  # Human-readable titles use explicit slugs in apply_reader_sections.py.

    if "Главное" in titles and '<section class="reader-section-block reader-section-main"><h2 id="main">Главное</h2><ol>' not in text:
        errors.append(f"{page}: Главное was not converted to a highlight list")

    for url in list(item["media"]):
        card = media_card_for(text, url)
        if not card:
            errors.append(f"{page}: missing media card for {url}")
            continue
        if url in previews and "reader-thumb" not in card:
            errors.append(f"{page}: missing preview image inside media card for {url}")

    return errors


def main() -> int:
    items = published_dispatches()
    if not items:
        print("No published dispatches to validate.")
        return 0
    previews = registry_previews()
    errors: list[str] = []
    for item in items:
        errors.extend(validate_dispatch(item, previews))
    if errors:
        print("Reader output validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validated reader output for {len(items)} published dispatch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
