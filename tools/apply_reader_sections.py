#!/usr/bin/env python3
"""Add reader dashboard structure to generated article pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"

SECTION_CLASS = {
    "Главное": "reader-section-main",
    "Слухи и мнения": "reader-section-rumors",
    "Мнение людей": "reader-section-people",
    "Медиа и материалы": "reader-section-media",
    "Источники": "reader-section-sources",
    "Что наблюдать дальше": "reader-section-watch",
    "Итог": "reader-section-summary",
}

TOC = [
    ("Главное", "main"),
    ("Что произошло", "facts"),
    ("Анализ", "analysis"),
    ("Слухи и мнения", "rumors"),
    ("Мнение людей", "people"),
    ("Материалы", "media"),
]


def slug_for(title: str) -> str:
    return {
        "Главное": "main",
        "Что произошло": "facts",
        "Почему это важно": "why",
        "Анализ": "analysis",
        "Слухи и мнения": "rumors",
        "Мнение людей": "people",
        "Медиа и материалы": "media",
        "Источники": "sources",
        "Что наблюдать дальше": "watch",
        "Итог": "summary",
    }.get(title, "section")


def add_toc(text: str) -> str:
    if "reader-map" in text:
        return text
    links = "".join(f'<a href="#{anchor}">{label}</a>' for label, anchor in TOC)
    block = f'<nav class="reader-map" aria-label="Карта выпуска"><span>Карта выпуска</span>{links}</nav>'
    return text.replace('<main class="article-body">', f'<main class="article-body">{block}', 1)


def wrap_sections(text: str) -> str:
    if "reader-section-block" in text:
        return text
    pattern = re.compile(r"(<h2>([^<]+)</h2>)")
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    result: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else text.find("</main>", match.end())
        if end == -1:
            end = len(text)
        result.append(text[cursor:start])
        section_html = text[start:end]
        if title in SECTION_CLASS:
            anchor = slug_for(title)
            section_html = section_html.replace(f"<h2>{title}</h2>", f'<h2 id="{anchor}">{title}</h2>', 1)
            section_html = f'<section class="reader-section-block {SECTION_CLASS[title]}">{section_html}</section>'
        else:
            anchor = slug_for(title)
            section_html = section_html.replace(f"<h2>{title}</h2>", f'<h2 id="{anchor}">{title}</h2>', 1)
        result.append(section_html)
        cursor = end
    result.append(text[cursor:])
    return "".join(result)


def process_page(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if '<main class="article-body">' not in text:
        return False
    new_text = wrap_sections(add_toc(text))
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = 0
    for page in (SITE_DIR / "dispatches").glob("*.html"):
        if process_page(page):
            changed += 1
    print(f"Applied reader sections to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
