#!/usr/bin/env python3
"""Probe candidate RSS/Atom feed URLs before enabling them in sources/feeds.json."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "sources" / "feed-candidates.json"

USER_AGENT = "NewsDispatchFeedProbe/1.0 (+https://simple-zuev.github.io/news-dispatch/)"
CA_FALLBACKS = (
    "/etc/ssl/cert.pem",
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/openssl@3/cert.pem",
)


@dataclass
class ProbeResult:
    url: str
    ok: bool
    feed_type: str = ""
    item_count: int = 0
    first_title: str = ""
    sample_titles: list[str] = field(default_factory=list)
    error: str = ""
    http_status: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "ok": self.ok,
            "feed_type": self.feed_type,
            "item_count": self.item_count,
            "first_title": self.first_title,
            "sample_titles": self.sample_titles,
            "error": self.error,
            "http_status": self.http_status,
        }


def strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in list(node):
        if strip_ns(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def sample_titles(nodes: list[ET.Element], limit: int = 30) -> list[str]:
    titles: list[str] = []
    for node in nodes[:limit]:
        title = child_text(node, ("title",))
        if title:
            titles.append(title)
    return titles


def parse_feed_xml(text: str, url: str = "") -> ProbeResult:
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as exc:
        return ProbeResult(url=url, ok=False, error=f"xml_parse_error: {exc}")

    root_name = strip_ns(root.tag).lower()
    if root_name == "rss":
        channel = root.find("channel")
        if channel is None:
            return ProbeResult(url=url, ok=False, error="rss_without_channel")
        items = channel.findall("item")
        titles = sample_titles(items)
        first_title = titles[0] if titles else ""
        return ProbeResult(url=url, ok=bool(items), feed_type="rss", item_count=len(items), first_title=first_title, sample_titles=titles)

    if root_name == "feed":
        entries = [node for node in list(root) if strip_ns(node.tag).lower() == "entry"]
        titles = sample_titles(entries)
        first_title = titles[0] if titles else ""
        return ProbeResult(url=url, ok=bool(entries), feed_type="atom", item_count=len(entries), first_title=first_title, sample_titles=titles)

    return ProbeResult(url=url, ok=False, error=f"unsupported_root: {root_name}")


def fetch_url(url: str, timeout: float) -> ProbeResult:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        import certifi  # type: ignore[import-not-found]
    except Exception:
        ca_file = next((path for path in CA_FALLBACKS if Path(path).exists()), "")
        context = ssl.create_default_context(cafile=ca_file or None)
    else:
        context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            status = getattr(response, "status", None)
            body = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        return ProbeResult(url=url, ok=False, error=f"http_error: {exc.code}", http_status=exc.code)
    except urllib.error.URLError as exc:
        return ProbeResult(url=url, ok=False, error=f"url_error: {exc.reason}")
    except TimeoutError:
        return ProbeResult(url=url, ok=False, error="timeout")

    text = body.decode("utf-8", errors="replace")
    result = parse_feed_xml(text, url=url)
    result.http_status = status
    return result


def load_candidates(path: Path, stream: str | None) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("candidates", [])
    if stream:
        rows = [row for row in rows if str(row.get("stream")) == stream]
    return rows


def probe_candidates(candidates: list[dict[str, Any]], timeout: float) -> list[dict[str, Any]]:
    results = []
    for candidate in candidates:
        url = str(candidate.get("url") or "")
        if not url:
            continue
        probe = fetch_url(url, timeout=timeout).as_dict()
        results.append({**candidate, "probe": probe})
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*", help="Feed URLs to probe directly.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES), help="Candidate JSON file.")
    parser.add_argument("--stream", default="", help="Optional stream filter for candidate JSON.")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--require-ok", action="store_true", help="Exit non-zero if no candidate probes successfully.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.urls:
        candidates = [{"id": url, "title": url, "url": url, "stream": args.stream or "manual"} for url in args.urls]
    else:
        candidates = load_candidates(Path(args.candidates), args.stream or None)

    results = probe_candidates(candidates, timeout=args.timeout)
    print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))

    if args.require_ok and not any(row.get("probe", {}).get("ok") for row in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
