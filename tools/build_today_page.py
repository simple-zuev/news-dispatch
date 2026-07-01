#!/usr/bin/env python3
"""Build the autonomous Today digest from Daily Radar reports.

The page is public-safe: it turns machine-gated source-reported signals into a
reader-grade digest without requiring a daily human publish decision.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_reader_policy import build_policy_report, item_key
from core import SITE_DIR, VALIDATION_DIR, write_text

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
POLICY_PATH = VALIDATION_DIR / "reader-policy-latest.json"
AUTO_DISPATCH_PATH = VALIDATION_DIR / "auto-dispatch-latest.json"
REVIEWED_RADAR_PATH = VALIDATION_DIR / "reviewed-radar-latest.md"
OUTPUT_PATH = SITE_DIR / "today.html"

STREAM_LABELS = {
    "finance": "Финансы",
    "crypto-finance": "Криптофинансы",
    "ai": "AI",
    "tech-hardware-software": "Железо и софт",
    "gear-style-edc": "EDC / style",
    "moscow-city": "Москва",
    "dj-audio-creative": "DJ / audio",
    "science-discovery": "Наука",
}

STREAM_EFFECTS = {
    "finance": "Потенциальная зона внимания: рыночные ожидания, ставки, ликвидность, валютные и долговые условия.",
    "crypto-finance": "Потенциальная зона внимания: регулирование, инфраструктура оборота цифровых активов, AML/KYC/KYT и платёжные каналы.",
    "ai": "Потенциальная зона внимания: продуктовые возможности, вычислительная инфраструктура, модели, данные и регуляторный контур.",
    "tech-hardware-software": "Потенциальная зона внимания: технологические зависимости, цепочки поставок, платформы и инфраструктурные риски.",
    "gear-style-edc": "Потенциальная зона внимания: потребительские паттерны, дизайн, доступность, качество и прикладная полезность.",
    "moscow-city": "Потенциальная зона внимания: городская инфраструктура, сервисы, транспорт, регуляторика и повседневная среда.",
    "dj-audio-creative": "Потенциальная зона внимания: оборудование, софт, площадки, авторские права и творческая инфраструктура.",
    "science-discovery": "Потенциальная зона внимания: научная воспроизводимость, технологический перенос и горизонт прикладного эффекта.",
}

STREAM_MONITORING = {
    "finance": "Проверить первоисточник, реакцию регуляторов, динамику ставок, ликвидности, валютного рынка и комментарии крупных участников.",
    "crypto-finance": "Проверить первичные документы, правоприменение, позиции регуляторов, бирж, банков, кастодианов и провайдеров AML/KYT.",
    "ai": "Проверить релизные notes, paper/model card, лицензии, доступность API, benchmark-контекст и ограничения внедрения.",
    "tech-hardware-software": "Проверить vendor notes, security advisories, зависимые платформы, сроки поставок, совместимость и поддержку.",
    "gear-style-edc": "Проверить независимые обзоры, сертификацию, гарантию, реальные сценарии использования и устойчивость качества.",
    "moscow-city": "Проверить официальные документы, сроки запуска, фактическую доступность сервиса и влияние на жителей/бизнес.",
    "dj-audio-creative": "Проверить спецификации, совместимость, лицензионные условия, доступность и отзывы профессионального сообщества.",
    "science-discovery": "Проверить публикацию, методологию, данные, независимое подтверждение и границы применимости результата.",
}

SOURCE_TODAY_CAPS = {
    "openai-news": 2,
    "arxiv-cs-ai": 1,
    "google-security-blog": 2,
    "tomshardware": 2,
    "science-daily": 1,
    "sneaker-news": 1,
}

STREAM_TODAY_CAP = 4
GENERAL_SPECIAL_USE_STREAM = "general"

STOPWORDS = {
    "the", "and", "for", "from", "with", "this", "that", "into", "over", "after", "before", "about", "news", "update", "updates",
    "как", "что", "это", "для", "или", "при", "над", "под", "после", "перед", "новости", "обновление", "сигнал",
}

FORBIDDEN_READER_PATTERNS = [
    r"\b(buy|sell|hold)\b",
    r"\b(long|short)\b",
    r"\bprice target\b",
    r"\bwill rise\b",
    r"\bwill fall\b",
    r"покупать",
    r"продавать",
    r"держать позицию",
    r"целевая цена",
    r"точный прогноз",
    r"гарантированно",
]

PRIVATE_CONTEXT_PATTERNS = [
    r"api[_-]?key",
    r"access[_-]?token",
    r"refresh[_-]?token",
    r"auth[_-]?token",
    r"secret[_-]?key",
    r"client[_-]?secret",
    r"password",
    r"private[_-]?key\s*[:=]",
    r"our product",
    r"our company",
    r"internal roadmap",
    r"customer data",
    r"наш продукт",
    r"наша компания",
    r"внутренн(ий|яя|ие) роадмап",
    r"клиентские данные",
]

DIGEST_SECTIONS = [
    "Главное за период",
    "События с наибольшим эффектом",
    "Регуляторика и правовой контур",
    "Инфраструктура и участники рынка",
    "Продуктовые и организационные импликации",
    "Радар слабых сигналов",
    "Что проверять дальше",
    "Источники и уровень надёжности",
]


@dataclass(frozen=True)
class DigestGate:
    passed: bool
    reasons: list[str]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def score(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def numeric(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def effective_score(item: dict[str, Any]) -> float:
    score_value = item.get("selection_score")
    if score_value is None:
        score_value = item.get("final_score")
    return numeric(score_value)


def load_report(path: Path = REPORT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"date": "", "items": [], "fetch_errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_auto_dispatch_report(path: Path = AUTO_DISPATCH_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"date": "", "generated": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(report: dict[str, Any], path: Path = POLICY_PATH) -> dict[str, Any]:
    if path.exists():
        policy = json.loads(path.read_text(encoding="utf-8"))
        report_keys = {
            item_key(item)
            for item in report.get("items", [])
            if isinstance(item, dict)
        }
        policy_keys = {
            str(decision.get("item_key"))
            for decision in policy.get("decisions", [])
            if isinstance(decision, dict) and decision.get("item_key")
        }
        if report_keys and report_keys <= policy_keys:
            return policy
    return build_policy_report(report)


def reader_safe_keys(policy: dict[str, Any]) -> set[str]:
    decisions = policy.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    return {
        str(decision.get("item_key"))
        for decision in decisions
        if isinstance(decision, dict) and decision.get("decision") == "reader_safe" and decision.get("item_key")
    }


def policy_decisions(policy: dict[str, Any], decision: str) -> list[dict[str, Any]]:
    decisions = policy.get("decisions", [])
    if not isinstance(decisions, list):
        return []
    return [item for item in decisions if isinstance(item, dict) and item.get("decision") == decision]


def stream_slug(item: dict[str, Any]) -> str:
    return str(item.get("routed_stream") or item.get("configured_stream") or "")


def stream_label(slug: object) -> str:
    text = str(slug or "")
    return STREAM_LABELS.get(text, text or "Без потока")


def selected_items(report: dict[str, Any], policy: dict[str, Any] | None = None, limit: int = 18) -> list[dict[str, Any]]:
    items, _diagnostics = select_today_items(report, policy, limit=limit)
    return items


def source_cap(item: dict[str, Any]) -> int:
    return SOURCE_TODAY_CAPS.get(str(item.get("feed_id") or ""), 3)


def eligible_today_items(report: dict[str, Any], policy: dict[str, Any] | None) -> list[dict[str, Any]]:
    items = [
        item
        for item in report.get("items", [])
        if isinstance(item, dict)
        and item.get("source_rule_status") == "accepted_by_source_rules"
        and stream_slug(item) != GENERAL_SPECIAL_USE_STREAM
    ]
    if policy is None:
        return items
    allowed = reader_safe_keys(policy)
    return [item for item in items if item_key(item) in allowed]


def select_today_items(report: dict[str, Any], policy: dict[str, Any] | None = None, limit: int = 18) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = sorted(eligible_today_items(report, policy), key=effective_score, reverse=True)
    selected: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    stream_counts: Counter[str] = Counter()
    capped: Counter[str] = Counter()
    skipped_stream: Counter[str] = Counter()

    def can_add(item: dict[str, Any]) -> bool:
        feed_id = str(item.get("feed_id") or "unknown")
        stream = stream_slug(item)
        if source_counts[feed_id] >= source_cap(item):
            capped[feed_id] += 1
            return False
        if stream_counts[stream] >= STREAM_TODAY_CAP:
            skipped_stream[stream] += 1
            return False
        return True

    def add(item: dict[str, Any]) -> None:
        selected.append(item)
        source_counts[str(item.get("feed_id") or "unknown")] += 1
        stream_counts[stream_slug(item)] += 1

    seen_ids: set[str] = set()
    for stream in sorted({stream_slug(item) for item in candidates}):
        stream_items = [item for item in candidates if stream_slug(item) == stream]
        if stream_items and len(selected) < limit and can_add(stream_items[0]):
            add(stream_items[0])
            seen_ids.add(item_key(stream_items[0]))

    for item in candidates:
        if len(selected) >= limit:
            break
        key = item_key(item)
        if key in seen_ids:
            continue
        if can_add(item):
            add(item)
            seen_ids.add(key)

    selected = sorted(selected, key=effective_score, reverse=True)
    diagnostics = {
        "source_counts_by_stream": dict(Counter(stream_slug(item) for item in report.get("items", []) if isinstance(item, dict))),
        "eligible_reader_safe_by_stream": dict(Counter(stream_slug(item) for item in candidates)),
        "selected_today_by_stream": dict(stream_counts),
        "selected_today_by_source": dict(source_counts),
        "source_caps": SOURCE_TODAY_CAPS,
        "stream_cap": STREAM_TODAY_CAP,
        "capped_sources": dict(capped),
        "stream_cap_skips": dict(skipped_stream),
        "ranking_capped_rows": (report.get("ranking_diagnostics") or {}).get("capped_rows", {}),
        "downweighted_sources": downweighted_sources(report),
    }
    return selected, diagnostics


def downweighted_sources(report: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        adjustments = item.get("ranking_adjustments")
        if isinstance(adjustments, list) and any("downweighted" in str(adjustment) for adjustment in adjustments):
            counts[str(item.get("feed_id") or "unknown")] += 1
    return dict(counts)


def auto_dispatch_items(auto_report: dict[str, Any]) -> list[dict[str, Any]]:
    items = auto_report.get("generated", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def auto_dispatch_note(auto_report: dict[str, Any]) -> str:
    items = auto_dispatch_items(auto_report)
    if not items:
        return "Автоматические draft-only материалы отсутствуют; дайджест собран только из reader-safe radar items."
    streams = ", ".join(stream_label(item.get("stream")) for item in items[:6])
    draft_only = all(str(item.get("publication_mode")) == "draft_only" for item in items)
    status = "все отмечены как draft_only" if draft_only else "часть материалов требует отдельной проверки статуса"
    return f"Auto-dispatch artifacts использованы как контур проверки, а не как готовый анализ: {len(items)} stream draft(s), {status}. Потоки: {streams}."


def reviewed_radar_note() -> str:
    if REVIEWED_RADAR_PATH.exists():
        text = REVIEWED_RADAR_PATH.read_text(encoding="utf-8")
        summary_lines = [
            line.strip("- ").strip()
            for line in text.splitlines()
            if line.startswith("- Retained signals:") or line.startswith("- Streams with retained signals:") or line.startswith("- Fetch warnings:")
        ]
        if summary_lines:
            return "Reviewed radar artifact summary: " + "; ".join(summary_lines) + "."
        return "Reviewed radar artifact найден и используется как подтверждение, что сигнал прошёл предварительную машинную группировку."
    return "Reviewed radar artifact не найден; digest gate учитывает это как ограничение, но не просит ручного решения."


def stream_summary(items: list[dict[str, Any]]) -> str:
    counts = Counter(stream_slug(item) for item in items)
    if not counts:
        return "<p>Нет reader-safe данных для сводки по потокам.</p>"
    rows = "".join(f"<li>{esc(stream_label(slug))}: {count}</li>" for slug, count in counts.most_common())
    return f"<ul>{rows}</ul>"


def evidence_hits(item: dict[str, Any]) -> list[str]:
    for key in ("include_hits", "boost_hits", "stream_keyword_hits"):
        value = item.get(key)
        if isinstance(value, list) and value:
            return [str(part) for part in value[:5]]
    return []


def all_evidence_hits(item: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for key in ("include_hits", "boost_hits", "stream_keyword_hits"):
        value = item.get(key)
        if isinstance(value, list):
            hits.extend(str(part) for part in value)
    return hits


def topic_terms(item: dict[str, Any]) -> set[str]:
    haystack = " ".join([str(item.get("title") or ""), " ".join(all_evidence_hits(item))]).lower()
    terms = set(re.findall(r"[a-zа-я0-9]{3,}", haystack))
    return {term for term in terms if term not in STOPWORDS}


def topic_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    if stream_slug(left) != stream_slug(right):
        return 0.0
    left_terms = topic_terms(left)
    right_terms = topic_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    overlap = len(left_terms & right_terms)
    return overlap / min(len(left_terms), len(right_terms))


def cluster_items(items: list[dict[str, Any]], limit: int = 12) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    for item in items:
        for cluster in clusters:
            if topic_similarity(item, cluster[0]) >= 0.5:
                cluster.append(item)
                break
        else:
            clusters.append([item])
    clusters = sorted(clusters, key=lambda cluster: numeric(cluster[0].get("final_score")), reverse=True)
    return clusters[:limit]


def cluster_sources(cluster: list[dict[str, Any]]) -> list[str]:
    sources: list[str] = []
    for item in cluster:
        source = str(item.get("feed_title") or item.get("feed_id") or "Публичный источник")
        if source not in sources:
            sources.append(source)
    return sources


def cluster_materials(cluster: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for index, item in enumerate(cluster, start=1):
        source = item.get("feed_title") or item.get("feed_id") or "Публичный источник"
        title = item.get("title") or "Без заголовка"
        url = item.get("url") or ""
        title_html = esc(title)
        if url:
            title_html = f'<a href="{esc(url)}">{title_html}</a>'
        rows.append(f"<li><strong>{index}. {esc(source)}:</strong> {title_html}</li>")
    return '<ul class="cluster-materials">' + "".join(rows) + "</ul>"


def confirmation_level(item: dict[str, Any]) -> str:
    source_class = str(item.get("source_class") or "public_source")
    source_type = str(item.get("source_type") or "public source")
    status = str(item.get("source_rule_status") or "unknown")
    if source_class in {"official", "official_source", "regulator", "company"}:
        base = "высокий для факта публикации первоисточником"
    elif source_class in {"public_media", "industry_media", "specialized_media"}:
        base = "средний для факта публикации в публичном источнике"
    elif source_class == "research_media":
        base = "ограниченный; research/preprint signal, не финальное подтверждение"
    else:
        base = "ограниченный; требуется ручная сверка источника"
    return f"{base}; source class: {source_class}, source type: {source_type}, rule status: {status}."


def thesis(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    title = str(item.get("title") or "Без заголовка")
    stream = stream_label(stream_slug(item))
    if len(cluster) > 1:
        return f"В потоке «{stream}» зафиксирован кластер публичных сигналов по теме: {title}"
    return f"В потоке «{stream}» зафиксирован публичный сигнал: {title}"


def argument(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    sources = cluster_sources(cluster)
    hits = evidence_hits(item)
    parts = [
        f"Источники в кластере: {len(sources)} ({', '.join(sources[:4])}).",
        f"Итоговый score: {score(item.get('final_score'))}.",
        f"Relevance: {score(item.get('relevance_score'))}.",
    ]
    if hits:
        parts.append("Ключевые совпадения: " + ", ".join(hits) + ".")
    if item.get("translation_required"):
        parts.append("Для русскоязычного выпуска требуется смысловая нормализация, а не буквальный перевод.")
    return " ".join(parts)


def implication(item: dict[str, Any]) -> str:
    slug = stream_slug(item)
    effect = STREAM_EFFECTS.get(slug, "Потенциальная зона внимания: уточнить рыночный, продуктовый, регуляторный или инфраструктурный эффект.")
    return effect + " Формулировка является зоной мониторинга, а не прогнозом и не инструкцией к действию."


def uncertainty(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    if len(cluster) > 1:
        rank_note = f"Кластер объединяет {len(cluster)} похожих items; это повышает видимость сигнала, но не подтверждает факт само по себе."
    elif item.get("selected"):
        rank_note = "Сигнал выбран ранжированием Daily Radar."
    else:
        rank_note = "Сигнал прошёл source-rule отбор, но не был выбран как top-ranked item."
    return rank_note + " Требуется сверка первоисточника, даты, контекста и независимых подтверждений перед включением в аналитический выпуск."


def monitoring(item: dict[str, Any]) -> str:
    return STREAM_MONITORING.get(
        stream_slug(item),
        "Проверить первоисточник, дату, контекст, независимое подтверждение и возможный эффект для соответствующего тематического потока.",
    )


def card(cluster: list[dict[str, Any]]) -> str:
    item = cluster[0]
    stream = stream_label(stream_slug(item))
    sources = cluster_sources(cluster)
    title = item.get("title") or "Без заголовка"
    url = item.get("url") or ""
    title_html = esc(title)
    if url:
        title_html = f'<a href="{esc(url)}">{title_html}</a>'
    cluster_label = f"cluster {len(cluster)} item(s) · {len(sources)} source(s)"

    return f"""<article class="card signal-card">
  <p class="label">{esc(stream)} · {esc(cluster_label)} · score {score(effective_score(item))} · relevance {score(item.get("relevance_score"))}</p>
  <h3>{title_html}</h3>
  <p><strong>Тезис:</strong> {esc(thesis(item, cluster))}</p>
  <p><strong>Аргумент:</strong> {esc(argument(item, cluster))}</p>
  <p><strong>Следствие/риск:</strong> {esc(implication(item))}</p>
  <p><strong>Уровень подтверждения:</strong> {esc(confirmation_level(item))}</p>
  <p><strong>Что отслеживать дальше:</strong> {esc(monitoring(item))}</p>
  <p><strong>Материалы кластера:</strong></p>
  {cluster_materials(cluster)}
  <p><strong>Неопределённость:</strong> {esc(uncertainty(item, cluster))}</p>
