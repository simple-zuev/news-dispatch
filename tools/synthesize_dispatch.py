#!/usr/bin/env python3
"""Synthesize analytical dispatch drafts from News Dispatch signal files.

This tool is deliberately AI-ready but not API-dependent.  It turns selected
``signals/YYYY-MM-DD/<stream>/*.md`` files into a consistent analytical draft
with public-safety front matter and reader sections.  A human editor or an LLM
can then tighten the text, add primary-source verification and run the existing
promotion workflow before publication.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from core import (
    DISPATCH_DIR,
    ROOT,
    SIGNALS_DIR,
    VALIDATION_DIR,
    NewsDispatchError,
    clean_text,
    coalesce,
    ensure_list,
    fail,
    first_value,
    format_front_matter,
    log,
    parse_front_matter_file,
    project_path,
    read_json,
    repo_path,
    slugify,
    stable_hash,
    unique_preserve_order,
    write_text,
)

DEFAULT_SECTIONS = (
    "Issue Panel",
    "Лид",
    "Главное",
    "Что произошло",
    "Почему это важно",
    "Анализ",
    "Evidence Ledger",
    "Слухи и мнения",
    "Мнение людей",
    "Медиа и материалы",
    "Источники",
    "Что наблюдать дальше",
    "Итог",
)

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "regulation": ("регуля", "закон", "минюст", "цб", "центробанк", "надзор", "ответствен", "санкц", "лиценз"),
    "market": ("рын", "market", "fx", "stablecoin", "бирж", "trading", "стоим", "цена", "капитал"),
    "infrastructure": ("chip", "чип", "data center", "инфраструкт", "gpu", "accelerator", "модель", "api", "platform"),
    "security": ("security", "abuse", "distill", "утеч", "атака", "защит", "fraud", "risk"),
    "product": ("product", "продукт", "релиз", "платформ", "интерфейс", "пользовател"),
}

STREAM_DEFAULTS: dict[str, dict[str, str]] = {
    "finance": {
        "title": "Финансовый и регуляторный сигнал",
        "lens": "регуляторный, рыночный и организационный контур",
    },
    "crypto-finance": {
        "title": "Криптофинансовый радар",
        "lens": "регуляторика, market structure, инфраструктура и участники рынка",
    },
    "ai": {
        "title": "AI-радар",
        "lens": "модели, платформы, инфраструктура, безопасность и регулирование",
    },
    "tech-hardware-software": {
        "title": "Технологический инфраструктурный радар",
        "lens": "железо, софт, платформы, безопасность и supply chain",
    },
    "science-discovery": {
        "title": "Научный радар",
        "lens": "исследования, качество источников и прикладные последствия",
    },
}

TOPIC_RUBRICS: dict[str, tuple[str, ...]] = {
    "regulation": ("reg-watch",),
    "market": ("market-structure", "reg-watch"),
    "infrastructure": ("infrastructure",),
    "security": ("security-abuse",),
    "product": ("product-platform", "consumer-use"),
    "general-monitoring": ("weak-signals",),
}

TOPIC_ISSUE_TYPES: dict[str, str] = {
    "regulation": "reg-brief",
    "market": "market-structure-note",
    "infrastructure": "infrastructure-radar",
    "security": "claim-check",
    "product": "daily-radar-review",
    "general-monitoring": "daily-radar-review",
}

STRICT_STREAMS = {"finance", "crypto-finance"}


@dataclass(frozen=True)
class Signal:
    path: Path
    title: str
    date: str
    status: str
    confidence: str
    source_class: str
    streams: tuple[str, ...]
    sources: tuple[str, ...]
    source_titles: tuple[str, ...]
    source_types: tuple[str, ...]
    body: str

    @property
    def stream(self) -> str:
        return self.streams[0] if self.streams else "general"

    @property
    def primary_source_title(self) -> str:
        return first_value(list(self.source_titles), self.title)

    @property
    def primary_source_type(self) -> str:
        return first_value(list(self.source_types), "public_source")

    @property
    def primary_source_url(self) -> str:
        return first_value(list(self.sources), "")


@dataclass(frozen=True)
class TaxonomyDecision:
    topic: str
    primary_rubric: str
    rubrics: tuple[str, ...]
    issue_type: str
    confidence: str
    publication_mode: str
    evidence_status: str
    verification_gap: str
    claim_types: tuple[str, ...]


def load_signal(path: Path) -> Signal:
    doc = parse_front_matter_file(path)
    if doc.errors:
        raise NewsDispatchError(f"{repo_path(path)}: invalid front matter: {'; '.join(doc.errors)}")
    meta = doc.metadata
    return Signal(
        path=path,
        title=clean_text(coalesce(meta.get("title"), path.stem), 500),
        date=coalesce(meta.get("date")),
        status=coalesce(meta.get("status"), default="draft"),
        confidence=coalesce(meta.get("confidence"), default="source_reported"),
        source_class=coalesce(meta.get("source_class"), default="public_media"),
        streams=tuple(ensure_list(meta.get("streams"))),
        sources=tuple(ensure_list(meta.get("sources"))),
        source_titles=tuple(ensure_list(meta.get("source_titles"))),
        source_types=tuple(ensure_list(meta.get("source_types"))),
        body=doc.body.strip(),
    )


def load_signals(paths: Iterable[Path]) -> list[Signal]:
    signals = [load_signal(path) for path in paths]
    if not signals:
        raise NewsDispatchError("No signals selected.")
    return signals


def signal_paths_from_radar(path: Path, *, stream: str | None, limit: int) -> list[Path]:
    data = read_json(path, default={})
    paths: list[Path] = []
    for item in data.get("generated", []):
        if stream and item.get("stream") != stream:
            continue
        for raw in item.get("signals", []):
            paths.append(project_path(str(raw)))
            if limit and len(paths) >= limit:
                return paths
    return paths


def signal_paths_from_directory(day: str, *, stream: str | None, limit: int) -> list[Path]:
    root = SIGNALS_DIR / day
    if stream:
        root = root / stream
    paths = sorted(root.rglob("*.md")) if root.exists() else []
    return paths[:limit] if limit else paths


def infer_stream(signals: list[Signal], explicit: str | None) -> str:
    if explicit:
        return explicit
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal.stream] = counts.get(signal.stream, 0) + 1
    if not counts:
        return "general"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def infer_date(signals: list[Signal], explicit: str | None) -> str:
    if explicit:
        return explicit
    dates = [signal.date for signal in signals if signal.date]
    return dates[0] if dates else date.today().isoformat()


def classify_topic(signals: list[Signal]) -> str:
    haystack = " ".join(signal.title + " " + signal.body for signal in signals).lower()
    scores = {
        topic: sum(1 for keyword in keywords if keyword.lower() in haystack)
        for topic, keywords in TOPIC_KEYWORDS.items()
    }
    best, score = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0]
    return best if score else "general-monitoring"


def title_from_signals(signals: list[Signal], stream: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    default = STREAM_DEFAULTS.get(stream, {}).get("title", "Аналитический радар")
    if len(signals) == 1:
        return clean_text(signals[0].title, 96)
    topic = classify_topic(signals)
    if topic == "regulation":
        return f"{default}: регуляторный сигнал"
    if topic == "infrastructure":
        return f"{default}: инфраструктурный сигнал"
    if topic == "security":
        return f"{default}: security-сигнал"
    if topic == "market":
        return f"{default}: рыночный сигнал"
    return default


def signal_has_primary_source(signal: Signal) -> bool:
    values = {signal.source_class, *signal.source_types}
    return bool(values & {"official_source", "primary_source", "regulator", "research_media"})


def infer_rubrics(signals: list[Signal], stream: str) -> tuple[str, ...]:
    topic = classify_topic(signals)
    rubrics = list(TOPIC_RUBRICS.get(topic, ("weak-signals",)))
    if stream == "crypto-finance" and "reg-watch" not in rubrics:
        rubrics.append("reg-watch")
    if stream == "science-discovery" and "research-evidence" not in rubrics:
        rubrics.insert(0, "research-evidence")
    if stream == "moscow-city" and "city-culture" not in rubrics:
        rubrics.insert(0, "city-culture")
    return tuple(unique_preserve_order(rubrics))


def infer_issue_type(signals: list[Signal]) -> str:
    return TOPIC_ISSUE_TYPES.get(classify_topic(signals), "daily-radar-review")


def infer_confidence(signals: list[Signal]) -> str:
    source_count = len(unique_preserve_order(url for signal in signals for url in signal.sources if url))
    has_primary = any(signal_has_primary_source(signal) for signal in signals)
    if has_primary and source_count >= 2:
        return "medium"
    if has_primary:
        return "medium"
    if source_count >= 2:
        return "low"
    return "unknown"


def publication_mode_for(status: str) -> str:
    return "draft_only" if status == "draft" else "limited_publication"


def claim_types_for(signals: list[Signal]) -> tuple[str, ...]:
    values = ["source_reported_claim", "editorial_inference"]
    if any(signal_has_primary_source(signal) for signal in signals):
        values.insert(0, "confirmed_fact")
    if classify_topic(signals) == "security":
        values.append("weak_signal")
    return tuple(unique_preserve_order(values))


def evidence_status_for(signals: list[Signal], status: str) -> str:
    if status == "draft":
        return "needs_primary_source_review"
    if any(signal_has_primary_source(signal) for signal in signals):
        return "limited_publication_primary_source_present"
    return "limited_publication_media_only"


def verification_gap_for(signals: list[Signal], stream: str) -> str:
    if stream in STRICT_STREAMS:
        return "Перед публикацией проверить первичные документы, статус источников, адресатов требований и независимые подтверждения."
    if any(signal_has_primary_source(signal) for signal in signals):
        return "Проверить полноту первичного источника, независимое подтверждение и границы редакционного вывода."
    return "Найти первичные источники или явно оставить материал как source-reported / weak-signal draft."


def taxonomy_for(signals: list[Signal], stream: str, status: str) -> TaxonomyDecision:
    topic = classify_topic(signals)
    rubrics = infer_rubrics(signals, stream)
    return TaxonomyDecision(
        topic=topic,
        primary_rubric=rubrics[0],
        rubrics=rubrics,
        issue_type=infer_issue_type(signals),
        confidence=infer_confidence(signals),
        publication_mode=publication_mode_for(status),
        evidence_status=evidence_status_for(signals, status),
        verification_gap=verification_gap_for(signals, stream),
        claim_types=claim_types_for(signals),
    )


def front_matter(signals: list[Signal], *, title: str, day: str, stream: str, status: str) -> dict[str, Any]:
    sources = unique_preserve_order(url for signal in signals for url in signal.sources if url)
    source_titles = unique_preserve_order(title for signal in signals for title in signal.source_titles if title)
    source_types = unique_preserve_order(kind for signal in signals for kind in signal.source_types if kind)
    source_notes = [
        f"{signal.primary_source_type}; signal confidence: {signal.confidence}; path: {repo_path(signal.path)}."
        for signal in signals
    ]
    summary = build_summary(signals, stream)
    taxonomy = taxonomy_for(signals, stream, status)
    return {
        "title": title,
        "date": day,
        "period": day,
        "stream": stream,
        "type": "daily",
        "primary_rubric": taxonomy.primary_rubric,
        "rubrics": list(taxonomy.rubrics),
        "issue_type": taxonomy.issue_type,
        "language": "ru",
        "status": status,
        "review_level": "strict_publication_review",
        "publication_scope": "public",
        "publication_mode": taxonomy.publication_mode,
        "public_safe": True,
        "private_context_used": False,
        "contains_personal_data": False,
        "contains_internal_company_data": False,
        "contains_confidential_strategy": False,
        "contains_nonpublic_sources": False,
        "contains_investment_advice": False,
        "contains_legal_advice": False,
        "contains_advertising": False,
        "contains_paid_promotion": False,
        "source_mode": "public_sources_only",
        "summary": summary,
        "tags": tags_for(signals, stream),
        "claim_types": list(taxonomy.claim_types),
        "confidence": taxonomy.confidence,
        "evidence_status": taxonomy.evidence_status,
        "verification_gap": taxonomy.verification_gap,
        "sources": sources,
        "source_titles": source_titles,
        "source_types": source_types or ["public_source"],
        "source_notes": source_notes,
        "media": [],
        "media_titles": [],
        "media_types": [],
        "media_notes": [],
        "visuals": [],
        "visual_titles": [],
        "visual_types": [],
        "privacy_review": "passed_public_safe_draft" if status == "draft" else "passed_public_safe",
        "editorial_review": "draft_needs_primary_confirmation" if status == "draft" else "limited_publication",
    }


def tags_for(signals: list[Signal], stream: str) -> list[str]:
    topic = classify_topic(signals)
    rubrics = infer_rubrics(signals, stream)
    values = [stream, topic, *rubrics]
    for signal in signals:
        if signal.source_class:
            values.append(signal.source_class)
    return [slugify(value, fallback="tag", latin_only=True, max_len=40) for value in unique_preserve_order(values)]


def build_summary(signals: list[Signal], stream: str) -> str:
    lens = STREAM_DEFAULTS.get(stream, {}).get("lens", "рыночный, продуктовый и инфраструктурный контур")
    if len(signals) == 1:
        return f"Публичный сигнал: {signals[0].title}. Требуется первичная проверка и оценка влияния на {lens}."
    return f"Кластер из {len(signals)} публичных сигналов требует проверки первичных источников и оценки влияния на {lens}."


def bulletize(values: Iterable[str], *, limit: int = 5) -> str:
    items = [clean_text(value, 240) for value in values if clean_text(value, 240)]
    if not items:
        return "- Нет данных для вывода."
    return "\n".join(f"- {item}" for item in items[:limit])


def ordered_signal_titles(signals: list[Signal]) -> list[str]:
    return [signal.title for signal in sorted(signals, key=lambda item: (item.source_class, item.title))]


def source_inventory(signals: list[Signal]) -> str:
    lines: list[str] = []
    for signal in signals:
        lines.append(
            f"- {signal.primary_source_title} — {signal.primary_source_type}; "
            f"confidence: {signal.confidence}; signal: `{repo_path(signal.path)}`."
        )
    return "\n".join(lines)


def table_cell(value: str) -> str:
    return clean_text(value, 180).replace("|", "/") or "нет"


def claim_type_for_signal(signal: Signal) -> str:
    if signal_has_primary_source(signal):
        return "confirmed_fact"
    if "marketing" in {signal.source_class, *signal.source_types}:
        return "marketing_claim"
    return "source_reported_claim"


def evidence_ledger(signals: list[Signal], *, status: str) -> str:
    publication_mode = publication_mode_for(status)
    rows = [
        "| Claim | Claim type | Primary source | Secondary source | Confidence | Verification gap | Publication mode |",
        "|---|---|---|---|---|---|---|",
    ]
    for signal in signals:
        claim_type = claim_type_for_signal(signal)
        primary = signal.primary_source_title if claim_type == "confirmed_fact" else "нет"
        secondary = "нет" if claim_type == "confirmed_fact" else signal.primary_source_title
        gap = "Проверить первичный источник, контекст, дату, статус и независимое подтверждение."
        rows.append(
            "| "
            + " | ".join(
                [
                    table_cell(signal.title),
                    table_cell(claim_type),
                    table_cell(primary),
                    table_cell(secondary),
                    table_cell("medium" if claim_type == "confirmed_fact" else "low"),
                    table_cell(gap),
                    table_cell(publication_mode),
                ]
            )
            + " |"
        )
    rows.append(
        "| Редакционный вывод о возможном эффекте кластера | editorial_inference | нет | source packet | "
        + table_cell(infer_confidence(signals))
        + " | Проверить причинно-следственный механизм и альтернативные объяснения. | "
        + table_cell(publication_mode)
        + " |"
    )
    return "\n".join(rows)


def analysis_blocks(signals: list[Signal], stream: str) -> str:
    topic = classify_topic(signals)
    if topic == "regulation":
        return """Тезис: сигнал может указывать на формирование нового регуляторного контура.

