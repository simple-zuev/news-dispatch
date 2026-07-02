#!/usr/bin/env python3
"""Render News Dispatch Markdown files into a small static site.

No external dependencies. This renderer is intentionally conservative:
- reads public-safe published Markdown dispatches from dispatches/**/*.md;
- reads public radar signal metadata for stream pages;
- writes HTML pages to site/dispatches/, site/streams/ and site/rubrics/;
- writes RSS and sitemap files;
- does not fetch remote resources;
- does not inject tracking scripts.
"""

from __future__ import annotations

import html
import hashlib
import json
import re
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path

from build_today_page import (
    public_href as safe_href,
    public_text as reader_public_text,
    source_name as ranking_source_name,
)
from core import DISPATCH_DIR, ROOT, SITE_DIR, coalesce, parse_front_matter_file
from reader_text import compact_time_ru, reader_excerpt_ru, reader_source_line_ru, reader_title_ru
from newsroom_visuals import stream_visual
from stream_registry import streams as registry_streams

OUTPUT_DIR = SITE_DIR / "dispatches"
STREAM_DIR = SITE_DIR / "streams"
RUBRIC_DIR = SITE_DIR / "rubrics"
RUBRICS_PATH = ROOT / "data" / "rubrics.json"
RADAR_PATH = ROOT / "validation" / "daily-radar-latest.json"
RANKING_PATH = ROOT / "validation" / "daily-radar-ranking-latest.json"
POLICY_PATH = ROOT / "validation" / "reader-policy-latest.json"
BASE_URL = "https://simple-zuev.github.io/news-dispatch"


@dataclass(frozen=True)
class StreamInfo:
    slug: str
    title: str
    review_label: str
    description: str
    strict: bool = False

    @property
    def relative_url(self) -> str:
        return f"streams/{self.slug}.html"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.relative_url}"


@dataclass(frozen=True)
class RubricInfo:
    slug: str
    title: str
    description: str

    @property
    def relative_url(self) -> str:
        return f"rubrics/{self.slug}.html"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.relative_url}"


@dataclass
class Dispatch:
    source_path: Path
    title: str
    date: str
    stream: str
    summary: str
    body: str
    output_name: str
    primary_rubric: str = ""
    issue_type: str = ""
    publication_mode: str = ""

    @property
    def url(self) -> str:
        return f"{BASE_URL}/dispatches/{self.output_name}"

    @property
    def relative_url(self) -> str:
        return f"dispatches/{self.output_name}"


@dataclass
class Signal:
    source_path: Path
    title: str
    date: str
    stream: str
    status: str
    source_class: str
    source_type: str
    source_title: str
    source_url: str
    summary: str
    raw_title_only: bool
    confirmation_level: str
    reader_context: str
    next_check: str

    @property
    def radar_relative_url(self) -> str:
        return f"radar/{self.stream}.html"


