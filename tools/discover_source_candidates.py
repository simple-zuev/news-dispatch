#!/usr/bin/env python3
"""Discover and score candidate RSS/Atom sources before promotion to live config.

This tool is intentionally provider-agnostic. It can consume search-result JSON
from any web-search provider, or direct URLs supplied by an operator. It does not
write to sources/feeds.json and does not publish reader-facing conclusions.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from core import ROOT, VALIDATION_DIR, repo_path, write_json
from probe_feed_candidates import fetch_url
from stream_registry import stream_keywords, stream_slugs

DISCOVERY_QUERIES = ROOT / "sources" / "discovery-queries.json"
REPORT_PATH = VALIDATION_DIR / "source-discovery-latest.json"
USER_AGENT = "NewsDispatchSourceDiscovery/1.0 (+https://simple-zuev.github.io/news-dispatch/)"

FEED_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/rdf+xml",
    "application/feed+json",
}


@dataclass(frozen=True)
class SearchResult:
    stream: str
    title: str
    url: str
    snippet: str = ""


class FeedLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        row = {key.lower(): (value or "") for key, value in attrs}
        rel = row.get("rel", "").lower()
        link_type = row.get("type", "").lower()
        href = row.get("href", "").strip()
        if not href:
            return
        if "alternate" not in rel:
            return
        if link_type not in FEED_TYPES and "rss" not in link_type and "atom" not in link_type:
            return
        self.links.append(urllib.parse.urljoin(self.base_url, href))


def normalize_text(value: str) -> str:
    value = value.lower().replace("ё", "е")
    for char in "'’`—–_/|:;,.!?()[]{}\n\t":
        value = value.replace(char, " ")
    return " ".join(value.split())


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def autodiscovered_feed_urls(page_url: str, html: str) -> list[str]:
    parser = FeedLinkParser(page_url)
    parser.feed(html)
    return unique(parser.links)


def common_feed_candidates(page_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(page_url)
    if not parsed.scheme or not parsed.netloc:
        return []
    origin = f"{parsed.scheme}://{parsed.netloc}"
    paths = ["/feed", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml"]
    return [urllib.parse.urljoin(origin, path) for path in paths]


def candidate_feed_urls(page_url: str, html: str = "") -> list[str]:
    return unique([*autodiscovered_feed_urls(page_url, html), *common_feed_candidates(page_url)])


def fetch_page(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(1_500_000)
    return body.decode("utf-8", errors="replace")


def keyword_hits(stream: str, text: str) -> list[str]:
    normalized = normalize_text(text)
    haystack = f" {normalized} "
    tokens = normalized.split()
    hits = []
    for word in stream_keywords().get(stream, []):
        raw = str(word)
        phrase = normalize_text(raw)
        if not phrase:
            continue
        if " " in phrase:
            matched = f" {phrase} " in haystack
        elif len(phrase) >= 4:
            matched = any(token == phrase or token.startswith(phrase) for token in tokens)
        else:
            matched = f" {phrase} " in haystack
        if matched:
            hits.append(raw)
    return hits


def score_candidate(stream: str, feed_url: str, probe: dict[str, Any], title: str = "", snippet: str = "") -> dict[str, Any]:
    raw_sample_titles = probe.get("sample_titles", [])
    sample_titles = " ".join(str(item) for item in raw_sample_titles if str(item).strip()) if isinstance(raw_sample_titles, list) else ""
    hits = keyword_hits(stream, " ".join([feed_url, title, snippet, str(probe.get("first_title", "")), sample_titles]))
    item_count = int(probe.get("item_count") or 0)

    if not probe.get("ok"):
        return {
            "candidate_status": "failed_probe",
            "score": 0.0,
            "keyword_hits": hits,
            "reason": str(probe.get("error") or "probe_failed"),
        }

    if item_count < 2:
        return {
            "candidate_status": "low_item_count",
            "score": 0.25,
            "keyword_hits": hits,
            "reason": "feed parsed, but item_count is below promotion threshold",
        }

    score = 0.55
    score += min(item_count, 20) / 100
    score += min(len(hits), 5) * 0.06
    score = round(min(score, 1.0), 3)

    return {
        "candidate_status": "passed_probe",
        "score": score,
        "keyword_hits": hits,
        "reason": "feed parsed and has enough items; editorial/source-rule review still required",
    }


def load_discovery_queries(path: Path = DISCOVERY_QUERIES) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_search_results(path: Path, default_stream: str = "") -> list[SearchResult]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_results = data.get("results", data if isinstance(data, list) else [])
    results: list[SearchResult] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or raw.get("link") or "").strip()
        if not url:
            continue
        stream = str(raw.get("stream") or default_stream).strip()
        if stream not in stream_slugs():
            stream = default_stream
        if not stream:
            continue
        results.append(SearchResult(
            stream=stream,
            title=str(raw.get("title") or ""),
            url=url,
            snippet=str(raw.get("snippet") or raw.get("description") or ""),
        ))
    return results


def direct_results(urls: list[str], stream: str) -> list[SearchResult]:
    if stream not in stream_slugs():
        raise ValueError(f"unknown stream: {stream}")
    return [SearchResult(stream=stream, title=url, url=url) for url in urls]


def discover_from_results(results: list[SearchResult], timeout: float, max_pages: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results[:max_pages]:
        try:
            html = fetch_page(result.url, timeout=timeout)
            page_error = ""
        except Exception as exc:
            html = ""
            page_error = f"{exc.__class__.__name__}: {exc}"

        feed_urls = candidate_feed_urls(result.url, html)
        for feed_url in feed_urls:
            probe = fetch_url(feed_url, timeout=timeout).as_dict()
            scoring = score_candidate(result.stream, feed_url, probe, title=result.title, snippet=result.snippet)
            rows.append({
                "stream": result.stream,
                "source_page_url": result.url,
                "source_page_title": result.title,
                "source_page_error": page_error,
                "feed_url": feed_url,
                "probe": probe,
                **scoring,
            })
    rows.sort(key=lambda row: (float(row.get("score", 0.0)), row.get("candidate_status") == "passed_probe"), reverse=True)
    return rows


def build_report(rows: list[dict[str, Any]], provider: str) -> dict[str, Any]:
    return {
        "date": date.today().isoformat(),
        "report_type": "source_discovery",
        "provider": provider,
        "items": rows,
        "promotion_policy": "Candidates are not promoted automatically. A source must pass probe, source-class review, stream relevance review, and noise checks before editing sources/feeds.json.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*", help="Direct site URLs to inspect for feed autodiscovery.")
    parser.add_argument("--stream", default="", help="Required for direct URLs.")
    parser.add_argument("--search-results", default="", help="Provider-agnostic JSON with search results.")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--provider", default="manual")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=str(REPORT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.search_results:
        results = load_search_results(Path(args.search_results), default_stream=args.stream)
    else:
        results = direct_results(args.urls, args.stream)

    rows = discover_from_results(results, timeout=args.timeout, max_pages=args.max_pages)
    report = build_report(rows, provider=args.provider)

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        output = Path(args.output)
        write_json(output, report)
        print(f"wrote {repo_path(output)} with {len(rows)} candidate feed(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
