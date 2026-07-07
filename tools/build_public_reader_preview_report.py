#!/usr/bin/env python3
"""Write a small QA report for pull request public-reader previews."""

from __future__ import annotations

import argparse
import html.parser
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REPORT_PATH = ROOT / "validation" / "public-reader-preview-report.md"

sys.path.insert(0, str(ROOT / "tests"))
from public_html_scan import assert_public_pages_clean, public_page_paths  # noqa: E402


REQUIRED_READER_ROUTES = [
    "index.html",
    "news/index.html",
    "news/crypto-finance.html",
    "today.html",
    "digests/index.html",
    "sources/index.html",
]

FORBIDDEN_PRODUCT_COPY = [
    "Как читать",
    "Рубрики анализа анализа",
    "PUBLIC-SAFE EDITORIAL BRIEFING SYSTEM",
    "Publication boundary",
]

TRUST_TERMS = [
    "регулятор",
    "официальный источник",
    "деловое медиа",
    "публичное медиа",
    "компания",
    "исследовательский источник",
]

GENERIC_HEADLINE_PHRASES = [
    "без заголовка",
    "источник сообщает: криптофинансы",
    "источник сообщает: финансы",
    "источник сообщает: ии",
    "источник описывает тему",
    "короткое сообщение источника",
    "свежих новостей для показа сейчас нет",
]

CONTENT_SURFACE_ROUTES = [
    "index.html",
    "news/index.html",
    "news/crypto-finance.html",
    "today.html",
]


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


class HeadingParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current: str | None = None
        self.buffer: list[str] = []
        self.headings: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.current = tag
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.current:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current == tag:
            text = " ".join("".join(self.buffer).split())
            if text:
                self.headings.append((tag, text))
            self.current = None
            self.buffer = []


def html_pages(site_dir: Path) -> list[Path]:
    return sorted(path for path in site_dir.rglob("*.html") if path.is_file())


def route(path: Path, site_dir: Path) -> str:
    rel = path.relative_to(site_dir).as_posix()
    return "/" if rel == "index.html" else f"/{rel}"


def page_hrefs(path: Path) -> list[str]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.hrefs


def page_headings(text: str) -> list[tuple[str, str]]:
    parser = HeadingParser()
    parser.feed(text)
    return parser.headings


