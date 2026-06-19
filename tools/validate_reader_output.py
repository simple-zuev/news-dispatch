#!/usr/bin/env python3
"""Validate generated reader/dashboard HTML after post-processing."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
SITE_DIR = ROOT / "site"
REGISTRY_PATHS = [
    ROOT / "media" / "registry.json",
    ROOT / "media" / "registry.generated.json",
]

SECTIONS = {
    "Лид": ("reader-section-lede", "lede"),
    "Главное": ("reader-section-main", "main"),
    "Что произошло": ("reader-section-facts", "facts"),
    "Почему это важно": ("reader-section-why", "why"),
    "Анализ": ("reader-section-analysis", "analysis"),
    "Слухи и мнения": ("reader-section-rumors", "rumors"),
    "Мнение людей": ("reader-section-people", "people"),
    "Медиа и материалы": ("reader-section-media", "media"),
    "Источники": ("reader-section-sources", "sources"),
    "Что наблюдать дальше": ("reader-section-watch", "watch"),
    "Итог": ("reader-section-summary", "summary"),
}


def front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, object] = {}
    list_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            assert isinstance(meta[list_key], list)
            meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip().strip('"')
        if value:
            list_key = None
            meta[key] = value
        else:
            list_key = key
            meta[key] = []
    return meta, text[end + 5 :]


def list_value(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value else []


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def published() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, body = front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) != "published":
            continue
        items.append(
            {
                "source": path,
                "page": SITE_DIR / "dispatches" / f"{slugify(path)}.html",
                "body": body,
                "media": list_value(meta, "media"),
            }
        )
    return items


def registry_preview_urls() -> set[str]:
    urls: set[str] = set()
    for path in REGISTRY_PATHS:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            has_media = item.get("preview") or item.get("image_url") or item.get("video_url") or item.get("embed_url")
            if url and has_media:
                urls.add(url)
    return urls


def body_html(text: str) -> str:
    marker = '<main class="article-body">'
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    end = text.find("</main>", start)
    return text[start:] if end == -1 else text[start:end]


def markdown_h2(body: str) -> list[str]:
    return [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]


def media_card(text: str, url: str) -> str:
    escaped = html.escape(url, quote=True)
    pattern = re.compile(
        r'<article class="(?=[^"]*\bsource-card\b)(?=[^"]*\bmedia-card\b)[^"]*">.*?</article>',
        re.S,
    )
    for match in pattern.finditer(text):
        if escaped in match.group(0):
            return match.group(0)
    return ""


def has_rendered_media(card: str) -> bool:
    return any(token in card for token in ("reader-thumb", "reader-video", "reader-video-frame"))


def validate(item: dict[str, object], previews: set[str]) -> list[str]:
    page = Path(item["page"])
    source = Path(item["source"])
    if not page.exists():
        return [f"{source}: generated HTML page is missing"]

    text = page.read_text(encoding="utf-8")
    body = body_html(text)
    errors: list[str] = []
    if not body:
        errors.append(f"{page}: missing article-body")
    if 'class="reader-map"' not in text:
        errors.append(f"{page}: missing reader map")
    if "<h1>" in body:
        errors.append(f"{page}: duplicate body h1 was not removed")

    titles = markdown_h2(str(item["body"]))
    known = [title for title in titles if title in SECTIONS]
    if not known:
        errors.append(f"{source}: no known reader sections")
    for title in known:
        css_class, slug = SECTIONS[title]
        if f"reader-section-block {css_class}" not in text:
            errors.append(f"{page}: missing section wrapper for {title!r}")
        if f'<h2 id="{slug}">{html.escape(title)}</h2>' not in text:
            errors.append(f"{page}: missing anchor for {title!r}")

    if "Главное" in titles:
        match = re.search(r'<section class="reader-section-block reader-section-main">.*?</section>', text, re.S)
        main_html = match.group(0) if match else ""
        if "<ol>" not in main_html or "<li>" not in main_html:
            errors.append(f"{page}: Главное is not a highlight list")

    for url in list(item["media"]):
        card = media_card(text, url)
        if not card:
            errors.append(f"{page}: missing media card for {url}")
        elif url in previews and not has_rendered_media(card):
            errors.append(f"{page}: missing rendered media preview inside media card for {url}")

    return errors


def main() -> int:
    items = published()
    if not items:
        print("No published dispatches to validate.")
        return 0
    previews = registry_preview_urls()
    errors: list[str] = []
    for item in items:
        errors.extend(validate(item, previews))
    if errors:
        print("Reader output validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validated reader output for {len(items)} published dispatch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
