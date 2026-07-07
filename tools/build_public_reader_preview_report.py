#!/usr/bin/env python3
"""Write a small QA report for pull request public-reader previews."""

from __future__ import annotations

import argparse
import html.parser
import os
import sys
from pathlib import Path
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REPORT_PATH = ROOT / "validation" / "public-reader-preview-report.md"

sys.path.insert(0, str(ROOT / "tests"))
from public_html_scan import assert_public_pages_clean, public_page_paths  # noqa: E402


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


def html_pages(site_dir: Path) -> list[Path]:
    return sorted(path for path in site_dir.rglob("*.html") if path.is_file())


def route(path: Path, site_dir: Path) -> str:
    rel = path.relative_to(site_dir).as_posix()
    return "/" if rel == "index.html" else f"/{rel}"


def page_hrefs(path: Path) -> list[str]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.hrefs


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


def write_report(site_dir: Path, output: Path, build_mode: str, commit_sha: str) -> list[str]:
    site_dir = site_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pages = html_pages(site_dir)
    public_pages = public_page_paths(site_dir)
    assert_public_pages_clean(site_dir)
    checked, external, missing = check_internal_links(site_dir)
    status = "passed" if not missing else "failed"
    missing_lines = "\n".join(f"- {item}" for item in missing[:50]) if missing else "- none"
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
- Link check result: {status}

## Generated routes

{route_lines or "- none"}

## Missing internal links

{missing_lines}
"""
    output.write_text(text, encoding="utf-8")
    return missing


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    missing = write_report(
        site_dir=Path(args.site_dir),
        output=Path(args.output),
        build_mode=str(args.build_mode),
        commit_sha=str(args.commit_sha),
    )
    print(f"Wrote {args.output}")
    if missing and not args.allow_missing_links:
        print(f"Missing internal links: {len(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
