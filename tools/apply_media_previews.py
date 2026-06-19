#!/usr/bin/env python3
"""Apply media previews from manual and generated media registries."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REGISTRY_PATHS = [
    ROOT / "media" / "registry.json",
    ROOT / "media" / "registry.generated.json",
]

MEDIA_CARD_RE = re.compile(
    r'(<article class="(?=[^"]*\bsource-card\b)(?=[^"]*\bmedia-card\b)[^"]*">)(.*?</article>)',
    re.S,
)


def registry_items(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    cleaned: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        cleaned.append({key: str(value) for key, value in item.items() if value is not None})
    return cleaned


def load_registry() -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for path in REGISTRY_PATHS:
        for item in registry_items(path):
            url = item["url"]
            previous = registry.get(url, {})
            merged = dict(previous)
            for key, value in item.items():
                if value:
                    merged[key] = value
            if merged.get("preview") or merged.get("image_url"):
                registry[url] = merged
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


def preview_source(item: dict[str, str]) -> str:
    image_source = item.get("image_source") or item.get("site_name") or item.get("type") or "источник"
    metadata_source = item.get("metadata_source")
    if metadata_source == "open_graph" and item.get("image_url"):
        return f"Изображение: {image_source} · Open Graph"
    return f"Изображение: {image_source}"


def preview_html(url: str, item: dict[str, str], prefix: str) -> str:
    external = item.get("image_url", "").strip()
    fallback = item.get("preview", "").strip()
    preview = external or resolve_preview_path(fallback, prefix)
    title = item.get("external_title") or item.get("title") or "Материал"
    attribution = preview_source(item)
    return (
        f'<a class="reader-preview-link" href="{html.escape(url, quote=True)}">'
        f'<img class="reader-thumb" src="{html.escape(preview, quote=True)}" '
        f'alt="{html.escape(title, quote=True)}" loading="lazy" referrerpolicy="no-referrer"></a>'
        f'<p class="reader-preview-credit">{html.escape(attribution)}</p>'
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
