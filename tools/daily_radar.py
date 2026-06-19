#!/usr/bin/env python3
"""Build topic-separated daily News Dispatch digests from public RSS/Atom feeds."""

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

from stream_registry import stream_keywords, stream_min_publish_items, stream_review_level, stream_slugs, stream_title

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = ROOT / "data" / "daily-radar-seen.json"
DISPATCH_ROOT = ROOT / "dispatches"
SIGNALS_DIR = ROOT / "signals"
REPORT_PATH = ROOT / "validation" / "daily-radar-latest.json"
USER_AGENT = "NewsDispatchDailyRadar/0.4 (+https://simple-zuev.github.io/news-dispatch/)"
STREAMS = stream_slugs()
KEYWORDS = stream_keywords()
MEDIA_LIMIT = 4
SOURCE_LIMIT = 12


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
        feeds.append(
            Feed(
                id=str(raw["id"]),
                title=str(raw["title"]),
                url=str(raw["url"]),
                stream=stream,
                source_type=str(raw.get("source_type", "Источник")),
                source_class=str(raw.get("source_class", "public_media")),
                priority=float(raw.get("priority", 0.5)),
                tags=tuple(str(tag) for tag in raw.get("tags", [])),
            )
        )
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
    haystack = f"{title} {summary} {' '.join(feed.tags)}".lower()
    scores = {stream: sum(1 for word in words if word in haystack) for stream, words in KEYWORDS.items()}
    if not scores:
        return feed.stream
    best_stream, best_score = max(scores.items(), key=lambda pair: pair[1])
    return best_stream if best_score > 0 else feed.stream


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


def yaml_list(key: str, values: list[str]) -> str:
    if not values:
        return f"{key}: []"
    return key + ":\n" + "\n".join(f"  - {yaml_quote(value)}" for value in values)


def top_items(items: list[Item], limit: int) -> list[Item]:
    return sorted(items, key=lambda item: (item.score, item.published), reverse=True)[:limit]


def source_lists(items: list[Item]) -> tuple[list[str], list[str], list[str], list[str]]:
    selected = top_items(items, SOURCE_LIMIT)
    return (
        [item.url for item in selected],
        [f"{item.feed.title}: {item.title}" for item in selected],
        [item.feed.source_type for item in selected],
        ["Публичный RSS/Atom-сигнал; перед сильными выводами нужно открыть первичный материал и проверить контекст." for _ in selected],
    )


def media_lists(items: list[Item]) -> tuple[list[str], list[str], list[str], list[str]]:
    selected = top_items(items, min(MEDIA_LIMIT, len(items)))
    return (
        [item.url for item in selected],
        [f"{item.feed.title}: {item.title}" for item in selected],
        [item.feed.source_type for item in selected],
        ["Ключевой материал выпуска: используется для media-карточки и последующего Open Graph/Twitter preview enrichment." for _ in selected],
    )


def front_matter(day: date, status: str, stream: str, items: list[Item]) -> str:
    urls, source_titles, source_types, source_notes = source_lists(items)
    media, media_titles, media_types, media_notes = media_lists(items)
    title = f"{stream_title(stream)} — {day.isoformat()}"
    summary = f"Автоматический тематический радар по потоку «{stream_title(stream)}»: {len(items)} публичных сигналов, ключевые материалы, источники и зоны наблюдения."
    tags = sorted({"daily-radar", "public-sources", stream, *[tag for item in items for tag in item.feed.tags]})[:16]
    review = stream_review_level(stream)
    return "\n".join([
        "---",
        f"title: {yaml_quote(title)}",
        f"date: {yaml_quote(day.isoformat())}",
        f"period: {yaml_quote(day.isoformat())}",
        f"stream: {yaml_quote(stream)}",
        'type: "daily"',
        'language: "ru"',
        f"status: {yaml_quote(status)}",
        f"review_level: {yaml_quote(review)}",
        'publication_scope: "public"',
        "public_safe: true",
        "private_context_used: false",
        "contains_personal_data: false",
        "contains_internal_company_data: false",
        "contains_confidential_strategy: false",
        "contains_nonpublic_sources: false",
        "contains_investment_advice: false",
        "contains_legal_advice: false",
        "contains_advertising: false",
        "contains_paid_promotion: false",
        'source_mode: "public_sources_only"',
        f"summary: {yaml_quote(summary)}",
        yaml_list("tags", tags),
        yaml_list("sources", urls),
        yaml_list("source_titles", source_titles),
        yaml_list("source_types", source_types),
        yaml_list("source_notes", source_notes),
        yaml_list("media", media),
        yaml_list("media_titles", media_titles),
        yaml_list("media_types", media_types),
        yaml_list("media_notes", media_notes),
        "visuals: []",
        "visual_titles: []",
        "visual_types: []",
        'privacy_review: "automated_public_safe_scan_pending"',
        'editorial_review: "automated_topic_radar_v2"',
        "---",
        "",
    ])


