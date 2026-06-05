#!/usr/bin/env python3
"""Add reader dashboard structure to generated article pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
ASSET_MARKER = '<section class="sources-block reader-assets">'

SECTION_CLASS = {
    "Лид": "reader-section-lede",
    "Главное": "reader-section-main",
    "Что произошло": "reader-section-facts",
    "Почему это важно": "reader-section-why",
    "Анализ": "reader-section-analysis",
    "Слухи и мнения": "reader-section-rumors",
    "Мнение людей": "reader-section-people",
    "Медиа и материалы": "reader-section-media",
    "Источники": "reader-section-sources",
    "Что наблюдать дальше": "reader-section-watch",
    "Итог": "reader-section-summary",
}

SLUGS = {
    "Лид": "lede",
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
}

TOC_LABELS = {
    "Лид": "Лид",
    "Главное": "Главное",
    "Что произошло": "Что произошло",
    "Почему это важно": "Почему важно",
    "Анализ": "Анализ",
    "Слухи и мнения": "Слухи и мнения",
    "Мнение людей": "Мнение людей",
    "Медиа и материалы": "Материалы",
    "Источники": "Источники",
    "Что наблюдать дальше": "Что дальше",
    "Итог": "Итог",
}


def headings_in(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"<h2>([^<]+)</h2>", text)]


def add_toc(text: str) -> str:
    if "reader-map" in text:
        return text
    links = []
    for title in headings_in(text):
        if title in SLUGS:
            links.append(f'<a href="#{SLUGS[title]}">{TOC_LABELS[title]}</a>')
    if not links:
        return text
    block = '<nav class="reader-map" aria-label="Карта выпуска"><span>Карта выпуска</span>' + "".join(links) + "</nav>"
    return text.replace('<main class="article-body">', f'<main class="article-body">{block}', 1)


def drop_redundant_body_h1(text: str) -> str:
    pattern = re.compile(
        r'(<main class="article-body">(?:\s*<nav class="reader-map"[^>]*>.*?</nav>)?\s*)<h1>.*?</h1>\s*',
        re.S,
    )
    return pattern.sub(r"\1", text, count=1)


def promote_orphan_subtitle(text: str) -> str:
    """Turn a stand-alone body subtitle into a scannable deck line instead of a huge empty h2."""
    match = re.search(r'(<main class="article-body">\s*)<h2>([^<]+)</h2>\s*(?=<h2>)', text, re.S)
    if not match:
        return text
    title = match.group(2).strip()
    if title in SLUGS:
        return text
    replacement = f'{match.group(1)}<p class="reader-deck">{title}</p>\n'
    return text[: match.start()] + replacement + text[match.end() :]


def split_assets(text: str) -> tuple[str, str]:
    position = text.find(ASSET_MARKER)
    if position == -1:
        return text, ""
    return text[:position], text[position:]


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
        next_heading = matches[index + 1].start() if index + 1 < len(matches) else -1
        end = next_heading if next_heading != -1 else text.find("</main>", match.end())
        if end == -1:
            end = len(text)
        result.append(text[cursor:start])
        section_html = text[start:end]
        if title in SLUGS:
            anchor = SLUGS[title]
            section_html = section_html.replace(f"<h2>{title}</h2>", f'<h2 id="{anchor}">{title}</h2>', 1)
        if title in SECTION_CLASS:
            section_html = f'<section class="reader-section-block {SECTION_CLASS[title]}">{section_html}</section>'
        result.append(section_html)
        cursor = end
    result.append(text[cursor:])
    return "".join(result)


def upgrade_numbered_highlights(text: str) -> str:
    section_pattern = re.compile(
        r'(<section class="reader-section-block reader-section-main">)(.*?)(</section>)',
        re.S,
    )
    paragraph_pattern = re.compile(r"<p>(\d+\.\s.*?(?:\s+\d+\.\s.*?)+)</p>", re.S)

    def convert_paragraph(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        parts = re.split(r"\s+(?=\d+\.\s+)", body)
        if len(parts) < 2:
            return match.group(0)
        items: list[str] = []
        for part in parts:
            item = re.sub(r"^\d+\.\s*", "", part).strip()
            if item:
                items.append(f"<li>{item}</li>")
        if not items:
            return match.group(0)
        return "<ol>" + "".join(items) + "</ol>"

    def convert_section(match: re.Match[str]) -> str:
        opening, body, closing = match.groups()
        return opening + paragraph_pattern.sub(convert_paragraph, body, count=1) + closing

    return section_pattern.sub(convert_section, text)


def process_page(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if '<main class="article-body">' not in text:
        return False
    article_text, asset_text = split_assets(text)
    new_article = drop_redundant_body_h1(article_text)
    new_article = promote_orphan_subtitle(new_article)
    new_article = add_toc(new_article)
    new_article = wrap_sections(new_article)
    new_article = upgrade_numbered_highlights(new_article)
    new_text = new_article + asset_text
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
