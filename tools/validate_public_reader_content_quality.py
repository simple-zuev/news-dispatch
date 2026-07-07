#!/usr/bin/env python3
"""Check daily-use quality of generated public reader pages."""

from __future__ import annotations

import argparse
import html.parser
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REPORT_PATH = ROOT / "validation" / "public-reader-preview-report.md"
JSON_PATH = ROOT / "validation" / "public-reader-content-quality-latest.json"

SURFACE = ["index.html", "news/index.html", "news/crypto-finance.html", "today.html"]
GENERIC = [
    "без заголовка",
    "источник сообщает: криптофинансы",
    "источник сообщает: финансы",
    "источник сообщает: ии",
    "источник описывает тему",
    "короткое сообщение источника",
]


class HeadingParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tag: str | None = None
        self.buf: list[str] = []
        self.headings: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.tag = tag
            self.buf = []

    def handle_data(self, data: str) -> None:
        if self.tag:
            self.buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.tag:
            text = " ".join("".join(self.buf).split())
            if text:
                self.headings.append((tag, text))
            self.tag = None
            self.buf = []


def read(site_dir: Path, rel: str) -> str:
    path = site_dir / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def visible(html_text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html_text).split())


def headings(html_text: str) -> list[tuple[str, str]]:
    parser = HeadingParser()
    parser.feed(html_text)
    return parser.headings


def norm(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"[^0-9a-zа-яё]+", " ", text).strip()


def check(site_dir: Path) -> list[str]:
    pages = {rel: read(site_dir, rel) for rel in SURFACE}
    combined = visible("\n".join(pages.values())).lower()
    issues: list[str] = []

    for phrase in GENERIC:
        if phrase in combined:
            issues.append(f"generic fallback copy is visible: {phrase}")

    for rel in ["index.html", "today.html"]:
        h3 = [text for tag, text in headings(pages.get(rel, "")) if tag == "h3" and not text.lower().startswith("нет ")]
        counts = Counter(norm(text) for text in h3 if norm(text))
        repeated = [title for title, count in counts.items() if count > 2]
        if repeated:
            issues.append(f"excessive duplicate headlines on {rel}: {', '.join(repeated[:5])}")

    home = pages.get("index.html", "")
    news = pages.get("news/index.html", "") + pages.get("news/crypto-finance.html", "")
    today = pages.get("today.html", "")

    if "home-news-row" in home and ("home-news-meta" not in home or "Открыть источник" not in home):
        issues.append("homepage news rows lack metadata or source action")
    if "news-item--text" in news and ("news-meta" not in news or "Открыть источник" not in news):
        issues.append("news rows lack metadata or source action")
    if "today-highlight-list" in today and "news-meta" not in today:
        issues.append("today highlights lack source metadata")
    if "Нет публичных сигналов" in today and "news-item--text" in news:
        issues.append("today is empty while reader-safe news exists")

    return issues


def write_outputs(issues: list[str], output: Path) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"passed": not issues, "issues": issues}
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = "passed" if not issues else "failed"
    lines = "\n".join(f"- {issue}" for issue in issues) if issues else "- none"
    with output.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## Daily content quality check\n\n- Result: {status}\n\n{lines}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", default=str(SITE_DIR))
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    issues = check(Path(args.site_dir))
    write_outputs(issues, Path(args.report))
    if issues:
        print(f"Content quality issues: {len(issues)}")
        return 1
    print("Content quality check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
