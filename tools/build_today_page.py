#!/usr/bin/env python3
"""Build Today Radar from the Daily Radar ranking report.

The page is public-safe: it renders source-reported signals as a radar, not as
confirmed conclusions or recommendations.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from core import SITE_DIR, VALIDATION_DIR, write_text

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
OUTPUT_PATH = SITE_DIR / "today.html"

STREAM_LABELS = {
    "finance": "Финансы",
    "crypto-finance": "Криптофинансы",
    "ai": "AI",
    "tech-hardware-software": "Железо и софт",
    "gear-style-edc": "EDC / style",
    "moscow-city": "Москва",
    "dj-audio-creative": "DJ / audio",
    "science-discovery": "Наука",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def score(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def load_report(path: Path = REPORT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"date": "", "items": [], "fetch_errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def stream_label(slug: object) -> str:
    text = str(slug or "")
    return STREAM_LABELS.get(text, text or "Без потока")


def selected_items(report: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    items = [item for item in report.get("items", []) if item.get("selected")]
    if not items:
        items = [item for item in report.get("items", []) if item.get("source_rule_status") == "accepted_by_source_rules"]
    return sorted(items, key=lambda item: float(item.get("final_score", 0.0)), reverse=True)[:limit]


def stream_summary(report: dict[str, Any]) -> str:
    counts = Counter(
        str(item.get("routed_stream") or item.get("configured_stream") or "")
        for item in report.get("items", [])
    )
    if not counts:
        return "<p>Нет данных для сводки по потокам.</p>"
    rows = "".join(f"<li>{esc(stream_label(slug))}: {count}</li>" for slug, count in counts.most_common())
    return f"<ul>{rows}</ul>"


def card(item: dict[str, Any]) -> str:
    stream = stream_label(item.get("routed_stream") or item.get("configured_stream"))
    source = item.get("feed_title") or item.get("feed_id") or "Публичный источник"
    title = item.get("title") or "Без заголовка"
    url = item.get("url") or ""
    translation = " · нужна русская нормализация" if item.get("translation_required") else ""
    hit_list = item.get("include_hits") or item.get("boost_hits") or item.get("stream_keyword_hits") or []
    hits = ", ".join(str(hit) for hit in hit_list[:5]) if isinstance(hit_list, list) else ""
    why = "Сигнал прошёл первичный source-rule отбор."
    if hits:
        why += f" Ключевые совпадения: {hits}."

    title_html = esc(title)
    if url:
        title_html = f'<a href="{esc(url)}">{title_html}</a>'

    return f"""<article class="card signal-card">
  <p class="label">{esc(stream)} · {esc(source)} · score {score(item.get("final_score"))} · relevance {score(item.get("relevance_score"))}{translation}</p>
  <h3>{title_html}</h3>
  <p>{esc(why)}</p>
  <p><strong>Статус:</strong> публичный source-reported сигнал; это не подтверждённый аналитический вывод и не рекомендация.</p>
</article>"""


def cards_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<article class="card empty-state"><p class="label">Нет данных</p><h3>Нет выбранных сигналов</h3><p>Свежие items не прошли первичный отбор.</p></article>'
    return "\n".join(card(item) for item in items)


def render(report: dict[str, Any]) -> str:
    items = selected_items(report)
    total = len(report.get("items", []))
    selected = len([item for item in report.get("items", []) if item.get("selected")])
    filtered = len([item for item in report.get("items", []) if item.get("source_rule_status") != "accepted_by_source_rules"])
    errors = len(report.get("fetch_errors", []))

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>News Dispatch — Today Radar</title>
  <meta name="description" content="Ежедневная панель публичных сигналов News Dispatch.">
  <link rel="stylesheet" href="styles/main.css">
</head>
<body>
  <header class="masthead compact">
    <a class="backlink" href="index.html">News Dispatch</a>
    <p class="eyebrow">Today Radar · {esc(report.get("date"))}</p>
    <h1>Today Radar</h1>
    <p class="lede">Панель свежих публичных сигналов, прошедших первичный source-rule отбор. Это рабочий радар, а не финальный аналитический выпуск.</p>
    <p class="hero-actions"><a href="daily-radar-ranking-latest.json">Ranking JSON</a><a href="radar/index.html">Live Radar</a><a href="dispatches.html">Архив</a></p>
  </header>
  <main>
    <section class="panel"><h2>Сводка отбора</h2><p>Всего items: {total}. Выбрано: {selected}. Отфильтровано: {filtered}. Ошибок источников: {errors}.</p></section>
    <section class="panel"><h2>Потоки</h2>{stream_summary(report)}</section>
    <section class="panel"><h2>Главные сигналы</h2><p>Карточки ниже ранжированы по итоговому score и relevance. Каждая карточка показывает первичный источник, поток, объяснение отбора и границу интерпретации.</p></section>
    <section class="grid latest-grid" aria-label="Today Radar cards">{cards_block(items)}</section>
    <section class="panel boundary"><h2>Граница интерпретации</h2><p>Факт появления материала в источнике не равен подтверждённому изменению рынка, регулирования или инфраструктуры. Это не инвестиционная, юридическая или операционная рекомендация.</p></section>
  </main>
</body>
</html>
"""


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    write_text(OUTPUT_PATH, render(load_report()))
    print(f"Built {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
