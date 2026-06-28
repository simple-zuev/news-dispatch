#!/usr/bin/env python3
"""Regression checks for source discovery helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "discover_source_candidates.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("discover_source_candidates", MODULE_PATH)
assert spec is not None and spec.loader is not None
discover = importlib.util.module_from_spec(spec)
sys.modules["discover_source_candidates"] = discover
spec.loader.exec_module(discover)


def test_autodiscovered_feed_urls_from_html() -> None:
    html = """
    <html><head>
      <link rel="alternate" type="application/rss+xml" title="RSS" href="/rss.xml">
      <link rel="alternate" type="application/atom+xml" title="Atom" href="https://example.com/atom.xml">
    </head></html>
    """
    urls = discover.autodiscovered_feed_urls("https://example.com/news", html)
    assert urls == ["https://example.com/rss.xml", "https://example.com/atom.xml"]


def test_common_feed_candidates_are_origin_scoped() -> None:
    urls = discover.common_feed_candidates("https://example.com/news/page")
    assert "https://example.com/feed" in urls
    assert "https://example.com/rss.xml" in urls
    assert all(url.startswith("https://example.com/") for url in urls)


def test_candidate_scoring_passes_valid_feed_probe() -> None:
    probe = {
        "ok": True,
        "feed_type": "rss",
        "item_count": 12,
        "first_title": "Москва открыла новый участок метро",
        "error": "",
    }
    result = discover.score_candidate("moscow-city", "https://example.com/rss.xml", probe)
    assert result["candidate_status"] == "passed_probe"
    assert result["score"] > 0.55
    assert "москва" in result["keyword_hits"]


def test_candidate_scoring_rejects_failed_probe() -> None:
    probe = {
        "ok": False,
        "item_count": 0,
        "error": "http_error: 404",
    }
    result = discover.score_candidate("moscow-city", "https://example.com/rss.xml", probe)
    assert result["candidate_status"] == "failed_probe"
    assert result["score"] == 0.0


def test_discovery_queries_cover_primary_streams() -> None:
    data = discover.load_discovery_queries(ROOT / "sources" / "discovery-queries.json")
    streams = data["streams"]
    for slug in [
        "finance",
        "crypto-finance",
        "ai",
        "tech-hardware-software",
        "gear-style-edc",
        "moscow-city",
        "dj-audio-creative",
        "science-discovery",
    ]:
        assert slug in streams
        assert streams[slug]["queries"]


def main() -> int:
    test_autodiscovered_feed_urls_from_html()
    test_common_feed_candidates_are_origin_scoped()
    test_candidate_scoring_passes_valid_feed_probe()
    test_candidate_scoring_rejects_failed_probe()
    test_discovery_queries_cover_primary_streams()
    print("source discovery tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
