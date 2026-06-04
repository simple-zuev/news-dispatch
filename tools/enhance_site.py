#!/usr/bin/env python3
"""Enhance rendered News Dispatch site.

Adds:
- Russian public-facing copy normalization;
- OpenGraph and Twitter meta tags to rendered HTML;
- robots.txt;
- dispatches.json machine-readable index.

No external dependencies and no network access.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DISPATCH_DIR = ROOT / "dispatches"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"

PUBLIC_COPY_REPLACEMENTS = {
    "Public-safe editorial briefing system": "Публичная редакционная система",
    "Public-safe editorial dispatches across technology, finance, culture, gear, infrastructure, and science.": "Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.",
    "Аналитический хаб для обезличенных выпусков о технологиях, рынках, инфраструктуре, вещах, городе, культуре и научном горизонте.": "Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.",
    "Open dispatch archive": "Архив выпусков",
    "Latest dispatches": "Последние выпуски",
    "Editorial model": "Редакционная модель",
    "Each dispatch turns public external signals into structured analysis: signal, verification, context, mechanism, second-order effects, decision criteria, and new knowledge.": "Каждый выпуск превращает публичные внешние сигналы в структурированную аналитику: сигнал, проверка, контекст, механизм влияния, вторичные эффекты, критерии оценки и новое знание.",
    "Streams": "Потоки",
    "Потоки помогают разделять разные типы аналитики, review level и источниковую модель.": "Потоки разделяют темы, уровень проверки, источниковую модель и правила публикации.",
    "Publication boundary": "Граница публикации",
    "Everything committed to the repository is treated as public. Private context may calibrate selection, but never appears as disclosure.": "Всё, что попадает в репозиторий, считается публичным. Личный или рабочий контекст может влиять на отбор тем, но не раскрывается в тексте.",
    "Archive": "Архив",
    "Dispatches": "Выпуски",
    "Public-safe dispatch archive.": "Архив публично-безопасных выпусков.",
    "Обезличенный архив public-safe выпусков.": "Архив публично-безопасных выпусков.",
    "Editorial stream index.": "Индекс редакционных потоков.",
    "Потоки разделяют темы, уровни проверки и правила публикации.": "Потоки разделяют темы, уровень проверки и правила публикации.",
    "Strict review": "Строгая проверка",
    "Editorial review": "Редакционная проверка",
    "General Dispatch": "Общий выпуск",
    "Digital Assets Infrastructure": "Инфраструктура цифровых активов",
    "Work Dispatch": "Рабочий выпуск",
    "Finance Dispatch": "Финансовая среда",
    "Home & Environment": "Дом и среда",
    "Gear & Material Culture": "Вещи и материальная культура",
    "City & Culture": "Город и культура",
    "Audio & Creative Tech": "Аудио и креативные технологии",
    "Horizon Notes": "Горизонт знаний",
    "Multi-domain analysis across technology, finance, gear, culture, cities, science, and adjacent fields.": "Междисциплинарная аналитика о технологиях, рынках, вещах, культуре, городе, науке и смежных областях.",
    "Public-source analysis of regulation, restrictions, technology, market structure, public competitors, vendor landscape, security, trust, and infrastructure resilience.": "Аналитика по публичным источникам о регулировании, ограничениях, технологиях, рыночной структуре, публичных конкурентах, поставщиках, безопасности, доверии и устойчивости инфраструктуры.",
    "Public market and product signals, AI, UX, operating models, and organizational implications without internal company or product data.": "Публичные рыночные и продуктовые сигналы, ИИ, UX, операционные модели и организационные эффекты без внутренних данных компаний и продуктов.",
    "Rates, banking products, consumer economics, liquidity, subscriptions, and large-purchase context in educational framing.": "Ставки, банковские продукты, потребительская экономика, ликвидность, подписки и крупные покупки в образовательной рамке.",
    "Home, smart home, energy, safety, infrastructure patterns, comfort, and practical systems.": "Дом, умная среда, энергия, безопасность, инфраструктурные паттерны, комфорт и практические системы.",
    "EDC, bags, watches, tools, apparel, materials, repairability, ownership, and everyday-use criteria.": "EDC, сумки, часы, инструменты, одежда, материалы, ремонтопригодность, владение и критерии повседневного использования.",
    "City life, culture, media, events, urban services, and lifestyle signals.": "Городская жизнь, культура, медиа, события, городские сервисы и повседневные сигналы.",
    "DJ gear, audio, MIDI, music production, performance interfaces, and creator tools.": "DJ-оборудование, аудио, MIDI, музыкальное производство, исполнительские интерфейсы и инструменты создателей.",
    "Science, systems, materials, robotics, biotech, cognition, HCI, and futures.": "Наука, системы, материалы, робототехника, биотех, когнитивные науки, HCI и сценарии будущего.",
    "No dispatches in this stream yet.": "В этом потоке пока нет выпусков.",
}


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, str] = {}
    list_key: str | None = None
    lists: dict[str, list[str]] = {}

    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            lists.setdefault(list_key, []).append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value == "":
            list_key = key
            meta[key] = ""
        else:
            list_key = None
            meta[key] = value

    for key, values in lists.items():
        meta[key] = json.dumps(values, ensure_ascii=False)
    return meta, body


def localize_public_copy(text: str) -> str:
    for source, target in PUBLIC_COPY_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def page_url(path: Path) -> str:
    rel = path.relative_to(SITE_DIR).as_posix()
    if rel == "index.html":
        return f"{BASE_URL}/"
    return f"{BASE_URL}/{rel}"


def extract_title(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else "News Dispatch"


def extract_description(text: str) -> str:
    match = re.search(r'<meta name="description" content="(.*?)">', text, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else "Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке."


def enhance_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = localize_public_copy(text)
    if 'property="og:title"' in text:
        path.write_text(text, encoding="utf-8")
        return
    title = extract_title(text)
    description = extract_description(text)
    url = page_url(path)
    meta = f"""  <link rel=\"canonical\" href=\"{html.escape(url)}\">
  <meta property=\"og:type\" content=\"article\">
  <meta property=\"og:site_name\" content=\"News Dispatch\">
  <meta property=\"og:title\" content=\"{html.escape(title)}\">
  <meta property=\"og:description\" content=\"{html.escape(description)}\">
  <meta property=\"og:url\" content=\"{html.escape(url)}\">
  <meta name=\"twitter:card\" content=\"summary\">
  <meta name=\"twitter:title\" content=\"{html.escape(title)}\">
  <meta name=\"twitter:description\" content=\"{html.escape(description)}\">
"""
    text = text.replace("  <link rel=\"stylesheet\"", meta + "  <link rel=\"stylesheet\"", 1)
    path.write_text(text, encoding="utf-8")


def write_robots() -> None:
    (SITE_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def write_dispatches_json() -> None:
    items = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        output_name = f"{slugify(path)}.html"
        items.append(
            {
                "title": meta.get("title", path.stem),
                "date": meta.get("date", ""),
                "period": meta.get("period", ""),
                "stream": meta.get("stream", "general"),
                "type": meta.get("type", "daily"),
                "review_level": meta.get("review_level", ""),
                "summary": meta.get("summary", ""),
                "public_safe": meta.get("public_safe", ""),
                "private_context_used": meta.get("private_context_used", ""),
                "url": f"{BASE_URL}/dispatches/{output_name}",
                "path": f"dispatches/{output_name}",
                "source_path": path.relative_to(ROOT).as_posix(),
            }
        )
    items.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
    (SITE_DIR / "dispatches.json").write_text(json.dumps({"dispatches": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    for html_path in SITE_DIR.rglob("*.html"):
        enhance_html(html_path)
    write_robots()
    write_dispatches_json()
    print("Enhanced News Dispatch site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
