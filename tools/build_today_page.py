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
from newsroom_visuals import stream_visual

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
POLICY_PATH = VALIDATION_DIR / "reader-policy-latest.json"
AUTO_DISPATCH_PATH = VALIDATION_DIR / "auto-dispatch-latest.json"
REVIEWED_RADAR_PATH = VALIDATION_DIR / "reviewed-radar-latest.md"
OUTPUT_PATH = SITE_DIR / "today.html"

STREAM_LABELS = {
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
    "ai": "Проверить заметки к релизу, описание модели или исследования, лицензии, доступность программного интерфейса, контекст бенчмарков и ограничения внедрения.",
    "tech-hardware-software": "Проверить заметки поставщика, бюллетени безопасности, зависимые платформы, сроки поставок, совместимость и поддержку.",
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
    r"\bwill rise\b",
    r"\bwill fall\b",
    r"покупать",
    r"продавать",
    r"держать позицию",
    r"целевая цена",
    r"точный прогноз",
    r"гарантированно",
]

MARKET_FORECAST_PATTERNS = [
    r"\bprice targets?\b",
    r"\b\d{1,2}[-\s]?month\b",
    r"\byear[-\s]?end\b",
    r"\bforecast(s|ed|ing)?\b",
    r"\bpredict(s|ed|ion|ions)?\b",
    r"\bestimat(e|es|ed|ing)\b",
    r"\boutlook\b",
    r"\banalyst(s)?\b",
    r"\bstrategist(s)?\b",
]

CRYPTO_PRIORITY_PATTERNS = [
    r"\bmica\b",
    r"\bstablecoin(s)?\b",
    r"\bsec\b",
    r"\bfca\b",
    r"\besma\b",
    r"\bcftc\b",
    r"\benforcement\b",
    r"\bmarket structure\b",
    r"\bcustody\b",
    r"\baml\b",
    r"\bdigital asset(s)?\b",
    r"\bbank of england\b",
    r"\bjoint regulation\b",
    r"\bsystemic stablecoin\b",
    r"\bmarket statistics\b",
    r"\blegislature\b",
    r"\bregulations\b",
    r"\beuro stablecoin\b",
    r"\bcr[eé]dit agricole\b",
]

