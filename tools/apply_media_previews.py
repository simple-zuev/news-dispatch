#!/usr/bin/env python3
"""Apply media previews from media/registry.json to generated HTML cards."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REGISTRY_PATH = ROOT / "media" / "registry.json"


def load_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY_PATH.exists():
        return {}
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    items = data.get("items", [])
    registry: dict[str, dict[str, str]] = {}
    for item in items:
        if isinstance(item, dict) and item.get("url"):
            registry[str(item["url"])] = {key: str(value) for key, value in item.items() if value is not None}
    return registry


def prefix_for(page: Path) -> str:
    rel = page.relative_to(SITE_DIR).as_posix()
    if rel.startswith("dispatches/") or rel.startswith("streams/"):
        return "../"
    return ""


def preview_html(url: str, item: dict[str, str], prefix: str) -> str:
    preview = item.get("preview", "")
    title = item.get("title", "Материал")
    return (
        f'<a class="reader-preview-link" href="{html.escape(url)}">'
        f'<img class="reader-thumb" src="{html.escape(prefix + preview)}" '
        f'alt="{html.escape(title)}" loading="lazy"></a>'
    )


def insert_preview_before_media_link(text: str, url: str, item: dict[str, str], prefix: str) -> str:
    preview = item.get("preview", "")
    if not preview or url not in text or preview in text:
        return text
    escaped_url = html.escape(url)
    marker = f'<h3><a href="{escaped_url}"'
    position = text.find(marker)
    if position == -1:
        return text
    article_start = text.rfind('<article class="source-card media-card"', 0, position)
    article_end = text.find("</article>", position)
    if article_start == -1 or article_end == -1:
        return text
    article = text[article_start:article_end]
    if "reader-thumb" in article:
        return text
    return text[:article_start] + preview_html(url, item, prefix) + text[article_start:]


def enrich_html(text: str, registry: dict[str, dict[str, str]], prefix: str) -> str:
    for url, item in registry.items():
        text = insert_preview_before_media_link(text, url, item, prefix)
    return text


def main() -> int:
    registry = load_registry()
    if not registry:
        print("No media registry found.")
        return 0
    changed = 0
    for page in SITE_DIR.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new_text = enrich_html(text, registry, prefix_for(page))
        if new_text != text:
            page.write_text(new_text, encoding="utf-8")
            changed += 1
    print(f"Applied media previews to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