def list_meta(meta: dict[str, object], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def first_meta(meta: dict[str, object], key: str, default: str = "") -> str:
    values = list_meta(meta, key)
    if values:
        return values[0]
    return coalesce(meta.get(key), default=default)


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


def source_name(source_title: str) -> str:
    if ":" in source_title:
        return source_title.split(":", 1)[0].strip()
    return source_title.strip()


SOURCE_CLASS_LABELS = {
    "official_source": "официальный источник",
    "official": "официальный источник",
    "regulator": "регулятор",
    "company": "компания",
    "public_media": "публичное медиа",
    "specialized_media": "профильное медиа",
    "business_media": "деловое медиа",
    "industry_media": "отраслевое медиа",
    "research_media": "исследовательский источник",
}

PUBLIC_STREAM_LABELS = {
    "finance": "Финансы",
    "crypto-finance": "Криптофинансы",
    "ai": "ИИ",
    "tech-hardware-software": "Железо и софт",
    "gear-style-edc": "EDC / стиль / вещи",
    "moscow-city": "Москва",
    "dj-audio-creative": "DJ / аудио / креатив",
    "science-discovery": "Наука",
    "general": "Спецвыпуски",
}


def has_cyrillic(value: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", value or ""))


def source_class_label(value: str) -> str:
    cleaned = str(value or "").strip()
    return SOURCE_CLASS_LABELS.get(cleaned, cleaned.replace("_", " ") or "публичный источник")


def stream_title(slug: str) -> str:
    if slug in PUBLIC_STREAM_LABELS:
        return PUBLIC_STREAM_LABELS[slug]
    stream = STREAM_BY_SLUG.get(slug)
    return stream.title if stream else slug


def stream_description(slug: str) -> str:
    stream = STREAM_BY_SLUG.get(slug)
    return stream.description if stream else ""


def signal_reader_summary(meta: dict[str, object], body: str, title: str, source_title: str) -> tuple[str, bool]:
    summary = coalesce(meta.get("summary"))
    if not summary:
        summary = first_section_paragraph(body, "Что произошло")
    if summary:
        return summary, False
    source = source_name(source_title) or "публичный источник"
    return f"{source} передал заголовок: «{title}». Это входной сигнал; контекст, последствия и интерпретации требуют проверки.", True


def signal_confirmation_level(source_class: str, confidence: str) -> str:
    confidence_part = f" Уровень уверенности: {confidence}." if confidence else ""
    if source_class in {"official_source", "official", "regulator", "company"}:
        return "Подтверждён факт публикации первичным или официальным источником; последствия и интерпретации требуют проверки." + confidence_part
    if source_class == "research_media":
        return "Предварительное исследование: подтверждён факт появления материала, но выводы не являются финальным подтверждением." + confidence_part
    if source_class in {"public_media", "specialized_media", "business_media", "industry_media", "research_media"}:
        return "Подтверждён факт появления материала в публичной ленте источника; утверждения и последствия не подтверждены." + confidence_part
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


def load_streams() -> list[StreamInfo]:
    items: list[StreamInfo] = []
    for stream in registry_streams():
        items.append(
            StreamInfo(
                slug=str(stream["slug"]),
                title=str(stream["title"]),
                review_label=str(stream.get("label", "Редакционная проверка")),
                description=str(stream.get("description", "")),
                strict=bool(stream.get("strict", False)),
            )
        )
    return items


def load_rubrics() -> list[RubricInfo]:
    if not RUBRICS_PATH.exists():
        return []
    data = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
    items: list[RubricInfo] = []
    for rubric in data.get("rubrics", []):
        slug = str(rubric.get("slug", "")).strip()
        if not slug:
            continue
        items.append(
            RubricInfo(
                slug=slug,
                title=str(rubric.get("title", slug)),
                description=str(rubric.get("description", "")),
            )
        )
    return items


STREAMS = load_streams()
RUBRICS = load_rubrics()
STREAM_BY_SLUG = {stream.slug: stream for stream in STREAMS}
RUBRIC_BY_SLUG = {rubric.slug: rubric for rubric in RUBRICS}


def output_slug(path: Path) -> str:
    return path.stem.lower().replace(" ", "-").replace("_", "-")


def load_dispatch(path: Path) -> Dispatch | None:
    doc = parse_front_matter_file(path)
    if doc.errors:
        return None
    meta = doc.metadata
    if coalesce(meta.get("status"), default="draft") != "published":
        return None
    title = coalesce(meta.get("title"), default=path.stem.replace("-", " ").title())
    return Dispatch(
        source_path=path,
        title=title,
        date=coalesce(meta.get("date")),
        stream=coalesce(meta.get("stream"), default="general"),
        summary=coalesce(meta.get("summary")),
        body=doc.body.strip(),
        output_name=f"{output_slug(path)}.html",
        primary_rubric=coalesce(meta.get("primary_rubric")),
        issue_type=coalesce(meta.get("issue_type")),
        publication_mode=coalesce(meta.get("publication_mode")),
    )


def load_signal(path_text: str) -> Signal | None:
    path = ROOT / path_text
    if not path.exists():
        return None
    doc = parse_front_matter_file(path)
    if doc.errors:
        return None
    meta = doc.metadata
    stream = first_meta(meta, "streams", default=coalesce(meta.get("stream"), default="general"))
    title = coalesce(meta.get("title"), default=path.stem.replace("-", " ").title())
    source_title = first_meta(meta, "source_titles", default=first_meta(meta, "sources", default="Публичный источник"))
    source_class = coalesce(meta.get("source_class"), default="public_source")
    summary, raw_title_only = signal_reader_summary(meta, doc.body, title, source_title)
    return Signal(
        source_path=path,
        title=title,
        date=coalesce(meta.get("date")),
        stream=stream,
        status=coalesce(meta.get("status"), default="draft"),
        source_class=source_class,
        source_type=first_meta(meta, "source_types"),
        source_title=source_title,
        source_url=first_meta(meta, "sources"),
        summary=summary,
        raw_title_only=raw_title_only,
        confirmation_level=signal_confirmation_level(source_class, coalesce(meta.get("confidence"))),
        reader_context=signal_reader_context(doc.body, stream),
        next_check=signal_next_check(doc.body, source_class),
    )


def load_live_signals() -> dict[str, list[Signal]]:
    by_stream: dict[str, list[Signal]] = {stream.slug: [] for stream in STREAMS}
    if not RADAR_PATH.exists():
        return by_stream
    data = json.loads(RADAR_PATH.read_text(encoding="utf-8"))
    for item in data.get("generated", []):
        stream = str(item.get("stream", "")).strip()
        if not stream:
            continue
        for path_text in item.get("signals", []):
            signal = load_signal(str(path_text))
            if signal is not None:
                by_stream.setdefault(stream, []).append(signal)
    return by_stream


def ordered_dispatches(dispatches: list[Dispatch]) -> list[Dispatch]:
    return sorted(dispatches, key=lambda item: (item.date, item.title), reverse=True)


def ordered_signals(signals: list[Signal]) -> list[Signal]:
    return sorted(signals, key=lambda item: (item.date, item.title), reverse=True)


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def render_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    out = ['<div class="table-scroll" role="region" aria-label="Таблица" tabindex="0">', "<table>", "<thead><tr>"]
    out.extend(f"<th>{inline_markup(cell)}</th>" for cell in header)
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            out.extend(f"<td>{inline_markup(cell)}</td>" for cell in row)
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    out.append("</div>")
    return "\n".join(out)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph)
            out.append(f"<p>{inline_markup(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            out.append("<ul>")
            out.extend(f"<li>{inline_markup(item)}</li>" for item in list_items)
            out.append("</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(render_table(table_lines))
            table_lines = []

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        flush_table()
        if stripped.startswith("### "):
            flush_paragraph()
            flush_list()
            out.append(f"<h3>{inline_markup(stripped[4:].strip())}</h3>")
        elif stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            out.append(f"<h2>{inline_markup(stripped[3:].strip())}</h2>")
        elif stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            out.append(f"<h1>{inline_markup(stripped[2:].strip())}</h1>")
        elif stripped.startswith("- "):
            flush_paragraph()
            list_items.append(stripped[2:].strip())
        else:
            paragraph.append(stripped)
    flush_paragraph()
    flush_list()
    flush_table()
    return "\n".join(out)


def head(title: str, description: str, css_href: str = "styles/main.css") -> str:
    return f"""<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="alternate" type="application/rss+xml" title="News Dispatch RSS" href="{BASE_URL}/rss.xml">
  <link rel="stylesheet" href="{css_href}">
</head>"""


def dispatch_stream_title(dispatch: Dispatch) -> str:
    stream = STREAM_BY_SLUG.get(dispatch.stream)
    return stream.title if stream else dispatch.stream


def rubric_title(slug: str) -> str:
    rubric = RUBRIC_BY_SLUG.get(slug)
    return rubric.title if rubric else slug


def dispatch_meta_label(dispatch: Dispatch) -> str:
    parts = [dispatch_stream_title(dispatch), dispatch.date]
    if dispatch.primary_rubric:
        parts.append(rubric_title(dispatch.primary_rubric))
    if dispatch.issue_type:
        parts.append(dispatch.issue_type)
    if dispatch.publication_mode and dispatch.publication_mode != "published":
        parts.append(dispatch.publication_mode)
    return " · ".join(part for part in parts if part)


def signal_meta_label(signal: Signal) -> str:
    parts = [signal.date, stream_title(signal.stream), source_class_label(signal.source_class), source_name(signal.source_title), "не опубликовано"]
    return " · ".join(part for part in parts if part)


def dispatch_card(dispatch: Dispatch, prefix: str = "") -> str:
    return f"""<article class="card">
  <p class="label">{html.escape(dispatch_meta_label(dispatch))}</p>
  <h3><a href="{prefix}{html.escape(dispatch.relative_url)}">{html.escape(dispatch.title)}</a></h3>
  <p>{html.escape(dispatch.summary)}</p>
</article>"""


def signal_card(signal: Signal, prefix: str = "") -> str:
    title = signal.title
    if signal.raw_title_only or not has_cyrillic(title):
        title = f"Источник сообщает: {stream_title(signal.stream)}"
    raw_label = '<span class="signal-raw-label">входной заголовок источника</span>' if signal.raw_title_only else '<span class="signal-raw-label">сообщение источника</span>'
    source_url = signal.source_url
    source_link = ""
    if source_url:
        source_link = f'<p class="signal-source-link"><a href="{html.escape(source_url, quote=True)}">Открыть источник</a></p>'
    source_parts = [source_name(signal.source_title) or signal.source_title, source_class_label(signal.source_class)]
    if signal.source_type:
        source_parts.append(signal.source_type)
    original_line = f'<p class="signal-original-title"><strong>Оригинал:</strong> {html.escape(signal.title)}</p>' if signal.title != title else ""
    return f"""<article class="card signal-card">
  <p class="label">Сигнал · не опубликовано · не материал · {html.escape(signal_meta_label(signal))}</p>
  <h3><a href="{prefix}{html.escape(signal.radar_relative_url)}">{html.escape(title)}</a></h3>
  {original_line}
  <p class="signal-raw-title">{raw_label}<span>Что произошло: {html.escape(signal.summary)}</span></p>
  <dl class="signal-facts">
    <div><dt>Источник</dt><dd>{html.escape(" · ".join(part for part in source_parts if part))}</dd></div>
    <div><dt>Поток</dt><dd>{html.escape(stream_title(signal.stream))}</dd></div>
    <div><dt>Подтверждение</dt><dd>{html.escape(signal.confirmation_level)}</dd></div>
    <div><dt>Почему важно</dt><dd>{html.escape(signal.reader_context)}</dd></div>
    <div><dt>Что проверить</dt><dd>{html.escape(signal.next_check)}</dd></div>
  </dl>
  <p class="signal-safety">Сигнал не является опубликованным материалом: источник сообщает факт появления материала, а выводы требуют проверки.</p>
  {source_link}
</article>"""


def stream_card(stream: StreamInfo, prefix: str = "", count: int | None = None, signal_count: int | None = None) -> str:
    parts: list[str] = []
    if count is not None:
        parts.append(f"{count} выпусков")
    if signal_count is not None:
        parts.append(f"{signal_count} сигналов")
    count_label = "" if not parts else " · " + " · ".join(parts)
    strict_class = " strict" if stream.strict else ""
    return f"""<article class="card{strict_class}">
  <p class="label">{html.escape(stream.review_label)}{html.escape(count_label)}</p>
  <h3><a href="{prefix}{html.escape(stream.relative_url)}">{html.escape(stream_title(stream.slug))}</a></h3>
  <p>{html.escape(stream.description)}</p>
</article>"""


def rubric_card(rubric: RubricInfo, prefix: str = "", count: int | None = None) -> str:
    count_label = "" if count is None else f" · {count} выпусков"
    return f"""<article class="card">
  <p class="label">Аналитическая рубрика{html.escape(count_label)}</p>
  <h3><a href="{prefix}{html.escape(rubric.relative_url)}">{html.escape(rubric.title)}</a></h3>
  <p>{html.escape(rubric.description)}</p>
</article>"""


def page_template(dispatch: Dispatch, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
{head(dispatch.title, dispatch.summary, css_href="../styles/main.css")}
<body class="dispatch-page">
  <header class="article-hero">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">{html.escape(dispatch_meta_label(dispatch))}</p>
    <h1>{html.escape(dispatch.title)}</h1>
    <p class="lede">{html.escape(dispatch.summary)}</p>
  </header>
  <main class="article-body">
    {body_html}
  </main>
</body>
</html>
"""


def stream_counts(dispatches: list[Dispatch]) -> dict[str, int]:
    counts = {stream.slug: 0 for stream in STREAMS}
    for dispatch in dispatches:
        counts[dispatch.stream] = counts.get(dispatch.stream, 0) + 1
    return counts


def signal_counts(signals: dict[str, list[Signal]]) -> dict[str, int]:
    return {stream: len(items) for stream, items in signals.items()}


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def ranking_policy_key(item: dict[str, object]) -> str:
    stable = "|".join([
        str(item.get("feed_id") or ""),
        str(item.get("url") or ""),
        str(item.get("title") or ""),
    ])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def ranking_item_key(item: dict[str, object]) -> str:
    return str(item.get("item_key") or "").strip()


def reader_safe_keys() -> set[str]:
    policy = load_json(POLICY_PATH)
    decisions = policy.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    return {
        str(row.get("item_key"))
        for row in decisions
        if isinstance(row, dict) and row.get("decision") == "reader_safe" and row.get("item_key")
    }


def ranking_stream(item: dict[str, object]) -> str:
    return str(item.get("routed_stream") or item.get("configured_stream") or "general")


def ranking_published(item: dict[str, object]) -> str:
    return compact_time_ru(item.get("published") or item.get("date"))


def load_ranking_items(limit: int | None = 32) -> list[dict[str, object]]:
    report = load_json(RANKING_PATH)
    safe_keys = reader_safe_keys()
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        stream = ranking_stream(item)
        if stream not in PUBLIC_STREAM_LABELS:
            continue
        if item.get("source_rule_status") != "accepted_by_source_rules":
            continue
        if safe_keys and ranking_item_key(item) not in safe_keys and ranking_policy_key(item) not in safe_keys:
            continue
        key = str(item.get("url") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(item)
    rows.sort(
        key=lambda item: (
            bool(item.get("selected")),
            float(item.get("selection_score") or item.get("final_score") or 0.0),
            str(item.get("published") or item.get("date") or ""),
        ),
        reverse=True,
    )
    return rows[:limit] if limit is not None else rows


def home_item_link(item: dict[str, object], text: str) -> str:
    url = str(item.get("url") or "").strip()
    if not url:
        return html.escape(text)
    return f'<a href="{html.escape(safe_href(url), quote=True)}">{html.escape(text)}</a>'


def home_ranking_title(item: dict[str, object]) -> str:
    return reader_public_text(reader_title_ru(item))


def home_ranking_excerpt(item: dict[str, object], max_len: int = 180) -> str:
    return reader_public_text(reader_excerpt_ru(item, max_len=max_len))


def home_rubric_title(slug: str) -> str:
    short = {
        "gear-style-edc": "EDC / стиль",
        "dj-audio-creative": "DJ / аудио",
    }
    return short.get(slug, stream_title(slug))


def home_feature_card(item: dict[str, object] | None) -> str:
    if not item:
        return f"""<article class="feature-card">
  {stream_visual("general", variant="feature")}
  <div class="feature-card-body">
    <p class="label">Сегодня</p>
    <h2><a href="today.html">Открыть короткий обзор за сегодня</a></h2>
  </div>
</article>"""
    stream = ranking_stream(item)
    title = home_ranking_title(item)
    original = reader_public_text(str(item.get("title") or ""))
    original_line = f'\n    <p class="feature-original">Оригинал: {html.escape(original)}</p>' if original and original != title else ""
    excerpt = home_ranking_excerpt(item, max_len=220)
    source_line = reader_public_text(reader_source_line_ru(item))
    return f"""<article class="feature-card">
  {stream_visual(stream, variant="feature")}
  <div class="feature-card-body">
    <p class="label">{html.escape(source_line)}</p>
    <h2>{home_item_link(item, title)}</h2>
    <p class="feature-summary">{html.escape(excerpt)}</p>{original_line}
  </div>
</article>"""


def quick_signal_row(item: dict[str, object]) -> str:
    stream = ranking_stream(item)
    title = home_ranking_title(item)
    source_line = reader_public_text(reader_source_line_ru(item))
    return f"""<article class="quick-signal-row">
  <span class="stream-dot stream-dot--{html.escape(stream)}" aria-hidden="true"></span>
  <div><h3>{home_item_link(item, title)}</h3><p>{html.escape(source_line)}</p></div>
</article>"""


def feed_preview_card(item: dict[str, object]) -> str:
    stream = ranking_stream(item)
    title = home_ranking_title(item)
    excerpt = home_ranking_excerpt(item, max_len=150)
    source_line = reader_public_text(reader_source_line_ru(item))
    return f"""<article class="news-preview-card">
  <span class="stream-dot stream-dot--{html.escape(stream)}" aria-hidden="true"></span>
  <div><h3>{home_item_link(item, title)}</h3><p class="news-preview-excerpt">{html.escape(excerpt)}</p><p class="news-meta">{html.escape(source_line)}</p></div>
</article>"""


def source_strip_items(items: list[dict[str, object]], limit: int = 7) -> str:
    seen: list[str] = []
    for item in items:
        source = reader_public_text(ranking_source_name(item))
        if source and source not in seen:
            seen.append(source)
        if len(seen) >= limit:
            break
    if not seen:
        seen = ["Публичные источники"]
    return "\n".join(f'<span class="source-pill">{html.escape(source)}</span>' for source in seen)


def homepage_template(dispatches: list[Dispatch], signals: dict[str, list[Signal]]) -> str:
    dispatch_counts = stream_counts(dispatches)
    all_ranking_items = load_ranking_items(limit=None)
    ranking_items = all_ranking_items[:32]
    live_counts = dict(signal_counts(signals))
    if all_ranking_items:
        live_counts = {stream.slug: 0 for stream in STREAMS}
        for item in all_ranking_items:
            stream = ranking_stream(item)
            live_counts[stream] = live_counts.get(stream, 0) + 1
    latest_time = ranking_published(ranking_items[0]) if ranking_items else "сегодня"
    feature = ranking_items[0] if ranking_items else None
    quick_rows = "\n".join(quick_signal_row(item) for item in ranking_items[1:7])
    if not quick_rows:
        quick_rows = """<article class="quick-signal-row"><div><p class="label">Сегодня</p><h3><a href="today.html">Открыть короткий обзор за сегодня</a></h3></div></article>"""
    stream_order = ["crypto-finance", "finance", "ai", "tech-hardware-software", "moscow-city", "dj-audio-creative", "gear-style-edc", "science-discovery"]
    stream_lookup = {stream.slug: stream for stream in STREAMS}
    feed_cards = "\n".join(
        f"""<article class="rubric-tile">
  <span class="stream-dot stream-dot--{html.escape(stream.slug)}" aria-hidden="true"></span>
  <h3><a href="news/{html.escape(stream.slug)}.html">{html.escape(home_rubric_title(stream.slug))}</a></h3>
  <p>{live_counts.get(stream.slug, 0)} материалов</p>
</article>"""
        for stream in (stream_lookup[slug] for slug in stream_order if slug in stream_lookup)
    )
    latest_cards = "\n".join(feed_preview_card(item) for item in ranking_items[7:22])
    if not latest_cards:
        latest_cards = """<article class="news-preview-card"><div><p class="label">Ленты</p><h3><a href="news/index.html">Открыть все ленты новостей</a></h3></div></article>"""
    digest_cards = "\n".join(
        f"""<article class="digest-preview-card">
  {stream_visual(dispatch.stream, variant="mini")}
  <p class="label">{html.escape(dispatch.date)} · {html.escape(stream_title(dispatch.stream))}</p>
  <h3><a href="{html.escape(dispatch.relative_url)}">{html.escape(dispatch.title)}</a></h3>
  <p>{html.escape(dispatch.summary)}</p>
</article>"""
        for dispatch in ordered_dispatches(dispatches)[:3]
    )
    if not digest_cards:
        digest_cards = """<article class="digest-preview-card empty-state">
  <p class="label">Нет дайджестов</p>
  <h3>Большие дайджесты пока не опубликованы.</h3>
</article>"""
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — ленты и дайджесты", "Ленты новостей и аналитические дайджесты по рубрикам.")}
<body>
  <header class="newsroom-header">
    <div class="newsroom-brand">
      <a class="brand-mark" href="index.html" aria-label="News Dispatch">ND</a>
      <a class="brand-link" href="index.html">News Dispatch</a>
    </div>
    <nav class="top-nav" aria-label="Навигация"><a href="news/index.html">Ленты</a><a href="digests/index.html">Дайджесты</a><a href="today.html">Сегодня</a><a href="radar/index.html">Источники</a></nav>
    <p class="newsroom-updated">Обновлено: {html.escape(latest_time)}</p>
  </header>

  <main class="newsroom-main">
    <section class="newsroom-top" aria-label="Главные материалы">
      {home_feature_card(feature)}
      <aside class="quick-signals" aria-label="Короткие сигналы">
        <div class="section-heading"><h2>Быстрые сигналы</h2><a href="today.html">Все сигналы</a></div>
        {quick_rows}
      </aside>
    </section>

    <section class="newsroom-bottom">
      <section class="latest-news" aria-label="Последние новости">
        <div class="section-heading"><h2>Последние новости</h2><a href="news/index.html">Все новости</a></div>
        <div class="news-preview-list">{latest_cards}</div>
      </section>

      <section class="digest-preview" aria-label="Дайджесты">
        <div class="section-heading"><h2>Дайджесты</h2><a href="digests/index.html">Все дайджесты</a></div>
        <div class="digest-preview-list">{digest_cards}</div>
      </section>
    </section>

    <section class="rubric-tiles" aria-label="Рубрики">
      <div class="section-heading"><h2>Рубрики</h2><a href="news/index.html">Все рубрики</a></div>
      <div class="rubric-tile-grid">{feed_cards}</div>
    </section>

    <footer class="source-strip" aria-label="Источники">
      <div class="section-heading"><h2>Источники</h2><a href="radar/index.html">Все источники</a></div>
      <div>{source_strip_items(ranking_items)}</div>
    </footer>
  </main>
</body>
</html>
"""


def archive_template(dispatches: list[Dispatch]) -> str:
    cards = "\n".join(dispatch_card(dispatch) for dispatch in ordered_dispatches(dispatches))
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Выпуски", "Архив выпусков.")}
<body>
  <header class="masthead compact"><a class="backlink" href="index.html">News Dispatch</a><p class="eyebrow">Архив</p><h1>Выпуски</h1><p class="lede">Архив опубликованных материалов.</p></header>
  <main><section class="grid">{cards}</section></main>
</body>
</html>
"""


def stream_index_template(dispatches: list[Dispatch], signals: dict[str, list[Signal]]) -> str:
    dispatch_counts = stream_counts(dispatches)
    live_counts = signal_counts(signals)
    cards = "\n".join(
        stream_card(stream, prefix="../", count=dispatch_counts.get(stream.slug, 0), signal_count=live_counts.get(stream.slug, 0))
        for stream in STREAMS
    )
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Темы", "Тематические разделы.", css_href="../styles/main.css")}
<body>
  <header class="masthead compact"><a class="backlink" href="../index.html">News Dispatch</a><p class="eyebrow">Темы</p><h1>Темы</h1><p class="lede">Тематические разделы объединяют опубликованные материалы и последние публичные сигналы.</p></header>
  <main><section class="grid">{cards}</section></main>
</body>
</html>
"""


def stream_page_template(stream: StreamInfo, dispatches: list[Dispatch], signals: dict[str, list[Signal]]) -> str:
    stream_dispatches = [dispatch for dispatch in ordered_dispatches(dispatches) if dispatch.stream == stream.slug]
    stream_signals = ordered_signals(signals.get(stream.slug, []))[:8]
    cards = "\n".join(dispatch_card(dispatch, prefix="../") for dispatch in stream_dispatches)
    signal_cards = "\n".join(signal_card(signal, prefix="../") for signal in stream_signals)
    published_empty = "" if cards else "<p>В этой теме пока нет опубликованных материалов.</p>"
    signals_empty = "" if signal_cards else "<p>В этой теме сейчас нет свежих сигналов.</p>"
    return f"""<!doctype html>
<html lang="ru">
{head(f"News Dispatch — {stream_title(stream.slug)}", stream.description, css_href="../styles/main.css")}
<body>
  <header class="masthead compact">
    <a class="backlink" href="../index.html">News Dispatch</a>
    <p class="eyebrow">{html.escape(stream.review_label)}</p>
    <h1>{html.escape(stream_title(stream.slug))}</h1>
    <p class="lede">{html.escape(stream.description)}</p>
    <p class="hero-actions"><a href="../radar/{html.escape(stream.slug)}.html">Открыть ленту источников</a></p>
  </header>
  <main>
    <section class="panel"><h2>Опубликованные материалы</h2><p>Материалы, прошедшие редакционную проверку.</p></section>
    <section class="grid">{cards}</section>
    {published_empty}
    <section class="panel"><h2>Свежие сигналы</h2><p>Последние публичные сигналы темы. Это повод для проверки, а не опубликованные выводы.</p></section>
    <section class="grid">{signal_cards}</section>
    {signals_empty}
  </main>
</body>
</html>
"""


def rubric_counts_for(dispatches: list[Dispatch]) -> dict[str, int]:
    counts = {rubric.slug: 0 for rubric in RUBRICS}
    for dispatch in dispatches:
        if dispatch.primary_rubric:
            counts[dispatch.primary_rubric] = counts.get(dispatch.primary_rubric, 0) + 1
    return counts


def rubric_index_template(dispatches: list[Dispatch]) -> str:
    counts = rubric_counts_for(dispatches)
    cards = "\n".join(rubric_card(rubric, prefix="../", count=counts.get(rubric.slug, 0)) for rubric in RUBRICS)
    return f"""<!doctype html>
<html lang="ru">
{head("News Dispatch — Рубрики", "Аналитические рубрики.", css_href="../styles/main.css")}
<body>
  <header class="masthead compact"><a class="backlink" href="../index.html">News Dispatch</a><p class="eyebrow">Рубрики анализа</p><h1>Рубрики анализа</h1><p class="lede">Повторяющиеся аналитические линзы: регулирование, структура рынка, инфраструктура, продукт, безопасность, исследования, пользовательская практика и слабые сигналы.</p></header>
  <main><section class="grid">{cards}</section></main>
</body>
</html>
"""


def rubric_page_template(rubric: RubricInfo, dispatches: list[Dispatch]) -> str:
    rubric_dispatches = [dispatch for dispatch in ordered_dispatches(dispatches) if dispatch.primary_rubric == rubric.slug]
    cards = "\n".join(dispatch_card(dispatch, prefix="../") for dispatch in rubric_dispatches)
    empty = "" if cards else "<p>В этой рубрике пока нет выпусков.</p>"
    return f"""<!doctype html>
<html lang="ru">
{head(f"News Dispatch — {rubric.title}", rubric.description, css_href="../styles/main.css")}
<body>
  <header class="masthead compact"><a class="backlink" href="../index.html">News Dispatch</a><p class="eyebrow">Аналитическая рубрика</p><h1>{html.escape(rubric.title)}</h1><p class="lede">{html.escape(rubric.description)}</p></header>
  <main><section class="grid">{cards}</section>{empty}</main>
</body>
</html>
"""


def rss_template(dispatches: list[Dispatch]) -> str:
    items = []
    for dispatch in ordered_dispatches(dispatches)[:20]:
        items.append(
            f"""    <item>
      <title>{html.escape(dispatch.title)}</title>
      <link>{html.escape(dispatch.url)}</link>
      <guid>{html.escape(dispatch.url)}</guid>
      <pubDate>{formatdate(usegmt=True)}</pubDate>
      <description>{html.escape(dispatch.summary)}</description>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>News Dispatch</title>
    <link>{BASE_URL}/</link>
    <description>Personal reader/radar dispatches.</description>
    <language>ru</language>
{chr(10).join(items)}
  </channel>
</rss>
"""


def sitemap_template(dispatches: list[Dispatch]) -> str:
    urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/dispatches.html",
        f"{BASE_URL}/rss.xml",
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/streams/index.html",
        f"{BASE_URL}/rubrics/index.html",
        f"{BASE_URL}/radar/index.html",
    ]
    urls.extend(stream.url for stream in STREAMS)
    urls.extend(rubric.url for rubric in RUBRICS)
    urls.extend(f"{BASE_URL}/radar/{stream.slug}.html" for stream in STREAMS)
    urls.extend(dispatch.url for dispatch in ordered_dispatches(dispatches))
    entries = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in dict.fromkeys(urls))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""


def render() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_DIR.mkdir(parents=True, exist_ok=True)
    RUBRIC_DIR.mkdir(parents=True, exist_ok=True)

    for page in OUTPUT_DIR.glob("*.html"):
        page.unlink()
    for page in RUBRIC_DIR.glob("*.html"):
        page.unlink()

    dispatches: list[Dispatch] = []
    for path in sorted(DISPATCH_DIR.rglob("*.md")):
        dispatch = load_dispatch(path)
        if dispatch is not None:
            dispatches.append(dispatch)
    signals = load_live_signals()

    for dispatch in dispatches:
        body_html = markdown_to_html(dispatch.body)
        (OUTPUT_DIR / dispatch.output_name).write_text(page_template(dispatch, body_html), encoding="utf-8")
    for stream in STREAMS:
        (STREAM_DIR / f"{stream.slug}.html").write_text(stream_page_template(stream, dispatches, signals), encoding="utf-8")
    for rubric in RUBRICS:
        (RUBRIC_DIR / f"{rubric.slug}.html").write_text(rubric_page_template(rubric, dispatches), encoding="utf-8")
    (STREAM_DIR / "index.html").write_text(stream_index_template(dispatches, signals), encoding="utf-8")
    (RUBRIC_DIR / "index.html").write_text(rubric_index_template(dispatches), encoding="utf-8")
    (SITE_DIR / "index.html").write_text(homepage_template(dispatches, signals), encoding="utf-8")
    (SITE_DIR / "dispatches.html").write_text(archive_template(dispatches), encoding="utf-8")
    (SITE_DIR / "rss.xml").write_text(rss_template(dispatches), encoding="utf-8")
    (SITE_DIR / "sitemap.xml").write_text(sitemap_template(dispatches), encoding="utf-8")


if __name__ == "__main__":
    render()
    print("Rendered News Dispatch site.")
