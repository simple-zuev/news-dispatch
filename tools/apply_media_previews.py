#!/usr/bin/env python3
"""Apply media previews from media/registry.json to generated HTML cards."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REGISTRY_PATH = ROOT / "media" / "registry.json"

MEDIA_CARD_RE = re.compile(
    r'(<article class="(?=[^"]*\bsource-card\b)(?=[^"]*\bmedia-card\b)[^"]*">)(.*?</article>)',
    re.S,
)


def load_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY_PATH.exists():
        return {}
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    items = data.get("items", [])
    registry: dict[str, dict[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        preview = str(item.get("preview", "")).strip()
        if url and preview:
            registry[url] = {key: str(value) for key, value in item.items() if value is not None}
    return registry


def prefix_for(page: Path) -> str:
    rel = page.relative_to(SITE_DIR).as_posix()
    if rel.startswith("dispatches/") or rel.startswith("streams/"):
        return "../"
    return ""


def resolve_preview_path(preview: str, prefix: str) -> str:
    if preview.startswith(("http://", "https://", "/", "../")):
        return preview
    return prefix + preview.lstrip("/")


def preview_html(url: str, item: dict[str, str], prefix: str) -> str:
    preview = resolve_preview_path(item.get("preview", ""), prefix)
    title = item.get("title", "Материал")
    return (
        f'<a class="reader-preview-link" href="{html.escape(url, quote=True)}">'
        f'<img class="reader-thumb" src="{html.escape(preview, quote=True)}" '
        f'alt="{html.escape(title, quote=True)}" loading="lazy"></a>'
    )


def insert_preview_in_media_cards(text: str, url: str, item: dict[str, str], prefix: str) -> str:
    escaped_url = html.escape(url, quote=True)
    if escaped_url not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        opening, body = match.groups()
        article = match.group(0)
        if escaped_url not in article or "reader-thumb" in article:
            return article
        return opening + preview_html(url, item, prefix) + body

    return MEDIA_CARD_RE.sub(replace, text)


def enrich_html(text: str, registry: dict[str, dict[str, str]], prefix: str) -> str:
    for url, item in registry.items():
        text = insert_preview_in_media_cards(text, url, item, prefix)
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
