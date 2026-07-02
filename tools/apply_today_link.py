#!/usr/bin/env python3
"""Add Today Radar link to the generated home page."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "site" / "index.html"


def main() -> int:
    if not HOME.exists():
        return 0
    text = HOME.read_text(encoding="utf-8")
    if 'href="today.html"' in text:
        return 0
    text = text.replace('<p class="hero-actions">', '<p class="hero-actions"><a href="today.html">Главное за сегодня</a>', 1)
    HOME.write_text(text, encoding="utf-8")
    print("Applied Today Radar link.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
