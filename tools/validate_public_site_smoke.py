#!/usr/bin/env python3
"""Smoke-check deployed public reader pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "public-site-smoke-latest.json"
DEFAULT_BASE_URL = "https://simple-zuev.github.io/news-dispatch/"
DEFAULT_PAGES = ("", "news/", "today.html")
FORBIDDEN = (
    "/comments/default",
    "/feeds/comments",
    "Google Security Blog: регуляторика и надзор",
    "Источник сообщает: Криптофинансы — регуляторика и надзор",
    "source_rule_status",
    "reader_safe",
    "source_rule",
    "score=",
)
REQUIRED_BY_PAGE = {
    "": ("Последние новости", "Открыть источник"),
    "news/": ("Новости", "Открыть источник"),
    "today.html": ("Сегодня",),
}


@dataclass(frozen=True)
class FetchedPage:
    page: str
    url: str
    body: str


def join_url(base_url: str, page: str) -> str:
    return base_url.rstrip("/") + "/" + page.lstrip("/")


def fetch_url(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "news-dispatch-public-site-smoke/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def visible(html_text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html_text).split())


def check_page(page: FetchedPage) -> list[str]:
    issues: list[str] = []
    raw = page.body
    shown = visible(raw)
    for marker in FORBIDDEN:
        if marker in raw or marker in shown:
            issues.append(f"forbidden marker visible on {page.page or 'index'}: {marker}")
    for marker in REQUIRED_BY_PAGE.get(page.page, ()):  # page names are normalized by caller.
        if marker not in shown:
            issues.append(f"required marker missing on {page.page or 'index'}: {marker}")
    return issues


def run_smoke(base_url: str, pages: tuple[str, ...], timeout: float) -> dict[str, object]:
    fetched: list[FetchedPage] = []
    issues: list[str] = []
    for page in pages:
        url = join_url(base_url, page)
        try:
            body = fetch_url(url, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            issues.append(f"failed to fetch {page or 'index'}: {exc}")
            continue
        fetched_page = FetchedPage(page=page, url=url, body=body)
        fetched.append(fetched_page)
        issues.extend(check_page(fetched_page))
    return {
        "report_type": "public_site_smoke",
        "base_url": base_url,
        "checked_pages": [page.page or "index" for page in fetched],
        "passed": not issues,
        "issues": issues,
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = run_smoke(args.base_url, DEFAULT_PAGES, args.timeout)
    write_report(Path(args.output), report)
    if not report["passed"]:
        print(f"Public site smoke failed: {len(report['issues'])} issue(s)")
        return 1
    print("Public site smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