def main_points(stream: str, items: list[Item]) -> str:
    points = [f"{item.feed.title}: {item.title}." for item in top_items(items, 5)]
    while len(points) < 5:
        points.append(f"В потоке «{stream_title(stream)}» пока мало свежих сильных сигналов; такой выпуск следует читать как неполную карту дня.")
    return "\n".join(f"{idx}. {point}" for idx, point in enumerate(points[:5], 1))


def facts(items: list[Item]) -> str:
    return "\n".join(
        f"- {item.feed.title} опубликовал материал: {item.title}. Дата в ленте: {item.published.date().isoformat()}."
        for item in top_items(items, 10)
    )


def media_text(items: list[Item]) -> str:
    selected = top_items(items, min(MEDIA_LIMIT, len(items)))
    if not selected:
        return "Ключевые media-материалы для этого выпуска не определены. Карточки источников ниже остаются основным слоем проверки."
    lines = [
        "В media-блок вынесены самые сильные материалы этого выпуска. Для них будет выполнено Open Graph/Twitter metadata enrichment: если источник отдаёт preview-изображение, оно появится в карточке с атрибуцией."
    ]
    for item in selected:
        lines.append(f"- {item.feed.title}: {item.title}.")
    return "\n".join(lines)


def body(day: date, stream: str, items: list[Item]) -> str:
    title = stream_title(stream)
    return f"""# {title}
## {day.isoformat()}

## Лид

Это автоматический тематический радар потока «{title}». Он показывает свежие публичные сигналы, выделяет ключевые материалы для проверки и отделяет наблюдения от сильных выводов. Выпуск нужен как карта чтения на день, а не как окончательная редакционная позиция.

## Главное

{main_points(stream, items)}

## Что произошло

{facts(items)}

## Почему это важно

Разделение по темам уменьшает шум. У разных потоков разные источники, темп проверки и цена ошибки. Поэтому такой радар полезен не как список ссылок, а как первичная карта: где появились новые сигналы, какие источники повторяются и какие сюжеты требуют отдельного анализа.

## Анализ

Сильные выводы по одному RSS-сигналу делать нельзя. В этом выпуске важно смотреть на повторяемость тем, тип источника и наличие первичных материалов. Официальные источники и исследования сильнее пересказов; мнения и ожидания остаются слабым слоем до независимого подтверждения.

## Скрытые и косвенные сигналы

Отдельно стоит смотреть не только на факт публикации, но и на направление сдвига: усиливается ли роль платформы, меняется ли стоимость действия, появляется ли новый риск зависимости, становится ли источник менее проверяемым, повторяется ли тема в нескольких независимых каналах. Эти признаки могут быть важнее одиночного анонса.

## Слухи и мнения

Автоматический сбор не подтверждает слухи, инсайды или прогнозы. Если источник публикует ожидание, колонку, утечку или мнение, такой материал остаётся слабым сигналом до независимого подтверждения.

## Мнение людей

Публичная реакция в этой версии не оценивается автоматически. Для такого слоя нужны отдельные источники: комментарии, форумы, Telegram, Reddit, YouTube, профильные сообщества и отзывы пользователей. До подключения такого слоя этот раздел фиксирует ограничение метода.

## Медиа и материалы

{media_text(items)}

## Источники

Источники выпуска — публичные RSS/Atom-ленты из файла источников проекта. Перед сильными выводами нужно открыть первичный материал и проверить контекст, дату, автора, тип источника и наличие независимых подтверждений.

## Что наблюдать дальше

- Какие темы повторяются в нескольких независимых источниках.
- Где появляется первичный документ, а не только пересказ.
- Какие сигналы требуют отдельного аналитического выпуска.
- Какие источники дают шум и требуют снижения веса.
- Какие подтемы внутри потока нужно вынести в отдельные постоянные фильтры.

## Итог

Этот дайджест — тематическая полка личного reader/radar. Его задача — быстро показать, что появилось в публичных источниках по теме «{title}», где есть проверяемые материалы и какие сигналы могут повлиять на продукт, команду, организацию или рынок косвенно, а не только напрямую.
"""


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
public_safe: true
private_context_used: false
contains_personal_data: false
contains_internal_company_data: false
contains_confidential_strategy: false
contains_nonpublic_sources: false
contains_advertising: false
contains_paid_promotion: false
sources:
  - {yaml_quote(item.url)}
