#!/usr/bin/env python3
"""Build an automatic daily News Dispatch from public RSS/Atom feeds.

Dependency-free by design: GitHub Actions can run it with stdlib Python only.
The script writes public-source signals plus one daily dispatch. It does not
scrape full article bodies, use private context, or call an LLM from CI.
"""

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

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "feeds.json"
STATE_PATH = ROOT / "data" / "daily-radar-seen.json"
DISPATCH_DIR = ROOT / "dispatches" / "general"
SIGNALS_DIR = ROOT / "signals"
REPORT_PATH = ROOT / "validation" / "daily-radar-latest.json"
USER_AGENT = "NewsDispatchDailyRadar/0.1 (+https://simple-zuev.github.io/news-dispatch/)"
STREAMS = {
    "general",
    "work",
    "finance",
    "digital-assets-infrastructure",
    "home-environment",
    "gear",
    "city-culture",
    "audio-creative",
    "horizon",
}

KEYWORDS = {
    "finance": ["rate", "inflation", "central bank", "bank", "market", "economy", "банк", "цб", "ставк", "инфляц", "эконом"],
    "work": ["ai", "model", "openai", "google", "microsoft", "platform", "developer", "search", "product", "ии", "модель", "платформ", "поиск"],
    "gear": ["nvidia", "chip", "gpu", "hardware", "pc", "laptop", "iphone", "mac", "device", "устройств", "желез"],
    "digital-assets-infrastructure": ["crypto", "bitcoin", "ethereum", "stablecoin", "token", "blockchain", "крипт", "биткоин", "стейбл"],
    "city-culture": ["moscow", "москва", "city", "город", "transport", "транспорт", "culture", "культур"],
    "horizon": ["science", "research", "space", "robot", "biotech", "climate", "наук", "космос", "робот", "биотех"],
}


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
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


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
    best_stream = feed.stream
    best_score = 0
    for stream, words in KEYWORDS.items():
        score = sum(1 for word in words if word in haystack)
        if score > best_score:
            best_stream = stream
            best_score = score
    return best_stream


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
        raw_date = text_of(node, ("pubDate", "published", "updated", "date"))
        published = parse_date(raw_date, now)
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
    merged = list(dict.fromkeys([*new_keys, *sorted(old)]))[:2000]
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


def source_lists(items: list[Item]) -> tuple[list[str], list[str], list[str], list[str]]:
    urls: list[str] = []
    titles: list[str] = []
    types: list[str] = []
    notes: list[str] = []
    for item in items:
        urls.append(item.url)
        titles.append(f"{item.feed.title}: {item.title}")
        types.append(item.feed.source_type)
        notes.append("Автоматически собранный публичный RSS/Atom-сигнал; требует чтения первичного материала перед сильными выводами.")
    return urls, titles, types, notes


def yaml_list(key: str, values: list[str]) -> str:
    if not values:
        return f"{key}: []"
    return key + ":\n" + "\n".join(f"  - {yaml_quote(value)}" for value in values)


def front_matter(day: date, status: str, title: str, summary: str, items: list[Item]) -> str:
    urls, source_titles, source_types, source_notes = source_lists(items)
    tags = sorted({"daily-radar", "news", "public-sources", *[item.stream for item in items]})
    fields = [
        "---",
        f"title: {yaml_quote(title)}",
        f"date: {yaml_quote(day.isoformat())}",
        f"period: {yaml_quote(day.isoformat())}",
        'stream: "general"',
        'type: "daily"',
        'language: "ru"',
        f"status: {yaml_quote(status)}",
        'review_level: "standard_public_review"',
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
        "media: []",
        "media_titles: []",
        "media_types: []",
        "media_notes: []",
        "visuals: []",
        "visual_titles: []",
        "visual_types: []",
        'privacy_review: "automated_public_safe_scan_pending"',
        'editorial_review: "automated_source_collection"',
        "---",
        "",
    ]
    return "\n".join(fields)


def grouped(items: list[Item]) -> dict[str, list[Item]]:
    groups: dict[str, list[Item]] = {}
    for item in items:
        groups.setdefault(item.stream, []).append(item)
    return groups


