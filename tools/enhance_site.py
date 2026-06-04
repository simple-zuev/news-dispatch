#!/usr/bin/env python3
"""Enhance rendered News Dispatch site.

Adds:
- Russian public-facing copy normalization;
- Homepage v2 editorial hierarchy;
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

STREAMS = [
    {
        "slug": "general",
        "title": "Общий выпуск",
        "label": "Редакционная проверка",
        "description": "Междисциплинарная аналитика о технологиях, рынках, вещах, культуре, городе, науке и смежных областях.",
    },
    {
        "slug": "digital-assets-infrastructure",
        "title": "Инфраструктура цифровых активов",
        "label": "Строгая проверка",
        "description": "Публичная аналитика о регулировании, технологиях, рыночной структуре, доверии и устойчивости инфраструктуры.",
        "strict": True,
    },
    {
        "slug": "work",
        "title": "Рабочий выпуск",
        "label": "Строгая проверка",
        "description": "Рыночные и продуктовые сигналы, ИИ, UX, операционные модели и организационные эффекты.",
        "strict": True,
    },
    {
        "slug": "finance",
        "title": "Финансовая среда",
        "label": "Строгая проверка",
        "description": "Ставки, банковские продукты, потребительская экономика, ликвидность, подписки и крупные покупки.",
        "strict": True,
    },
    {
        "slug": "gear",
        "title": "Вещи и материальная культура",
        "label": "Редакционная проверка",
        "description": "EDC, сумки, часы, инструменты, материалы, ремонтопригодность и критерии повседневного использования.",
    },
    {
        "slug": "horizon",
        "title": "Горизонт знаний",
        "label": "Редакционная проверка",
        "description": "Наука, системы, материалы, робототехника, биотех, когнитивные науки, HCI и сценарии будущего.",
    },
]

STREAM_BY_SLUG = {stream["slug"]: stream for stream in STREAMS}

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
    "Everything committed to the repository is treated as public. Private context may calibrate selection, but never appears as disclosure.": "Всё, что попадает в репозиторий, считается публичным. Закрытый контекст не раскрывается в тексте.",
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


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def collect_dispatches() -> list[dict[str, str]]:
    items = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        output_name = f"{slugify(path)}.html"
        item = {
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
        item["is_sample"] = "true" if item["period"] == "sample" or "sample" in item["path"] else "false"
        items.append(item)
    items.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
    return items


def stream_title(slug: str) -> str:
    return STREAM_BY_SLUG.get(slug, {"title": slug})["title"]


def badge(item: dict[str, str]) -> str:
    if item.get("is_sample") == "true":
        return '<span class="badge badge-sample">Sample</span>'
    return '<span class="badge badge-issue">Issue</span>'


def dispatch_card(item: dict[str, str], css_class: str = "card") -> str:
    sample_class = " is-sample" if item.get("is_sample") == "true" else ""
    return f"""<article class=\"{css_class}{sample_class}\">
  <div class=\"meta-row\">
    <p class=\"label\">{html.escape(stream_title(item['stream']))} · {html.escape(item['date'])}</p>
    {badge(item)}
  </div>
  <h3><a href=\"{html.escape(item['path'])}\">{html.escape(item['title'])}</a></h3>
  <p>{html.escape(item['summary'])}</p>
</article>"""


def stream_card(stream: dict[str, str], count: int) -> str:
    strict_class = " strict" if stream.get("strict") else ""
    return f"""<article class=\"stream-card{strict_class}\">
  <p class=\"label\">{html.escape(stream['label'])} · {count} выпусков</p>
  <h3><a href=\"streams/{html.escape(stream['slug'])}.html\">{html.escape(stream['title'])}</a></h3>
  <p>{html.escape(stream['description'])}</p>
</article>"""


def render_homepage_v2(items: list[dict[str, str]]) -> None:
    real_items = [item for item in items if item.get("is_sample") != "true"]
    featured = real_items[0] if real_items else items[0]
    latest = [item for item in items if item != featured][:4]

    counts = {stream["slug"]: 0 for stream in STREAMS}
    for item in items:
        counts[item["stream"]] = counts.get(item["stream"], 0) + 1

    latest_cards = "\n".join(dispatch_card(item) for item in latest)
    stream_cards = "\n".join(stream_card(stream, counts.get(stream["slug"], 0)) for stream in STREAMS)

    html_text = f"""<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>News Dispatch</title>
  <meta name=\"description\" content=\"Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.\">
  <link rel=\"alternate\" type=\"application/rss+xml\" title=\"News Dispatch RSS\" href=\"{BASE_URL}/rss.xml\">
  <link rel=\"stylesheet\" href=\"styles/main.css\">
</head>
<body>
  <header class=\"masthead homepage-hero\">
    <p class=\"eyebrow\">Редакционный журнал</p>
    <h1>News Dispatch</h1>
    <p class=\"lede\">Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.</p>
    <nav class=\"hero-actions\" aria-label=\"Основная навигация\">
      <a href=\"dispatches.html\">Архив выпусков</a>
      <a href=\"streams/index.html\">Потоки</a>
      <a href=\"rss.xml\">RSS</a>
    </nav>
  </header>

  <main>
    <section class=\"featured-section\" aria-label=\"Главный выпуск\">
      <p class=\"section-kicker\">Главный выпуск</p>
      {dispatch_card(featured, css_class="featured-card")}
    </section>

    <section class=\"panel section-header\">
      <h2>Последние выпуски</h2>
      <p>Новые материалы из редакционных потоков. Демонстрационные материалы помечены как sample.</p>
    </section>

    <section class=\"grid latest-grid\" aria-label=\"Последние выпуски\">
      {latest_cards}
    </section>

    <section class=\"panel section-header\">
      <h2>Потоки</h2>
      <p>Потоки разделяют темы, уровень проверки, источниковую модель и правила публикации.</p>
    </section>

    <section class=\"stream-grid\" aria-label=\"Редакционные потоки\">
      {stream_cards}
    </section>

    <footer class=\"quiet-footer\">
      <p><strong>Граница публикации.</strong> Все материалы строятся как публичная редакционная аналитика. Закрытый контекст не раскрывается в тексте.</p>
    </footer>
  </main>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(html_text, encoding="utf-8")


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


def write_dispatches_json(items: list[dict[str, str]]) -> None:
    (SITE_DIR / "dispatches.json").write_text(json.dumps({"dispatches": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    items = collect_dispatches()
    render_homepage_v2(items)
    for html_path in SITE_DIR.rglob("*.html"):
        enhance_html(html_path)
    write_robots()
    write_dispatches_json(items)
    print("Enhanced News Dispatch site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