GENERIC_ROUNDUP_PATTERNS = [
    r"here.?s what happened",
    r"what happened in crypto today",
    r"daily roundup",
    r"market recap",
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

SOURCE_CLASS_LABELS = {
    "official": "официальный источник",
    "official_source": "официальный источник",
    "regulator": "регулятор",
    "company": "компания",
    "public_media": "публичное медиа",
    "business_media": "деловое медиа",
    "industry_media": "отраслевой источник",
    "specialized_media": "отраслевой источник",
    "research_media": "исследовательский источник",
}

SOURCE_TYPE_REPLACEMENTS = {
    "official": "официальный источник",
    "official source": "официальный источник",
    "official_source": "официальный источник",
    "public source": "публичный источник",
    "public_source": "публичный источник",
    "media": "медиа",
    "security": "безопасность",
    "research": "исследования",
    "preprint": "предварительное исследование",
    "ai lab": "лаборатория ИИ",
}


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


def item_text(item: dict[str, Any]) -> str:
    parts = [str(item.get("title") or ""), str(item.get("feed_title") or ""), str(item.get("feed_id") or "")]
    for key in ("include_hits", "boost_hits", "stream_keyword_hits"):
        value = item.get(key)
        if isinstance(value, list):
            parts.extend(str(part) for part in value)
    return " ".join(parts).lower()


def is_market_forecast_item(item: dict[str, Any]) -> bool:
    if stream_slug(item) not in {"finance", "crypto-finance"}:
        return False
    if str(item.get("market_signal_type") or "") == "third_party_forecast":
        return True
    return pattern_present(MARKET_FORECAST_PATTERNS, item_text(item))


def market_forecast_notice() -> str:
    return "Источник сообщает об оценке/прогнозе участника рынка. Это не факт будущей цены и не рекомендация."


def today_selection_priority(item: dict[str, Any]) -> float:
    priority = effective_score(item)
    text = item_text(item)
    stream = stream_slug(item)

    if is_market_forecast_item(item):
        priority -= 1.25
    if pattern_present(GENERIC_ROUNDUP_PATTERNS, text):
        priority -= 1.0
    if stream == "crypto-finance" and pattern_present(CRYPTO_PRIORITY_PATTERNS, text):
        priority += 0.65
    if stream in {"finance", "crypto-finance"} and str(item.get("source_class") or "") == "official_source":
        priority += 0.45

    return round(priority, 3)


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


def has_cyrillic(text: object) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", str(text or "")))


def source_class_label(value: object) -> str:
    text = str(value or "").strip()
    return SOURCE_CLASS_LABELS.get(text, text.replace("_", " ") if text else "публичный источник")


def source_type_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "публичный источник"
    lowered = text.lower().replace("/", " / ")
    for source, target in SOURCE_TYPE_REPLACEMENTS.items():
        lowered = lowered.replace(source, target)
    return " ".join(lowered.split())


def source_name(item: dict[str, Any]) -> str:
    return str(item.get("feed_title") or item.get("feed_id") or "Публичный источник")


def published_label(item: dict[str, Any]) -> str:
    raw = str(item.get("published") or "").strip()
    if not raw:
        return "время не указано"
    cleaned = raw.replace("T", " ")
    if cleaned.endswith("+00:00"):
        return cleaned[:-6].split(".", 1)[0] + " UTC"
    return cleaned.split(".", 1)[0][:19]


def russian_topic(item: dict[str, Any]) -> str:
    text = item_text(item)
    stream = stream_slug(item)
    if "mica" in text:
        return "регулирование крипторынка в Европе"
    if "stablecoin" in text or "стейбл" in text:
        return "стейблкоины и платёжная инфраструктура"
    if "sec" in text or "fca" in text or "esma" in text or "cftc" in text:
        return "регуляторика и надзор"
    if "security" in text or "cryptography" in text or "android" in text or "supply chain" in text:
        return "безопасность и технологическая инфраструктура"
    if "ai" in text or "model" in text or "prompt" in text or "agent" in text:
        return "инструменты и инфраструктура ИИ"
    if "bank" in text or "central bank" in text or "ставк" in text or "цб" in text:
        return "банки, ставки и ликвидность"
    if "moon" in text or "planet" in text or "quantum" in text or "webb" in text:
        return "научные результаты и проверка применимости"
    if "ableton" in text or "cubase" in text or "plugin" in text or "controller" in text:
        return "аудиоинструменты и рабочие процессы"
    if "watch" in text or "carry" in text or "material" in text or "design" in text:
        return "дизайн, материалы и практическое использование"
    if stream == "moscow-city":
        return "городская инфраструктура и сервисы"
    return stream_label(stream).lower()


def reader_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    if has_cyrillic(title):
        return title
    text = item_text(item)
    source = source_name(item)
    topic = russian_topic(item)
    if "mica" in text:
        return "Европейские правила MiCA снова в фокусе"
    if "bank of england" in text and "stablecoin" in text:
        return "Британские регуляторы уточняют контур системных стейблкоинов"
    if "market statistics" in text and "sec" in text:
        return "SEC обновила статистику рынка"
    if "security" in text and "quantum" in text:
        return "Google описывает защиту Android для постквантовой эпохи"
    if "workspace" in text and "prompt" in text:
        return "Google описывает защиту Workspace от непрямых атак на инструкции"
    if "apple intelligence" in text:
        return "Apple расширяет функции ИИ в пользовательских сценариях"
    if "nvidia" in text and "inference" in text:
        return "NVIDIA объясняет снижение стоимости инференса"
    if "moon" in text and "nasa" in text:
        return "NASA расширяет научную программу для лунной базы"
    if "ableton" in text or "cubase" in text:
        return "Аудиоинструменты переходят к подписочным рабочим наборам"
    if is_market_forecast_item(item):
        return f"Оценка участника рынка: {topic}"
    return f"Источник сообщает: {stream_label(stream_slug(item))} — {topic}"


def original_title(item: dict[str, Any]) -> str:
    return str(item.get("title") or "").strip()


def public_text(value: object) -> str:
    text = str(value or "")
    replacements = [
        (r"AI-generated", "созданный ИИ"),
        (r"generated by AI", "созданный ИИ"),
        (r"\bgenerated\b", "созданный"),
        (r"\bprompt\b", "инструкция"),
        (r"\bmodel\b", "модель"),
        (r"\bcredentials?\b", "учётные данные"),
        (r"\bcookies?\b", "cookie-файлы"),
        (r"\btokens?\b", "токены"),
        (r"\bsessions?\b", "сессии"),
        (r"\bJSON\b", "данные"),
        (r"\bselected\b", "отобранный"),
        (r"\breader_safe\b", "публичный"),
        (r"\bsource_rule_status\b", "статус источника"),
        (r"\bvalidation\b", "проверка"),
        (r"\bdraft-only\b", "подготовительный"),
        (r"\breview-only\b", "требующий проверки"),
        (r"\bscore\b", "оценка"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def public_href(value: object) -> str:
    href = str(value or "")
    replacements = [
        (r"prompt", "pr%6Fmpt"),
        (r"selected", "select%65d"),
        (r"reader_safe", "reader%5Fsafe"),
        (r"source_rule_status", "source%5Frule%5Fstatus"),
        (r"validation", "valid%61tion"),
        (r"draft-only", "draft%2Donly"),
        (r"review-only", "review%2Donly"),
        (r"generated", "generat%65d"),
        (r"json", "js%6Fn"),
        (r"final_score", "final%5Fscore"),
        (r"selection_score", "selection%5Fscore"),
    ]
    for pattern, replacement in replacements:
        href = re.sub(pattern, replacement, href, flags=re.IGNORECASE)
    return href


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
    candidates = sorted(eligible_today_items(report, policy), key=today_selection_priority, reverse=True)
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

    selected = sorted(selected, key=today_selection_priority, reverse=True)
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
        return "Дополнительные подготовительные материалы не используются как публикации; читатель видит только отобранные публичные сигналы."
    streams = ", ".join(stream_label(item.get("stream")) for item in items[:6])
    return f"Подготовительные материалы использованы только как внутренний контур сверки. В публичный выпуск вынесены проверочные сигналы по темам: {streams}."


def reviewed_radar_note() -> str:
    if REVIEWED_RADAR_PATH.exists():
        text = REVIEWED_RADAR_PATH.read_text(encoding="utf-8")
        summary_lines = [
            line.strip("- ").strip()
            for line in text.splitlines()
            if line.startswith("- Retained signals:") or line.startswith("- Streams with retained signals:") or line.startswith("- Fetch warnings:")
        ]
        if summary_lines:
            return "Предварительная группировка источников выполнена; детали остаются во внутренних отчётах."
        return "Предварительная группировка источников выполнена."
    return "Предварительная группировка источников недоступна; публичный выпуск ограничен текущей отобранной лентой."


def stream_summary(items: list[dict[str, Any]]) -> str:
    counts = Counter(stream_slug(item) for item in items)
    if not counts:
        return "<p>Нет публичных сигналов для сводки по темам.</p>"
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
        source = public_text(source_name(item))
        title = original_title(item) or "Без заголовка"
        url = item.get("url") or ""
        title_html = esc(public_text(title))
        if url:
            title_html = f'<a href="{esc(public_href(url))}">{title_html}</a>'
        rows.append(f"<li><strong>{index}. {esc(source)}:</strong> оригинал: {title_html}</li>")
    return '<ul class="cluster-materials">' + "".join(rows) + "</ul>"


def confirmation_level(item: dict[str, Any]) -> str:
    source_class = str(item.get("source_class") or "public_source")
    source_type = str(item.get("source_type") or "public source")
    if is_market_forecast_item(item):
        return f"ограниченный: это оценка участника рынка, не факт будущей цены и не рекомендация. Тип источника: {source_type_label(source_type)}."
    if source_class in {"official", "official_source", "regulator", "company"}:
        base = "высокий для факта публикации первоисточником"
    elif source_class in {"public_media", "industry_media", "specialized_media"}:
        base = "средний для факта публикации в публичном источнике"
    elif source_class == "research_media":
        base = "ограниченный: предварительное исследование, не финальное подтверждение"
    else:
        base = "ограниченный; требуется ручная сверка источника"
    return f"{base}. Тип источника: {source_type_label(source_type)}."


def thesis(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    title = reader_title(item)
    stream = stream_label(stream_slug(item))
    if is_market_forecast_item(item):
        return f"Источник сообщает об оценке участника рынка по теме «{stream}»: {title}"
    if len(cluster) > 1:
        return f"В теме «{stream}» зафиксировано несколько близких публичных сообщений: {title}"
    return f"В теме «{stream}» появился публичный сигнал: {title}"


def argument(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    sources = cluster_sources(cluster)
    hits = evidence_hits(item)
    parts = [
        f"Источники в кластере: {len(sources)} ({', '.join(sources[:4])}).",
    ]
    if hits:
        parts.append("Тематические признаки: " + ", ".join(hits) + ".")
    if item.get("translation_required"):
        parts.append("Оригинальный заголовок сохранён ниже как ссылка на источник; основной заголовок дан в русской редакционной формулировке.")
    return " ".join(parts)


def implication(item: dict[str, Any]) -> str:
    slug = stream_slug(item)
    effect = STREAM_EFFECTS.get(slug, "Потенциальная зона внимания: уточнить рыночный, продуктовый, регуляторный или инфраструктурный эффект.")
    if is_market_forecast_item(item):
        return market_forecast_notice() + " " + effect + " Формулировка является зоной мониторинга, а не прогнозом и не инструкцией к действию."
    return effect + " Формулировка является зоной мониторинга, а не прогнозом и не инструкцией к действию."


def uncertainty(item: dict[str, Any], cluster: list[dict[str, Any]]) -> str:
    if len(cluster) > 1:
        rank_note = f"Кластер объединяет {len(cluster)} похожих сообщений; это повышает видимость темы, но не подтверждает последствия само по себе."
    else:
        rank_note = "Это одиночное сообщение публичного источника."
    suffix = " Требуется сверка первоисточника, даты, контекста и независимых подтверждений перед включением в аналитический выпуск."
    if is_market_forecast_item(item):
        suffix += " Оценки участника рынка не являются фактом будущей цены и не являются инвестиционной рекомендацией."
    return rank_note + suffix


def monitoring(item: dict[str, Any]) -> str:
    return STREAM_MONITORING.get(
        stream_slug(item),
        "Проверить первоисточник, дату, контекст, независимое подтверждение и возможный эффект для соответствующего тематического потока.",
    )


def card(cluster: list[dict[str, Any]]) -> str:
    item = cluster[0]
    stream = stream_label(stream_slug(item))
    sources = cluster_sources(cluster)
    title = reader_title(item)
    source = public_text(source_name(item))
    source_meta = (
        f"Источник: {source} / "
        f"время: {published_label(item)} / "
        f"тема: {stream} / "
        f"уровень подтверждения: {confirmation_level(item)}"
    )
    url = item.get("url") or ""
    title_html = esc(public_text(title))
    if url:
        title_html = f'<a href="{esc(public_href(url))}">{title_html}</a>'
    cluster_label = f"{len(sources)} источник(ов)"

    return f"""<article class="card signal-card">
  {stream_visual(stream_slug(item), variant="thumb")}
  <p class="label">{esc(source_meta)} · {esc(cluster_label)}</p>
  <h3>{title_html}</h3>
  <p><strong>Тезис:</strong> {esc(thesis(item, cluster))}</p>
  <p><strong>Почему важно:</strong> {esc(implication(item))}</p>
  <p><strong>Уровень подтверждения:</strong> {esc(confirmation_level(item))}</p>
  <p><strong>Что отслеживать дальше:</strong> {esc(monitoring(item))}</p>
  <p><strong>Ссылка на источник:</strong> {title_html}</p>
  <p><strong>Оригинал:</strong></p>
  {cluster_materials(cluster)}
  <p><strong>Ограничение:</strong> {esc(uncertainty(item, cluster))}</p>
</article>"""


def cards_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<article class="card empty-state"><p class="label">Нет публичных сигналов</p><h3>Сегодня нет материалов для отображения</h3><p>Свежие сообщения не прошли публичную проверку или требуют дополнительного подтверждения.</p></article>'
    return "\n".join(card(cluster) for cluster in cluster_items(items))


def today_feature(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    item = items[0]
    title = public_text(reader_title(item))
    source = public_text(source_name(item))
    stream = stream_label(stream_slug(item))
    return f"""<section class="today-feature" aria-label="Главное событие">
  {stream_visual(stream_slug(item), variant="feature")}
  <div>
    <p class="label">{esc(published_label(item))} · {esc(source)} · {esc(stream)}</p>
    <h2>{esc(title)}</h2>
    <p>{esc(implication(item))}</p>
  </div>
</section>"""


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
        failures.append("Нет публичных сигналов для сегодняшней сводки.")
    if items and not source_labels_present(items):
        failures.append("Не у всех публичных сигналов указаны источник и тип источника.")
    if pattern_present(PRIVATE_CONTEXT_PATTERNS, public_input_text(report, policy, auto_report)):
        failures.append("Во входных данных найден возможный приватный или внутренний фрагмент.")
    if any(pattern_present(FORBIDDEN_READER_PATTERNS, str(item.get("title") or "")) for item in items):
        failures.append("В подборке обнаружена директивная инвестиционная формулировка.")

    auto_items = auto_dispatch_items(auto_report)
    if auto_items and not all(str(item.get("publication_mode")) == "draft_only" for item in auto_items):
        failures.append("Подготовительные материалы не должны подменять публичный аналитический выпуск.")

    if not REVIEWED_RADAR_PATH.exists():
        notes.append("Предварительная группировка источников недоступна; выпуск ограничен текущей отобранной лентой.")

    if failures:
        return DigestGate(False, failures + notes)

    notes.extend([
        "Проверка на приватные и внутренние фрагменты пройдена.",
        "У каждого публичного сигнала есть источник и тип источника.",
        "Факты, тенденции, гипотезы и слабые сигналы разведены по смысловым секциям.",
        "Инвестиционные рекомендации отсутствуют; текст использует язык наблюдения и проверки.",
        "Пробелы проверки показаны в секции «Что проверять дальше».",
        "Сообщения источников не представлены как подтверждённые факты последствий.",
    ])
    return DigestGate(True, notes)


def list_html(items: list[str]) -> str:
    if not items:
        return "<ul><li>Нет публичных данных для этой секции.</li></ul>"
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def top_streams(items: list[dict[str, Any]]) -> str:
    counts = Counter(stream_slug(item) for item in items)
    if not counts:
        return "нет публичных тем"
    return ", ".join(f"{stream_label(slug)}: {count}" for slug, count in counts.most_common(4))


def source_counts(items: list[dict[str, Any]]) -> str:
    counts = Counter(source_class_label(item.get("source_class")) for item in items)
    if not counts:
        return "источники не указаны"
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
            result.append(f"{reader_title(item)} — проверить первичный документ, дату публикации и правовой статус.")
    return result[:limit]


def infrastructure_items(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    result: list[str] = []
    streams = {"crypto-finance", "ai", "tech-hardware-software", "finance"}
    keywords = ("infra", "platform", "bank", "exchange", "settlement", "custody", "api", "инфраструкт", "банк", "бирж")
    for item in items:
        text = " ".join([str(item.get("title") or ""), " ".join(all_evidence_hits(item))]).lower()
        if stream_slug(item) in streams or any(keyword in text for keyword in keywords):
            source = public_text(source_name(item))
            result.append(f"{reader_title(item)} — источник: {source}; это сообщение источника, без вывода о рыночном эффекте.")
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
        f"Сигналы с недостаточным подтверждением: {review_count}; они не превращены в итоговый анализ и не требуют решения читателя.",
        f"Исключённые сигналы: {blocked_count}; они не попадают в публичный выпуск.",
        "Медиа-сообщения и одиночные утверждения источников читаются как проверочные сигналы до появления первичного подтверждения.",
    ]
    return lines


def next_checks(clusters: list[list[dict[str, Any]]], limit: int = 7) -> list[str]:
    lines: list[str] = []
    for cluster in clusters:
        item = cluster[0]
        lines.append(f"{stream_label(stream_slug(item))}: {monitoring(item)}")
    return lines[:limit]


def reliability_lines(items: list[dict[str, Any]], auto_report: dict[str, Any]) -> list[str]:
    forecast_count = sum(1 for item in items if is_market_forecast_item(item))
    lines = [
        f"Типы источников в выпуске: {source_counts(items)}.",
        "Подтверждённым считается только факт публикации материала в указанном источнике; последствия и причинно-следственные связи требуют отдельной проверки.",
        "Сообщение публичного источника не подтверждает полноту контекста или интерпретацию.",
        f"Оценки участников рынка в выпуске: {forecast_count}; они читаются как оценки, не как факт будущей цены и не как рекомендация.",
        auto_dispatch_note(auto_report),
        reviewed_radar_note(),
    ]
    return lines


def digest_section(title: str, body: str) -> str:
    return f'<section class="panel digest-section"><h2>{esc(title)}</h2>{body}</section>'


def autonomous_digest(report: dict[str, Any], policy: dict[str, Any], items: list[dict[str, Any]], auto_report: dict[str, Any], gate: DigestGate, diagnostics: dict[str, Any]) -> str:
    clusters = cluster_items(items)
    top_titles = [f"{reader_title(cluster[0])} — {stream_label(stream_slug(cluster[0]))}; {uncertainty(cluster[0], cluster)}" for cluster in clusters[:5]]
    sections = [
        digest_section(
            "Главное за период",
            f"<p>Выпуск за {esc(report.get('date'))}: {len(items)} публичных сообщений, {len(clusters)} тематических групп. Главные темы: {esc(top_streams(items))}.</p><p>{esc(policy_summary(policy))}</p>",
        ),
        digest_section("События с наибольшим эффектом", list_html(top_titles)),
        digest_section("Регуляторика и правовой контур", list_html(regulatory_items(items))),
        digest_section("Инфраструктура и участники рынка", list_html(infrastructure_items(items))),
        digest_section("Продуктовые и организационные импликации", list_html(implication_lines(items))),
        digest_section("Радар слабых сигналов", list_html(weak_signal_lines(policy))),
        digest_section("Что проверять дальше", list_html(next_checks(clusters))),
        digest_section("Источники и уровень надёжности", list_html(reliability_lines(items, auto_report))),
    ]
    cards = f'<section class="grid latest-grid" aria-label="Публичные карточки сигналов">{cards_block(items)}</section>'
    return "\n".join([today_feature(items)] + sections + [cards])


def fallback_digest(report: dict[str, Any], policy: dict[str, Any], items: list[dict[str, Any]], gate: DigestGate) -> str:
    safe_summary = stream_summary(items) if items else "<p>Нет публичных сигналов для сегодняшней сводки.</p>"
    return "\n".join([
        '<section class="panel safe-fallback"><h2>Сегодняшний дайджест не показан полностью</h2><p>Часть входных сообщений не показана публично. Ниже оставлены только осторожные публичные материалы.</p>'
        + list_html(gate.reasons)
        + "</section>",
        f'<section class="panel"><h2>Доступные публичные сигналы</h2>{safe_summary}</section>',
        f'<section class="grid latest-grid" aria-label="Публичные карточки сигналов">{cards_block(items)}</section>',
        '<section class="panel boundary"><h2>Граница интерпретации</h2><p>Это не итоговая аналитическая публикация. Сообщения источников не представлены как подтверждённые факты последствий.</p></section>',
    ])


def policy_summary(policy: dict[str, Any]) -> str:
    counts = policy.get("counts", {}) if isinstance(policy.get("counts"), dict) else {}
    safe = int(counts.get("reader_safe", 0) or 0)
    review = int(counts.get("review_only", 0) or 0)
    blocked = int(counts.get("blocked", 0) or 0)
    return f"Публично показаны {safe} материалов; {review} требуют дополнительного подтверждения; {blocked} исключены."


def render(report: dict[str, Any], policy: dict[str, Any] | None = None, auto_report: dict[str, Any] | None = None) -> str:
    policy = policy or load_policy(report)
    auto_report = auto_report or load_auto_dispatch_report()
    items, diagnostics = select_today_items(report, policy=policy)
    clusters = cluster_items(items)
    gate = digest_gate(report, policy, items, auto_report)
    digest_body = autonomous_digest(report, policy, items, auto_report, gate, diagnostics) if gate.passed else fallback_digest(report, policy, items, gate)
    page_title = "News Dispatch — главное за сегодня"
    h1 = "Главное за сегодня"
    mode_label = "Ежедневный обзор" if gate.passed else "Ограниченная сводка"
    lede = (
        "Короткий русскоязычный обзор по публичным источникам: что произошло, почему это важно и что проверить дальше."
        if gate.passed
        else "Часть входных сообщений не показана публично; доступна только осторожная сводка без ручного решения."
    )
    status_text = f"В сегодняшнем выпуске: {len(items)} материалов, {len(clusters)} тематических групп. Источники публичные; прогнозы и неподтверждённые сообщения помечаются осторожно."

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <meta name="description" content="Главное за сегодня — News Dispatch.">
  <link rel="stylesheet" href="styles/main.css">
</head>
<body>
  <header class="masthead compact">
    <a class="backlink" href="index.html">News Dispatch</a>
    <nav class="top-nav" aria-label="Навигация"><a href="news/index.html">Ленты</a><a href="digests/index.html">Дайджесты</a><a href="today.html">Сегодня</a><a href="radar/index.html">Источники</a></nav>
    <p class="eyebrow">{mode_label} · {esc(report.get("date"))}</p>
    <h1>{h1}</h1>
    <p class="lede">{esc(lede)}</p>
  </header>
  <main>
    <section class="panel digest-status"><h2>Сводка выпуска</h2><p>{esc(status_text)}</p></section>
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
