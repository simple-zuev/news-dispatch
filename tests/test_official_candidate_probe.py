#!/usr/bin/env python3
"""Regression checks for candidate feed probe helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "probe_official_candidates.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("probe_official_candidates", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules["probe_official_candidates"] = module
spec.loader.exec_module(module)


def test_detects_rss_items() -> None:
    xml = b"""<?xml version='1.0'?><rss version='2.0'><channel><title>T</title><item><title>A</title></item><item><title>B</title></item></channel></rss>"""
    feed_type, item_count = module.detect_feed_type(xml)
    assert feed_type == "rss"
    assert item_count == 2


def test_detects_atom_entries() -> None:
    xml = b"""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'><title>T</title><entry><title>A</title></entry></feed>"""
    feed_type, item_count = module.detect_feed_type(xml)
    assert feed_type == "atom"
    assert item_count == 1


def test_build_report_counts_statuses() -> None:
    results = [
        module.ProbeResult("a", "finance", "official_source", "https://example.com/a.xml", "ok", 200, "application/rss+xml", "rss", 3, 10, ""),
        module.ProbeResult("b", "finance", "official_source", "", "skipped", None, "", "", 0, 0, "candidate_url is empty"),
        module.ProbeResult("c", "finance", "official_source", "https://example.com/c.xml", "failed", None, "", "", 0, 10, "error"),
    ]
    report = module.build_report(results)
    assert report["status"] == "pre-production candidate feed probe"
    assert report["total_candidates_with_url"] == 2
    assert report["ok"] == 1
    assert report["skipped"] == 1
    assert report["failed"] == 1


def main() -> int:
    test_detects_rss_items()
    test_detects_atom_entries()
    test_build_report_counts_statuses()
    print("official candidate probe tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
