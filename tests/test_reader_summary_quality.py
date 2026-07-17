#!/usr/bin/env python3
"""Regression checks for useful Russian reader summaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from reader_text import clean_source_excerpt, has_cyrillic, public_excerpt_ru, public_why_it_matters_ru  # noqa: E402


def item(title: str, excerpt: str, *, stream: str, source: str = "Example Source") -> dict[str, object]:
    return {
        "title": title,
        "source_original_title": title,
        "source_excerpt": excerpt,
        "feed_title": source,
        "feed_id": source.lower().replace(" ", "-"),
        "routed_stream": stream,
        "configured_stream": stream,
        "translation_required": True,
    }


def test_stablecoin_summary_contains_event_and_regulators() -> None:
    row = item(
        "FCA and the Bank of England set out approach to joint regulation of systemic stablecoin issuers",
        "The regulators explain how responsibilities will be split between the authorities.",
        stream="crypto-finance",
        source="Financial Conduct Authority",
    )
    summary = public_excerpt_ru(row, max_len=360)
    assert "FCA и Банк Англии" in summary
    assert "системными эмитентами стейблкоинов" in summary
    assert "обязанности" in summary


def test_bitcoin_wallet_summary_preserves_amount_and_uncertainty() -> None:
    row = item(
        "A bitcoin wallet dormant since the 2017 peak just moved $383 million",
        "The coins went to a fresh address rather than an exchange, so nothing has been sold yet.",
        stream="crypto-finance",
        source="CoinDesk",
    )
    summary = public_excerpt_ru(row, max_len=360)
    assert "$383 млн" in summary
    assert "неактивный с 2017 года" in summary
    assert "не сообщает о продаже" in summary


def test_unknown_english_item_gets_attributed_russian_summary() -> None:
    row = item(
        "Company announces a new platform update",
        "The company published details about availability and product capabilities.",
        stream="tech-hardware-software",
    )
    summary = public_excerpt_ru(row, max_len=360)
    assert has_cyrillic(summary)
    assert "По сообщению Example Source" in summary
    assert "Источник описывает тему" not in summary
    assert "Подробности и формулировки сохранены" not in summary


def test_russian_source_excerpt_is_preserved() -> None:
    row = item(
        "В Москве изменят схему движения",
        "С 20 июля на двух улицах изменится схема движения городского транспорта.",
        stream="moscow-city",
        source="Москва 24",
    )
    assert public_excerpt_ru(row) == "С 20 июля на двух улицах изменится схема движения городского транспорта."


def test_why_it_matters_uses_event_context() -> None:
    row = item(
        "NVIDIA introduces Jetson Thor computers for robotics and edge AI",
        "The platform targets robotics developers.",
        stream="tech-hardware-software",
        source="NVIDIA",
    )
    why = public_why_it_matters_ru(row)
    assert "оборудования" in why
    assert "совместимость" in why


def test_nasa_summary_uses_source_facts_instead_of_generic_topic() -> None:
    row = item(
        "NASA’s Perseverance Rover Reads Record of Ancient Mars Impacts",
        (
            "NASA’s Perseverance Mars rover has uncovered evidence that a 75-meter-thick stack of ancient rock "
            "on the rim of Jezero Crater was built by repeated asteroid impacts and is more than 3.9 billion years old."
        ),
        stream="science-discovery",
        source="NASA",
    )
    summary = public_excerpt_ru(row, max_len=360)
    assert "75 метров" in summary
    assert "3,9 млрд лет" in summary
    assert "опубликованы новые сведения" not in summary


def test_compact_summary_does_not_cut_a_word() -> None:
    summary = clean_source_excerpt(
        "Регулятор опубликовал подробное сообщение об изменении требований к участникам финансового рынка.",
        max_len=58,
    )
    assert summary.endswith("…")
    assert not summary.endswith("требован…")
    assert summary == "Регулятор опубликовал подробное сообщение об изменении…"


def test_audio_product_gets_specific_russian_framing() -> None:
    row = item(
        "Native Instruments SuperStarSaw: a playground for supersaw synth sounds",
        "A new synthesizer for layered supersaw sounds.",
        stream="dj-audio-creative",
        source="SYNTH ANATOMY",
    )
    summary = public_excerpt_ru(row, max_len=360)
    assert "Native Instruments SuperStarSaw" in summary
    assert "функции, совместимость" in summary
    assert "опубликованы новые сведения" not in summary


def test_second_wave_selected_items_get_specific_summaries() -> None:
    bank = item(
        "Bank of Canada maintains the policy rate at 2¼%",
        "The Bank held its target for the overnight rate at 2.25%, the Bank Rate at 2.5% and the deposit rate at 2.20%.",
        stream="finance",
        source="Bank of Canada",
    )
    nature = item(
        "Why do astronauts' bodies waste away? Space Station study points to mitochondria",
        "",
        stream="science-discovery",
        source="Nature",
    )
    watches = item(
        "Organic Second-Hand Horology: The Joys of Uncovering a Used Gem at a Local Shop or Sale",
        "A watch collector describes finding used watches at local shops and community sales.",
        stream="gear-style-edc",
        source="Worn & Wound",
    )
    assert "2,25%" in public_excerpt_ru(bank, max_len=360)
    assert "митохондрий" in public_excerpt_ru(nature, max_len=360)
    assert "подержанных часов" in public_excerpt_ru(watches, max_len=360)
    for row in (bank, nature, watches):
        assert "опубликованы новые сведения" not in public_excerpt_ru(row, max_len=360)


def main() -> int:
    test_stablecoin_summary_contains_event_and_regulators()
    test_bitcoin_wallet_summary_preserves_amount_and_uncertainty()
    test_unknown_english_item_gets_attributed_russian_summary()
    test_russian_source_excerpt_is_preserved()
    test_why_it_matters_uses_event_context()
    test_nasa_summary_uses_source_facts_instead_of_generic_topic()
    test_compact_summary_does_not_cut_a_word()
    test_audio_product_gets_specific_russian_framing()
    test_second_wave_selected_items_get_specific_summaries()
    print("reader summary quality tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
