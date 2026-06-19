#!/usr/bin/env python3
"""Validate that draft dispatches are not exposed by render output.

This is a preflight guard for Daily Radar and render changes. It does not modify
site output. It fails when a draft dispatch has a matching generated HTML page.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = SITE_DIR / "dispatches"


def parse_front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    meta: dict[str, Any] = {}
    list_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            meta.setdefault(list_key, [])
            if isinstance(meta[list_key], list):
                meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value:
            list_key = None
            meta[key] = value
        else:
            list_key = key
            meta[key] = []
    return meta


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def main() -> int:
    leaked: list[str] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta = parse_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) == "published":
            continue
        page = OUTPUT_DIR / f"{slugify(path)}.html"
        if page.exists():
            leaked.append(f"{path.relative_to(ROOT)} -> {page.relative_to(ROOT)}")

    if leaked:
        print("Draft dispatch render exposure detected:")
        for item in leaked:
            print(f"- {item}")
        return 1

    print("Render visibility validation passed: no draft dispatch pages found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
