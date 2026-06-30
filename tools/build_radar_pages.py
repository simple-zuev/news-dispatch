#!/usr/bin/env python3
"""Build static radar pages from validation/daily-radar-latest.json."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from core import ROOT
from stream_registry import streams as registry_streams

SITE_DIR = ROOT / "site"
RADAR_DIR = SITE_DIR / "radar"
RADAR_PATH = ROOT / "validation" / "daily-radar-latest.json"
SOURCES_PATH = ROOT / "sources" / "feeds.json"
AUTO_DISPATCH_LATEST = ROOT / "validation" / "auto-dispatch-latest.json"
AUTO_DISPATCH_DIR = ROOT / "validation" / "auto-dispatches"
CURATED_DRAFT_DIR = ROOT / "validation" / "curated-drafts"
DRAFTS_PATH = SITE_DIR / "drafts.html"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    raw = text[4:end]
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
            list_key = key
            meta[key] = []
        else:
            list_key = None
            meta[key] = value
    return meta


def parse_document(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    return parse_front_matter(text), text[end + 5 :]


def first_value(meta: dict[str, Any], key: str, default: str = "") -> str:
    value = meta.get(key, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value or default)


def list_value(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    scalar = str(value).strip()
    return [scalar] if scalar else []


def source_name(source_title: str) -> str:
    if ":" in source_title:
        return source_title.split(":", 1)[0].strip()
    return source_title.strip()


def stream_title(slug: str) -> str:
    return str(STREAM_BY_SLUG.get(slug, {}).get("title", slug))


def stream_description(slug: str) -> str:
    return str(STREAM_BY_SLUG.get(slug, {}).get("description", ""))


def first_section_paragraph(body: str, heading: str) -> str:
    lines = body.splitlines()
    in_section = False
    chunks: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped[3:].strip() == heading
            continue
        if not in_section:
            continue
        if not stripped:
            if chunks:
                break
            continue
        if stripped.startswith("#"):
            break
        chunks.append(stripped.removeprefix("- ").strip())
    return " ".join(chunks).strip()


def draft_excerpt(body: str, fallback: str) -> str:
    for heading in ("Лид", "Почему это важно", "Статус"):
        excerpt = first_section_paragraph(body, heading)
        if excerpt:
            return excerpt
    cleaned = " ".join(line.strip() for line in body.splitlines() if line.strip() and not line.startswith("#"))
    return cleaned[:280] if cleaned else fallback


def signal_reader_summary(meta: dict[str, Any], body: str, title: str, source_title: str) -> tuple[str, bool]:
    summary = first_value(meta, "summary")
    if not summary:
        summary = first_section_paragraph(body, "Что произошло")
    if summary:
        return summary, False
    source = source_name(source_title) or "публичный источник"
    return f"{source} передал в RSS/Atom заголовок: «{title}». Это сырой сигнал; контекст, последствия и интерпретации требуют проверки.", True


def signal_confirmation_level(source_class: str, confidence: str) -> str:
    confidence_part = f" Уверенность в metadata: {confidence}." if confidence else ""
    if source_class in {"official_source", "official", "regulator", "company"}:
        return "Подтверждён факт публикации первичным или официальным источником; последствия и интерпретации требуют проверки." + confidence_part
    if source_class in {"public_media", "specialized_media", "business_media", "industry_media", "research_media"}:
        return "Source-reported: подтверждён факт появления материала в публичной ленте источника; утверждения и последствия не подтверждены." + confidence_part
    return "Ограниченный публичный сигнал: требуется ручная проверка источника, статуса и контекста." + confidence_part


def signal_reader_context(body: str, stream: str) -> str:
    why = first_section_paragraph(body, "Почему это важно")
    if why:
        return why
    description = stream_description(stream)
    if description:
        return f"Контекст для читателя: сигнал относится к теме «{stream_title(stream)}» ({description}). Это повод для проверки, а не готовый вывод."
    return "Контекст для читателя: сигнал показывает, что появилось в публичном источнике, но не заменяет редакционную проверку."


def signal_next_check(body: str, source_class: str) -> str:
    status = first_section_paragraph(body, "Статус проверки")
    match = re.search(r"Не подтверждено:\s*(.+)$", status)
    if match:
        return "Проверить: " + match.group(1).strip()
    if source_class in {"official_source", "official", "regulator", "company"}:
        return "Проверить первичный документ: дату, статус, адресатов, вступление в силу и реальные последствия."
    return "Найти первичный источник или независимое подтверждение; отделить факт сообщения источника от интерпретации."


def stream_data() -> list[dict[str, Any]]:
    rows = []
    for item in registry_streams():
        rows.append({
            "slug": str(item["slug"]),
            "title": str(item["title"]),
            "description": str(item.get("description", "")),
            "label": str(item.get("label", "Редакционная проверка")),
        })
    return rows


STREAM_BY_SLUG = {item["slug"]: item for item in stream_data()}


def source_status_by_stream() -> dict[str, dict[str, Any]]:
    data = load_json(SOURCES_PATH)
    result: dict[str, dict[str, Any]] = {}
    for feed in data.get("feeds", []):
        if not isinstance(feed, dict):
            continue
        stream = str(feed.get("stream") or "").strip()
        if not stream:
            continue
        row = result.setdefault(stream, {"active": [], "disabled": []})
        source = {
            "id": str(feed.get("id") or ""),
            "title": str(feed.get("title") or feed.get("id") or "Источник"),
            "reason": str(feed.get("disabled_reason") or "Отключён в конфигурации источников."),
        }
        if feed.get("enabled") is False:
            row["disabled"].append(source)
        else:
            row["active"].append(source)
    return result


def radar_items() -> dict[str, list[dict[str, str]]]:
    data = load_json(RADAR_PATH)
    result: dict[str, list[dict[str, str]]] = {}
    for group in data.get("generated", []):
        if not isinstance(group, dict):
            continue
        stream = str(group.get("stream", "")).strip()
        if not stream:
            continue
        result.setdefault(stream, [])
        for path_text in group.get("signals", []):
            path = ROOT / str(path_text)
            if not path.exists():
                continue
            meta, body = parse_document(path.read_text(encoding="utf-8"))
            title = first_value(meta, "title", path.stem.replace("-", " "))
            source = first_value(meta, "source_titles", first_value(meta, "sources", "Публичный источник"))
            source_class = first_value(meta, "source_class", "public_source")
            summary, raw_title_only = signal_reader_summary(meta, body, title, source)
            result[stream].append({
                "title": title,
                "date": first_value(meta, "date"),
                "source": source,
                "source_type": first_value(meta, "source_types"),
                "url": first_value(meta, "sources"),
                "source_class": source_class,
                "status": first_value(meta, "status", "draft"),
                "stream": stream,
                "summary": summary,
                "raw_title_only": "yes" if raw_title_only else "",
                "confirmation_level": signal_confirmation_level(source_class, first_value(meta, "confidence")),
                "reader_context": signal_reader_context(body, stream),
                "next_check": signal_next_check(body, source_class),
            })
    for rows in result.values():
        rows.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
    return result


def head(title: str, description: str, css_href: str = "../styles/main.css") -> str:
    return f"""<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <meta name=\"description\" content=\"{html.escape(description)}\">
  <link rel=\"stylesheet\" href=\"{html.escape(css_href)}\">
