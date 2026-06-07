#!/usr/bin/env python3
"""Prepare the reader-facing News Dispatch site after the base render step.

Only dispatches with `status: published` are exposed on the public site.
Drafts, samples and review files may exist in the repository but are removed
from generated HTML, RSS, sitemap and JSON outputs.
"""

from __future__ import annotations

import html
import json
import re
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DISPATCH_DIR = ROOT / "dispatches"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"

STREAMS = [
    {"slug": "general", "title": "Общий выпуск", "label": "Редакционная проверка", "description": "Междисциплинарная аналитика о технологиях, рынках, вещах, культуре, городе, науке и смежных областях."},
    {"slug": "digital-assets-infrastructure", "title": "Инфраструктура цифровых активов", "label": "Строгая проверка", "description": "Публичная аналитика о регулировании, технологиях, рыночной структуре, доверии и устойчивости инфраструктуры.", "strict": True},
    {"slug": "work", "title": "Рабочий выпуск", "label": "Строгая проверка", "description": "Рыночные и продуктовые сигналы, ИИ, UX, операционные модели и организационные эффекты.", "strict": True},
    {"slug": "finance", "title": "Финансовая среда", "label": "Строгая проверка", "description": "Ставки, банковские продукты, потребительская экономика, ликвидность, подписки и крупные покупки.", "strict": True},
    {"slug": "gear", "title": "Вещи и материальная культура", "label": "Редакционная проверка", "description": "EDC, сумки, часы, инструменты, материалы, ремонтопригодность и критерии повседневного использования."},
    {"slug": "horizon", "title": "Горизонт знаний", "label": "Редакционная проверка", "description": "Наука, системы, материалы, робототехника, биотех, когнитивные науки, HCI и сценарии будущего."},
]

STREAM_BY_SLUG = {stream["slug"]: stream for stream in STREAMS}