Аргумент: в кластере присутствуют публичные сообщения о правилах, ответственности, надзоре или позиции регулятора. Пока первичные документы не проверены, это не следует трактовать как действующую норму.

Следствие/Риск: зона внимания — появление официального документа, проекта поправок, сроков вступления в силу, адресатов требований и переходных положений."""
    if topic == "infrastructure":
        return """Тезис: инфраструктурный слой становится самостоятельным источником риска и конкурентного преимущества.

Аргумент: сигналы затрагивают компоненты, от которых зависят продукты и рынки: вычисления, платформы, поставки, доступность сервисов или технические ограничения.

Следствие/Риск: зона внимания — сроки внедрения, зависимость от поставщиков, операционная устойчивость и ограничения масштабирования."""
    if topic == "security":
        return """Тезис: security-контур следует отделять от обычного продуктового шума.

Аргумент: сигналы с признаками abuse, утечки, обхода правил или атак могут быстро переходить из медийной плоскости в операционные и регуляторные последствия.

Следствие/Риск: зона внимания — первичные подтверждения, масштаб инцидента, затронутые участники и меры реагирования."""
    if topic == "market":
        return """Тезис: рыночный сигнал важен только после отделения факта от интерпретации.

Аргумент: публичные сообщения часто смешивают сделку, продуктовую инициативу, цену, ожидания участников и редакционную оценку.

