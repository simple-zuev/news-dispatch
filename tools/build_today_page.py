#!/usr/bin/env python3
"""Build Today Radar from the Daily Radar ranking report.

The page is public-safe: it renders source-reported signals as an analytical
radar, not as confirmed facts, forecasts or recommendations.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from build_reader_policy import build_policy_report, item_key
from core import SITE_DIR, VALIDATION_DIR, write_text

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"
POLICY_PATH = VALIDATION_DIR / "reader-policy-latest.json"
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

STOPWORDS = {
    "the", "and", "for", "from", "with", "this", "that", "into", "over", "after", "before", "about", "news", "update", "updates",
    "как", "что", "это", "для", "или", "при", "над", "под", "после", "перед", "новости", "обновление", "сигнал",
}


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


def load_report(path: Path = REPORT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"date": "", "items": [], "fetch_errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(report: dict[str, Any], path: Path = POLICY_PATH) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
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


def stream_slug(item: dict[str, Any]) -> str:
    return str(item.get("routed_stream") or item.get("configured_stream") or "")


def stream_label(slug: object) -> str:
    text = str(slug or "")
    return STREAM_LABELS.get(text, text or "Без потока")


def selected_items(report: dict[str, Any], policy: dict[str, Any] | None = None, limit: int = 18) -> list[dict[str, Any]]:
    items = [item for item in report.get("items", []) if item.get("selected")]
    if not items:
        items = [item for item in report.get("items", []) if item.get("source_rule_status") == "accepted_by_source_rules"]
    if policy is not None:
        allowed = reader_safe_keys(policy)
        items = [item for item in items if item_key(item) in allowed]
    return sorted(items, key=lambda item: numeric(item.get("final_score")), reverse=True)[:limit]


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
    if source_class in {"official", "regulator", "company"}:
        base = "высокий для факта публикации первоисточником"
    elif source_class in {"public_media", "industry_media"}:
        base = "средний для факта публикации в публичном источнике"
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
  <p class="label">{esc(stream)} · {esc(cluster_label)} · score {score(item.get("final_score"))} · relevance {score(item.get("relevance_score"))}</p>
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


def policy_summary(policy: dict[str, Any]) -> str:
    counts = policy.get("counts", {}) if isinstance(policy.get("counts"), dict) else {}
    safe = int(counts.get("reader_safe", 0) or 0)
    review = int(counts.get("review_only", 0) or 0)
    blocked = int(counts.get("blocked", 0) or 0)
    return f"Reader policy gate: reader_safe={safe}, review_only={review}, blocked={blocked}. Today Radar рендерит только reader_safe items."


def render(report: dict[str, Any], policy: dict[str, Any] | None = None) -> str:
    policy = policy or load_policy(report)
    items = selected_items(report, policy=policy)
    clusters = cluster_items(items)
    total = len(report.get("items", []))
    selected = len([item for item in report.get("items", []) if item.get("selected")])
    filtered = len([item for item in report.get("items", []) if item.get("source_rule_status") != "accepted_by_source_rules"])
    errors = len(report.get("fetch_errors", []))

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>News Dispatch — Today Radar</title>
  <meta name="description" content="Ежедневная панель публичных сигналов News Dispatch.">
  <link rel="stylesheet" href="styles/main.css">
</head>
<body>
  <header class="masthead compact">
    <a class="backlink" href="index.html">News Dispatch</a>
    <p class="eyebrow">Today Radar · {esc(report.get("date"))}</p>
    <h1>Today Radar</h1>
    <p class="lede">Панель свежих публичных сигналов, прошедших source-rule отбор и reader policy gate. Это рабочий аналитический радар, а не финальный выпуск, прогноз или рекомендация.</p>
    <p class="hero-actions"><a href="daily-radar-ranking-latest.json">Ranking JSON</a><a href="reader-policy-latest.json">Reader Policy JSON</a><a href="radar/index.html">Live Radar</a><a href="dispatches.html">Архив</a></p>
  </header>
  <main>
    <section class="panel"><h2>Сводка отбора</h2><p>Всего items: {total}. Выбрано ранжированием: {selected}. Reader-safe items: {len(items)}. Кластеров: {len(clusters)}. Отфильтровано source rules: {filtered}. Ошибок источников: {errors}.</p><p>{esc(policy_summary(policy))}</p></section>
    <section class="panel"><h2>Потоки</h2>{stream_summary(items)}</section>
    <section class="panel"><h2>Главные сигналы</h2><p>Карточки ниже сгруппированы в тематические кластеры и показывают первичную аналитическую рамку: тезис, аргумент, следствие/риск, уровень подтверждения, неопределённость и что отслеживать дальше.</p></section>
    <section class="grid latest-grid" aria-label="Today Radar cards">{cards_block(items)}</section>
    <section class="panel boundary"><h2>Граница интерпретации</h2><p>Факт появления материала в источнике не равен подтверждённому изменению рынка, регулирования или инфраструктуры. Это не инвестиционная, юридическая или операционная рекомендация.</p></section>
  </main>
</body>
</html>
"""


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    report = load_report()
    write_text(OUTPUT_PATH, render(report, load_policy(report)))
    print(f"Built {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
