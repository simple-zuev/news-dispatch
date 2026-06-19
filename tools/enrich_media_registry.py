#!/usr/bin/env python3
"""Enrich media registry from public Open Graph / Twitter metadata.

The script is intentionally conservative:
- reads published dispatches and their media/sources URLs;
- fetches only the source page itself, not random image or video search results;
- extracts publisher-provided metadata such as og:image, twitter:image,
  og:video, and twitter:player;
- writes a generated registry file used during static site rendering;
- never fails the build because one source blocks metadata fetching.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_DIR = ROOT / "dispatches"
MEDIA_DIR = ROOT / "media"
MANUAL_REGISTRY = MEDIA_DIR / "registry.json"
GENERATED_REGISTRY = MEDIA_DIR / "registry.generated.json"
MAX_URLS = 80
FETCH_TIMEOUT_SECONDS = 12
USER_AGENT = "NewsDispatchBot/1.0 (+https://simple-zuev.github.io/news-dispatch/)"


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.in_title = False
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
            return
        if tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            self.canonical = attrs_dict.get("href", "").strip()
            return
        if tag != "meta":
            return
        key = attrs_dict.get("property") or attrs_dict.get("name")
        content = attrs_dict.get("content", "").strip()
        if key and content:
            self.meta[key.lower()] = html.unescape(content)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data.strip())

    @property
    def title(self) -> str:
        return " ".join(part for part in self.title_parts if part).strip()


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, Any] = {}
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
            meta[key] = []
            list_key = key
        else:
            meta[key] = value
            list_key = None
    return meta, body


def list_value(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def load_manual_registry() -> dict[str, dict[str, str]]:
    if not MANUAL_REGISTRY.exists():
        return {}
    data = json.loads(MANUAL_REGISTRY.read_text(encoding="utf-8"))
    registry: dict[str, dict[str, str]] = {}
    for item in data.get("items", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if url:
            registry[url] = {key: str(value) for key, value in item.items() if value is not None}
    return registry


def dispatch_urls() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        meta, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("status", "draft")) != "published":
            continue
        media = list_value(meta, "media")
        titles = list_value(meta, "media_titles")
        types = list_value(meta, "media_types")
        notes = list_value(meta, "media_notes")
        sources = list_value(meta, "sources")
        source_titles = list_value(meta, "source_titles")
        source_types = list_value(meta, "source_types")
        source_notes = list_value(meta, "source_notes")
        rows = []
        for idx, url in enumerate(media):
            rows.append({
                "url": url,
                "title": titles[idx] if idx < len(titles) else "",
                "type": types[idx] if idx < len(types) else "",
                "note": notes[idx] if idx < len(notes) else "",
                "role": "media",
            })
        if not rows:
            for idx, url in enumerate(sources[:6]):
                rows.append({
                    "url": url,
                    "title": source_titles[idx] if idx < len(source_titles) else "",
                    "type": source_types[idx] if idx < len(source_types) else "",
                    "note": source_notes[idx] if idx < len(source_notes) else "",
                    "role": "source",
                })
        for row in rows:
            parsed = urlparse(row["url"])
            if parsed.scheme not in {"http", "https"}:
                continue
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            items.append(row)
            if len(items) >= MAX_URLS:
                return items
    return items


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def absolute_url(base_url: str, value: str) -> str:
    value = clean_text(value)
    if not value:
        return ""
    return urljoin(base_url, value)


def metadata_video(meta: dict[str, str], url: str) -> tuple[str, str, str]:
    embed = absolute_url(url, meta.get("twitter:player") or meta.get("og:video:url") or meta.get("og:video:secure_url") or "")
    video = absolute_url(url, meta.get("og:video") or meta.get("video") or "")
    video_type = clean_text(meta.get("og:video:type") or "")
    if embed and embed == video:
        # Keep direct video files in video_url; iframe-like players in embed_url.
        parsed = urlparse(embed)
        if parsed.path.lower().endswith((".mp4", ".webm", ".ogg", ".mov")):
            return "", embed, video_type
    return embed, video, video_type


def fetch_metadata(url: str) -> dict[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(512_000)
    charset_match = re.search(r"charset=([^;]+)", content_type, re.I)
    charset = charset_match.group(1).strip() if charset_match else "utf-8"
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    parser = MetadataParser()
    parser.feed(text)
    meta = parser.meta
    title = clean_text(meta.get("og:title") or meta.get("twitter:title") or parser.title)
    description = clean_text(meta.get("og:description") or meta.get("twitter:description") or meta.get("description") or "")
    image = absolute_url(url, meta.get("og:image:secure_url") or meta.get("og:image") or meta.get("twitter:image") or meta.get("twitter:image:src") or "")
    site_name = clean_text(meta.get("og:site_name") or urlparse(url).netloc.replace("www.", ""))
    canonical = absolute_url(url, meta.get("og:url") or parser.canonical or url)
    embed_url, video_url, video_type = metadata_video(meta, url)
    result = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metadata_source": "open_graph",
        "site_name": site_name,
        "canonical_url": canonical,
        "external_title": title,
        "external_description": description,
        "image_url": image,
        "image_source": site_name,
    }
    if embed_url:
        result["embed_url"] = embed_url
        result["video_source"] = site_name
    if video_url:
        result["video_url"] = video_url
        result["video_source"] = site_name
    if video_type:
        result["video_type"] = video_type
    return result


def enrich_item(row: dict[str, str], manual: dict[str, dict[str, str]]) -> dict[str, str]:
    url = row["url"]
    item = dict(manual.get(url, {}))
    item.setdefault("id", re.sub(r"[^a-z0-9]+", "-", urlparse(url).netloc.lower() + "-" + urlparse(url).path.strip("/").lower()).strip("-")[:80])
    item["url"] = url
    if row.get("title"):
        item.setdefault("title", row["title"])
    if row.get("type"):
        item.setdefault("type", row["type"])
    if row.get("note"):
        item.setdefault("note", row["note"])
    item.setdefault("role", row.get("role", "media"))
    try:
        fetched = fetch_metadata(url)
        item.update({key: value for key, value in fetched.items() if value})
        if not item.get("title") and fetched.get("external_title"):
            item["title"] = fetched["external_title"]
        if not item.get("note") and fetched.get("external_description"):
            item["note"] = fetched["external_description"]
        print(f"enriched: {url}")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        item["metadata_error"] = exc.__class__.__name__
        print(f"metadata skipped: {url}: {exc.__class__.__name__}")
    return item


def main() -> int:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    manual = load_manual_registry()
    rows = dispatch_urls()
    generated = [enrich_item(row, manual) for row in rows]
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "tools/enrich_media_registry.py",
        "items": generated,
    }
    GENERATED_REGISTRY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {GENERATED_REGISTRY.relative_to(ROOT)} with {len(generated)} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
