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


def enrich_html(text: str, registry: dict[str, dict[str, str]], prefix: str) -> str:
    for url, item in registry.items():
        preview = item.get("preview", "")
        if not preview:
            continue
        if url not in text:
            continue
        if preview in text:
            continue
        escaped_url = html.escape(url)
        escaped_preview = html.escape(prefix + preview)
        title = html.escape(item.get("title", "Материал"))
        image_html = f'<a class="reader-preview-link" href="{escaped_url}"><img class="reader-thumb" src="{escaped_preview}" alt="{title}" loading="lazy"></a>'
        pattern = f'(<article class="source-card media-card">)(<p class="label">[^<]*</p><h3><a href="{re.escape(escaped_url)}")'
        replacement = r"\1" + image_html + r"\2"
        text = re.sub(pattern, replacement, text)
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
