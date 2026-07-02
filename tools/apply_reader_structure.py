#!/usr/bin/env python3
"""Keep generated reader pages free of legacy helper blocks."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"

HOME_MARKER = "reader-home-intro"
TOPIC_MARKER = "reader-topic-context"

LEGACY_BLOCK_RE = r'\s*<section class="panel (?:reader-home-intro|reader-topic-context)">.*?</section>'


def insert_after_main(text: str, block: str) -> str:
    if "<main>" not in text:
        return text
    return text.replace("<main>", "<main>\n" + block, 1)


def insert_after_status(text: str, block: str) -> str:
    marker = "<!-- site-status:end -->"
    if marker in text:
        return text.replace(marker, marker + "\n" + block, 1)
    return insert_after_main(text, block)


def process_homepage() -> bool:
    path = SITE_DIR / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(LEGACY_BLOCK_RE, "", text, flags=re.S)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def process_stream_pages() -> int:
    changed = 0
    for path in (SITE_DIR / "streams").glob("*.html"):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8")
        new_text = re.sub(LEGACY_BLOCK_RE, "", text, flags=re.S)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def main() -> int:
    changed = 0
    if process_homepage():
        changed += 1
    changed += process_stream_pages()
    print(f"Applied reader structure to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
