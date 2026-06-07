#!/usr/bin/env python3
"""Render topic-first stream index and stream pages from the shared registry."""

from __future__ import annotations

import html
import re
from pathlib import Path

from stream_registry import stream_by_slug, streams

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DISPATCH_DIR = ROOT / "dispatches"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"
STREAMS = streams()
STREAM_BY_SLUG = stream_by_slug()


def parse_front_matter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    raw = text[4:end]
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
    return meta


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def collect_dispatches() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta = parse_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) != "published":
            continue
        output_name = f"{slugify(path)}.html"
        items.append(
            {
                "title": str(meta.get("title", path.stem)),
                "date": str(meta.get("date", "")),
                "stream": str(meta.get("stream", "general")),
                "summary": str(meta.get("summary", "")),
                "path": f"dispatches/{output_name}",
                "url": f"{BASE_URL}/dispatches/{output_name}",
            }
        )
    return sorted(items, key=lambda item: (item["date"], item["title"]), reverse=True)


def card(item: dict[str, str], prefix: str = "") -> str:
    stream = STREAM_BY_SLUG.get(item["stream"], {"title": item["stream"]})
    return f"""<article class=\"card\"><p class=\"label\">{html.escape(str(stream['title']))} · {html.escape(item['date'])}</p><h3><a href=\"{prefix}{html.escape(item['path'])}\">{html.escape(item['title'])}</a></h3><p>{html.escape(item['summary'])}</p></article>"""


def stream_card(stream: dict[str, object], count: int, prefix: str = "") -> str:
    strict_class = " strict" if stream.get("strict") else ""
    return f"""<article class=\"stream-card{strict_class}\"><p class=\"label\">{html.escape(str(stream['label']))} · {count} выпусков</p><h3><a href=\"{prefix}streams/{html.escape(str(stream['slug']))}.html\">{html.escape(str(stream['title']))}</a></h3><p>{html.escape(str(stream['description']))}</p></article>"""


def head(title: str, description: str, prefix: str = "") -> str:
    return f"""<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>{html.escape(title)}</title><meta name=\"description\" content=\"{html.escape(description)}\"><link rel=\"stylesheet\" href=\"{prefix}styles/main.css\"><link rel=\"stylesheet\" href=\"{prefix}styles/reader.css\"></head>"""


def counts_by_stream(items: list[dict[str, str]]) -> dict[str, int]:
    counts = {str(stream["slug"]): 0 for stream in STREAMS}
    for item in items:
        counts[item["stream"]] = counts.get(item["stream"], 0) + 1
    return counts


def render_stream_index(items: list[dict[str, str]]) -> None:
    counts = counts_by_stream(items)
    cards = "".join(stream_card(stream, counts.get(str(stream["slug"]), 0), prefix="../") for stream in STREAMS)
    text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — Потоки', 'Тематические дайджесты личного reader/radar.', prefix='../')}<body><header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">News Dispatch</a><p class=\"eyebrow\">Потоки</p><h1>Тематические дайджесты</h1><p class=\"lede\">Новости разделены по самостоятельным полкам: финансы, криптофинансы, AI, железо и софт, EDC, Москва, DJ/audio и наука. Общий поток остаётся только для специальных кросс-доменных выпусков.</p></header><main><section class=\"grid\">{cards}</section></main></body></html>"""
    stream_dir = SITE_DIR / "streams"
    stream_dir.mkdir(parents=True, exist_ok=True)
    (stream_dir / "index.html").write_text(text, encoding="utf-8")


def render_stream_pages(items: list[dict[str, str]]) -> None:
    stream_dir = SITE_DIR / "streams"
    stream_dir.mkdir(parents=True, exist_ok=True)
    for stream in STREAMS:
        stream_items = [item for item in items if item["stream"] == stream["slug"]]
        content = "".join(card(item, prefix="../") for item in stream_items) or "<p>В этом потоке пока нет опубликованных выпусков.</p>"
        text = f"""<!doctype html><html lang=\"ru\">{head('News Dispatch — ' + str(stream['title']), str(stream['description']), prefix='../')}<body><header class=\"masthead compact\"><a class=\"backlink\" href=\"../streams/index.html\">Потоки</a><p class=\"eyebrow\">{html.escape(str(stream['label']))}</p><h1>{html.escape(str(stream['title']))}</h1><p class=\"lede\">{html.escape(str(stream['description']))}</p></header><main><section class=\"grid\">{content}</section></main></body></html>"""
        (stream_dir / f"{stream['slug']}.html").write_text(text, encoding="utf-8")


def patch_homepage(items: list[dict[str, str]]) -> None:
    page = SITE_DIR / "index.html"
    if not page.exists():
        return
    counts = counts_by_stream(items)
    cards = "".join(stream_card(stream, counts.get(str(stream["slug"]), 0)) for stream in STREAMS)
    text = page.read_text(encoding="utf-8")
    replacement = f'<section class="stream-grid" aria-label="Редакционные потоки">{cards}</section>'
    text = re.sub(r'<section class="stream-grid" aria-label="Редакционные потоки">.*?</section>', replacement, text, flags=re.S)
    page.write_text(text, encoding="utf-8")


def normalize_topic_labels() -> None:
    for page in SITE_DIR.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new_text = text
        for slug, stream in STREAM_BY_SLUG.items():
            new_text = new_text.replace(f">{html.escape(slug)} ·", f">{html.escape(str(stream['title']))} ·")
        if new_text != text:
            page.write_text(new_text, encoding="utf-8")


def write_sitemap(items: list[dict[str, str]]) -> None:
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/dispatches.html",
        f"{BASE_URL}/rss.xml",
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/streams/index.html",
    ]
    urls.extend(f"{BASE_URL}/streams/{stream['slug']}.html" for stream in STREAMS)
    urls.extend(item["url"] for item in items)
    entries = "".join(f"<url><loc>{html.escape(url)}</loc></url>" for url in dict.fromkeys(urls))
    (SITE_DIR / "sitemap.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">{entries}</urlset>", encoding="utf-8")


def main() -> int:
    items = collect_dispatches()
    render_stream_index(items)
    render_stream_pages(items)
    patch_homepage(items)
    normalize_topic_labels()
    write_sitemap(items)
    print("Applied topic stream pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
