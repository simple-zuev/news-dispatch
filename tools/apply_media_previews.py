#!/usr/bin/env python3
"""Apply media previews from manual and generated media registries."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REGISTRY_PATHS = [
    ROOT / "media" / "registry.json",
    ROOT / "media" / "registry.generated.json",
]

SOURCE_CARD_RE = re.compile(
    r'(<article class="(?=[^"]*\bsource-card\b)[^"]*">)(.*?</article>)',
    re.S,
)
ALLOWED_EMBED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
    "player.vimeo.com",
}
VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg", ".mov")


def registry_items(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    cleaned: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        cleaned.append({key: str(value) for key, value in item.items() if value is not None})
    return cleaned


def load_registry() -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for path in REGISTRY_PATHS:
        for item in registry_items(path):
            url = item["url"]
            previous = registry.get(url, {})
            merged = dict(previous)
            for key, value in item.items():
                if value:
                    merged[key] = value
            if merged.get("preview") or merged.get("image_url") or merged.get("video_url") or merged.get("embed_url"):
                registry[url] = merged
    return registry


def prefix_for(page: Path) -> str:
    rel = page.relative_to(SITE_DIR).as_posix()
    if "/" in rel:
        return "../"
    return ""


def resolve_preview_path(preview: str, prefix: str) -> str:
    if preview.startswith(("http://", "https://", "/", "../")):
        return preview
    return prefix + preview.lstrip("/")


def host_label(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return host or "источник"


def material_source(url: str, item: dict[str, str]) -> str:
    return item.get("site_name") or item.get("image_source") or host_label(url)


def image_source(url: str, item: dict[str, str]) -> str:
    return item.get("image_source") or item.get("site_name") or material_source(url, item)


def video_source(url: str, item: dict[str, str]) -> str:
    return item.get("video_source") or item.get("site_name") or material_source(url, item)


def is_direct_video(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.path.lower().endswith(VIDEO_EXTENSIONS)


def is_allowed_embed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc.lower() in ALLOWED_EMBED_HOSTS


def preview_origin(item: dict[str, str]) -> str:
    if item.get("embed_url") or item.get("video_url"):
        return "метаданные видео"
    if item.get("metadata_source") == "open_graph" and item.get("image_url"):
        return "Open Graph / Twitter metadata"
    if item.get("image_url"):
        return "метаданные источника"
    return "локальный fallback"


def media_object_html(url: str, item: dict[str, str], preview: str, title: str) -> str:
    embed = item.get("embed_url", "").strip()
    video = item.get("video_url", "").strip()
    if embed and is_allowed_embed(embed):
        return (
            f'<div class="reader-video-frame">'
            f'<iframe src="{html.escape(embed, quote=True)}" title="{html.escape(title, quote=True)}" '
            f'loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share" '
            f'allowfullscreen referrerpolicy="no-referrer"></iframe></div>'
        )
    if video and is_direct_video(video):
        poster = f' poster="{html.escape(preview, quote=True)}"' if preview else ""
        return (
            f'<video class="reader-video" controls preload="metadata"{poster}>'
            f'<source src="{html.escape(video, quote=True)}">'
            f'<a href="{html.escape(video, quote=True)}">Открыть видео</a>'
            f'</video>'
        )
    if preview:
        return (
            f'<a class="reader-preview-link" href="{html.escape(url, quote=True)}">'
            f'<img class="reader-thumb" src="{html.escape(preview, quote=True)}" '
            f'alt="{html.escape(title, quote=True)}" loading="lazy" referrerpolicy="no-referrer"></a>'
        )
    return ""


def preview_html(url: str, item: dict[str, str], prefix: str) -> str:
    external = item.get("image_url", "").strip()
    fallback = item.get("preview", "").strip()
    preview = external or resolve_preview_path(fallback, prefix)
    title = item.get("external_title") or item.get("title") or "Материал"
    material = material_source(url, item)
    image = image_source(url, item)
    video = video_source(url, item)
    origin = preview_origin(item)
    canonical = item.get("canonical_url") or url
    media_object = media_object_html(url, item, preview, title)
    if not media_object:
        return ""
    video_line = f'<span><strong>Видео:</strong> {html.escape(video)}</span>' if item.get("embed_url") or item.get("video_url") else ""
    return (
        f'<figure class="reader-preview-figure">'
        f'{media_object}'
        f'<figcaption class="reader-preview-meta">'
        f'<span><strong>Материал:</strong> {html.escape(material)}</span>'
        f'<span><strong>Изображение:</strong> {html.escape(image)}</span>'
        f'{video_line}'
        f'<span><strong>Превью:</strong> {html.escape(origin)}</span>'
        f'<span><strong>Сайт:</strong> {html.escape(host_label(canonical))}</span>'
        f'</figcaption>'
        f'</figure>'
    )


def insert_preview_in_source_cards(text: str, url: str, item: dict[str, str], prefix: str) -> str:
    escaped_url = html.escape(url, quote=True)
    if escaped_url not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        opening, body = match.groups()
        article = match.group(0)
        if escaped_url not in article or "reader-thumb" in article or "reader-video" in article or "reader-video-frame" in article:
            return article
        preview = preview_html(url, item, prefix)
        if not preview:
            return article
        return opening + preview + body

    return SOURCE_CARD_RE.sub(replace, text)


def enrich_html(text: str, registry: dict[str, dict[str, str]], prefix: str) -> str:
    for url, item in registry.items():
        text = insert_preview_in_source_cards(text, url, item, prefix)
    return text


def main() -> int:
    registry = load_registry()
    if not registry:
        print("No media registry found.")
        return 0
    changed = 0
    for page in SITE_DIR.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new_text = enrich_html(text, registry, prefix_for(page))
        if new_text != text:
            page.write_text(new_text, encoding="utf-8")
            changed += 1
    print(f"Applied media previews to {changed} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