Следствие/Риск: зона внимания — первичный источник, участники, инфраструктурный эффект и регуляторные ограничения. Материал не должен превращаться в торговую рекомендацию."""
    return """Тезис: сигнал требует редакционной группировки и проверки причинно-следственных связей.

Аргумент: факт появления материала в публичном источнике сам по себе не равен подтверждённому изменению правил, рынка или инфраструктуры.

Следствие/Риск: зона внимания — первичный источник, затронутые участники, практический эффект и неопределённости."""


def watch_items(signals: list[Signal]) -> list[str]:
    topic = classify_topic(signals)
    base = [
        "первичные документы или официальные заявления участников",
        "уточнение сроков, адресатов и практического эффекта",
        "реакция затронутых компаний, регуляторов или отраслевых ассоциаций",
    ]
    if topic == "regulation":
        base.extend(["проект нормы, поправки или поручения", "правоприменительные сигналы и переходные периоды"])
    elif topic == "infrastructure":
        base.extend(["техническая готовность и производственные ограничения", "зависимость от поставщиков и совместимость с текущим стеком"])
    elif topic == "security":
        base.extend(["масштаб инцидента и публичные меры реагирования", "наличие audit trail, mitigation и disclosure"])
    else:
        base.extend(["дедупликация связанных сообщений", "появление независимого подтверждения"])
    return base


def build_body(signals: list[Signal], *, title: str, stream: str, status: str) -> str:
    taxonomy = taxonomy_for(signals, stream, status)
    signal_titles = ordered_signal_titles(signals)
    source_count = len(unique_preserve_order(url for signal in signals for url in signal.sources if url))
    caveat = "Это draft: публикация требует первичной проверки." if status == "draft" else "Это limited publication note: выводы ограничены публичными источниками."

    return f"""# {title}