</head>"""


def signal_card(row: dict[str, str]) -> str:
    source = row.get("source") or "Публичный источник"
    stream = row.get("stream", "")
    label = " · ".join(part for part in [row.get("date", ""), stream_title(stream), row.get("source_class", ""), source_name(source), f"status: {row.get('status', 'draft')}"] if part)
    link = row.get("url", "")
    title = row.get("title", "Сигнал")
    source_parts = [source_name(source) or source, row.get("source_class", "")]
    if row.get("source_type"):
        source_parts.append(row["source_type"])
    if link:
        heading = f'<h3><a href="{html.escape(link, quote=True)}">{html.escape(title)}</a></h3>'
    else:
        heading = f"<h3>{html.escape(title)}</h3>"
    raw_label = '<span class="signal-raw-label">raw RSS title</span>' if row.get("raw_title_only") else '<span class="signal-raw-label">source-reported</span>'
    return f"""<article class=\"card signal-card\">
  <p class=\"label\">Raw signal · not published · signal != dispatch · {html.escape(label)}</p>
  {heading}
  <p class=\"signal-raw-title\">{raw_label}<span>Что произошло: {html.escape(row.get("summary", ""))}</span></p>
  <dl class=\"signal-facts\">
    <div><dt>Источник</dt><dd>{html.escape(" · ".join(part for part in source_parts if part))}</dd></div>
    <div><dt>Поток</dt><dd>{html.escape(stream_title(stream))}</dd></div>
    <div><dt>Подтверждение</dt><dd>{html.escape(row.get("confirmation_level", ""))}</dd></div>
    <div><dt>Почему важно</dt><dd>{html.escape(row.get("reader_context", ""))}</dd></div>
    <div><dt>Что проверить</dt><dd>{html.escape(row.get("next_check", ""))}</dd></div>
  </dl>
  <p class=\"signal-safety\">Сигнал не является опубликованным материалом: источник сообщает факт появления материала, а выводы требуют проверки.</p>
