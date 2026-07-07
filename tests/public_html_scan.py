#!/usr/bin/env python3
"""Shared public HTML leak checks for reader-facing pages."""

from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN_PUBLIC_TERMS = [
    "UTC",
    "Источник описывает тему",
    "Подробности и формулировки сохранены",
    "score=",
    "selected",
    "reader_safe",
    "source_rule_status",
    "item_key",
    "feed_id",
    "final_score",
    "selection_score",
    "validation",
    "threshold",
    "coverage",
    "PUBLIC-SAFE EDITORIAL BRIEFING SYSTEM",
    "Editorial model",
    "Publication boundary",
]

FORBIDDEN_PUBLIC_PATTERNS = [
    r"\b20\d{2}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\b",
    r"\b\d{1,2}:\d{2}:\d{2}\b",
    r"Источник сообщает:\s*.*\s+—\s+",
]


def assert_public_html_clean(html: str) -> None:
    lower = html.lower()
    for term in FORBIDDEN_PUBLIC_TERMS:
        assert term.lower() not in lower
    for pattern in FORBIDDEN_PUBLIC_PATTERNS:
        assert not re.search(pattern, html)


def public_page_paths(site_dir: Path) -> list[Path]:
    news_dir = site_dir / "news"
    paths = [
        site_dir / "index.html",
        news_dir / "index.html",
        site_dir / "today.html",
    ]
    sources_index = site_dir / "sources" / "index.html"
    if sources_index.exists():
        paths.append(sources_index)
    if news_dir.exists():
        paths.extend(sorted(path for path in news_dir.glob("*.html") if path.name != "index.html"))
    return paths


def assert_public_pages_clean(site_dir: Path) -> None:
    for path in public_page_paths(site_dir):
        assert path.exists(), path
        assert_public_html_clean(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    site_dir = Path(args[0]) if args else Path("site")
    assert_public_pages_clean(site_dir)
    print(f"Public HTML scan passed for {len(public_page_paths(site_dir))} page(s) in {site_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