## Issue Panel

- Stream: `{stream}`.
- Primary rubric: `{taxonomy.primary_rubric}`.
- Rubrics: {', '.join(f'`{rubric}`' for rubric in taxonomy.rubrics)}.
- Issue type: `{taxonomy.issue_type}`.
- Confidence: `{taxonomy.confidence}`.
- Publication mode: `{taxonomy.publication_mode}`.
- Evidence status: `{taxonomy.evidence_status}`.

## Лид

{build_summary(signals, stream)} {caveat}

## Главное

1. Кластер относится к теме `{taxonomy.topic}` и требует отделения факта появления сообщения от интерпретации последствий.
2. Источниковая база: {source_count} публичных source item(s); приватные источники не используются.
3. Уровень подтверждения: `{taxonomy.confidence}`; ключевой gap — {taxonomy.verification_gap}
4. Потенциальный эффект следует оценивать через {STREAM_DEFAULTS.get(stream, {}).get('lens', 'рыночный, продуктовый и инфраструктурный контур')}.
5. Материал не содержит investment advice, legal advice или внутренних данных.

## Что произошло

В публичном радаре выделен следующий набор сигналов:

{bulletize(signal_titles)}

На текущем этапе подтверждён только факт появления этих материалов в публичных источниках или RSS/Atom-ленте. Полнота контекста, первичные документы и последствия требуют отдельной проверки.

