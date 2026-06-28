#!/usr/bin/env python3
"""Collect public RSS/Atom signals for News Dispatch.

Daily Radar is intentionally signal-only. It records that a public source
reported something; it does not publish analytical conclusions and it does not
turn signals into reader-facing dispatches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from core import (
    DATA_DIR,
    ROOT,
    SIGNALS_DIR,
    VALIDATION_DIR,
    NewsDispatchError,
    clean_text,
    log as core_log,
    repo_path,
    slugify,
    write_json,
    yaml_quote,
)
from stream_registry import stream_keywords, stream_slugs

CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = DATA_DIR / "daily-radar-seen.json"
REPORT_PATH = VALIDATION_DIR / "daily-radar-latest.json"
USER_AGENT = "NewsDispatchDailyRadar/0.7 (+https://simple-zuev.github.io/news-dispatch/)"
STREAMS = set(stream_slugs())
KEYWORDS = stream_keywords()
MEDIA_LIMIT = 4
MAX_SEEN_ITEMS = 3000

EXPLICIT_STREAM_TERMS: dict[str, tuple[str, ...]] = {
    "ai": (
        "ai agent",
        "ai agents",
        "ai coding",
        "artificial intelligence",
        "claude code",
        "copilot",
        "gemini",
        "generative ai",
        "large language model",
        "llm",
        "openai",
    ),
    "crypto-finance": (
        "bitcoin",
        "blockchain",
        "coinbase",
        "crypto",
        "cryptocurrency",
        "ethereum",
        "mi ca",
        "mica",
        "onchain",
        "stablecoin",
        "tokenization",
    ),
}

SEMANTIC_ROUTE_DENY: dict[str, set[str]] = {
    # Keep highly regulated finance/crypto sources in their configured lane unless
    # an explicit crypto term appears in finance. Avoid broad automatic remapping.
    "crypto-finance": {"finance"},
}


class FeedConfigError(NewsDispatchError):
    """Raised when the feed configuration cannot be used safely."""


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
    core_log(message, scope="daily-radar")


def parse_date(value: str, fallback: datetime) -> datetime:
    """Parse common RSS/Atom date formats and normalize them to UTC."""
    if not value:
        return fallback
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
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
    """Load enabled public feeds from ``sources/feeds.json``.

    Invalid stream names are downgraded to ``general`` to preserve historical
    behavior and avoid failing the whole radar job because of one feed row.
    Feeds with ``enabled: false`` are retained in metadata but skipped at run
    time.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FeedConfigError(f"Missing feed configuration: {repo_path(path)}") from exc
    except json.JSONDecodeError as exc:
        raise FeedConfigError(f"Invalid feed configuration JSON: {repo_path(path)}: {exc}") from exc

    feeds: list[Feed] = []
    for index, raw in enumerate(data.get("feeds", []), start=1):
        if not isinstance(raw, dict):
            log(f"skipping feed #{index}: expected object")
            continue
        if raw.get("enabled", True) is False:
            continue
        try:
            feed_id = str(raw["id"])
            title = str(raw["title"])
            url = str(raw["url"])
        except KeyError as exc:
            log(f"skipping feed #{index}: missing required key {exc}")
            continue

        stream = str(raw.get("stream", "general"))
        if stream not in STREAMS:
            log(f"feed {feed_id}: unknown stream {stream!r}; using 'general'")
            stream = "general"

        try:
            priority = float(raw.get("priority", 0.5))
        except (TypeError, ValueError):
            log(f"feed {feed_id}: invalid priority; using 0.5")
            priority = 0.5

        feeds.append(
            Feed(
                id=feed_id,
                title=title,
                url=url,
                stream=stream,
                source_type=str(raw.get("source_type", "Источник")),
                source_class=str(raw.get("source_class", "public_media")),
                priority=priority,
                tags=tuple(str(tag) for tag in raw.get("tags", [])),
            )
        )
    return feeds, dict(data.get("defaults", {}))