def visible_text(text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def normalize_headline(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"[^0-9a-zа-яё]+", " ", text).strip()


def read_page(site_dir: Path, relative: str) -> str:
    path = site_dir / relative
    return path.read_text(encoding="utf-8") if path.exists() else ""


def check_internal_links(site_dir: Path) -> tuple[int, int, list[str]]:
    checked = 0
    external = 0
    missing: list[str] = []
    site_dir = site_dir.resolve()
    for page in html_pages(site_dir):
        for href in page_hrefs(page):
            clean_href = urldefrag(href)[0]
            if not clean_href or clean_href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            if clean_href.startswith(("http://", "https://")):
                external += 1
                continue
            if clean_href.startswith("/"):
                target = site_dir / clean_href.lstrip("/")
            else:
                target = (page.parent / clean_href).resolve()
            if target.is_dir():
                target = target / "index.html"
            checked += 1
            try:
                target.relative_to(site_dir)
            except ValueError:
                continue
            if not target.exists():
                missing.append(f"{page.relative_to(site_dir).as_posix()} -> {href}")
    return checked, external, missing


def check_reader_trust(site_dir: Path) -> list[str]:
    issues: list[str] = []
    for route_path in REQUIRED_READER_ROUTES:
        if not (site_dir / route_path).exists():
            issues.append(f"missing required reader route: {route_path}")

    home = read_page(site_dir, "index.html")
    news = read_page(site_dir, "news/index.html") + read_page(site_dir, "news/crypto-finance.html")
    today = read_page(site_dir, "today.html")
    sources = read_page(site_dir, "sources/index.html")
    public_surface = "\n".join([home, news, today, sources])
    public_lower = public_surface.lower()

    for phrase in FORBIDDEN_PRODUCT_COPY:
        if phrase.lower() in public_lower:
            issues.append(f"forbidden old reader copy is visible: {phrase}")

    if "Последние новости" not in home or "Сегодня" not in home or "Дайджесты" not in home:
        issues.append("homepage does not expose daily-use reader sections")
    if "Открыть источник" not in public_surface:
        issues.append("reader surface does not expose source links")
    if not any(term in public_lower for term in TRUST_TERMS):
        issues.append("reader surface does not expose source type / reliability labels")
    if "Источники и проверка" not in today:
        issues.append("today page does not expose source verification note")
    if "Сообщения источников не являются готовым выводом" not in today:
        issues.append("today page does not separate source messages from conclusions")
    if "не инвестиционная" not in today:
        issues.append("today page does not show no-advice boundary")
    if "Надёжность" not in sources:
        issues.append("sources page does not expose reliability tiers")

    return issues


def check_content_quality(site_dir: Path) -> list[str]:
    issues: list[str] = []
    page_text = {relative: read_page(site_dir, relative) for relative in CONTENT_SURFACE_ROUTES}
    public_surface = "\n".join(page_text.values())
    public_lower = visible_text(public_surface).lower()

    for phrase in GENERIC_HEADLINE_PHRASES:
        if phrase in public_lower:
            issues.append(f"generic or fallback copy is visible: {phrase}")

    for relative in ["index.html", "today.html"]:
        headings = [
            text
            for tag, text in page_headings(page_text.get(relative, ""))
            if tag == "h3" and not text.lower().startswith(("нет ", "дайджесты пока"))
        ]
        counts = Counter(normalize_headline(text) for text in headings if normalize_headline(text))
        duplicates = [title for title, count in counts.items() if count > 1]
        if duplicates:
            issues.append(f"duplicate reader headlines on {relative}: {', '.join(duplicates[:5])}")

    surface_headings = [text for html_text in page_text.values() for tag, text in page_headings(html_text) if tag == "h3"]
    weak_headings = [
        text
        for text in surface_headings
        if len(text.strip()) < 12 or any(phrase in text.lower() for phrase in GENERIC_HEADLINE_PHRASES)
    ]
    if weak_headings:
        issues.append("weak reader headlines: " + "; ".join(weak_headings[:8]))

    home = page_text.get("index.html", "")
    news = page_text.get("news/index.html", "") + page_text.get("news/crypto-finance.html", "")
    today = page_text.get("today.html", "")

    if "home-news-row" in home and ("home-news-meta" not in home or "Открыть источник" not in home):
        issues.append("homepage news rows lack metadata or source action")
    if "news-item--text" in news and ("news-meta" not in news or "Открыть источник" not in news):
        issues.append("news feed rows lack metadata or source action")
    if "today-highlight-list" in today and "news-meta" not in today:
        issues.append("today highlights lack source metadata")
    if "Нет публичных сигналов" in today and "news-item--text" in news:
        issues.append("today is empty while reader-safe news items exist")

    if "официальный источник" in public_lower or "регулятор" in public_lower:
        if "Источники и проверка" not in today:
            issues.append("official/regulatory source context exists but Today lacks verification context")

    return issues


def write_report(site_dir: Path, output: Path, build_mode: str, commit_sha: str) -> tuple[list[str], list[str], list[str]]:
    site_dir = site_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pages = html_pages(site_dir)
    public_pages = public_page_paths(site_dir)
    assert_public_pages_clean(site_dir)
    checked, external, missing = check_internal_links(site_dir)
    trust_issues = check_reader_trust(site_dir)
    content_issues = check_content_quality(site_dir)
    link_status = "passed" if not missing else "failed"
    trust_status = "passed" if not trust_issues else "failed"
    content_status = "passed" if not content_issues else "failed"
    missing_lines = "\n".join(f"- {item}" for item in missing[:50]) if missing else "- none"
    trust_lines = "\n".join(f"- {item}" for item in trust_issues[:50]) if trust_issues else "- none"
    content_lines = "\n".join(f"- {item}" for item in content_issues[:50]) if content_issues else "- none"
    route_lines = "\n".join(f"- {route(path, site_dir)}" for path in pages[:120])
    if len(pages) > 120:
        route_lines += f"\n- ... {len(pages) - 120} more"
    text = f"""# Public Reader Preview Report

- Build mode: `{build_mode}`
- Commit SHA: `{commit_sha}`
- Generated HTML routes: {len(pages)}
- Public HTML forbidden-pattern scan: passed ({len(public_pages)} reader page(s))
- Internal links checked: {checked}
- External links observed: {external}
- Link check result: {link_status}
- Daily reader trust check: {trust_status}
- Daily content quality check: {content_status}

## Generated routes

{route_lines or "- none"}

## Missing internal links

{missing_lines}

## Reader trust issues

{trust_lines}

## Content quality issues

{content_lines}
"""
    output.write_text(text, encoding="utf-8")
    return missing, trust_issues, content_issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", default=str(SITE_DIR))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--build-mode", default="fixture / media skip")
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA", "local"))
    parser.add_argument(
        "--allow-missing-links",
        action="store_true",
        help="Write the QA report but do not fail when internal links are missing.",
    )
    parser.add_argument(
        "--allow-trust-issues",
        action="store_true",
        help="Write the QA report but do not fail when daily reader trust checks fail.",
    )
    parser.add_argument(
        "--allow-content-issues",
        action="store_true",
        help="Write the QA report but do not fail when daily content quality checks fail.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    missing, trust_issues, content_issues = write_report(
        site_dir=Path(args.site_dir),
        output=Path(args.output),
        build_mode=str(args.build_mode),
        commit_sha=str(args.commit_sha),
    )
    print(f"Wrote {args.output}")
    failed = False
    if missing and not args.allow_missing_links:
        print(f"Missing internal links: {len(missing)}", file=sys.stderr)
        failed = True
    if trust_issues and not args.allow_trust_issues:
        print(f"Reader trust issues: {len(trust_issues)}", file=sys.stderr)
        failed = True
    if content_issues and not args.allow_content_issues:
        print(f"Content quality issues: {len(content_issues)}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