## Почему это важно

Такие сигналы полезны не как новостной пересказ, а как раннее указание на возможное изменение повестки. Они помогают понять, где может появиться рыночный, продуктовый, регуляторный, инфраструктурный или организационный эффект.

Для публикации важно не смешивать source-reported факт, редакционную оценку и гипотезу о последствиях. До проверки первичных материалов выводы должны оставаться ограниченными.

## Анализ

{analysis_blocks(signals, stream)}

## Evidence Ledger

{evidence_ledger(signals, status=status)}

## Слухи и мнения

Слухи, инсайды, Telegram/X и форумы не использовались. Если такие сигналы будут добавлены позднее, их нужно выделить отдельно как неподтверждённый weak signal.

## Мнение людей

Пользовательская реакция и social sentiment отдельно не анализировались. Для расширенной версии можно добавить реакцию рынка, профильных экспертов, разработчиков или регуляторного сообщества.

## Медиа и материалы

Отдельные медиа-материалы не добавлены. Для следующей версии желательно прикрепить первичные документы, official release, court/regulator/company source или техническую публикацию.

## Источники

{source_inventory(signals)}

Уровень надёжности: source-reported public signals. Для перехода в published требуется promotion review.

## Что наблюдать дальше

{bulletize(watch_items(signals), limit=8)}

