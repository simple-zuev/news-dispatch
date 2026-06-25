#!/usr/bin/env python3
"""Collect public RSS/Atom signals for News Dispatch."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from stream_registry import stream_keywords, stream_slugs, stream_title

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = ROOT / "data" / "daily-radar-seen.json"
SIGNALS_DIR = ROOT / "signals"
REPORT_PATH = ROOT / "validation" / "daily-radar-latest.json"
USER_AGENT = "NewsDispatchDailyRadar/0.5 (+https://simple-zuev.github.io/news-dispatch/)"
STREAMS = stream_slugs()
KEYWORDS = stream_keywords()
MEDIA_LIMIT = 4


@dataclass(frozen=True)
class Feed:
    id: str
    title: str
    url: str
    stream: str
    source_type: str
    source_class: str
    priority: float
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Item:
    feed: Feed
    title: str
    url: str
    published: datetime
    summary: str
    guid: str
    stream: str
    score: float

    @property
    def key(self) -> str:
        value = self.url or self.guid or self.title
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def log(message: str) -> None:
    print(f"[daily-radar] {message}")


def clean_text(value: str, max_len: int = 280) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slugify(value: str, fallback: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-z0-9а-я-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    latin = re.sub(r"[^a-z0-9-]+", "", value).strip("-")
    return (latin or fallback)[:72].strip("-") or fallback


def parse_date(value: str, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value[:25], fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return fallback


def load_config(path: Path) -> tuple[list[Feed], dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    feeds: list[Feed] = []
    for raw in data.get("feeds", []):
        if raw.get("enabled", True) is False:
            continue
        stream = str(raw.get("stream", "general"))
        if stream not in STREAMS:
            stream = "general"
        feeds.append(Feed(
            id=str(raw["id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            stream=stream,
            source_type=str(raw.get("source_type", "Источник")),
            source_class=str(raw.get("source_class", "public_media")),
            priority=float(raw.get("priority", 0.5)),
            tags=tuple(str(tag) for tag in raw.get("tags", [])),
        ))
    return feeds, dict(data.get("defaults", {}))


def download(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def text_of(node: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    for child in node.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names and child.text:
            return child.text.strip()
    return ""


def link_of(node: ET.Element) -> str:
    link = text_of(node, ("link",))
    if link:
        return link
    for child in node.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local == "link" and child.attrib.get("href"):
            return child.attrib["href"].strip()
    return ""


def classify(feed: Feed, title: str, summary: str) -> str:
    return feed.stream


def item_score(feed: Feed, title: str, summary: str, published: datetime, now: datetime) -> float:
    age_hours = max((now - published).total_seconds() / 3600, 0)
    freshness = max(0, 1 - age_hours / 72)
    haystack = f"{title} {summary}".lower()
    topic_hits = sum(1 for words in KEYWORDS.values() for word in words if word in haystack)
    return round(feed.priority * 10 + freshness * 4 + min(topic_hits, 6) * 0.35, 3)


def parse_feed(feed: Feed, payload: bytes, now: datetime) -> list[Item]:
    root = ET.fromstring(payload)
    nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry")
    items: list[Item] = []
    for node in nodes:
        title = clean_text(text_of(node, ("title",)))
        url = clean_text(link_of(node), 500)
        if not title or not url:
            continue
        summary = clean_text(text_of(node, ("description", "summary", "content")))
        guid = clean_text(text_of(node, ("guid", "id")), 500) or url
        published = parse_date(text_of(node, ("pubDate", "published", "updated", "date")), now)
        stream = classify(feed, title, summary)
        score = item_score(feed, title, summary, published, now)
        items.append(Item(feed, title, url, published, summary, guid, stream, score))
    return items


def fetch_items(feeds: list[Feed], timeout: int) -> tuple[list[Item], list[str]]:
    now = datetime.now(timezone.utc)
    items: list[Item] = []
    errors: list[str] = []
    for feed in feeds:
        try:
            items.extend(parse_feed(feed, download(feed.url, timeout), now))
        except Exception as exc:
            errors.append(f"{feed.id}: {exc.__class__.__name__}: {exc}")
    return items, errors


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {str(item) for item in data.get("seen", [])}


def save_seen(path: Path, old: set[str], new_keys: list[str], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = list(dict.fromkeys([*new_keys, *sorted(old)]))[:3000]
    path.write_text(json.dumps({"seen": merged}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def select_items(items: list[Item], seen: set[str], max_items: int, per_source: int, lookback_hours: int) -> list[Item]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)
    unique: dict[str, Item] = {}
    for item in items:
        if item.key in seen or item.published < cutoff:
            continue
        unique.setdefault(item.key, item)
    counts: dict[str, int] = {}
    selected: list[Item] = []
    for item in sorted(unique.values(), key=lambda x: (x.score, x.published), reverse=True):
        count = counts.get(item.feed.id, 0)
        if count >= per_source:
            continue
        selected.append(item)
        counts[item.feed.id] = count + 1
        if len(selected) >= max_items:
            break
    return selected


def group_by_stream(items: list[Item]) -> dict[str, list[Item]]:
    groups: dict[str, list[Item]] = {}
    for item in items:
        groups.setdefault(item.stream, []).append(item)
    return {stream: sorted(values, key=lambda item: item.score, reverse=True) for stream, values in groups.items()}


def write_signal(day: date, item: Item, dry_run: bool) -> Path:
    directory = SIGNALS_DIR / day.isoformat() / item.stream
    path = directory / f"{item.key}-{slugify(item.title, item.feed.id)}.md"
    content = f"""---
