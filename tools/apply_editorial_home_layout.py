#!/usr/bin/env python3
"""Remove legacy homepage blocks after static rendering.

The homepage layout itself lives in tools/render_site.py. This postprocessor is
kept only as a cleanup guard for older generated fragments.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
STATUS_START = "<!-- site-status:start -->"
STATUS_END = "<!-- site-status:end -->"

LEGACY_HOME_BLOCK_RE = re.compile(
    r'\s*<section class="(?:editorial-home-topline|editorial-home-hero|editorial-home-lanes|panel reader-home-intro)"[^>]*>.*?</section>',
    re.S,
)


def remove_status_block(text: str) -> str:
    start = text.find(STATUS_START)
    end = text.find(STATUS_END)
    if start == -1 or end == -1 or end < start:
        return text
    return text[:start] + text[end + len(STATUS_END) :]


def apply_homepage() -> bool:
    path = SITE_DIR / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    new_text = remove_status_block(text)
    new_text = LEGACY_HOME_BLOCK_RE.sub("", new_text)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    changed = apply_homepage()
    print(f"Applied editorial home cleanup: {'yes' if changed else 'no changes'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