</article>"""


def latest_draft_paths() -> list[Path]:
    curated = sorted(path for path in CURATED_DRAFT_DIR.rglob("*.md") if path.is_file()) if CURATED_DRAFT_DIR.exists() else []
    if curated:
        return curated

    paths: list[Path] = []
    latest = load_json(AUTO_DISPATCH_LATEST)
    for row in latest.get("generated", []):
        if not isinstance(row, dict):
            continue
        path = ROOT / str(row.get("path", ""))
        if path.exists() and path.is_file():
            paths.append(path)
    if not paths and AUTO_DISPATCH_DIR.exists():
        paths.extend(path for path in sorted(AUTO_DISPATCH_DIR.glob("*/*-auto-radar-draft.md")) if path.is_file())
    return list(dict.fromkeys(paths))


def draft_card(path: Path) -> str:
    meta, body = parse_document(path.read_text(encoding="utf-8"))
    title = first_value(meta, "title", path.stem.replace("-", " "))
    streams = list_value(meta, "streams") or [first_value(meta, "stream", "general")]
    stream_titles = [str(STREAM_BY_SLUG.get(stream, {}).get("title", stream)) for stream in streams if stream]
    date = first_value(meta, "date")
    status = first_value(meta, "status", "draft")
    publication_mode = first_value(meta, "publication_mode", "draft_only")
    sources = len(list_value(meta, "sources"))
    summary = first_value(meta, "summary") or draft_excerpt(body, "Черновик для редакционной проверки.")
    rel = path.relative_to(ROOT).as_posix()
    source_count = f"{sources} источн." if sources else ""
    label = " · ".join(part for part in [date, ", ".join(stream_titles), f"status: {status}", publication_mode, source_count] if part)
    return f"""<article class=\"card draft-review-card\">
  <p class=\"label\">Draft != publication · {html.escape(label)}</p>
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(summary)}</p>
  <p class=\"draft-source-path\">{html.escape(rel)}</p>
</article>"""


def drafts_page() -> str:
    drafts = latest_draft_paths()
    cards = "\n".join(draft_card(path) for path in drafts)
    if not cards:
        cards = """<article class=\"card empty-state\"><p class=\"label\">Нет черновиков</p><h3>Нет draft-only материалов к проверке</h3><p>Папка validation/curated-drafts отсутствует, а в текущем auto-dispatch индексе нет доступных черновиков.</p></article>"""
    return f"""<!doctype html>
<html lang=\"ru\">
{head("Дайджест — Черновики к проверке", "Draft-only материалы для редакционной проверки.", css_href="styles/main.css")}
<body>
  <header class=\"masthead compact\"><a class=\"backlink\" href=\"index.html\">Дайджест</a><p class=\"eyebrow\">Review only</p><h1>Черновики к проверке</h1><p class=\"lede\">Материалы из validation/curated-drafts. Это не публикации, не dispatches и не финальные выводы.</p></header>
  <main>
    <section class=\"panel draft-review-notice\"><h2>Граница публикации</h2><p>Draft != publication. Черновики нужны для ручной проверки источников, дат, статусов и формулировок. Source-reported claims требуют верификации перед публикацией.</p></section>
    <section class=\"grid draft-review-grid\">{cards}</section>
  </main>
</body>
</html>
"""