title: {yaml_quote(item.title)}
date: {yaml_quote(day.isoformat())}
status: "draft"
signal_type: "fact"
confidence: "source_reported"
source_class: {yaml_quote(item.feed.source_class)}
streams:
  - {yaml_quote(item.stream)}
domains:
  - {yaml_quote(item.feed.id)}
sources:
  - {yaml_quote(item.url)}
source_titles:
  - {yaml_quote(item.feed.title + ': ' + item.title)}
source_types:
  - {yaml_quote(item.feed.source_type)}
---

# {item.title}

## Что произошло

{item.feed.title} опубликовал материал в публичной RSS/Atom-ленте.

## Статус проверки

- Подтверждено: факт появления материала в публичной ленте.
- Не подтверждено: полнота контекста, последствия и интерпретации.
"""
    if not dry_run:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def write_report(day: date, generated: list[dict[str, object]], errors: list[str], dry_run: bool) -> None:
    if dry_run:
        return
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps({"date": day.isoformat(), "generated": generated, "fetch_errors": errors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date) if args.date else date.today()
    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int(args.max_items or defaults.get("max_items", 40))
    per_source = int(args.per_source or defaults.get("per_source", 3))
    lookback = int(args.lookback_hours or defaults.get("lookback_hours", 36))
    log(f"loaded {len(feeds)} feed(s); day={day}; dry_run={args.dry_run}")
    raw_items, fetch_errors = fetch_items(feeds, timeout=args.timeout)
    seen = set() if args.no_state else load_seen(STATE_PATH)
    selected = select_items(raw_items, seen, max_items=max_items, per_source=per_source, lookback_hours=lookback)
    groups = group_by_stream(selected)
    generated: list[dict[str, object]] = []
    new_keys: list[str] = []
    for stream, stream_items in sorted(groups.items()):
        if not stream_items:
            continue
        signal_paths = [write_signal(day, item, args.dry_run) for item in stream_items]
        new_keys.extend(item.key for item in stream_items)
        generated.append({
            "stream": stream,
            "status": "signals-only",
            "count": len(stream_items),
            "signals": [path.as_posix() for path in signal_paths],
            "media_count": min(MEDIA_LIMIT, len(stream_items)),
            "routing": "feed_owned",
        })
        log(f"{stream}: {len(stream_items)} signal(s)")
    save_seen(STATE_PATH, seen, new_keys, args.dry_run or args.no_state)
    write_report(day, generated, fetch_errors, args.dry_run)
    if not generated:
        log("no new signals generated")
    if fetch_errors:
        log(f"feed warnings: {len(fetch_errors)}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=os.getenv("DAILY_RADAR_DATE", ""))
    parser.add_argument("--max-items", type=int, default=int(os.getenv("DAILY_RADAR_MAX_ITEMS", "0")))
    parser.add_argument("--per-source", type=int, default=int(os.getenv("DAILY_RADAR_PER_SOURCE", "0")))
    parser.add_argument("--lookback-hours", type=int, default=int(os.getenv("DAILY_RADAR_LOOKBACK_HOURS", "0")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("DAILY_RADAR_TIMEOUT", "20")))
    parser.add_argument("--dry-run", action="store_true", default=os.getenv("DAILY_RADAR_DRY_RUN", "") == "1")
    parser.add_argument("--no-state", action="store_true", default=os.getenv("DAILY_RADAR_NO_STATE", "") == "1")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return build(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