TEXT_REPLACEMENTS = {
    "Public-safe editorial briefing system": "Редакционный журнал",
    "Public-safe editorial dispatches across technology, finance, culture, gear, infrastructure, and science.": "Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.",
    "Open dispatch archive": "Архив выпусков",
    "Latest dispatches": "Последние выпуски",
    "Streams": "Потоки",
    "Archive": "Архив",
    "Dispatches": "Выпуски",
    "Strict review": "Строгая проверка",
    "Editorial review": "Редакционная проверка",
    "General Dispatch": "Общий выпуск",
    "Digital Assets Infrastructure": "Инфраструктура цифровых активов",
    "Work Dispatch": "Рабочий выпуск",
    "Finance Dispatch": "Финансовая среда",
    "Gear & Material Culture": "Вещи и материальная культура",
    "No dispatches in this stream yet.": "В этом потоке пока нет выпусков.",
    "Public-safe dispatch archive.": "Архив выпусков.",
    "Обезличенный архив public-safe выпусков.": "Архив выпусков.",
}


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, object] = {}
    list_key: str | None = None
    for line in raw.splitlines():
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
    return meta, body


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def list_value(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def collect_dispatches() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    published: list[dict[str, object]] = []
    hidden: list[dict[str, object]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        output_name = f"{slugify(path)}.html"
        item: dict[str, object] = {
            "title": str(meta.get("title", path.stem)),
            "date": str(meta.get("date", "")),
            "period": str(meta.get("period", "")),
            "stream": str(meta.get("stream", "general")),
            "type": str(meta.get("type", "daily")),
            "status": str(meta.get("status", "draft")),
            "review_level": str(meta.get("review_level", "")),
            "summary": str(meta.get("summary", "")),
            "sources": list_value(meta, "sources"),
            "source_titles": list_value(meta, "source_titles"),
            "source_types": list_value(meta, "source_types"),
            "source_notes": list_value(meta, "source_notes"),
            "media": list_value(meta, "media"),
            "media_titles": list_value(meta, "media_titles"),
            "media_types": list_value(meta, "media_types"),
            "media_notes": list_value(meta, "media_notes"),
            "media_images": list_value(meta, "media_images"),
            "visuals": list_value(meta, "visuals"),
            "visual_titles": list_value(meta, "visual_titles"),
            "visual_types": list_value(meta, "visual_types"),
            "url": f"{BASE_URL}/dispatches/{output_name}",
            "path": f"dispatches/{output_name}",
            "source_path": path.relative_to(ROOT).as_posix(),
        }
        (published if item["status"] == "published" else hidden).append(item)
    published.sort(key=lambda item: (str(item["date"]), str(item["title"])), reverse=True)
    hidden.sort(key=lambda item: (str(item["date"]), str(item["title"])), reverse=True)
    return published, hidden


def stream_title(slug: object) -> str:
    return str(STREAM_BY_SLUG.get(str(slug), {"title": str(slug)})["title"])


def clean_copy(text: str) -> str:
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def dispatch_card(item: dict[str, object], css_class: str = "card", prefix: str = "") -> str:
    href = f"{prefix}{html.escape(str(item['path']))}"
    return f"""<article class=\"{css_class}\">
  <p class=\"label\">{html.escape(stream_title(item['stream']))} · {html.escape(str(item['date']))}</p>
  <h3><a href=\"{href}\">{html.escape(str(item['title']))}</a></h3>
  <p>{html.escape(str(item['summary']))}</p>
</article>"""


def stream_card(stream: dict[str, object], count: int, prefix: str = "") -> str:
    strict_class = " strict" if stream.get("strict") else ""
    href = f"{prefix}streams/{html.escape(str(stream['slug']))}.html"
    return f"""<article class=\"stream-card{strict_class}\">
  <p class=\"label\">{html.escape(str(stream['label']))} · {count} выпусков</p>
  <h3><a href=\"{href}\">{html.escape(str(stream['title']))}</a></h3>
  <p>{html.escape(str(stream['description']))}</p>
</article>"""


def empty_notice() -> str:
    return "<section class=\"empty-state\"><h2>Выпуски готовятся</h2><p>Редакция готовит первые чистовые материалы. Черновики и технические тесты не публикуются.</p></section>"


def render_homepage(items: list[dict[str, object]]) -> None:
    counts = {str(stream["slug"]): 0 for stream in STREAMS}
    for item in items:
        counts[str(item["stream"])] = counts.get(str(item["stream"]), 0) + 1
    stream_cards = "\n".join(stream_card(stream, counts.get(str(stream["slug"]), 0)) for stream in STREAMS)
    if items:
        featured = items[0]
        latest = [item for item in items if item != featured][:4]
        main_content = f"""<section class=\"featured-section\" aria-label=\"Главный выпуск\"><p class=\"section-kicker\">Главный выпуск</p>{dispatch_card(featured, css_class="featured-card")}</section><section class=\"panel section-header\"><h2>Последние выпуски</h2><p>Новые материалы из редакционных потоков.</p></section><section class=\"grid latest-grid\" aria-label=\"Последние выпуски\">{''.join(dispatch_card(item) for item in latest)}</section>"""
    else:
        main_content = empty_notice()
    text = f"""<!doctype html>
<html lang=\"ru\">
<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>News Dispatch</title><meta name=\"description\" content=\"Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.\"><link rel=\"alternate\" type=\"application/rss+xml\" title=\"News Dispatch RSS\" href=\"{BASE_URL}/rss.xml\"><link rel=\"stylesheet\" href=\"styles/main.css\"><link rel=\"stylesheet\" href=\"styles/reader.css\"></head>
<body><header class=\"masthead homepage-hero\"><p class=\"eyebrow\">Редакционный журнал</p><h1>News Dispatch</h1><p class=\"lede\">Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке.</p><nav class=\"hero-actions\" aria-label=\"Основная навигация\"><a href=\"dispatches.html\">Архив выпусков</a><a href=\"streams/index.html\">Потоки</a><a href=\"rss.xml\">RSS</a></nav></header><main>{main_content}<section class=\"panel section-header\"><h2>Потоки</h2><p>Темы, форматы и направления редакционной аналитики.</p></section><section class=\"stream-grid\" aria-label=\"Редакционные потоки\">{stream_cards}</section></main></body></html>"""
    (SITE_DIR / "index.html").write_text(text, encoding="utf-8")


def render_archive(items: list[dict[str, object]]) -> None:
    cards = "\n".join(dispatch_card(item) for item in items) if items else empty_notice()
    text = f"""<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>News Dispatch — Выпуски</title><meta name=\"description\" content=\"Архив выпусков.\"><link rel=\"stylesheet\" href=\"styles/main.css\"><link rel=\"stylesheet\" href=\"styles/reader.css\"></head><body><header class=\"masthead compact\"><a class=\"backlink\" href=\"index.html\">News Dispatch</a><p class=\"eyebrow\">Архив</p><h1>Выпуски</h1><p class=\"lede\">Архив опубликованных материалов.</p></header><main><section class=\"grid\">{cards}</section></main></body></html>"""
    (SITE_DIR / "dispatches.html").write_text(text, encoding="utf-8")


def render_stream_pages(items: list[dict[str, object]]) -> None:
    stream_dir = SITE_DIR / "streams"
    stream_dir.mkdir(parents=True, exist_ok=True)
    index_cards = []
    for stream in STREAMS:
        stream_items = [item for item in items if item.get("stream") == stream["slug"]]
        index_cards.append(stream_card(stream, len(stream_items), prefix="../"))
        cards = "\n".join(dispatch_card(item, prefix="../") for item in stream_items) if stream_items else "<p>В этом потоке пока нет выпусков.</p>"
        page = f"""<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>News Dispatch — {html.escape(str(stream['title']))}</title><meta name=\"description\" content=\"{html.escape(str(stream['description']))}\"><link rel=\"stylesheet\" href=\"../styles/main.css\"><link rel=\"stylesheet\" href=\"../styles/reader.css\"></head><body><header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">News Dispatch</a><p class=\"eyebrow\">{html.escape(str(stream['label']))}</p><h1>{html.escape(str(stream['title']))}</h1><p class=\"lede\">{html.escape(str(stream['description']))}</p></header><main><section class=\"grid\">{cards}</section></main></body></html>"""
        (stream_dir / f"{stream['slug']}.html").write_text(page, encoding="utf-8")
    index = f"""<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>News Dispatch — Потоки</title><meta name=\"description\" content=\"Редакционные потоки.\"><link rel=\"stylesheet\" href=\"../styles/main.css\"><link rel=\"stylesheet\" href=\"../styles/reader.css\"></head><body><header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">News Dispatch</a><p class=\"eyebrow\">Потоки</p><h1>Потоки</h1><p class=\"lede\">Темы, форматы и направления редакционной аналитики.</p></header><main><section class=\"grid\">{''.join(index_cards)}</section></main></body></html>"""
    (stream_dir / "index.html").write_text(index, encoding="utf-8")


def remove_hidden_pages(items: list[dict[str, object]]) -> None:
    for item in items:
        target = SITE_DIR / str(item["path"])
        if target.exists():
            target.unlink()


def at(values: list[str], index: int, default: str = "") -> str:
    return values[index] if index < len(values) else default


def cards_from_parallel_lists(urls: list[str], titles: list[str], types: list[str], notes: list[str] | None = None, images: list[str] | None = None, css_extra: str = "") -> str:
    notes = notes or []
    images = images or []
    cards = []
    for index, url in enumerate(urls):
        title = at(titles, index, url)
        source_type = at(types, index, "Источник")
        note = at(notes, index, "")
        image = at(images, index, "")
        image_html = f'<a href="{html.escape(url)}"><img class="reader-thumb" src="{html.escape(image)}" alt="{html.escape(title)}" loading="lazy" referrerpolicy="no-referrer"></a>' if image else ""
        note_html = f"<p>{html.escape(note)}</p>" if note else ""
        cards.append(f"""<article class=\"source-card {css_extra}\">{image_html}<p class=\"label\">{html.escape(source_type)}</p><h3><a href=\"{html.escape(url)}\">{html.escape(title)}</a></h3>{note_html}</article>""")
    return "".join(cards)


def add_reader_blocks(items: list[dict[str, object]]) -> None:
    for item in items:
        page = SITE_DIR / str(item["path"])
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        if "<section class=\"sources-block\"" in text:
            text = re.sub(r'<section class="sources-block">.*?</section>', '', text, flags=re.S)
        blocks = []
        media_cards = cards_from_parallel_lists(list(item["media"]), list(item["media_titles"]), list(item["media_types"]), notes=list(item["media_notes"]), images=list(item["media_images"]), css_extra="media-card")
        source_cards = cards_from_parallel_lists(list(item["sources"]), list(item["source_titles"]), list(item["source_types"]), notes=list(item["source_notes"]))
        if media_cards:
            blocks.append(f"<section class=\"sources-block reader-assets\"><h2>Материалы и медиа</h2><div class=\"source-grid reader-grid\">{media_cards}</div></section>")
        if source_cards:
            blocks.append(f"<section class=\"sources-block reader-assets\"><h2>Источники</h2><div class=\"source-grid reader-grid\">{source_cards}</div></section>")
        if blocks and "reader-assets" not in text:
            text = text.replace("  </main>", f"    {''.join(blocks)}\n  </main>", 1)
            page.write_text(text, encoding="utf-8")


def page_url(path: Path) -> str:
    rel = path.relative_to(SITE_DIR).as_posix()
    return f"{BASE_URL}/" if rel == "index.html" else f"{BASE_URL}/{rel}"


def add_reader_css(text: str, path: Path) -> str:
    rel = path.relative_to(SITE_DIR).as_posix()
    prefix = "../" if rel.startswith("streams/") or rel.startswith("dispatches/") else ""
    href = f"{prefix}styles/reader.css"
    if href in text:
        return text
    return text.replace("</head>", f'<link rel="stylesheet" href="{href}"></head>', 1)


def enhance_html(path: Path) -> None:
    text = clean_copy(path.read_text(encoding="utf-8"))
    if 'property="og:title"' not in text:
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        title = html.unescape(title_match.group(1)) if title_match else "News Dispatch"
        description_match = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        description = html.unescape(description_match.group(1)) if description_match else "Редакционный журнал о технологиях, рынках, продуктах, инфраструктуре, вещах, городе, культуре и науке."
        meta = f"""  <link rel=\"canonical\" href=\"{html.escape(page_url(path))}\"><meta property=\"og:type\" content=\"article\"><meta property=\"og:site_name\" content=\"News Dispatch\"><meta property=\"og:title\" content=\"{html.escape(title)}\"><meta property=\"og:description\" content=\"{html.escape(description)}\"><meta property=\"og:url\" content=\"{html.escape(page_url(path))}\"><meta name=\"twitter:card\" content=\"summary\"><meta name=\"twitter:title\" content=\"{html.escape(title)}\"><meta name=\"twitter:description\" content=\"{html.escape(description)}\">"""
        text = text.replace("<link rel=\"stylesheet\"", meta + "<link rel=\"stylesheet\"", 1)
    text = add_reader_css(text, path)
    path.write_text(text, encoding="utf-8")


def write_rss(items: list[dict[str, object]]) -> None:
    rss_items = []
    for item in items[:20]:
        rss_items.append(f"<item><title>{html.escape(str(item['title']))}</title><link>{html.escape(str(item['url']))}</link><guid>{html.escape(str(item['url']))}</guid><pubDate>{formatdate(usegmt=True)}</pubDate><description>{html.escape(str(item['summary']))}</description></item>")
    (SITE_DIR / "rss.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>News Dispatch</title><link>{BASE_URL}/</link><description>Редакционный журнал.</description><language>ru</language>{''.join(rss_items)}</channel></rss>", encoding="utf-8")


def write_sitemap(items: list[dict[str, object]]) -> None:
    urls = [f"{BASE_URL}/", f"{BASE_URL}/dispatches.html", f"{BASE_URL}/rss.xml", f"{BASE_URL}/sitemap.xml", f"{BASE_URL}/streams/index.html"]
    urls.extend(f"{BASE_URL}/streams/{stream['slug']}.html" for stream in STREAMS)
    urls.extend(str(item["url"]) for item in items)
    entries = "".join(f"<url><loc>{html.escape(url)}</loc></url>" for url in urls)
    (SITE_DIR / "sitemap.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">{entries}</urlset>", encoding="utf-8")


def write_robots() -> None:
    (SITE_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")


def write_dispatches_json(items: list[dict[str, object]]) -> None:
    (SITE_DIR / "dispatches.json").write_text(json.dumps({"dispatches": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    items, hidden = collect_dispatches()
    remove_hidden_pages(hidden)
    render_homepage(items)
    render_archive(items)
    render_stream_pages(items)
    add_reader_blocks(items)
    for html_path in SITE_DIR.rglob("*.html"):
        enhance_html(html_path)
    write_rss(items)
    write_sitemap(items)
    write_robots()
    write_dispatches_json(items)
    print("Enhanced News Dispatch site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
