#!/usr/bin/env python3
"""Regression checks for source discovery helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
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



def test_keyword_hits_match_russian_stems() -> None:
    text = "Сезон томатов начался на московских ярмарках. Движение ограничено на улицах города."
    hits = discover.keyword_hits("moscow-city", text)
    assert "москов" in hits
    assert "улиц" in hits




def test_keyword_hits_ignore_weak_moscow_false_positives() -> None:
    text = "Клубничный оттенок Луны и Музей Мирового океана попали в федеральную повестку."
    hits = discover.keyword_hits("moscow-city", text)
    assert "клуб" not in hits
    assert "музей" not in hits
    assert hits == []


def test_sample_match_stats_measure_feed_density() -> None:
    titles = [
        "Один человек погиб при аварийной посадке самолета",
        "Москва открыла новый участок метро",
        "Движение ограничено на улицах города",
        "МИД Турции сделал заявление",
    ]
    stats = discover.sample_match_stats("moscow-city", titles)
    assert stats["sample_size"] == 4
    assert stats["sample_match_count"] == 2
    assert stats["sample_match_ratio"] == 0.5
    assert len(stats["matched_sample_titles"]) == 2



def test_deny_term_hits_are_reported() -> None:
    hits = discover.deny_term_hits("crypto-finance", "Bitcoin giveaway and casino promotion")
    assert "giveaway" in hits
    assert "casino" in hits


def test_load_search_results_accepts_top_level_list() -> None:
    payload = [
        {
            "title": "AI source",
            "url": "https://example.com/ai",
            "snippet": "LLM agents developer tools",
        }
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "search-results.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        results = discover.load_search_results(path, default_stream="ai")
    assert len(results) == 1
    assert results[0].stream == "ai"
    assert results[0].url == "https://example.com/ai"


def test_discovery_rules_cover_primary_streams() -> None:
    data = discover.load_discovery_rules(ROOT / "sources" / "discovery-rules.json")
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
        assert isinstance(streams[slug]["strong_terms"], list)
        assert isinstance(streams[slug]["weak_terms"], list)
        assert isinstance(streams[slug]["deny_terms"], list)
        assert streams[slug]["min_sample_ratio"] > 0


def test_candidate_scoring_passes_valid_feed_probe() -> None:
    probe = {
        "ok": True,
        "feed_type": "rss",
        "item_count": 12,
        "first_title": "Один человек погиб при аварийной посадке самолета",
        "sample_titles": [
            "Один человек погиб при аварийной посадке самолета",
            "Москва открыла новый участок метро",
            "Движение временно закрыто на ряде улиц в центре Москвы",
            "Сезон томатов начался на московских ярмарках",
        ],
        "error": "",
    }
    result = discover.score_candidate("moscow-city", "https://example.com/rss.xml", probe)
    assert result["candidate_status"] == "passed_probe"
    assert result["score"] > 0.55
    assert result["sample_match_count"] >= 2
    assert result["sample_match_ratio"] > 0
    assert result["min_sample_ratio"] == 0.2
    assert result["deny_term_hits"] == []
    assert "москов" in result["keyword_hits"] or "москв" in result["keyword_hits"]


def test_candidate_scoring_rejects_failed_probe() -> None:
    probe = {
        "ok": False,
        "item_count": 0,
        "error": "http_error: 404",
    }
    result = discover.score_candidate("moscow-city", "https://example.com/rss.xml", probe)
    assert result["candidate_status"] == "failed_probe"
    assert result["score"] == 0.0
    assert result["sample_match_ratio"] == 0.0


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
    test_keyword_hits_match_russian_stems()
    test_keyword_hits_ignore_weak_moscow_false_positives()
    test_sample_match_stats_measure_feed_density()
    test_deny_term_hits_are_reported()
    test_load_search_results_accepts_top_level_list()
    test_discovery_rules_cover_primary_streams()
    test_candidate_scoring_passes_valid_feed_probe()
    test_candidate_scoring_rejects_failed_probe()
    test_discovery_queries_cover_primary_streams()
    print("source discovery tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
