#!/usr/bin/env python3
"""Add lightweight reader structure to generated index and stream pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"

HOME_MARKER = "reader-home-intro"
TOPIC_MARKER = "reader-topic-context"

HOME_BLOCK = """
<section class="panel reader-home-intro">
  <h2>Как читать этот радар</h2>
  <p>Сигналы показывают, что появилось в публичных источниках. Материалы — это уже отобранные публикации с источниками, контекстом и ограничениями.</p>
</section>
<section class="panel reader-home-intro">
  <h2>Свежие сигналы</h2>
  <p>Для первичного просмотра новых публичных сообщений используйте радар. Сигнал не является готовым аналитическим выводом.</p>
  <p class="hero-actions"><a href="radar/index.html">Открыть свежие сигналы</a></p>
</section>
""".strip()

TOPIC_BLOCK = """
<section class="panel reader-topic-context">
  <h2>Контекст темы</h2>
  <p>Сначала смотрите свежие сигналы как входной радар. Опубликованные материалы ниже — только те сюжеты, которые прошли редакционную проверку.</p>
</section>
""".strip()


def insert_after_main(text: str, block: str) -> str:
    if "<main>" not in text:
        return text
    return text.replace("<main>", "<main>\n" + block, 1)


def insert_after_status(text: str, block: str) -> str:
    marker = "<!-- site-status:end -->"
    if marker in text:
        return text.replace(marker, marker + "\n" + block, 1)
    return insert_after_main(text, block)


def process_homepage() -> bool:
    path = SITE_DIR / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if HOME_MARKER in text:
        return False
    new_text = insert_after_status(text, HOME_BLOCK)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def process_stream_pages() -> int:
    changed = 0
    for path in (SITE_DIR / "streams").glob("*.html"):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8")
        if TOPIC_MARKER in text:
            continue
        new_text = insert_after_main(text, TOPIC_BLOCK)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def main() -> int:
    changed = 0
    if process_homepage():
        changed += 1
    changed += process_stream_pages()
    print(f"Applied reader structure to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