def lead(items: list[Item]) -> str:
    groups = grouped(items)
    streams = ", ".join(sorted(groups))
    return (
        f"Автоматический радар собрал {len(items)} публичных сигналов из RSS/Atom-источников. "
        f"Главная польза выпуска — быстро увидеть свежие материалы по потокам: {streams}. "
        "Это не финальная расследовательская статья: сильные выводы требуют чтения первичных материалов, но выпуск уже даёт карту того, что стоит открыть и проверить."
    )


def main_points(items: list[Item]) -> str:
    groups = grouped(items)
    points: list[str] = []
    for stream, stream_items in sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:5]:
        first = stream_items[0]
        points.append(f"{stream}: {len(stream_items)} сигнал(ов); самый сильный — {first.feed.title}: {first.title}.")
    while len(points) < 5:
        points.append("Радар продолжает накапливать источники; если сигналов мало, выпуск стоит читать как короткий список ссылок, а не как полную картину дня.")
    return "\n".join(f"{idx}. {point}" for idx, point in enumerate(points[:5], 1))


def facts(items: list[Item]) -> str:
    lines = []
    for item in items:
        date_label = item.published.date().isoformat()
        lines.append(f"- {item.feed.title} опубликовал материал: {item.title}. Дата в ленте: {date_label}. Поток: {item.stream}.")
    return "\n".join(lines)


def analysis(items: list[Item]) -> str:
    groups = grouped(items)
    ranked = sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True)
    first = ranked[0][0] if ranked else "general"
    return (
        f"Самый плотный поток в этом автосборе — {first}. Это не означает, что он объективно важнее других тем: RSS-ленты имеют разную частоту публикаций. "
        "Практическая ценность такого выпуска в другом: он быстро показывает, какие источники дали новые поводы для чтения, где нужен первичный документ, а где достаточно короткого просмотра. "
        "Автоматический радар не повышает пресс-релизы, слухи или мнения до уровня фактов. Он фиксирует публикацию и даёт маршрут проверки."
    )


def body(day: date, items: list[Item]) -> str:
    return f"""# Автоматический ежедневный радар
## {day.isoformat()}

## Лид

{lead(items)}

## Главное

{main_points(items)}

## Что произошло

{facts(items)}

## Почему это важно

Ежедневный reader должен экономить время: вместо ручного обхода десятков сайтов он собирает свежие публичные сигналы в одну карту выпуска. Для личного радара важны не только отдельные новости, но и распределение тем по источникам, повторяемость сигналов и появление первичных материалов.

## Анализ

{analysis(items)}

## Слухи и мнения

Автоматический сбор не подтверждает слухи, инсайды или прогнозы. Если источник публикует мнение, колонку, утечку или ожидание, такой материал остаётся слабым сигналом до проверки первичными данными, официальными документами или независимыми подтверждениями.

## Мнение людей

Публичная реакция в этой версии не оценивается автоматически. Для пользовательского чтения это означает, что комментарии, социальные сети и обсуждения нужно добавлять отдельным слоем, чтобы не смешивать факты публикации с настроениями аудитории.

## Медиа и материалы

В этом автоматическом выпуске медиа-карточки не добавляются отдельно. Ссылки на материалы доступны через карточки источников ниже.

## Источники

Источники выпуска — публичные RSS/Atom-ленты из `sources/feeds.json`. Каждая карточка ниже ведёт на исходный материал. Перед сильными выводами нужно открыть первоисточник и проверить контекст.

## Что наблюдать дальше

- Какие темы повторяются в нескольких независимых источниках.
- Где появляется первичный документ, а не только пересказ или пресс-релиз.
- Какие сигналы требуют отдельного выпуска с фактчекингом.
- Какие источники дают слишком много шума и нуждаются в снижении веса.
- Какие темы стоит добавить в личный radar как постоянные.

## Итог

Автоматический радар — это ежедневная карта чтения, а не окончательная редакционная позиция. Он показывает, что появилось в публичных источниках, какие темы сгруппировались в потоки и где нужен следующий шаг: открыть первичный материал, проверить слабый сигнал или собрать отдельный аналитический выпуск.
"""


