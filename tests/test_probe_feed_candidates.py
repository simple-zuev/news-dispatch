#!/usr/bin/env python3
"""Regression checks for feed candidate probing."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "probe_feed_candidates.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("probe_feed_candidates", MODULE_PATH)
assert spec is not None and spec.loader is not None
probe_feed_candidates = importlib.util.module_from_spec(spec)
sys.modules["probe_feed_candidates"] = probe_feed_candidates
spec.loader.exec_module(probe_feed_candidates)


def test_parse_rss_feed() -> None:
    xml = """<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title><item><title>First item</title></item><item><title>Second item</title></item></channel></rss>"""
    result = probe_feed_candidates.parse_feed_xml(xml, url="https://example.com/rss")
    assert result.ok
    assert result.feed_type == "rss"
    assert result.item_count == 2
    assert result.first_title == "First item"
    assert result.sample_titles == ["First item", "Second item"]


def test_parse_atom_feed() -> None:
    xml = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title><entry><title>Atom item</title></entry></feed>"""
    result = probe_feed_candidates.parse_feed_xml(xml, url="https://example.com/atom")
    assert result.ok
    assert result.feed_type == "atom"
    assert result.item_count == 1
    assert result.first_title == "Atom item"
    assert result.sample_titles == ["Atom item"]


def test_load_moscow_candidates() -> None:
    rows = probe_feed_candidates.load_candidates(ROOT / "sources" / "feed-candidates.json", "moscow-city")
    assert len(rows) >= 2
    assert all(row["stream"] == "moscow-city" for row in rows)
    statuses = {row["id"]: row["status"] for row in rows}
    assert statuses["m24-news-candidate"] == "promoted-to-live-source"
    assert statuses["mskagency-candidate"] == "rejected-404"
    assert statuses["interfax-moscow-candidate"] == "held-too-broad"


def main() -> int:
    test_parse_rss_feed()
    test_parse_atom_feed()
    test_load_moscow_candidates()
    print("feed candidate probe tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
