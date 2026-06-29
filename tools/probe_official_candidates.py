#!/usr/bin/env python3
"""Probe pre-production source candidate URLs.

This tool is intentionally separate from Daily Radar. It checks candidates from
sources/official-candidates.json and writes a validation report, but it does not
promote candidates into sources/feeds.json.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "sources" / "official-candidates.json"
REPORT_PATH = ROOT / "validation" / "official-candidate-probe-latest.json"
USER_AGENT = "news-dispatch-candidate-probe/1.0"
XML_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
}


@dataclass(frozen=True)
class ProbeResult:
    candidate_id: str
    stream: str
    source_class: str
    url: str
    status: str
    http_status: int | None
    content_type: str
    feed_type: str
    item_count: int
    elapsed_ms: int
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "stream": self.stream,
            "source_class": self.source_class,
            "url": self.url,
            "status": self.status,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "feed_type": self.feed_type,
            "item_count": self.item_count,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


def load_candidates(path: Path = CANDIDATES_PATH) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    return [candidate for candidate in candidates if isinstance(candidate, dict)]


def detect_feed_type(xml_bytes: bytes) -> tuple[str, int]:
    root = ET.fromstring(xml_bytes)
    tag = root.tag.lower()
    if tag.endswith("rss"):
        return "rss", len(root.findall("./channel/item"))
    if tag.endswith("feed"):
        return "atom", len(root.findall("atom:entry", XML_NAMESPACES))
    return "unknown", 0


def build_ssl_context(ca_file: str = "") -> ssl.SSLContext:
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)

    try:
        import certifi  # type: ignore[import-not-found]
    except Exception:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def is_tls_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLError):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLError):
        return True
    message = str(exc).lower()
    return "certificate verify failed" in message or "unable to get local issuer certificate" in message


def fetch_url(url: str, timeout: float, ca_file: str = "") -> tuple[int | None, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = build_ssl_context(ca_file=ca_file)
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        status = getattr(response, "status", None)
        content_type = response.headers.get("content-type", "")
        return status, content_type, response.read()


def probe_candidate(candidate: dict[str, Any], timeout: float, ca_file: str = "") -> ProbeResult:
    start = time.monotonic()
    candidate_id = str(candidate.get("id", "")).strip()
    stream = str(candidate.get("stream", "")).strip()
    source_class = str(candidate.get("source_class", "")).strip()
    url = str(candidate.get("candidate_url", "")).strip()
    if not url:
        return ProbeResult(candidate_id, stream, source_class, url, "skipped", None, "", "", 0, 0, "candidate_url is empty")

    try:
        http_status, content_type, body = fetch_url(url, timeout=timeout, ca_file=ca_file)
        feed_type, item_count = detect_feed_type(body)
    except ET.ParseError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ProbeResult(candidate_id, stream, source_class, url, "failed", None, "", "invalid_xml", 0, elapsed_ms, str(exc))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        status = "tls_error" if is_tls_error(exc) else "failed"
        return ProbeResult(candidate_id, stream, source_class, url, status, None, "", "", 0, elapsed_ms, str(exc))

    elapsed_ms = int((time.monotonic() - start) * 1000)
    status = "ok" if feed_type in {"rss", "atom"} and item_count > 0 else "failed"
    error = "" if status == "ok" else "URL did not return RSS/Atom entries"
    return ProbeResult(candidate_id, stream, source_class, url, status, http_status, content_type, feed_type, item_count, elapsed_ms, error)


def build_report(results: list[ProbeResult]) -> dict[str, Any]:
    return {
        "status": "pre-production candidate feed probe",
        "total_candidates_with_url": len([result for result in results if result.url]),
        "ok": len([result for result in results if result.status == "ok"]),
        "failed": len([result for result in results if result.status == "failed"]),
        "tls_error": len([result for result in results if result.status == "tls_error"]),
        "skipped": len([result for result in results if result.status == "skipped"]),
        "results": [result.to_dict() for result in results],
    }


def write_report(report: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe official candidate feed URLs")
    parser.add_argument("--id", dest="candidate_id", default="", help="Probe one candidate id only")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-candidate network timeout in seconds")
    parser.add_argument("--ca-file", default="", help="Optional CA bundle path for TLS verification")
    parser.add_argument("--write-report", action="store_true", help="Write validation/official-candidate-probe-latest.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    candidates = load_candidates()
    if args.candidate_id:
        candidates = [candidate for candidate in candidates if candidate.get("id") == args.candidate_id]
        if not candidates:
            print(f"No candidate found for id: {args.candidate_id}")
            return 1

    results = [probe_candidate(candidate, timeout=args.timeout, ca_file=args.ca_file) for candidate in candidates]
    report = build_report(results)
    if args.write_report:
        write_report(report)
        print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if report["failed"] == 0 and report["tls_error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