def write_signal(day: date, item: Item, dry_run: bool) -> Path:
    directory = SIGNALS_DIR / day.isoformat()
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
media: []
media_titles: []
media_types: []
visuals: []
visual_titles: []
visual_types: []
---

# {item.title}

## Что произошло

{item.feed.title} опубликовал материал в публичной RSS/Atom-ленте. Этот файл — атомарный сигнал для будущей редакционной сборки.

## Статус проверки

- Подтверждено: факт появления материала в публичной ленте.
- Не подтверждено: полнота контекста, последствия и интерпретации.
- Следующий шаг: открыть первичный материал и проверить детали.

## Почему это важно

Сигнал попал в поток `{item.stream}` и может быть полезен для ежедневного личного радара.

## Факты

- Источник: {item.feed.title}.
- Дата в ленте: {item.published.date().isoformat()}.
- Заголовок: {item.title}.

## Интерпретация

Автоматический сбор не делает сильных выводов по одному материалу. Сигнал нужен для маршрутизации внимания.

## Слухи и мнения

Нет отдельной автоматической оценки слухов или мнений.

## Мнение людей

Публичная реакция не оценивалась автоматически.

## Источники и материалы

Источник указан в front matter.

## Что наблюдать дальше

- Проверить первичный материал.
- Сравнить с другими источниками.
- Решить, нужен ли отдельный выпуск.
"""
    if not dry_run:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def write_dispatch(day: date, status: str, items: list[Item], dry_run: bool) -> Path:
    title = f"Автоматический ежедневный радар — {day.isoformat()}"
    summary = f"Автоматический выпуск из {len(items)} публичных RSS/Atom-сигналов: технологии, рынки, платформы, Россия и смежные темы."
    path = DISPATCH_DIR / f"{day.isoformat()}-auto-daily-radar.md"
    content = front_matter(day, status, title, summary, items) + body(day, items)
    if not dry_run:
        DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def write_report(day: date, status: str, selected: list[Item], errors: list[str], dispatch_path: Path, signal_paths: list[Path], dry_run: bool) -> None:
    if dry_run:
        return
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "date": day.isoformat(),
        "status": status,
        "selected_count": len(selected),
        "dispatch_path": dispatch_path.as_posix(),
        "signal_paths": [path.as_posix() for path in signal_paths],
        "fetch_errors": errors,
        "items": [
            {"title": item.title, "url": item.url, "source": item.feed.title, "stream": item.stream, "score": item.score}
            for item in selected
        ],
    }
    REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date) if args.date else date.today()
    status = args.status if args.status in {"draft", "published"} else "draft"
    feeds, defaults = load_config(CONFIG_PATH)
    max_items = int(args.max_items or defaults.get("max_items", 18))
    min_items = int(args.min_items or defaults.get("min_items", 4))
    per_source = int(args.per_source or defaults.get("per_source", 3))
    lookback = int(args.lookback_hours or defaults.get("lookback_hours", 36))
    log(f"loaded {len(feeds)} feed(s); day={day}; status={status}; dry_run={args.dry_run}")
    raw_items, fetch_errors = fetch_items(feeds, timeout=args.timeout)
    seen = set() if args.no_state else load_seen(STATE_PATH)
    selected = select_items(raw_items, seen, max_items=max_items, per_source=per_source, lookback_hours=lookback)
    if len(selected) < min_items and status == "published":
        log(f"only {len(selected)} item(s) selected; downgrading to draft")
        status = "draft"
    if not selected:
        log("no new items selected")
        write_report(day, status, [], fetch_errors, DISPATCH_DIR / f"{day.isoformat()}-auto-daily-radar.md", [], args.dry_run)
        return 0
    signal_paths = [write_signal(day, item, args.dry_run) for item in selected]
    dispatch_path = write_dispatch(day, status, selected, args.dry_run)
    save_seen(STATE_PATH, seen, [item.key for item in selected], args.dry_run or args.no_state)
    write_report(day, status, selected, fetch_errors, dispatch_path, signal_paths, args.dry_run)
    log(f"wrote {len(signal_paths)} signal(s) and dispatch {dispatch_path.relative_to(ROOT)}")
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
