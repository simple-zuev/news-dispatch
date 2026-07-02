#!/usr/bin/env python3
"""Remove legacy dashboard blocks from the generated homepage."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DISPATCH_DIR = ROOT / "dispatches"
SIGNAL_DIR = ROOT / "signals"
STREAMS_PATH = ROOT / "data" / "streams.json"
RADAR_PATH = ROOT / "validation" / "daily-radar-latest.json"

HERO_MARKER = "editorial-home-hero"
TOPLINE_MARKER = "editorial-home-topline"
STATUS_START = "<!-- site-status:start -->"
STATUS_END = "<!-- site-status:end -->"
EMPTY_SCALARS = {"", "[]", "null", "None", "none"}
CSS_HREF = "styles/editorial-home.css"

STREAM_PRIORITY = [
    "crypto-finance",
    "finance",
    "ai",
    "tech-hardware-software",
    "science-discovery",
    "moscow-city",
    "dj-audio-creative",
    "gear-style-edc",
    "general",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, object] = {}
    list_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            meta.setdefault(list_key, [])
            assert isinstance(meta[list_key], list)
            meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value == "":
            list_key = key
            meta[key] = []
        else:
            list_key = None
            meta[key] = value
    return meta, text[end + 5 :]


def list_value(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip() not in EMPTY_SCALARS]
    scalar = str(value).strip()
    if scalar in EMPTY_SCALARS:
        return []
    return [scalar]


def stream_titles() -> dict[str, str]:
    data = load_json(STREAMS_PATH)
    titles: dict[str, str] = {}
    for item in data.get("streams", []):
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug", "")).strip()
        title = str(item.get("title", slug)).strip()
        if slug and title:
            titles[slug] = title
    return titles


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def first_sentence(text: str, fallback: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return fallback
    match = re.search(r"(.{80,260}?[.!?])\s", cleaned + " ")
    return match.group(1) if match else cleaned[:240]


def collect_published() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) != "published":
            continue
        title = str(meta.get("title", path.stem)).strip()
        summary = str(meta.get("summary", "")).strip()
        if not summary:
            summary = first_sentence(body, "Опубликованный материал с редакционной проверкой источников и ограничений.")
        items.append(
            {
                "kind": "Материал",
                "title": title,
                "summary": summary,
                "stream": str(meta.get("stream", "general")).strip() or "general",
                "date": str(meta.get("date", "")).strip(),
                "url": f"dispatches/{slugify(path)}.html",
                "cta": "Открыть материал",
            }
        )
    return sorted(items, key=lambda item: (item["date"], item["title"]), reverse=True)


def signal_title(meta: dict[str, object], body: str, path: Path) -> str:
    title = str(meta.get("title", "")).strip()
    if title:
        return title
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ")


def first_signal() -> dict[str, str] | None:
    titles = stream_titles()
    radar = load_json(RADAR_PATH)
    generated = [item for item in radar.get("generated", []) if isinstance(item, dict)]

    def priority(item: dict[str, Any]) -> tuple[int, str]:
        stream = str(item.get("stream", "")).strip()
        index = STREAM_PRIORITY.index(stream) if stream in STREAM_PRIORITY else len(STREAM_PRIORITY)
        return index, stream

    for item in sorted(generated, key=priority):
        stream = str(item.get("stream", "")).strip()
        signals = item.get("signals", [])
        if not isinstance(signals, list) or not signals:
            continue
        for rel in signals:
            path = ROOT / str(rel)
            if not path.exists() or not path.is_file():
                continue
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            source_titles = list_value(meta, "source_titles")
            source_types = list_value(meta, "source_types")
            title = signal_title(meta, body, path)
            source_note = source_titles[0] if source_titles else "Публичный источник из радара"
            source_type = source_types[0] if source_types else str(meta.get("source_class", "источник")).replace("_", " ")
            return {
                "kind": "Сигнал",
                "title": title,
                "summary": (
                    f"{source_type}: {source_note}. Это входной сигнал, а не готовый аналитический вывод; "
                    "перед публикацией нужен контекст, проверка источника и редакционная оценка эффекта."
                ),
                "stream": stream or "general",
                "stream_title": titles.get(stream, stream or "Общий радар"),
                "date": str(meta.get("date", radar.get("date", ""))).strip(),
                "url": f"radar/{stream}.html" if stream else "radar/index.html",
                "cta": "Открыть тему в радаре",
            }
    return None


def choose_feature() -> dict[str, str]:
    published = collect_published()
    if published:
        item = published[0]
        item["stream_title"] = stream_titles().get(item["stream"], item["stream"])
        return item
    signal = first_signal()
    if signal:
        return signal
    return {
        "kind": "Радар",
        "title": "Публичный аналитический радар",
        "summary": "Входные сигналы появляются в радаре; опубликованные материалы проходят отдельную редакционную проверку источников, формулировок и ограничений.",
        "stream": "general",
        "stream_title": "Общий радар",
        "date": "",
        "url": "radar/index.html",
        "cta": "Открыть радар",
    }


def build_hero(feature: dict[str, str]) -> str:
    title = html.escape(feature.get("title", "Публичный аналитический радар"))
    summary = html.escape(feature.get("summary", ""))
    kind = html.escape(feature.get("kind", "Радар"))
    date = html.escape(feature.get("date", ""))
    stream = html.escape(feature.get("stream_title", feature.get("stream", "Общий радар")))
    url = html.escape(feature.get("url", "radar/index.html"))
    cta = html.escape(feature.get("cta", "Открыть"))
    date_part = f" · {date}" if date else ""
    return f"""