## Итог

Кластер является пригодной заготовкой для аналитического выпуска, но не заменяет редакционную проверку. Следующий шаг — найти первичные источники, отделить подтверждённые факты от оценок и решить, возможна ли публикация как full analysis или только как limited publication note.
"""


def build_dispatch(signals: list[Signal], *, title: str, day: str, stream: str, status: str) -> str:
    metadata = front_matter(signals, title=title, day=day, stream=stream, status=status)
    return format_front_matter(metadata) + "\n" + build_body(signals, title=title, stream=stream, status=status)


def output_path_for(title: str, day: str, stream: str) -> Path:
    slug = slugify(title, fallback=stable_hash(title), max_len=88)
    return DISPATCH_DIR / stream / f"{day}-{slug}.md"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--signals", nargs="*", help="Signal Markdown files to synthesize.")
    source.add_argument("--from-radar", nargs="?", const=str(VALIDATION_DIR / "daily-radar-latest.json"), help="Read signal paths from a Daily Radar JSON report.")
    source.add_argument("--from-date", help="Read signal files from signals/YYYY-MM-DD[/stream].")
    parser.add_argument("--stream", help="Target stream. Inferred from signals when omitted.")
    parser.add_argument("--title", help="Dispatch title. Inferred when omitted.")
    parser.add_argument("--date", help="Dispatch date. Inferred from signals when omitted.")
    parser.add_argument("--status", choices=("draft", "published"), default="draft")
    parser.add_argument("--output", help="Output Markdown file path. Defaults to dispatches/<stream>/<date>-<slug>.md.")
    parser.add_argument("--max-signals", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print", action="store_true", dest="print_output")
    return parser.parse_args(argv)


def resolve_signal_paths(args: argparse.Namespace) -> list[Path]:
    if args.signals is not None:
        paths = [project_path(path) if not Path(path).is_absolute() else Path(path) for path in args.signals]
        return paths[: args.max_signals] if args.max_signals else paths
    if args.from_radar:
        return signal_paths_from_radar(project_path(args.from_radar), stream=args.stream, limit=args.max_signals)
    if args.from_date:
        return signal_paths_from_directory(args.from_date, stream=args.stream, limit=args.max_signals)
    return []


def run(args: argparse.Namespace) -> int:
    paths = resolve_signal_paths(args)
    if not paths:
        raise NewsDispatchError("No signal paths resolved.")
    missing = [repo_path(path) for path in paths if not path.exists()]
    if missing:
        raise NewsDispatchError("Missing signal file(s): " + ", ".join(missing))

    signals = load_signals(paths)
    stream = infer_stream(signals, args.stream)
    day = infer_date(signals, args.date)
    title = title_from_signals(signals, stream, args.title)
    content = build_dispatch(signals, title=title, day=day, stream=stream, status=args.status)
    output = Path(args.output) if args.output else output_path_for(title, day, stream)

    if args.print_output or args.dry_run:
        print(content)
    if not args.dry_run:
        write_text(output, content)
        log(f"wrote {repo_path(output)}", scope="synthesize-dispatch")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(sys.argv[1:] if argv is None else argv))
    except NewsDispatchError as exc:
        fail(f"[synthesize-dispatch] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