</article>"""


def cards_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<article class="card empty-state"><p class="label">Нет reader-safe данных</p><h3>Нет сигналов для публичного отображения</h3><p>Свежие items не прошли reader policy gate или были оставлены только в audit/review контуре.</p></article>'
    return "\n".join(card(cluster) for cluster in cluster_items(items))


def pattern_present(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def source_labels_present(items: list[dict[str, Any]]) -> bool:
    return all(item.get("source_class") and item.get("source_type") and (item.get("feed_title") or item.get("feed_id")) for item in items)


def public_input_text(report: dict[str, Any], policy: dict[str, Any], auto_report: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in report.get("items", []):
        if isinstance(item, dict):
            chunks.extend(str(item.get(key) or "") for key in ("title", "feed_title", "feed_id", "url"))
    for item in policy.get("decisions", []):
        if isinstance(item, dict):
            chunks.extend(str(item.get(key) or "") for key in ("title", "url", "source_class", "source_rule_status"))
    for item in auto_dispatch_items(auto_report):
        chunks.extend(str(item.get(key) or "") for key in ("stream", "path", "publication_mode", "status"))
    return "\n".join(chunks)


def digest_gate(report: dict[str, Any], policy: dict[str, Any], items: list[dict[str, Any]], auto_report: dict[str, Any]) -> DigestGate:
    failures: list[str] = []
    notes: list[str] = []

    if not items:
        failures.append("Нет reader-safe items для автономного дайджеста.")
    if items and not source_labels_present(items):
        failures.append("Не у всех reader-safe items есть source name, source class и source type.")
    if pattern_present(PRIVATE_CONTEXT_PATTERNS, public_input_text(report, policy, auto_report)):
        failures.append("Privacy preflight нашёл private/internal-sensitive паттерн во входных данных.")
    if any(pattern_present(FORBIDDEN_READER_PATTERNS, str(item.get("title") or "")) for item in items):
        failures.append("Reader-safe выборка содержит инвестиционно-директивную формулировку.")

    auto_items = auto_dispatch_items(auto_report)
    if auto_items and not all(str(item.get("publication_mode")) == "draft_only" for item in auto_items):
        failures.append("Auto-dispatch artifacts должны оставаться draft_only и не подменять digest analysis.")

    if not REVIEWED_RADAR_PATH.exists():
        notes.append("Reviewed radar artifact отсутствует; digest построен только по ranking/policy gate.")

    if failures:
        return DigestGate(False, failures + notes)

    notes.extend([
        "Privacy preflight для входных данных Today passed; финальный build также запускает repository privacy_scan.",
        "Source labels present: source name, class and type доступны для reader-safe items.",
        "Факты, trends, hypotheses и weak signals разделены по секциям и safety labels.",
        "Investment advice отсутствует; reader text использует monitoring/verification language.",
        "Verification gaps явно показаны в секции «Что проверять дальше».",
        "Raw source-reported claims не представлены как confirmed facts.",
    ])
    return DigestGate(True, notes)


def list_html(items: list[str]) -> str:
    if not items:
        return "<ul><li>Нет reader-safe данных для этой секции.</li></ul>"
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def top_streams(items: list[dict[str, Any]]) -> str:
    counts = Counter(stream_slug(item) for item in items)
    if not counts:
        return "нет reader-safe потоков"
    return ", ".join(f"{stream_label(slug)}: {count}" for slug, count in counts.most_common(4))


def source_counts(items: list[dict[str, Any]]) -> str:
    counts = Counter(str(item.get("source_class") or "unknown") for item in items)
    if not counts:
        return "source labels unavailable"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def stream_count_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["Нет данных."]
    return [f"{stream_label(slug)}: {count}" for slug, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))]


def source_count_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["Нет сработавших caps/downweights."]
    return [f"{source}: {count}" for source, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))]


def diagnostics_section(diagnostics: dict[str, Any], gate: DigestGate) -> str:
    lines = [
        "Source counts by stream: " + "; ".join(stream_count_lines(diagnostics.get("source_counts_by_stream", {}))),
        "Reader-safe eligible by stream: " + "; ".join(stream_count_lines(diagnostics.get("eligible_reader_safe_by_stream", {}))),
        "Selected Today items by stream: " + "; ".join(stream_count_lines(diagnostics.get("selected_today_by_stream", {}))),
        "Capped sources in Today selection: " + "; ".join(source_count_lines(diagnostics.get("capped_sources", {}))),
        "Rows capped in ranking report: " + "; ".join(source_count_lines(diagnostics.get("ranking_capped_rows", {}))),
        "Downweighted sources: " + "; ".join(source_count_lines(diagnostics.get("downweighted_sources", {}))),
        "Withheld/privacy-gated reasons: " + "; ".join(gate.reasons),
    ]
    return digest_section("Диагностика отбора", list_html(lines))


def regulatory_items(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    result: list[str] = []
    keywords = ("regulat", "law", "legal", "cbr", "central bank", "банк", "цб", "регул", "прав")
    for item in items:
        text = " ".join([str(item.get("title") or ""), " ".join(all_evidence_hits(item))]).lower()
        if item.get("source_class") in {"official", "regulator"} or any(keyword in text for keyword in keywords):
            result.append(f"{item.get('title') or 'Без заголовка'} — source-reported; проверить первичный документ и правовой статус.")
    return result[:limit]


def infrastructure_items(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    result: list[str] = []
    streams = {"crypto-finance", "ai", "tech-hardware-software", "finance"}
    keywords = ("infra", "platform", "bank", "exchange", "settlement", "custody", "api", "инфраструкт", "банк", "бирж")
    for item in items:
        text = " ".join([str(item.get("title") or ""), " ".join(all_evidence_hits(item))]).lower()
        if stream_slug(item) in streams or any(keyword in text for keyword in keywords):
            source = item.get("feed_title") or item.get("feed_id") or "Публичный источник"
            result.append(f"{item.get('title') or 'Без заголовка'} — участник/источник: {source}; статус: source-reported, без вывода о рыночном эффекте.")
    return result[:limit]


def implication_lines(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for slug in [slug for slug, _ in Counter(stream_slug(item) for item in items).most_common()]:
        effect = STREAM_EFFECTS.get(slug)
        if effect:
            lines.append(f"{stream_label(slug)}: {effect} Это не рекомендация, а карта наблюдения.")
    return lines[:6]


def weak_signal_lines(policy: dict[str, Any]) -> list[str]:
    review_count = len(policy_decisions(policy, "review_only"))
    blocked_count = len(policy_decisions(policy, "blocked"))
    lines = [
        f"Review-only items: {review_count}; они не превращены в finished analysis и не требуют решения пользователя.",
        f"Blocked items: {blocked_count}; они исключены из reader digest автоматическим gate.",
        "Медиа-сообщения и одиночные source-reported claims в digest читаются как слабые/проверочные сигналы до появления первичного подтверждения.",
    ]
    return lines


def next_checks(clusters: list[list[dict[str, Any]]], limit: int = 7) -> list[str]:
    lines: list[str] = []
    for cluster in clusters:
        item = cluster[0]
        lines.append(f"{stream_label(stream_slug(item))}: {monitoring(item)}")
    return lines[:limit]


def reliability_lines(items: list[dict[str, Any]], auto_report: dict[str, Any]) -> list[str]:
    lines = [
        f"Source classes in reader-safe digest: {source_counts(items)}.",
        "Confirmed fact означает только факт появления материала в первичном/официальном источнике; impact и causality остаются отдельной проверкой.",
        "Source-reported claim означает сообщение публичного источника; оно не подтверждает последствия, полноту контекста или интерпретацию.",
        auto_dispatch_note(auto_report),
        reviewed_radar_note(),
    ]
    return lines


def digest_section(title: str, body: str) -> str:
    return f'<section class="panel digest-section"><h2>{esc(title)}</h2>{body}</section>'


def autonomous_digest(report: dict[str, Any], policy: dict[str, Any], items: list[dict[str, Any]], auto_report: dict[str, Any], gate: DigestGate, diagnostics: dict[str, Any]) -> str:
    clusters = cluster_items(items)
    top_titles = [f"{cluster[0].get('title') or 'Без заголовка'} — {stream_label(stream_slug(cluster[0]))}; {uncertainty(cluster[0], cluster)}" for cluster in clusters[:5]]
    sections = [
        digest_section(
            "Главное за период",
            f"<p>Автономный дайджест за {esc(report.get('date'))}: {len(items)} reader-safe item(s), {len(clusters)} cluster(s), основные потоки: {esc(top_streams(items))}. Human approval is not required for routine autonomous daily publication when machine gates pass.</p><p>{esc(policy_summary(policy))}</p>",
        ),
        digest_section("События с наибольшим эффектом", list_html(top_titles)),
        digest_section("Регуляторика и правовой контур", list_html(regulatory_items(items))),
        digest_section("Инфраструктура и участники рынка", list_html(infrastructure_items(items))),
        digest_section("Продуктовые и организационные импликации", list_html(implication_lines(items))),
        digest_section("Радар слабых сигналов", list_html(weak_signal_lines(policy))),
        digest_section("Что проверять дальше", list_html(next_checks(clusters))),
        digest_section("Источники и уровень надёжности", list_html(reliability_lines(items, auto_report))),
        diagnostics_section(diagnostics, gate),
        digest_section("Automated Gate", list_html([f"PASS: {reason}" for reason in gate.reasons])),
    ]
    cards = f'<section class="grid latest-grid" aria-label="Reader-safe signal cards">{cards_block(items)}</section>'
    return "\n".join(sections + [cards])


def fallback_digest(report: dict[str, Any], policy: dict[str, Any], items: list[dict[str, Any]], gate: DigestGate) -> str:
    safe_summary = stream_summary(items) if items else "<p>Нет reader-safe сигналов для fallback digest.</p>"
    return "\n".join([
        '<section class="panel gate-fallback"><h2>Digest withheld by automated gate</h2><p>Автономный daily digest не опубликован как reader-grade выпуск. Пользовательское решение не требуется: слабые или небезопасные элементы автоматически понижены, исключены или оставлены в audit контуре.</p>'
        + list_html(gate.reasons)
        + "</section>",
        f'<section class="panel"><h2>Available safe signals</h2>{safe_summary}</section>',
        f'<section class="grid latest-grid" aria-label="Safe fallback signal cards">{cards_block(items)}</section>',
        '<section class="panel boundary"><h2>Граница интерпретации</h2><p>Fallback не является публикацией анализа. Raw source-reported claims не представлены как confirmed facts.</p></section>',
    ])


def policy_summary(policy: dict[str, Any]) -> str:
    counts = policy.get("counts", {}) if isinstance(policy.get("counts"), dict) else {}
    safe = int(counts.get("reader_safe", 0) or 0)
    review = int(counts.get("review_only", 0) or 0)
    blocked = int(counts.get("blocked", 0) or 0)
    return f"Reader policy gate: reader_safe={safe}, review_only={review}, blocked={blocked}. Today Radar рендерит только reader_safe items."


def render(report: dict[str, Any], policy: dict[str, Any] | None = None, auto_report: dict[str, Any] | None = None) -> str:
    policy = policy or load_policy(report)
    auto_report = auto_report or load_auto_dispatch_report()
    items, diagnostics = select_today_items(report, policy=policy)
    clusters = cluster_items(items)
    total = len(report.get("items", []))
    selected = len([item for item in report.get("items", []) if item.get("selected")])
    filtered = len([item for item in report.get("items", []) if item.get("source_rule_status") != "accepted_by_source_rules"])
    errors = len(report.get("fetch_errors", []))
    gate = digest_gate(report, policy, items, auto_report)
    digest_body = autonomous_digest(report, policy, items, auto_report, gate, diagnostics) if gate.passed else fallback_digest(report, policy, items, gate)
    page_title = "News Dispatch — автономный дневной дайджест"
    h1 = "Автономный дневной дайджест"
    mode_label = "AUTONOMOUS DIGEST" if gate.passed else "AUTOMATED GATE FALLBACK"
    lede = (
        "Reader-grade daily digest, собранный автоматически из public-source radar artifacts после machine safety/source/quality gates. "
        "Routine human approval is not required."
        if gate.passed
        else "Safe fallback Today page: digest withheld by automated gate, без запроса ручного publish decision."
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <meta name="description" content="Автономный дневной дайджест News Dispatch.">
  <link rel="stylesheet" href="styles/main.css">
</head>
<body>
  <header class="masthead compact">
    <a class="backlink" href="index.html">News Dispatch</a>
    <p class="eyebrow">{mode_label} · {esc(report.get("date"))}</p>
    <h1>{h1}</h1>
    <p class="lede">{esc(lede)}</p>
    <p class="hero-actions"><a href="today.html">Открыть дайджест</a><a href="daily-radar-ranking-latest.json">Ranking JSON</a><a href="reader-policy-latest.json">Reader Policy JSON</a><a href="radar/index.html">Live Radar</a><a href="dispatches.html">Архив</a></p>
  </header>
  <main>
    <section class="panel digest-status"><h2>Статус автономного выпуска</h2><p>Всего items: {total}. Выбрано ранжированием: {selected}. Reader-safe items: {len(items)}. Кластеров: {len(clusters)}. Отфильтровано source rules: {filtered}. Ошибок источников: {errors}. Gate: {"passed" if gate.passed else "withheld"}.</p></section>
    {digest_body}
    <section class="panel boundary"><h2>Граница интерпретации</h2><p>Факт появления материала в источнике не равен подтверждённому изменению рынка, регулирования или инфраструктуры. Это не инвестиционная, юридическая или операционная рекомендация.</p></section>
  </main>
</body>
</html>
"""


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    report = load_report()
    write_text(OUTPUT_PATH, render(report, load_policy(report), load_auto_dispatch_report()))
    print(f"Built {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
