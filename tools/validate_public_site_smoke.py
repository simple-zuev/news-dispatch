#!/usr/bin/env python3
"""Smoke-check deployed public reader pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "public-site-smoke-latest.json"
DEFAULT_BASE_URL = "https://simple-zuev.github.io/news-dispatch/"
DEFAULT_PAGES = ("", "news/", "today.html", "digests/", "sources/")
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
    "digests/": ("Дайджесты",),
    "sources/": ("Источники",),
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


def fetch_with_retries(url: str, timeout: float, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch_url(url, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 4))
    assert last_error is not None
    raise last_error


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


def parse_utc(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def status_issues(
    payload: dict[str, object],
    *,
    reference: datetime,
    max_build_age_hours: float,
    max_content_age_hours: float,
) -> list[str]:
    issues: list[str] = []
    generated_at = parse_utc(payload.get("generated_at"))
    latest_item_at = parse_utc(payload.get("latest_public_item_at"))
    if generated_at is None:
        issues.append("status.json has no valid generated_at")
    else:
        age = (reference - generated_at).total_seconds() / 3600
        if age > max_build_age_hours:
            issues.append(f"published build is stale: {age:.1f}h > {max_build_age_hours:.1f}h")
    if latest_item_at is None:
        issues.append("status.json has no valid latest_public_item_at")
    else:
        age = (reference - latest_item_at).total_seconds() / 3600
        if age > max_content_age_hours:
            issues.append(f"published reader content is stale: {age:.1f}h > {max_content_age_hours:.1f}h")
    return issues


def run_smoke(
    base_url: str,
    pages: tuple[str, ...],
    timeout: float,
    *,
    retries: int = 2,
    reference: datetime | None = None,
    max_build_age_hours: float = 9,
    max_content_age_hours: float = 36,
) -> dict[str, object]:
    fetched: list[FetchedPage] = []
    issues: list[str] = []
    now = reference or datetime.now(timezone.utc)
    status_checked = False
    for page in pages:
        url = join_url(base_url, page)
        try:
            body = fetch_with_retries(url, timeout, retries)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            issues.append(f"failed to fetch {page or 'index'}: {exc}")
            continue
        fetched_page = FetchedPage(page=page, url=url, body=body)
        fetched.append(fetched_page)
        issues.extend(check_page(fetched_page))
    status_url = join_url(base_url, "status.json")
    try:
        status_body = fetch_with_retries(status_url, timeout, retries)
        status_payload = json.loads(status_body)
        if not isinstance(status_payload, dict):
            issues.append("status.json is not an object")
        else:
            status_checked = True
            issues.extend(
                status_issues(
                    status_payload,
                    reference=now,
                    max_build_age_hours=max_build_age_hours,
                    max_content_age_hours=max_content_age_hours,
                )
            )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        issues.append(f"failed to fetch status.json: {exc}")
    return {
        "report_type": "public_site_smoke",
        "base_url": base_url,
        "checked_pages": [page.page or "index" for page in fetched]
        + (["status.json"] if status_checked else []),
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
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--max-build-age-hours", type=float, default=9)
    parser.add_argument("--max-content-age-hours", type=float, default=36)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = run_smoke(
        args.base_url,
        DEFAULT_PAGES,
        args.timeout,
        retries=args.retries,
        max_build_age_hours=args.max_build_age_hours,
        max_content_age_hours=args.max_content_age_hours,
    )
    write_report(Path(args.output), report)
    if not report["passed"]:
        print(f"Public site smoke failed: {len(report['issues'])} issue(s)")
        return 1
    print("Public site smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
