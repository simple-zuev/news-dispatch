#!/usr/bin/env python3
"""Validate media registry contracts without fetching external resources."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REGISTRY_PATHS = [
    ROOT / "media" / "registry.json",
    ROOT / "media" / "registry.generated.json",
]
ALLOWED_EMBED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
    "player.vimeo.com",
}
VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg", ".mov")


def load_items(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    return [item for item in items if isinstance(item, dict)]


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def local_preview_exists(value: str) -> bool:
    if value.startswith(("http://", "https://", "/", "../")):
        return True
    return (SITE_DIR / value.lstrip("/")).exists()


def validate_item(path: Path, item: dict[str, object], index: int, generated: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = f"{path.relative_to(ROOT)} items[{index}]"

    url = str(item.get("url", "")).strip()
    if not url:
        errors.append(f"{label}: url is required")
    elif not is_http_url(url):
        errors.append(f"{label}: url must be http/https")

    preview = str(item.get("preview", "")).strip()
    image_url = str(item.get("image_url", "")).strip()
    embed_url = str(item.get("embed_url", "")).strip()
    video_url = str(item.get("video_url", "")).strip()

    if not (preview or image_url or embed_url or video_url):
        warnings.append(f"{label}: no preview/image/video metadata")

    if preview and not local_preview_exists(preview):
        errors.append(f"{label}: local preview does not exist: {preview}")

    if image_url and not is_http_url(image_url):
        errors.append(f"{label}: image_url must be http/https")

    if embed_url:
        parsed = urlparse(embed_url)
        if not is_https_url(embed_url):
            message = f"{label}: embed_url must be https"
            (warnings if generated else errors).append(message)
        elif parsed.netloc.lower() not in ALLOWED_EMBED_HOSTS:
            message = f"{label}: embed_url host is not allowlisted: {parsed.netloc}"
            (warnings if generated else errors).append(message)

    if video_url:
        parsed = urlparse(video_url)
        direct_file = parsed.path.lower().endswith(VIDEO_EXTENSIONS)
        if not is_https_url(video_url) or not direct_file:
            message = f"{label}: video_url should be direct https video file"
            (warnings if generated else errors).append(message)

    return errors, warnings


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    checked = 0

    for path in REGISTRY_PATHS:
        generated = path.name.endswith(".generated.json")
        for index, item in enumerate(load_items(path)):
            checked += 1
            url = str(item.get("url", "")).strip()
            if url:
                key = f"{path.name}:{url}"
                if key in seen:
                    warnings.append(f"{path.relative_to(ROOT)} items[{index}]: duplicate url in registry")
                seen.add(key)
            item_errors, item_warnings = validate_item(path, item, index, generated)
            errors.extend(item_errors)
            warnings.extend(item_warnings)

    if warnings:
        print("Media registry warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("Media registry validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Media registry validation passed for {checked} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
