#!/usr/bin/env python3
"""Regression checks for the Today Radar page builder."""

from __future__ import annotations

import importlib.util
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


def test_render_includes_required_links_and_boundary() -> None:
    html = build_today_page.render(sample_report())
    assert "daily-radar-ranking-latest.json" in html
    assert "radar/index.html" in html
    assert "dispatches.html" in html
    assert "Автономный дневной дайджест" in html
    assert "Граница интерпретации" in html
    assert "не инвестиционная" in html


def test_autonomous_digest_sections_and_no_human_approval() -> None:
    html = build_today_page.render(sample_report(), auto_report={"date": "2026-06-28", "generated": []})
    for heading in build_today_page.DIGEST_SECTIONS:
        assert heading in html
    assert "Human approval is not required" in html
    assert "Gate: passed" in html
    assert "Automated Gate" in html
    assert "PASS:" in html


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
    assert "Auto-dispatch artifacts использованы как контур проверки, а не как готовый анализ" in html
    assert "draft_only" in html


def test_gate_failure_renders_safe_fallback_without_human_decision() -> None:
    report = sample_report()
    report["items"][0]["source_type"] = ""
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    html = build_today_page.render(report, policy, auto_report={"generated": []})
    assert "Digest withheld by automated gate" in html
    assert "Пользовательское решение не требуется" in html
    assert "Available safe signals" in html
    assert "Gate: withheld" in html


def test_render_includes_analytical_card_structure() -> None:
    html = build_today_page.render(sample_report())
    assert "Central bank updates digital asset rules" in html
    assert "score 1.25" in html
    assert "relevance 0.82" in html
    assert "Тезис:" in html
    assert "Аргумент:" in html
    assert "Следствие/риск:" in html
    assert "Уровень подтверждения:" in html
    assert "Что отслеживать дальше:" in html
    assert "Неопределённость:" in html


def test_render_clusters_similar_signals() -> None:
    items = build_today_page.selected_items(sample_report())
    clusters = build_today_page.cluster_items(items)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2
    html = build_today_page.render(sample_report())
    assert "Кластеров: 1" in html
    assert "cluster 2 item(s)" in html
    assert "Источники в кластере: 2" in html
    assert "Материалы кластера:" in html
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
    assert "операционная рекомендация" in html
    assert "Требуется сверка первоисточника" in html


def test_today_selection_caps_overfed_source_and_keeps_crypto() -> None:
    report = live_balance_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    items, diagnostics = build_today_page.select_today_items(report, policy, limit=6)
    assert any(item["feed_id"] == "fca-news" for item in items)
    assert sum(1 for item in items if item["feed_id"] == "openai-news") <= build_today_page.SOURCE_TODAY_CAPS["openai-news"]
    assert diagnostics["selected_today_by_stream"]["crypto-finance"] == 1
    assert diagnostics["capped_sources"]["openai-news"] > 0


def test_today_diagnostics_are_rendered() -> None:
    report = live_balance_report()
    policy = build_today_page.load_policy(report, path=ROOT / "missing-reader-policy.json")
    html = build_today_page.render(report, policy, auto_report={"generated": []})
    assert "Диагностика отбора" in html
    assert "Source counts by stream" in html
    assert "Selected Today items by stream" in html
    assert "Криптофинансы" in html
    assert "FCA sets systemic stablecoin rules" in html


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
    test_today_diagnostics_are_rendered()
    print("today page tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
