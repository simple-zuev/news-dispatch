#!/usr/bin/env python3
"""Regression checks for newly promoted source filters."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_daily_radar_ranking_report.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_daily_radar_ranking_report", MODULE_PATH)
assert spec is not None and spec.loader is not None
ranking = importlib.util.module_from_spec(spec)
sys.modules["build_daily_radar_ranking_report"] = ranking
spec.loader.exec_module(ranking)


def feeds_by_id() -> dict[str, object]:
    feeds, _ = ranking.daily_radar.load_config(ROOT / "sources" / "feeds.json")
    return {feed.id: feed for feed in feeds}


def status(feed: object, title: str) -> str:
    evidence = ranking.source_rule_evidence(feed, title, "")
    return str(evidence["source_rule_status"])


def test_mskagency_transport_keeps_city_mobility_and_rejects_regional_noise() -> None:
    feed = feeds_by_id()["mskagency-transport"]
    assert status(feed, "Новую схему движения ввели у станции метро Текстильщики") == "accepted_by_source_rules"
    assert status(feed, "Хищение топлива из автобусов пресечено в Чехове") == "rejected_by_exclude_keywords"
    assert status(feed, "Аэропорт Внуково принимает и отправляет рейсы по согласованию") == "rejected_by_exclude_keywords"
    assert status(feed, "Ограничения на прием и выпуск самолетов сняты во Внуково") == "rejected_by_exclude_keywords"
    assert status(feed, "Проверят вагоны после задымления на крыше трамвая") == "rejected_by_exclude_keywords"
    assert status(feed, "Дополнительный поезд Ижевск – Москва назначен с 30 июля") == "rejected_by_exclude_keywords"
    assert status(feed, "Покрытие 75 региональных дорог в Подмосковье отремонтировано") == "rejected_by_exclude_keywords"
    assert status(feed, "Два пассажира госпитализированы после опасного маневра авто") == "rejected_by_exclude_keywords"
    assert status(feed, "Движение затруднено на Киевском шоссе из-за аварии") == "rejected_by_exclude_keywords"
    assert status(feed, "Электропоезда получили название Скворец") == "rejected_by_exclude_keywords"
    assert status(feed, "Посвященную Дню шахмат карту Тройка выпустили в Москве") == "rejected_by_exclude_keywords"
    assert status(feed, "Поездки в автобусах Мострансато выросли на 4%") == "rejected_by_exclude_keywords"
    assert ranking.SOURCE_ROW_CAPS["mskagency-transport"] <= 16


def test_govorit_moskva_keeps_city_services_and_rejects_incident_noise() -> None:
    feed = feeds_by_id()["govorit-moskva-city"]
    assert status(feed, "Более 60 тысяч москвичей прошли Московский чекап") == "accepted_by_source_rules"
    assert status(feed, "В Подмосковье при падении лифта пострадали люди") == "rejected_by_exclude_keywords"


def test_gearjunkie_keeps_edc_reviews_and_rejects_outdoor_roundups() -> None:
    feed = feeds_by_id()["gearjunkie-edc"]
    assert status(feed, "Field Review: A Compact EDC Knife for Everyday Carry") == "accepted_by_source_rules"
    assert status(feed, "The Best Hiking Deals for Summer") == "rejected_by_exclude_keywords"


def test_second_wave_official_sources_keep_policy_and_reject_housekeeping() -> None:
    feeds = feeds_by_id()
    assert status(feeds["bank-canada-news"], "Bank of Canada maintains the policy rate at 2.25%") == "accepted_by_source_rules"
    assert status(feeds["bank-canada-news"], "Media advisory for an upcoming museum webcast") == "rejected_by_exclude_keywords"
    assert status(feeds["cftc-general"], "CFTC approves final rule amending margin requirements for uncleared swaps") == "accepted_by_source_rules"
    assert status(feeds["cftc-general"], "CFTC advisory committee to meet in Washington") == "rejected_by_exclude_keywords"
    assert status(feeds["cftc-enforcement-crypto"], "CFTC resolves digital asset action against Celsius founder") == "accepted_by_source_rules"
    assert status(feeds["cftc-enforcement-crypto"], "CFTC charges a livestock commodity pool operator") != "accepted_by_source_rules"


def test_second_wave_editorial_sources_keep_substance_and_reject_promotions() -> None:
    feeds = feeds_by_id()
    assert status(feeds["huggingface-blog"], "Security incident disclosure for open source model hosting") == "accepted_by_source_rules"
    assert status(feeds["huggingface-blog"], "Community event and hiring update") == "rejected_by_exclude_keywords"
    assert status(feeds["nature-news"], "Replication study helps science self-correct") == "accepted_by_source_rules"
    assert status(feeds["nature-news"], "Nature careers podcast and book review") == "rejected_by_exclude_keywords"
    assert status(feeds["synth-anatomy"], "Novation Launchkey MIDI keyboard controller gets an 88-key version") == "accepted_by_source_rules"
    assert status(feeds["synth-anatomy"], "Summer sale discount and free download giveaway") == "rejected_by_exclude_keywords"


def test_mskagency_sections_share_one_publisher_cap() -> None:
    feeds = feeds_by_id()
    transport = feeds["mskagency-transport"]
    culture = feeds["mskagency-culture"]
    assert transport.publisher_id == culture.publisher_id == "mskagency"
    assert status(culture, "Новые экспозиции в Музее космонавтики откроются до конца июля") == "accepted_by_source_rules"
    assert status(culture, "Тренер футбольного клуба рассказал о задачах на сезон") == "rejected_by_exclude_keywords"


def test_third_wave_sources_keep_useful_design_and_moscow_items() -> None:
    feeds = feeds_by_id()
    core77 = feeds["core77-design"]
    ria_moscow = feeds["ria-moscow-city"]
    big_city = feeds["big-city-moscow"]
    assert status(core77, "Striking Chinese Industrial Design: Aulumu's M10 Powerbank") == "accepted_by_source_rules"
    assert status(core77, "Willem de Haan's Highrise Campsite") == "rejected_by_exclude_keywords"
    assert status(ria_moscow, "Верхний Люблинский пруд на юго-востоке Москвы привели в порядок") == "accepted_by_source_rules"
    assert status(ria_moscow, "На площадке Театрального бульвара выступят звезды балета Большого театра") == "accepted_by_source_rules"
    assert status(ria_moscow, "На ракете Союз-2.1а отправили корабль к МКС") == "rejected_by_exclude_keywords"
    assert status(big_city, "На Саввинской набережной в Москве начался снос исторического корпуса фабрики") == "accepted_by_source_rules"
    assert status(big_city, "Посольство Черногории изменило правила выдачи виз") == "rejected_by_exclude_keywords"


def test_tomshardware_rejects_discount_bundles_but_keeps_product_availability() -> None:
    feed = feeds_by_id()["tomshardware"]
    assert status(
        feed,
        "Get AMD Ryzen 7 7700X3D with RAM and a motherboard for $450 — save 31% on this bundle",
    ) == "rejected_by_exclude_keywords"
    assert status(
        feed,
        "AMD Ryzen 7 7700X3D is exclusive to Newegg in North America until Q4",
    ) == "accepted_by_source_rules"


def test_fourth_wave_sources_keep_substance_and_reject_noise() -> None:
    feeds = feeds_by_id()
    field_mag = feeds["field-mag-gear"]
    quanta = feeds["quanta-magazine"]
    science_news = feeds["science-news"]
    assert status(field_mag, "The Best Ultralight Tents, Tested and Reviewed") == "accepted_by_source_rules"
    assert status(field_mag, "The Ultimate Travel Guide to a Mountain Resort Hotel") == "rejected_by_exclude_keywords"
    assert status(quanta, "Researchers Reveal the Power of Quantum Proofs") == "accepted_by_source_rules"
    assert status(quanta, "Subscribe to the Quanta podcast newsletter") == "rejected_by_exclude_keywords"
    assert status(science_news, "Genes offer new clues to stopping Huntington's disease") == "accepted_by_source_rules"
    assert status(science_news, "Math puzzle: a sequence of odd events") == "rejected_by_exclude_keywords"


def test_fifth_wave_sources_keep_practical_and_city_signals() -> None:
    feeds = feeds_by_id()
    cointelegraph = feeds["cointelegraph"]
    the_block = feeds["the-block"]
    sec = feeds["crypto-finance-sec-press-releases"]
    eba = feeds["eba-news"]
    esma = feeds["esma-news"]
    fca = feeds["fca-news"]
    gadgeteer = feeds["gadgeteer-edc"]
    synthtopia = feeds["synthtopia"]
    m24 = feeds["m24-moscow-news"]
    moskvich = feeds["moskvichmag"]
    attack = feeds["attack-magazine"]
    assert status(cointelegraph, "Here’s what happened in crypto today") == "rejected_by_exclude_keywords"
    assert status(the_block, "London Stock Exchange plans overnight venue to extend trading hours") == "rejected_below_min_relevance"
    assert status(the_block, "Crypto exchange receives a new digital asset custody licence") == "accepted_by_source_rules"
    assert status(sec, "SEC rescinds policy regarding denials of settlements in enforcement actions") == "rejected_below_min_relevance"
    assert status(sec, "SEC proposes custody rules for crypto assets and spot bitcoin funds") == "accepted_by_source_rules"
    assert status(eba, "EBA publishes annual prudential banking assessment") == "rejected_below_min_relevance"
    assert status(eba, "EBA publishes MiCA rules for asset-referenced tokens") == "accepted_by_source_rules"
    assert status(esma, "ESMA reports DORA trading and settlement incidents") == "rejected_below_min_relevance"
    assert status(esma, "ESMA updates MiCA guidance for crypto assets") == "accepted_by_source_rules"
    assert status(fca, "FCA sets landmark crypto rules for digital asset firms") == "accepted_by_source_rules"
    assert status(fca, "FCA reviews the impact of AI on retail financial services") == "rejected_below_min_relevance"
    assert status(gadgeteer, "RODMAN Shark Blade Ti uses Damascus steel and titanium on an EDC keychain") == "accepted_by_source_rules"
    assert status(gadgeteer, "Five laptop backpack deals worth buying") == "rejected_by_exclude_keywords"
    assert status(gadgeteer, "Casio brings G-SHOCK to a Roblox virtual world") == "rejected_by_exclude_keywords"
    assert status(synthtopia, "Korg introduces NTS-4 performance mixer for compact hardware setups") == "accepted_by_source_rules"
    assert status(synthtopia, "Free Music Friday: a new ambient album") == "rejected_by_exclude_keywords"
    assert status(moskvich, "Дом недели: доходный дом Орловых на Арбате") == "accepted_by_source_rules"
    assert status(moskvich, "ФСБ задержала подозреваемых за поджог релейных шкафов") == "rejected_by_exclude_keywords"
    assert status(moskvich, "Мойщики окон призвали офисных сотрудников в Москве идти на обед") == "rejected_by_exclude_keywords"
    assert status(moskvich, "Мэрия признала эксперимент с именными билетами в театры") == "rejected_by_exclude_keywords"
    assert status(moskvich, "Это мой город: актер и директор музея МХАТ") == "rejected_by_exclude_keywords"
    assert status(m24, "Аэропорт Внуково перешел на обслуживание рейсов по согласованию") == "rejected_by_exclude_keywords"
    assert status(attack, "AlphaTheta releases CDJ-1500X with cloud DJing") == "accepted_by_source_rules"
    assert status(attack, "Amsterdam Dance Event announced the first wave of festival artists") == "rejected_by_exclude_keywords"


def test_sixth_wave_sources_keep_research_policy_objects_and_city_services() -> None:
    feeds = feeds_by_id()
    google_research = feeds["google-research-blog"]
    bank_england = feeds["bank-england-news"]
    yanko = feeds["yanko-practical-design"]
    coolhunting = feeds["coolhunting-objects"]
    vm = feeds["vm-moscow-infrastructure"]
    assert status(google_research, "Thinking to recall: reasoning unlocks parametric knowledge in LLMs") == "accepted_by_source_rules"
    assert status(google_research, "How we can reduce traffic congestion") == "rejected_by_exclude_keywords"
    assert status(bank_england, "Bank Rate maintained in the Monetary Policy Summary") == "accepted_by_source_rules"
    assert status(bank_england, "Bank of England appoints a new Chief Cashier") == "rejected_by_exclude_keywords"
    assert status(yanko, "This foldable chair uses repairable modular materials") == "accepted_by_source_rules"
    assert status(yanko, "A pocket e-reader gets a brighter screen") == "rejected_by_exclude_keywords"
    assert status(coolhunting, "A crafted bike helmet explores new materials") == "accepted_by_source_rules"
    assert status(coolhunting, "Original motion picture soundtrack") == "rejected_by_exclude_keywords"
    assert status(coolhunting, "Crafted in Greece at Four Seasons Astir Palace Athens") == "rejected_by_exclude_keywords"
    assert status(vm, "В Москве возобновили горячее водоснабжение в 51 тысяче зданий") == "accepted_by_source_rules"
    assert status(vm, "13-летняя девочка пропала в Серпухове") == "rejected_by_exclude_keywords"


def main() -> int:
    test_mskagency_transport_keeps_city_mobility_and_rejects_regional_noise()
    test_govorit_moskva_keeps_city_services_and_rejects_incident_noise()
    test_gearjunkie_keeps_edc_reviews_and_rejects_outdoor_roundups()
    test_second_wave_official_sources_keep_policy_and_reject_housekeeping()
    test_second_wave_editorial_sources_keep_substance_and_reject_promotions()
    test_mskagency_sections_share_one_publisher_cap()
    test_third_wave_sources_keep_useful_design_and_moscow_items()
    test_tomshardware_rejects_discount_bundles_but_keeps_product_availability()
    test_fourth_wave_sources_keep_substance_and_reject_noise()
    test_fifth_wave_sources_keep_practical_and_city_signals()
    test_sixth_wave_sources_keep_research_policy_objects_and_city_services()
    print("source expansion quality tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
