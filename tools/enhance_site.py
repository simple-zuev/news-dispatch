#!/usr/bin/env python3
"""Prepare the reader-facing News Dispatch site after the base render step."""

from __future__ import annotations

import html
import json
import re
from email.utils import formatdate
from pathlib import Path
from typing import Any

from build_site_status import main as build_site_status
from stream_registry import streams as registry_streams

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DISPATCH_DIR = ROOT / "dispatches"
RUBRICS_PATH = ROOT / "data" / "rubrics.json"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"
EMPTY_SCALARS = {"", "[]", "null", "None", "none"}
HTML_TAG_RE = re.compile(r"(<[^>]+>)")

TEXT_REPLACEMENTS = {
    "News Dispatch": "Дайджест",
    "Public-safe editorial briefing system": "Публичный аналитический обзор",
    "Public-safe editorial dispatches across technology, finance, culture, gear, infrastructure, and science.": "Публичный аналитический обзор по рынкам, технологиям, ИИ, криптофинансам, городской среде, вещам, аудио и науке.",
    "Персональный reader/radar": "Публичный аналитический обзор",
    "Личный reader/radar": "Публичный аналитический обзор",
    "Личный статический радар по зонам интереса: live-сигналы в течение дня, тематические полки и аналитические выпуски, когда есть что синтезировать.": "Публичные события, документы и рыночные сигналы с кратким разбором: что произошло, почему это важно и что требует дополнительной проверки.",
    "Live Radar": "Свежие сигналы",
    "Live signals": "Свежие сигналы",
    "Live signal": "Сигнал",
    "live-radar": "радар",
    "Потоки": "Темы",
    "Dispatch streams": "Темы",
    "Рубрики": "Рубрики анализа",
    "Dispatch rubrics": "Рубрики анализа",
    "Последние выпуски": "Новые материалы",
    "Latest dispatches": "Новые материалы",
    "Итоговые материалы и тематические synthesis-выпуски.": "Опубликованные материалы с источниками, контекстом и обозначенными ограничениями.",
    "Open dispatch archive": "Архив материалов",
    "Архив выпусков": "Архив материалов",
    "Dispatches": "Материалы",
    "Выпуски": "Материалы",
    "выпусков": "материалов",
    "В этом потоке пока нет выпусков.": "В этой теме пока нет опубликованных материалов.",
    "В этом потоке пока нет опубликованных выпусков.": "В этой теме пока нет опубликованных материалов.",
    "В этом потоке сейчас нет live-сигналов.": "В этой теме сейчас нет свежих сигналов.",
    "Reader-facing материалы, прошедшие публикационный контур.": "Материалы, прошедшие редакционную проверку.",
    "Опубликованные выпуски": "Опубликованные материалы",
    "Публичный сигнал из live-radar. Это не опубликованный выпуск и не аналитический вывод.": "Публичный сигнал для проверки. Это не готовый аналитический вывод.",
    "Открыть Live Radar": "Открыть свежие сигналы",
    "AI-инфраструктура": "ИИ-инфраструктура",
    "AI-конкуренция": "конкуренция в сфере ИИ",
    "AI-поиск": "ИИ-поиск",
    "AI PC": "ИИ-компьютеры",
    "AI,": "ИИ,",
    " AI ": " ИИ ",
    "Reg Watch": "Регуляторный контур",
    "Market Structure": "Структура рынка",
    "Infrastructure": "Инфраструктура",
    "Product / Platform": "Продукт и платформа",
    "Security / Abuse": "Безопасность и злоупотребления",
    "Research / Evidence": "Исследования и доказательная база",
    "Consumer / Use": "Пользовательская практика",
    "City / Culture": "Город и культура",
    "Weak Signals": "Слабые сигналы",
    "official_source": "официальный источник",
    "business_media": "деловое медиа",
    "public_media": "публичное медиа",
    "specialized_media": "отраслевое медиа",
    "research_media": "исследовательский источник",
    "limited_publication": "ограниченная публикация",
    "reg-brief": "регуляторная заметка",
    "market-structure-note": "заметка о структуре рынка",
    "infrastructure-radar": "инфраструктурный обзор",
    "source-dossier": "досье источников",
    "daily-radar-review": "обзор сигналов",
}


def load_streams() -> list[dict[str, Any]]:
    return [
        {
            "slug": str(item["slug"]),
            "title": str(item["title"]),
            "label": str(item.get("label", "Редакционная проверка")),
            "description": str(item.get("description", "")),
            "strict": bool(item.get("strict", False)),
        }
        for item in registry_streams()
    ]


def load_rubrics() -> list[dict[str, str]]:
    if not RUBRICS_PATH.exists():
        return []
    data = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
    return [
        {"slug": str(item.get("slug", "")), "title": str(item.get("title", item.get("slug", "")))}
        for item in data.get("rubrics", [])
        if str(item.get("slug", "")).strip()
    ]


STREAMS = load_streams()
RUBRICS = load_rubrics()
STREAM_BY_SLUG = {stream["slug"]: stream for stream in STREAMS}


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
        return [str(item) for item in value if str(item).strip() not in EMPTY_SCALARS]
    scalar = str(value).strip()
    if scalar in EMPTY_SCALARS:
        return []
    return [scalar]


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
            "primary_rubric": str(meta.get("primary_rubric", "")),
            "issue_type": str(meta.get("issue_type", "")),
            "publication_mode": str(meta.get("publication_mode", "")),
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


