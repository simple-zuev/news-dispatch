#!/usr/bin/env python3
"""Regression checks for the Today Radar page builder."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_today_page.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_today_page", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_today_page = importlib.util.module_from_spec(spec)
sys.modules["build_today_page"] = build_today_page
spec.loader.exec_module(build_today_page)


def sample_report() -> dict:
    return {
        "date": "2026-06-28",
        "fetch_errors": [],
        "items": [
            {
                "selected": True,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "regulator",
                "source_type": "official",
                "configured_stream": "crypto-finance",
                "routed_stream": "crypto-finance",
                "feed_title": "Example Regulator",
                "title": "Central bank updates digital asset rules",
                "url": "https://example.com/item",
                "final_score": 1.25,
                "relevance_score": 0.82,
                "include_hits": ["central bank", "digital asset"],
                "translation_required": True,
            },
            {
                "selected": True,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "public_media",
                "source_type": "media",
                "configured_stream": "crypto-finance",
                "routed_stream": "crypto-finance",
                "feed_title": "Example Media",
                "title": "Digital asset rules updated by central bank",
                "url": "https://example.com/item-2",
                "final_score": 1.10,
                "relevance_score": 0.76,
                "include_hits": ["central bank", "digital asset"],
                "translation_required": True,
            },
            {
                "selected": False,
                "source_rule_status": "rejected_by_exclude_keywords",
                "configured_stream": "finance",
                "title": "Sports item",
                "final_score": 0.0,
                "relevance_score": 0.0,
            },
        ],
    }


def live_balance_report() -> dict:
    items: list[dict[str, object]] = []
    for index in range(8):
        items.append(
            {
                "selected": False,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "official_source",
                "source_type": "Официальный блог / AI lab",
                "configured_stream": "ai",
                "routed_stream": "ai",
                "feed_id": "openai-news",
                "feed_title": "OpenAI News",
                "title": f"OpenAI model update {index}",
                "url": f"https://openai.com/news/{index}",
                "selection_score": 12.0 - index,
                "final_score": 12.0 - index,
                "relevance_score": 0.9,
                "include_hits": ["model"],
                "translation_required": True,
            }
        )
    items.append(
        {
            "selected": False,
            "source_rule_status": "accepted_by_source_rules",
            "source_class": "official_source",
            "source_type": "Официальный источник / регулятор",
            "configured_stream": "crypto-finance",
            "routed_stream": "crypto-finance",
            "feed_id": "fca-news",
            "feed_title": "Financial Conduct Authority",
            "title": "FCA sets systemic stablecoin rules",
            "url": "https://www.fca.org.uk/news/stablecoin-rules",
            "selection_score": 8.0,
            "final_score": 7.2,
            "relevance_score": 0.86,
            "include_hits": ["stablecoin", "crypto"],
            "boost_hits": ["stablecoin"],
            "translation_required": True,
        }
    )
    return {"date": "2026-07-01", "fetch_errors": [], "items": items}


def mixed_accepted_report(count: int = 200) -> dict:
    streams = [
        ("crypto-finance", ["fca-news", "coindesk", "the-block"]),
        ("tech-hardware-software", ["google-security-blog", "github-security-blog", "apple-newsroom-tech"]),
        ("finance", ["sec-market-statistics", "cbr-news", "kommersant-finance"]),
        ("ai", ["openai-news", "google-ai-blog", "anthropic-news"]),
        ("science-discovery", ["nasa-science", "phys-org", "science-daily"]),
        ("dj-audio-creative", ["dj-techtools", "ableton-blog", "create-digital-music"]),
        ("moscow-city", ["m24-moscow-news", "moskvichmag"]),
    ]
    items: list[dict[str, object]] = []
    for index in range(count):
        stream, sources = streams[index % len(streams)]
        feed_id = sources[index % len(sources)]
        items.append(
            {
                "selected": index < 2,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "official_source" if feed_id.endswith("news") or feed_id in {"fca-news", "google-security-blog"} else "public_media",
                "source_type": "public source",
                "configured_stream": stream,
                "routed_stream": stream,
                "feed_id": feed_id,
                "feed_title": feed_id,
                "title": f"{stream} accepted signal {index}",
                "url": f"https://example.com/{stream}/{index}",
                "selection_score": 16.0 - index * 0.01,
                "final_score": 16.0 - index * 0.01,
                "relevance_score": 0.82,
                "include_hits": [stream],
                "translation_required": True,
            }
        )
    return {"date": "2026-07-01", "fetch_errors": [], "items": items}


def forecast_report() -> dict:
    return {
        "date": "2026-07-01",
        "fetch_errors": [],
        "items": [
            {
                "selected": False,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": "specialized_media",
                "source_type": "Криптофинансовое медиа",
                "configured_stream": "crypto-finance",
                "routed_stream": "crypto-finance",
                "feed_id": "coindesk",
                "feed_title": "CoinDesk",
                "title": "Citi slashes 12-month bitcoin, ether targets",
                "url": "https://example.com/citi-crypto-targets",
                "market_signal_type": "third_party_forecast",
                "ranking_adjustments": ["third_party_market_forecast_labeled", "market_forecast_downweighted"],
                "selection_score": 7.0,
                "final_score": 12.0,
                "relevance_score": 0.86,
                "include_hits": ["bitcoin", "ether"],
                "translation_required": True,
            }
        ],
    }


PUBLIC_FORBIDDEN_TERMS = [
    "selected",
    "reader_safe",
    "source_rule_status",
    "validation",
    "draft-only",
    "review-only",
    "generated",
    "ai-generated",
    "prompt",
    "json",
    "score=",
    "ranking score",
    "final_score",
    "selection_score",
    "fetch warnings",
    "internal diagnostics",
    "machine policy",
    "gate",
    "gates",
    "source ok",
    "ai-generated",
    "ии сгенерировал",
    "модель считает",
    "автоматический анализ",
    "машинная проверка",
]


def card_headings(html: str) -> list[str]:
    return re.findall(r"<article class=\"card signal-card\">.*?<h3>(.*?)</h3>", html, flags=re.S)


def visible_text(html: str) -> str:
    without_scripts = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.I | re.S)
    return re.sub(r"<[^>]+>", " ", without_scripts)


def test_render_includes_required_links_and_boundary() -> None:
    html = build_today_page.render(sample_report())
    assert "daily-radar-ranking-latest.json" not in html
    assert "reader-policy-latest.json" not in html
    assert "news/index.html" in html
    assert "digests/index.html" in html
    assert "radar/index.html" in html
    assert "Главное за сегодня" in html
    assert "today-feature" in html
    assert "stream-visual" in html
    assert "Граница интерпретации" in html
    assert "не инвестиционная" in html


def test_autonomous_digest_sections_and_no_human_approval() -> None:
    html = build_today_page.render(sample_report(), auto_report={"date": "2026-06-28", "generated": []})
    for heading in build_today_page.DIGEST_SECTIONS:
        assert heading in html
    assert "Ежедневное ручное решение не требуется" not in html
    assert "Gate:" not in html
    assert "PASS:" not in html
    assert "автоматически" not in html.lower()
    assert "машинная" not in html.lower()


def test_auto_dispatch_artifacts_are_not_finished_analysis() -> None:
    html = build_today_page.render(
        sample_report(),
        auto_report={
            "date": "2026-06-28",
            "generated": [
                {
                    "stream": "crypto-finance",
                    "path": "validation/auto-dispatches/crypto-finance/2026-06-28-auto-radar-draft.md",
                    "publication_mode": "draft_only",
                    "status": "draft",
                }
            ],
        },
    )
    assert "Подготовительные материалы использованы только как внутренний контур сверки" in html
    assert "draft_only" not in html


def test_gate_failure_renders_safe_fallback_without_human_decision() -> None:
    report = sample_report()
    report["items"][0]["source_type"] = ""
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    html = build_today_page.render(report, policy, auto_report={"generated": []})
    assert "Сегодняшний дайджест не показан полностью" in html
    assert "Ниже оставлены только осторожные публичные материалы" in html
    assert "Доступные публичные сигналы" in html
    assert "Gate:" not in html
    assert "gate-fallback" not in html


def test_render_includes_analytical_card_structure() -> None:
    html = build_today_page.render(sample_report())
    headings = card_headings(html)
    assert headings
    assert not any("Central bank updates digital asset rules" in heading for heading in headings)
    assert any("Источник сообщает:" in heading for heading in headings)
    assert "оригинал: <a href=\"https://example.com/item\">Central bank updates digital asset rules</a>" in html
    assert "score 1.25" not in html
    assert "relevance 0.82" not in html
    assert "Тезис:" in html
    assert "Почему важно:" in html
    assert "Уровень подтверждения:" in html
    assert "Что отслеживать дальше:" in html
    assert "Ссылка на источник:" in html
    assert "Ограничение:" in html


def test_render_clusters_similar_signals() -> None:
    items = build_today_page.selected_items(sample_report())
    clusters = build_today_page.cluster_items(items)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2
    html = build_today_page.render(sample_report())
    assert "1 тематических групп" in html
    assert "2 источник(ов)" in html
    assert "Оригинал:" in html
    assert "cluster-materials" in html
    assert "Example Regulator" in html
    assert "Example Media" in html
    assert "https://example.com/item" in html
    assert "https://example.com/item-2" in html



def test_today_radar_css_has_cluster_materials_styles() -> None:
    css = (ROOT / "site" / "styles" / "main.css").read_text(encoding="utf-8")
    assert "/* Today Radar analytical cards */" in css
    assert ".cluster-materials" in css
    assert ".latest-grid:has(.signal-card)" in css


def test_card_stays_non_directive() -> None:
    html = build_today_page.render(sample_report())
    assert "не прогнозом и не инструкцией к действию" in html
    assert "инвестиционная, юридическая или операционная рекомендация" in html
    assert "Требуется сверка первоисточника" in html


def test_today_selection_caps_overfed_source_and_keeps_crypto() -> None:
    report = live_balance_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    items, diagnostics = build_today_page.select_today_items(report, policy, limit=6)
    assert any(item["feed_id"] == "fca-news" for item in items)
    assert sum(1 for item in items if item["feed_id"] == "openai-news") <= build_today_page.SOURCE_TODAY_CAPS["openai-news"]
    assert diagnostics["selected_today_by_stream"]["crypto-finance"] == 1
    assert diagnostics["capped_sources"]["openai-news"] > 0


def test_today_selection_uses_safe_mixed_report_instead_of_only_preselected_flags() -> None:
    report = mixed_accepted_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    items, diagnostics = build_today_page.select_today_items(report, policy, limit=18)

    assert len(items) >= 10
    assert len(items) == 18
    assert len(diagnostics["selected_today_by_stream"]) >= 4
    assert diagnostics["selected_today_by_stream"]["crypto-finance"] >= 1
    assert diagnostics["selected_today_by_stream"]["tech-hardware-software"] >= 1
    assert sum(1 for item in items if item.get("feed_id") == "google-security-blog") <= build_today_page.SOURCE_TODAY_CAPS["google-security-blog"]


def test_today_selection_prefers_crypto_regulatory_items_over_forecast_and_roundup() -> None:
    report = {
        "date": "2026-07-01",
        "fetch_errors": [],
        "items": [
            {
                "selected": False,
                "source_rule_status": "accepted_by_source_rules",
                "source_class": source_class,
                "source_type": "public source",
                "configured_stream": "crypto-finance",
                "routed_stream": "crypto-finance",
                "feed_id": feed_id,
                "feed_title": feed_id,
                "title": title,
                "url": f"https://example.com/crypto/{index}",
                "selection_score": score,
                "final_score": score,
                "relevance_score": 0.86,
                "include_hits": ["crypto"],
                "translation_required": True,
                **extra,
            }
            for index, (feed_id, title, score, source_class, extra) in enumerate(
                [
                    ("coindesk", "Europe is rewriting its landmark crypto rulebook MiCA as hard deadline passes", 16.2, "specialized_media", {}),
                    ("coindesk", "Citi slashes 12-month bitcoin, ether targets as ETF flows dry up", 15.96, "specialized_media", {"market_signal_type": "third_party_forecast"}),
                    ("cointelegraph", "Here’s what happened in crypto today", 15.8, "specialized_media", {}),
                    ("esma-news", "ESAs publish first report on DORA major ICT-related incidents", 15.59, "official_source", {}),
                    ("fca-news", "FCA and the Bank of England set out approach to joint regulation of systemic stablecoin issuers", 15.49, "official_source", {}),
                    ("crypto-finance-sec-press-releases", "SEC Publishes Updated Market Statistics, Highlighting Increase in IPOs and Proceeds Raised", 15.4, "official_source", {}),
                    ("cointelegraph", "French banking giant Crédit Agricole launches EURXT euro stablecoin", 15.26, "specialized_media", {}),
                    ("cointelegraph", "Taiwan’s legislature passes crypto, stablecoin regulations", 15.17, "specialized_media", {}),
                ]
            )
        ],
    }
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    items, _diagnostics = build_today_page.select_today_items(report, policy, limit=4)
    titles = [str(item["title"]) for item in items]

    assert any("MiCA" in title for title in titles)
    assert any("FCA and the Bank of England" in title for title in titles)
    assert any("SEC Publishes Updated Market Statistics" in title for title in titles)
    assert not any("Citi slashes" in title for title in titles)
    assert not any("Here’s what happened" in title for title in titles)


def test_today_diagnostics_remain_internal_not_public() -> None:
    report = live_balance_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    _items, diagnostics = build_today_page.select_today_items(report, policy, limit=6)
    assert diagnostics["source_counts_by_stream"]
    assert diagnostics["selected_today_by_stream"]
    html = build_today_page.render(report, policy, auto_report={"generated": []})
    assert "Диагностика отбора" not in html
    assert "Source counts by stream" not in html
    assert "Selected Today items by stream" not in html
    assert "Криптофинансы" in html
    headings = card_headings(html)
    assert headings
    assert not any("FCA sets systemic stablecoin rules" in heading for heading in headings)


def test_forecast_flavored_crypto_card_is_not_presented_as_future_fact() -> None:
    report = forecast_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    html = build_today_page.render(report, policy, auto_report={"generated": []})
    assert "Citi slashes 12-month bitcoin, ether targets" in html
    assert "Источник сообщает об оценке участника рынка" in html
    assert "Это не факт будущей цены и не рекомендация" in html
    assert "не являются инвестиционной рекомендацией" in html


def test_public_today_html_contains_no_debug_terms() -> None:
    html = build_today_page.render(sample_report(), auto_report={"generated": []})
    text = visible_text(html).lower()
    for term in PUBLIC_FORBIDDEN_TERMS:
        assert term not in text


def test_public_today_uses_required_stream_labels() -> None:
    expected = {
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
    for slug, title in expected.items():
        assert build_today_page.stream_label(slug) == title


def test_public_today_has_russian_reader_labels() -> None:
    html = build_today_page.render(sample_report(), auto_report={"generated": []})
    for text in ["Главное за сегодня", "Источник", "Тезис", "Почему важно", "Что отслеживать дальше", "Ссылка на источник"]:
        assert text in html


def main() -> int:
    test_render_includes_required_links_and_boundary()
    test_autonomous_digest_sections_and_no_human_approval()
    test_auto_dispatch_artifacts_are_not_finished_analysis()
    test_gate_failure_renders_safe_fallback_without_human_decision()
    test_render_includes_analytical_card_structure()
    test_render_clusters_similar_signals()
    test_today_radar_css_has_cluster_materials_styles()
    test_card_stays_non_directive()
    test_today_selection_caps_overfed_source_and_keeps_crypto()
    test_today_selection_uses_safe_mixed_report_instead_of_only_preselected_flags()
    test_today_selection_prefers_crypto_regulatory_items_over_forecast_and_roundup()
    test_today_diagnostics_remain_internal_not_public()
    test_forecast_flavored_crypto_card_is_not_presented_as_future_fact()
    test_public_today_html_contains_no_debug_terms()
    test_public_today_uses_required_stream_labels()
    test_public_today_has_russian_reader_labels()
    print("today page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