def download(url: str, timeout: int) -> bytes:
    """Download a feed payload with a deterministic User-Agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def text_of(node: ET.Element, names: tuple[str, ...]) -> str:
    """Read text from RSS/Atom nodes with and without namespaces."""
    wanted = {name.lower() for name in names}
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    for child in node.iter():
        if _local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def link_of(node: ET.Element) -> str:
    """Extract an item URL from RSS ``link`` text or Atom ``link href``."""
    link = text_of(node, ("link",))
    if link:
        return link
    for child in node.iter():
        if _local_name(child.tag) == "link" and child.attrib.get("href"):
            return child.attrib["href"].strip()
    return ""


def normalized_haystack(title: str, summary: str) -> str:
    text = f" {title} {summary} ".lower().replace("ё", "е")
    for char in "'’`—–_/|:;,.!?()[]{}\n\t":
        text = text.replace(char, " ")
    return " ".join(text.split())


def contains_phrase(haystack: str, phrase: str) -> bool:
    phrase = " ".join(phrase.lower().split())
    return f" {phrase} " in f" {haystack} "


def keyword_score(stream: str, haystack: str) -> int:
    return sum(1 for word in KEYWORDS.get(stream, []) if word and contains_phrase(haystack, word))


def explicit_stream_match(stream: str, haystack: str) -> bool:
    return any(contains_phrase(haystack, phrase) for phrase in EXPLICIT_STREAM_TERMS.get(stream, ()))


def semantic_candidate(feed_stream: str, haystack: str) -> str | None:
    """Return a conservative content-owned stream override.

    Routing remains feed-owned by default. A route changes only when explicit
    stream terms are present or another stream has a materially stronger keyword
    score than the feed's configured stream.
    """
    if feed_stream == "finance" and explicit_stream_match("crypto-finance", haystack):
        return "crypto-finance"

    for stream in ("ai", "crypto-finance"):
        if stream == feed_stream:
            continue
        if feed_stream in SEMANTIC_ROUTE_DENY.get(stream, set()):
            continue
        if explicit_stream_match(stream, haystack):
            return stream

    scores = {stream: keyword_score(stream, haystack) for stream in STREAMS if stream != "general"}
    if not scores:
        return None
    best_stream, best_score = max(scores.items(), key=lambda item: item[1])
    feed_score = scores.get(feed_stream, 0)
    if best_stream != feed_stream and best_score >= 3 and best_score >= feed_score + 2:
        return best_stream
    return None


def classify(feed: Feed, title: str, summary: str) -> str:
    """Return the stream for an item using conservative semantic routing.

    The feed stream remains the safe default. Content-owned routing is allowed
    only for high-signal cases, for example broad technology feeds producing
    explicit AI-agent stories or finance feeds producing explicit crypto-market
    stories.
    """
    haystack = normalized_haystack(title, summary)
    routed = semantic_candidate(feed.stream, haystack)
    return routed if routed in STREAMS else feed.stream


def item_score(feed: Feed, title: str, summary: str, published: datetime, now: datetime) -> float:
    """Score an item by source priority, freshness and broad topic hits."""
    age_hours = max((now - published).total_seconds() / 3600, 0)
    freshness = max(0, 1 - age_hours / 72)
    haystack = f"{title} {summary}".lower()
    topic_hits = sum(1 for words in KEYWORDS.values() for word in words if word in haystack)
    return round(feed.priority * 10 + freshness * 4 + min(topic_hits, 6) * 0.35, 3)


def feed_nodes(root: ET.Element) -> list[ET.Element]:
    """Return RSS item or Atom entry nodes from a parsed feed root."""
    return (
        root.findall(".//item")
        or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        or root.findall(".//entry")
    )


def parse_feed(feed: Feed, payload: bytes, now: datetime) -> list[Item]:
    """Parse one RSS/Atom payload into normalized radar items."""
    root = ET.fromstring(payload)
    items: list[Item] = []
    for node in feed_nodes(root):
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
    """Fetch every enabled feed, returning parsed items and non-fatal warnings."""
    now = datetime.now(timezone.utc)
    items: list[Item] = []
    errors: list[str] = []
    for feed in feeds:
        try:
            payload = download(feed.url, timeout)
            parsed = parse_feed(feed, payload, now)
            items.extend(parsed)
            log(f"{feed.id}: parsed {len(parsed)} item(s)")
        except (urllib.error.URLError, TimeoutError, ET.ParseError, UnicodeError, OSError) as exc:
            errors.append(f"{feed.id}: {exc.__class__.__name__}: {exc}")
        except Exception as exc:  # keep radar resilient; surface unexpected errors as warnings
            errors.append(f"{feed.id}: {exc.__class__.__name__}: {exc}")
    return items, errors


def load_seen(path: Path) -> set[str]:
    """Load previously seen item keys. Corrupt state is treated as empty."""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log(f"state file is not valid JSON; ignoring {repo_path(path)}")
        return set()
    return {str(item) for item in data.get("seen", [])}


def save_seen(path: Path, old: set[str], new_keys: list[str], dry_run: bool) -> None:
    if dry_run:
        return
    merged = list(dict.fromkeys([*new_keys, *sorted(old)]))[:MAX_SEEN_ITEMS]
    write_json(path, {"seen": merged})


def select_items(items: list[Item], seen: set[str], max_items: int, per_source: int, lookback_hours: int) -> list[Item]:
    """Deduplicate, filter by lookback and select the highest-scoring items."""
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
    """Write one signal Markdown file and return its intended path."""
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def write_report(day: date, generated: list[dict[str, object]], errors: list[str], dry_run: bool) -> None:
    if dry_run:
        return
    write_json(REPORT_PATH, {"date": day.isoformat(), "generated": generated, "fetch_errors": errors})


def int_setting(value: int | None, default: object, fallback: int) -> int:
    """Resolve CLI/env integer overrides against config defaults."""
    if value:
        return int(value)
    try:
        resolved = int(default) if default not in (None, "") else fallback
    except (TypeError, ValueError):
        return fallback
    return resolved


def build(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date) if args.date else date.today()
    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int_setting(args.max_items, defaults.get("max_items"), 40)
    per_source = int_setting(args.per_source, defaults.get("per_source"), 3)
    lookback = int_setting(args.lookback_hours, defaults.get("lookback_hours"), 36)

    log(
        f"loaded {len(feeds)} feed(s); day={day}; max_items={max_items}; "
        f"per_source={per_source}; lookback_hours={lookback}; dry_run={args.dry_run}"
    )

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
        generated.append(
            {
                "stream": stream,
                "status": "signals-only",
                "count": len(stream_items),
                "signals": [repo_path(path) for path in signal_paths],
                "media_count": min(MEDIA_LIMIT, len(stream_items)),
                "routing": "content_owned" if any(item.feed.stream != item.stream for item in stream_items) else "feed_owned",
            }
        )
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
    try:
        return build(parse_args(sys.argv[1:] if argv is None else argv))
    except FeedConfigError as exc:
        print(f"daily-radar: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
