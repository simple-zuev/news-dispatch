#!/usr/bin/env python3
"""Improve weak reader titles on generated HTML pages."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from reader_text import build_public_item, public_source_name, public_text, source_original_title

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
RANKING_REPORT = ROOT / "validation" / "daily-radar-ranking-latest.json"

GENERIC_TOPICS = {
    "регуляторика и надзор",
    "банки, ставки и ликвидность",
    "безопасность и технологическая инфраструктура",
    "модели и инфраструктура ии",
    "движение крипторынка",
}


def load_items(path: Path = RANKING_REPORT) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("items", []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def is_weak_source_topic(title: str, source: str) -> bool:
    prefix = f"{source}:"
    if not title.startswith(prefix):
        return False
    topic = compact(title[len(prefix) :])
    return topic in GENERIC_TOPICS


def title_map(items: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        rendered = build_public_item(item)["title"].strip()
        source = public_source_name(item)
        original = public_text(source_original_title(item)).strip()
        if rendered and original and original != rendered and is_weak_source_topic(rendered, source):
            out[rendered] = f"{source}: {original}"
    return out


def apply_map(site_dir: Path, mapping: dict[str, str]) -> int:
    changed = 0
    for path in site_dir.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in mapping.items():
            updated = updated.replace(html.escape(old), html.escape(new))
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def main() -> int:
    mapping = title_map(load_items())
    changed = apply_map(SITE_DIR, mapping)
    print(f"Reader title quality cleanup: {len(mapping)} title(s), {changed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