def replace_public_text(text: str) -> str:
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def clean_copy(text: str) -> str:
    """Apply reader copy substitutions only to visible text, not HTML attributes.

    Older cleanup replaced slug-like strings globally and could mutate href/src
    values, for example `infrastructure-radar.html` inside a generated link.
    Splitting on tags is intentionally conservative: tag attributes stay byte-for-byte
    intact while visible text still gets reader-facing Russian labels.
    """
    parts = HTML_TAG_RE.split(text)
    for index, part in enumerate(parts):
        if part.startswith("<") and part.endswith(">"):
            continue
        parts[index] = replace_public_text(part)
    return "".join(parts)


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
        if not url or url in EMPTY_SCALARS:
            continue
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
            text = re.sub(r'<section class="sources-block">.*?</section>', "", text, flags=re.S)
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
    prefix = "../" if "/" in rel else ""
    href = f"{prefix}styles/reader.css"
    if href in text:
        return text
    return text.replace("</head>", f'<link rel="stylesheet" href="{href}"></head>', 1)


def enhance_html(path: Path) -> None:
    raw_text = path.read_text(encoding="utf-8")
    rel = path.relative_to(SITE_DIR).as_posix()
    preserve_reader_copy = rel in {"index.html", "sources/index.html"}
    text = raw_text if preserve_reader_copy else clean_copy(raw_text)
    if 'property="og:title"' not in text:
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        site_name = "News Dispatch" if rel == "sources/index.html" else "Дайджест"
        title = html.unescape(title_match.group(1)) if title_match else site_name
        description_match = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        description = html.unescape(description_match.group(1)) if description_match else "Публичный аналитический обзор."
        meta = f"""  <link rel=\"canonical\" href=\"{html.escape(page_url(path))}\"><meta property=\"og:type\" content=\"article\"><meta property=\"og:site_name\" content=\"{site_name}\"><meta property=\"og:title\" content=\"{html.escape(title)}\"><meta property=\"og:description\" content=\"{html.escape(description)}\"><meta property=\"og:url\" content=\"{html.escape(page_url(path))}\"><meta name=\"twitter:card\" content=\"summary\"><meta name=\"twitter:title\" content=\"{html.escape(title)}\"><meta name=\"twitter:description\" content=\"{html.escape(description)}\">"""
        text = text.replace("<link rel=\"stylesheet\"", meta + "<link rel=\"stylesheet\"", 1)
    text = add_reader_css(text, path)
    path.write_text(text, encoding="utf-8")


def write_rss(items: list[dict[str, object]]) -> None:
    rss_items = []
    for item in items[:20]:
        rss_items.append(f"<item><title>{html.escape(str(item['title']))}</title><link>{html.escape(str(item['url']))}</link><guid>{html.escape(str(item['url']))}</guid><pubDate>{formatdate(usegmt=True)}</pubDate><description>{html.escape(str(item['summary']))}</description></item>")
    (SITE_DIR / "rss.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\"><channel><title>Дайджест</title><link>{BASE_URL}/</link><description>Публичный аналитический обзор.</description><language>ru</language>{''.join(rss_items)}</channel></rss>", encoding="utf-8")


def write_sitemap(items: list[dict[str, object]]) -> None:
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/news/index.html",
        f"{BASE_URL}/digests/index.html",
        f"{BASE_URL}/today.html",
        f"{BASE_URL}/sources/index.html",
        f"{BASE_URL}/dispatches.html",
        f"{BASE_URL}/rss.xml",
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/streams/index.html",
        f"{BASE_URL}/rubrics/index.html",
        f"{BASE_URL}/radar/index.html",
        f"{BASE_URL}/status.json",
    ]
    urls.extend(f"{BASE_URL}/streams/{stream['slug']}.html" for stream in STREAMS)
    urls.extend(f"{BASE_URL}/news/{stream['slug']}.html" for stream in STREAMS)
    urls.extend(f"{BASE_URL}/radar/{stream['slug']}.html" for stream in STREAMS)
    urls.extend(f"{BASE_URL}/rubrics/{rubric['slug']}.html" for rubric in RUBRICS)
    urls.extend(str(item["url"]) for item in items)
    entries = "".join(f"<url><loc>{html.escape(url)}</loc></url>" for url in dict.fromkeys(urls))
    (SITE_DIR / "sitemap.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">{entries}</urlset>", encoding="utf-8")


def write_robots() -> None:
    (SITE_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")


def write_dispatches_json(items: list[dict[str, object]]) -> None:
    (SITE_DIR / "dispatches.json").write_text(json.dumps({"dispatches": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    items, hidden = collect_dispatches()
    remove_hidden_pages(hidden)
    add_reader_blocks(items)
    for html_path in SITE_DIR.rglob("*.html"):
        enhance_html(html_path)
    write_rss(items)
    write_sitemap(items)
    write_robots()
    write_dispatches_json(items)
    build_site_status()
    print("Enhanced News Dispatch site.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
