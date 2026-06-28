#!/usr/bin/env python3
"""Fill generated reader grids that would otherwise render as empty sections.

The renderer can legitimately produce no cards when there are no published
materials for a section yet. This postprocessor keeps the public reader useful by
adding explicit empty-state cards instead of visually blank grid blocks.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"

EMPTY_MESSAGES = {
    "Latest dispatches": (
        "Пока нет опубликованных выпусков",
        "Секция появится после promotion review и публикации первого reader-facing материала.",
    ),
    "Dispatch rubrics": (
        "Пока нет опубликованных выпусков по рубрикам",
        "Рубрики уже заданы как аналитические линзы; счётчики заполняются после публикации материалов.",
    ),
    "Dispatch streams": (
        "Потоки пока без опубликованных материалов",
        "Потоки остаются доступными для live-сигналов и будущих выпусков.",
    ),
}

GENERIC_MESSAGES = {
    "dispatches.html": (
        "Архив пока пуст",
        "Опубликованные материалы появятся здесь после редакционной проверки и публикации.",
    ),
    "rubrics/index.html": (
        "Рубрики пока без опубликованных материалов",
        "Структура рубрик задана, но карточки выпусков появятся после публикации.",
    ),
}

EMPTY_GRID_RE = re.compile(
    r'(<section\b(?=[^>]*class="[^"]*\bgrid\b[^"]*")[^>]*(?:aria-label="([^"]+)")?[^>]*>)\s*(</section>)',
    re.S,
)

EMPTY_PARAGRAPH_RE = re.compile(r"\s*<p>В этом ([^<]+?) пока нет ([^<]+?)\.</p>")
LIVE_PARAGRAPH_RE = re.compile(r"\s*<p>В этом ([^<]+?) сейчас нет live-сигналов\.</p>")


def empty_card(title: str, body: str) -> str:
    return f"""<article class=\"card empty-state\">
  <p class=\"label\">Нет данных для отображения</p>
  <h3>{title}</h3>
  <p>{body}</p>
</article>"""


def message_for(path: Path, aria_label: str | None) -> tuple[str, str]:
    if aria_label and aria_label in EMPTY_MESSAGES:
        return EMPTY_MESSAGES[aria_label]
    rel = path.relative_to(SITE_DIR).as_posix()
    if rel in GENERIC_MESSAGES:
        return GENERIC_MESSAGES[rel]
    return (
        "Пока нет карточек для этого раздела",
        "Данные появятся после генерации сигналов или публикации материалов, прошедших редакционную проверку.",
    )


def fill_empty_grids(path: Path, text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        title, body = message_for(path, match.group(2))
        return match.group(1) + empty_card(title, body) + match.group(3)

    return EMPTY_GRID_RE.sub(repl, text)


def replace_loose_empty_paragraphs(text: str) -> str:
    text = EMPTY_PARAGRAPH_RE.sub(
        lambda match: "\n" + empty_card(
            "Пока нет опубликованных выпусков",
            "Материалы появятся после редакционной проверки, promotion review и публикации.",
        ),
        text,
    )
    text = LIVE_PARAGRAPH_RE.sub(
        lambda match: "\n" + empty_card(
            "Сейчас нет live-сигналов",
            "Live-сигналы появятся после следующего успешного прохода Daily Radar для этого потока.",
        ),
        text,
    )
    return text


def process_page(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text = fill_empty_grids(path, text)
    new_text = replace_loose_empty_paragraphs(new_text)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in sorted(SITE_DIR.rglob("*.html")):
        if process_page(path):
            changed += 1
    print(f"Applied empty states to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