source_titles:
  - {yaml_quote(item.feed.title + ': ' + item.title)}
source_types:
  - {yaml_quote(item.feed.source_type)}
media:
  - {yaml_quote(item.url)}
media_titles:
  - {yaml_quote(item.feed.title + ': ' + item.title)}
media_types:
  - {yaml_quote(item.feed.source_type)}
visuals: []
visual_titles: []
visual_types: []
---

# {item.title}

## Что произошло

{item.feed.title} опубликовал материал в публичной RSS/Atom-ленте.

## Статус проверки

- Подтверждено: факт появления материала в публичной ленте.
- Не подтверждено: полнота контекста, последствия и интерпретации.

## Почему это важно

Сигнал попал в поток «{stream_title(item.stream)}» и может быть полезен для тематического дайджеста.

## Факты

- Источник: {item.feed.title}.
- Дата в ленте: {item.published.date().isoformat()}.
- Заголовок: {item.title}.

## Интерпретация

Автоматический сбор не делает сильных выводов по одному материалу.

## Слухи и мнения

Нет отдельной автоматической оценки слухов или мнений.

## Мнение людей

Публичная реакция не оценивалась автоматически.

## Источники и материалы

Источник указан в метаданных сигнала.

## Что наблюдать дальше

- Проверить первичный материал.
- Сравнить с другими источниками.
- Решить, нужен ли отдельный выпуск.
"""
    if not dry_run:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def write_dispatch(day: date, stream: str, status: str, items: list[Item], dry_run: bool) -> Path:
    directory = DISPATCH_ROOT / stream
    path = directory / f"{day.isoformat()}-{stream}-daily-radar.md"
    content = front_matter(day, status, stream, items) + body(day, stream, items)
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
    requested_status = args.status if args.status in {"draft", "published"} else "draft"
    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int(args.max_items or defaults.get("max_items", 40))
    min_items = int(args.min_items or defaults.get("min_items", 2))
    per_source = int(args.per_source or defaults.get("per_source", 3))
    lookback = int(args.lookback_hours or defaults.get("lookback_hours", 36))
    log(f"loaded {len(feeds)} feed(s); day={day}; status={requested_status}; dry_run={args.dry_run}")
    raw_items, fetch_errors = fetch_items(feeds, timeout=args.timeout)
    seen = set() if args.no_state else load_seen(STATE_PATH)
    selected = select_items(raw_items, seen, max_items=max_items, per_source=per_source, lookback_hours=lookback)
    groups = group_by_stream(selected)
    generated: list[dict[str, object]] = []
    new_keys: list[str] = []
    for stream, stream_items in sorted(groups.items()):
        if not stream_items:
            continue
        status = requested_status
        required_items = max(min_items, stream_min_publish_items(stream, min_items))
        if requested_status == "published" and len(stream_items) < required_items:
            status = "draft"
        signal_paths = [write_signal(day, item, args.dry_run) for item in stream_items]
        dispatch_path = write_dispatch(day, stream, status, stream_items, args.dry_run)
        new_keys.extend(item.key for item in stream_items)
        generated.append(
            {
                "stream": stream,
                "status": status,
                "count": len(stream_items),
                "required_items": required_items,
                "dispatch_path": dispatch_path.as_posix(),
                "signals": [path.as_posix() for path in signal_paths],
                "media_count": min(MEDIA_LIMIT, len(stream_items)),
            }
        )
        log(f"{stream}: {len(stream_items)} item(s), status={status}")
    save_seen(STATE_PATH, seen, new_keys, args.dry_run or args.no_state)
    write_report(day, generated, fetch_errors, args.dry_run)
    if not generated:
        log("no new topic digests generated")
    if fetch_errors:
        log(f"feed warnings: {len(fetch_errors)}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=os.getenv("DAILY_RADAR_DATE", ""))
    parser.add_argument("--status", default=os.getenv("DAILY_RADAR_STATUS", "published"))
    parser.add_argument("--max-items", type=int, default=int(os.getenv("DAILY_RADAR_MAX_ITEMS", "0")))
    parser.add_argument("--min-items", type=int, default=int(os.getenv("DAILY_RADAR_MIN_ITEMS", "0")))
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