def stream_card(stream: dict[str, Any], count: int, source_status: dict[str, Any]) -> str:
    slug = str(stream["slug"])
    title = str(stream["title"])
    description = str(stream.get("description", ""))
    active = len(source_status.get("active", []))
    disabled = len(source_status.get("disabled", []))
    source_note = f"{active} active / {disabled} paused sources"
    return f"""<article class=\"card\">
  <p class=\"label\">{count} сигналов · {html.escape(source_note)}</p>
  <h3><a href=\"{html.escape(slug)}.html\">{html.escape(title)}</a></h3>
  <p>{html.escape(description)}</p>
</article>"""


def disabled_sources_list(disabled: list[dict[str, str]]) -> str:
    if not disabled:
        return ""
    rows = "".join(
        f"<li><strong>{html.escape(source.get('title', 'Источник'))}:</strong> {html.escape(source.get('reason', 'Отключён.'))}</li>"
        for source in disabled[:6]
    )
    return f"<ul class=\"cluster-materials\">{rows}</ul>"


def empty_state(stream: dict[str, Any], source_status: dict[str, Any]) -> str:
    active = source_status.get("active", [])
    disabled = source_status.get("disabled", [])
    if active:
        reason = "Активные источники есть, но в последнем Daily Radar run свежие материалы не прошли фильтры, source rules или порог релевантности."
    elif disabled:
        reason = "Все известные источники рубрики сейчас отключены или нестабильны; для восстановления нужны рабочие feed endpoints или fallback-источники."
    else:
        reason = "Для этой рубрики пока не задано активных источников в sources/feeds.json."
    return f"""<article class=\"card empty-state\">
  <p class=\"label\">Нет свежих сигналов</p>
  <h3>Почему рубрика пустая</h3>
  <p>{html.escape(reason)}</p>
  <p>Активные источники: {len(active)}. Отключённые источники: {len(disabled)}.</p>
  {disabled_sources_list(disabled)}
  <p>Это диагностическое состояние, а не редакционный вывод.</p>
</article>"""


def index_page(streams: list[dict[str, Any]], items: dict[str, list[dict[str, str]]], source_status: dict[str, dict[str, Any]]) -> str:
    cards = "\n".join(stream_card(stream, len(items.get(str(stream["slug"]), [])), source_status.get(str(stream["slug"]), {})) for stream in streams)
    return f"""<!doctype html>
<html lang=\"ru\">
{head("Дайджест — Свежие сигналы", "Публичный радар сигналов по темам.")}
<body>
  <header class=\"masthead compact\"><a class=\"backlink\" href=\"../index.html\">Дайджест</a><p class=\"eyebrow\">Радар</p><h1>Свежие сигналы</h1><p class=\"lede\">Публичные сигналы по темам. Это сырьё для анализа, а не опубликованные выводы.</p></header>
  <main><section class=\"grid\">{cards}</section></main>
</body>
</html>
"""


def stream_page(stream: dict[str, Any], rows: list[dict[str, str]], source_status: dict[str, Any]) -> str:
    cards = "\n".join(signal_card(row) for row in rows)
    content = f"<section class=\"grid\">{cards}</section>" if cards else empty_state(stream, source_status)
    title = str(stream["title"])
    description = str(stream.get("description", ""))
    return f"""<!doctype html>
<html lang=\"ru\">
{head(f"Дайджест — Свежие сигналы — {title}", description)}
<body>
  <header class=\"masthead compact\"><a class=\"backlink\" href=\"index.html\">Свежие сигналы</a><p class=\"eyebrow\">Радар темы</p><h1>{html.escape(title)}</h1><p class=\"lede\">{html.escape(description)}</p></header>
  <main>{content}</main>
</body>
</html>
"""


def main() -> int:
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    for page in RADAR_DIR.glob("*.html"):
        page.unlink()
    streams = stream_data()
    items = radar_items()
    source_status = source_status_by_stream()
    (RADAR_DIR / "index.html").write_text(index_page(streams, items, source_status), encoding="utf-8")
    for stream in streams:
        slug = str(stream["slug"])
        (RADAR_DIR / f"{slug}.html").write_text(stream_page(stream, items.get(slug, []), source_status.get(slug, {})), encoding="utf-8")
    DRAFTS_PATH.write_text(drafts_page(), encoding="utf-8")
    print(f"Built radar pages for {len(streams)} stream(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
