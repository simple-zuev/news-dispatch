#!/usr/bin/env python3
"""Regression checks for generated reader empty states."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "apply_empty_states.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("apply_empty_states", MODULE_PATH)
assert spec is not None and spec.loader is not None
apply_empty_states = importlib.util.module_from_spec(spec)
sys.modules["apply_empty_states"] = apply_empty_states
spec.loader.exec_module(apply_empty_states)


def test_grid_placeholder_is_inserted() -> None:
    path = apply_empty_states.SITE_DIR / "index.html"
    source = '<section class="grid" aria-label="Latest dispatches"></section>'
    rendered = apply_empty_states.fill_empty_grids(path, source)
    assert "empty-state" in rendered
    assert "Нет данных" in rendered
    assert "promotion review" not in rendered
    assert "reader-facing" not in rendered
    assert "live-сигнал" not in rendered


def test_grid_with_content_is_preserved() -> None:
    path = apply_empty_states.SITE_DIR / "index.html"
    source = '<section class="grid" aria-label="Latest dispatches"><article>x</article></section>'
    assert apply_empty_states.fill_empty_grids(path, source) == source


def test_loose_live_empty_copy_is_reader_friendly() -> None:
    rendered = apply_empty_states.replace_loose_empty_paragraphs("<p>В этом потоке сейчас нет live-сигналов.</p>")
    assert "Сегодня новых материалов по теме нет." in rendered
    assert "Daily Radar" not in rendered
    assert "live-сигнал" not in rendered


def main() -> int:
    test_grid_placeholder_is_inserted()
    test_grid_with_content_is_preserved()
    test_loose_live_empty_copy_is_reader_friendly()
    print("empty-state tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