<section class="editorial-home-hero" aria-label="Главное на главной странице">
  <article class="editorial-hero-main">
    <p class="eyebrow">Главное за сегодня · {date_part}</p>
    <h2><a href="today.html">Открыть сегодняшний обзор</a></h2>
    <p>Короткая русскоязычная сводка по публичным источникам: что произошло, почему это важно и что проверять дальше.</p>
    <p class="hero-meta">Главный вход: ежедневный обзор. Дополнительно: темы и архив материалов.</p>
    <p class="hero-actions"><a href="today.html">Главное за сегодня</a><a href="streams/index.html">Темы</a><a href="dispatches.html">Архив материалов</a></p>
  </article>
  <aside class="editorial-hero-side" aria-label="Логика чтения">
    <h3>Как читать</h3>
    <p><strong>Сигнал</strong> — входная точка из публичного источника.</p>
    <p><strong>Материал</strong> — проверенный слой с контекстом, ограничениями и источниками.</p>
    <p><strong>Тема</strong> помогает быстро перейти к интересующему направлению.</p>
  </aside>
</section>
<section class="editorial-home-lanes" aria-label="Основные входы">
  <article>
    <p class="label">Сегодня</p>
    <h3><a href="today.html">Главное за сегодня</a></h3>
    <p>Отобранные публичные сигналы с тезисом, контекстом, источником и следующими проверками.</p>
  </article>
  <article>
    <p class="label">Публикации</p>
    <h3><a href="dispatches.html">Новые материалы</a></h3>
    <p>Материалы с источниками, контекстом и обозначенными ограничениями.</p>
  </article>
  <article>
    <p class="label">Навигация</p>
    <h3><a href="streams/index.html">Темы</a></h3>
    <p>Финансы, криптофинансы, ИИ, железо и софт, Москва, EDC, аудио и наука.</p>
  </article>
  <article>
    <p class="label">Сигналы</p>
    <h3><a href="radar/index.html">Лента источников</a></h3>
    <p>Публичные сообщения по темам. Это повод для проверки, а не итоговый вывод.</p>
  </article>
</section>
""".strip()


def status_block(text: str) -> str:
    start = text.find(STATUS_START)
    end = text.find(STATUS_END)
    if start == -1 or end == -1 or end < start:
        return ""
    return text[start : end + len(STATUS_END)]


def remove_status_block(text: str) -> str:
    block = status_block(text)
    if not block:
        return text
    return text.replace(block, "", 1)


def ensure_css(text: str) -> str:
    if CSS_HREF in text:
        return text
    link = f'  <link rel="stylesheet" href="{CSS_HREF}">\n'
    return text.replace("</head>", link + "</head>", 1)


def apply_homepage() -> bool:
    path = SITE_DIR / "index.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text
    text = remove_status_block(text)
    text = re.sub(r'\s*<section class="editorial-home-topline">.*?</section>\s*</section>', "", text, flags=re.S)
    text = re.sub(r'\s*<section class="editorial-home-hero".*?</section>', "", text, flags=re.S)
    text = re.sub(r'\s*<section class="editorial-home-lanes".*?</section>', "", text, flags=re.S)
    text = re.sub(r'\s*<section class="panel reader-home-intro">.*?</section>', "", text, flags=re.S)

    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changed = apply_homepage()
    print(f"Applied editorial home layout: {'yes' if changed else 'no changes'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
