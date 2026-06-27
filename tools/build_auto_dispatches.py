#!/usr/bin/env python3
"""Build draft-only thematic dispatches from the latest public radar signals.

This tool creates editorial drafts, not public conclusions. It is intentionally
conservative: every generated file remains `status: draft`, uses
`publication_mode: draft_only`, and records source limitations.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from core import DISPATCH_DIR, ROOT, VALIDATION_DIR, coalesce, parse_front_matter_file, yaml_quote
from stream_registry import streams as registry_streams

RADAR_PATH = VALIDATION_DIR / "daily-radar-latest.json"
REPORT_PATH = VALIDATION_DIR / "auto-dispatch-latest.json"
MAX_SIGNALS_PER_STREAM = 6

STREAM_INFO = {str(item["slug"]): item for item in registry_streams()}
STRICT_STREAMS = {slug for slug, item in STREAM_INFO.items() if bool(item.get("strict"))}

STREAM_DEFAULTS = {
    "finance": ("reg-watch", ["reg-watch", "market-structure"], "reg-brief"),
    "crypto-finance": ("market-structure", ["market-structure", "reg-watch", "infrastructure"], "market-structure-note"),
    "ai": ("product-platform", ["product-platform", "research-evidence", "security-abuse"], "daily-radar-review"),
    "tech-hardware-software": ("infrastructure", ["infrastructure", "product-platform", "security-abuse"], "infrastructure-radar"),
    "gear-style-edc": ("consumer-use", ["consumer-use", "weak-signals"], "daily-radar-review"),
    "moscow-city": ("city-culture", ["city-culture", "consumer-use"], "daily-radar-review"),
    "dj-audio-creative": ("product-platform", ["product-platform", "consumer-use"], "daily-radar-review"),
    "science-discovery": ("research-evidence", ["research-evidence", "weak-signals"], "source-dossier"),
    "general": ("weak-signals", ["weak-signals"], "special-issue"),
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def slug_date() -> str:
    if RADAR_PATH.exists():
        data = json.loads(RADAR_PATH.read_text(encoding="utf-8"))
        raw = str(data.get("date", "")).strip()
        if raw:
            return raw
    return date.today().isoformat()


def list_value(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


@dataclass
class Signal:
    path: str
    title: str
    stream: str
    url: str
    source_title: str
    source_type: str
    source_class: str
    summary: str


def read_signal(path_text: str, fallback_stream: str) -> Signal | None:
    path = ROOT / path_text
    if not path.exists():
        return None
    doc = parse_front_matter_file(path)
    if doc.errors:
        return None
    meta = doc.metadata
    sources = list_value(meta, "sources")
    source_titles = list_value(meta, "source_titles")
    source_types = list_value(meta, "source_types")
    title = clean(coalesce(meta.get("title"), default=path.stem.replace("-", " ")))
    url = sources[0] if sources else ""
    return Signal(
        path=path_text,
        title=title,
        stream=coalesce(meta.get("stream"), default=fallback_stream),
        url=url,
        source_title=source_titles[0] if source_titles else url,
        source_type=source_types[0] if source_types else coalesce(meta.get("source_class"), default="public_source"),
        source_class=coalesce(meta.get("source_class"), default="public_source"),
        summary=clean(coalesce(meta.get("summary"), default="")),
    )


def radar_signals() -> dict[str, list[Signal]]:
    if not RADAR_PATH.exists():
        return {}
    data = json.loads(RADAR_PATH.read_text(encoding="utf-8"))
    result: dict[str, list[Signal]] = {}
    for item in data.get("generated", []):
        stream = str(item.get("stream", "")).strip()
        if not stream:
            continue
        signals = []
        for path_text in item.get("signals", [])[:MAX_SIGNALS_PER_STREAM]:
            signal = read_signal(str(path_text), stream)
            if signal is not None:
                signals.append(signal)
        result[stream] = signals
    return result


def source_classes(signals: list[Signal]) -> list[str]:
    values = []
    for signal in signals:
        value = signal.source_class or signal.source_type or "public_source"
        values.append(value)
    return sorted(set(values))


def confidence_for(stream: str, signals: list[Signal]) -> str:
    if not signals:
        return "unknown"
    classes = source_classes(signals)
    if "official_source" in classes and len(classes) >= 2:
        return "medium"
    if stream in STRICT_STREAMS:
        return "low"
    return "medium"


def claim_types_for(stream: str, signals: list[Signal]) -> list[str]:
    claims = ["source_reported_claim", "editorial_inference"]
    if any(signal.source_class == "official_source" for signal in signals):
        claims.insert(0, "confirmed_fact")
    if stream in {"gear-style-edc", "moscow-city", "dj-audio-creative"}:
        claims.append("community_signal")
    return list(dict.fromkeys(claims))


def yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "\n".join(f"  - {yaml_quote(value)}" for value in values)


def output_path(stream: str, day: str) -> Path:
    return DISPATCH_DIR / stream / f"{day}-auto-radar-draft.md"


def source_summary(signals: list[Signal]) -> str:
    classes = Counter(signal.source_class or signal.source_type or "public_source" for signal in signals)
    return ", ".join(f"{key}: {value}" for key, value in sorted(classes.items()))


def build_dispatch(stream: str, signals: list[Signal], day: str) -> str:
    stream_title = str(STREAM_INFO.get(stream, {}).get("title", stream))
    primary, rubrics, issue_type = STREAM_DEFAULTS.get(stream, STREAM_DEFAULTS["general"])
    confidence = confidence_for(stream, signals)
    claim_types = claim_types_for(stream, signals)
    title = f"{stream_title}: черновик обзора сигналов за {day}"
    summary = f"Автоматически подготовленный черновик по теме «{stream_title}»: {len(signals)} публичных сигналов для редакционной проверки."
    verification_gap = "Автоматическая сборка не подтверждает факты за пределами самих публичных сообщений источников; перед публикацией нужна проверка первичных документов, статусов, дат и контекста."
    source_urls = [signal.url for signal in signals if signal.url]
    source_titles = [signal.source_title or signal.title for signal in signals if signal.url]
    source_types = [signal.source_type or signal.source_class or "Публичный источник" for signal in signals if signal.url]
    source_notes = ["Сигнал из автоматического радара; требует редакционной проверки перед публикацией." for signal in signals if signal.url]

    lines = [
        "---",
        f"title: {yaml_quote(title)}",
        f"date: {yaml_quote(day)}",
        f"period: {yaml_quote(day)}",
        f"stream: {yaml_quote(stream)}",
        'type: "daily"',
        f"primary_rubric: {yaml_quote(primary)}",
        "rubrics:",
        yaml_list(rubrics),
        f"issue_type: {yaml_quote(issue_type)}",
        'language: "ru"',
        'status: "draft"',
        'review_level: "strict_publication_review"' if stream in STRICT_STREAMS else 'review_level: "standard_public_review"',
        'publication_scope: "public"',
        'publication_mode: "draft_only"',
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
        "tags:",
        yaml_list([stream, primary, "auto-draft", "radar"]),
        "claim_types:",
        yaml_list(claim_types),
        f"confidence: {yaml_quote(confidence)}",
        f"evidence_status: {yaml_quote('automatic_draft_source_reported_signals')}",
        f"verification_gap: {yaml_quote(verification_gap)}",
        "sources:",
        yaml_list(source_urls),
        "source_titles:",
        yaml_list(source_titles),
        "source_types:",
        yaml_list(source_types),
        "source_notes:",
        yaml_list(source_notes),
        "media:",
        yaml_list(source_urls[:4]),
        "media_titles:",
        yaml_list(source_titles[:4]),
        "media_types:",
        yaml_list(source_types[:4]),
        "media_notes:",
        yaml_list(["Внешний публичный материал; визуальное превью берётся из метаданных источника при наличии." for _ in source_urls[:4]]),
        "visuals: []",
        "visual_titles: []",
        "visual_types: []",
        'privacy_review: "auto_passed_public_sources_only"',
        'editorial_review: "automatic_draft_needs_human_review"',
        "---",
        "",
        f"# {title}",
        "",
        "## Лид",
        "",
        f"Это автоматический черновик по теме «{stream_title}». Он собирает публичные сигналы за период и помогает редактору быстро понять, какие события стоит проверить дальше. Черновик не является опубликованным выпуском и не содержит итоговых рекомендаций.",
        "",
        "## Главное",
        "",
    ]
    for index, signal in enumerate(signals[:5], start=1):
        lines.append(f"{index}. {signal.title} — сообщение источника «{signal.source_title or signal.source_type}»; требует проверки перед выводами.")
    if not signals:
        lines.append("1. За период нет достаточного количества публичных сигналов для тематического черновика.")
    lines.extend([
        "",
        "## Что произошло",
        "",
    ])
    for signal in signals:
        line = f"- {signal.title}"
        if signal.source_title:
            line += f". Источник: {signal.source_title}."
        if signal.url:
            line += f" URL: {signal.url}"
        lines.append(line)
    lines.extend([
        "",
        "## Почему это важно",
        "",
        "Сигналы сгруппированы по теме, но автоматическая группировка не доказывает общий тренд. Для публикации нужно проверить первичные документы, сопоставить независимые источники и отделить факты от сообщений медиа, оценок и слабых сигналов.",
        "",
        "## Аналитическая рамка",
        "",
        "Тезис: подборка показывает область для наблюдения, а не готовый вывод.",
        "",
        f"Аргумент: в черновик попали источники классов: {source_summary(signals) or 'нет данных'}. Разные классы источников дают разный уровень подтверждения.",
        "",
        "Следствие/риск: публикационная версия должна отдельно указать, что подтверждено первичным источником, что является сообщением медиа и что остаётся редакционной гипотезой.",
        "",
        "## Реестр подтверждения",
        "",
        "| Сигнал | Тип | Источник | Уверенность | Что проверить |",
        "|---|---|---|---|---|",
    ])
    for signal in signals:
        lines.append(f"| {signal.title} | source_reported_claim | {signal.source_title or signal.source_type} | {confidence} | Первичный источник, дата, статус, контекст и независимые подтверждения. |")
    lines.extend([
        "",
        "## Что проверять дальше",
        "",
        "- Наличие первичных источников по каждому значимому утверждению.",
        "- Дедупликацию связанных материалов и повторяющихся сообщений.",
        "- Разделение факта, сообщения источника, оценки, гипотезы и слабого сигнала.",
        "- Для финансовых, криптофинансовых, регуляторных и security-сюжетов — отсутствие инвестиционных, юридических, налоговых или операционных рекомендаций.",
        "",
        "## Статус",
        "",
        "Материал является автоматическим черновиком. Для публикации требуется редакционная проверка источников, статусов и формулировок.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    day = slug_date()
    by_stream = radar_signals()
    generated = []
    for stream, signals in sorted(by_stream.items()):
        if not signals:
            continue
        path = output_path(stream, day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_dispatch(stream, signals, day), encoding="utf-8")
        generated.append({
            "stream": stream,
            "signals": len(signals),
            "path": path.relative_to(ROOT).as_posix(),
            "publication_mode": "draft_only",
            "status": "draft",
        })
        print(f"Wrote {path.relative_to(ROOT)}")
    REPORT_PATH.write_text(json.dumps({"date": day, "generated": generated}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
