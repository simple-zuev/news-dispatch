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


def main() -> int:
    test_mskagency_transport_keeps_city_mobility_and_rejects_regional_noise()
    test_govorit_moskva_keeps_city_services_and_rejects_incident_noise()
    test_gearjunkie_keeps_edc_reviews_and_rejects_outdoor_roundups()
    test_second_wave_official_sources_keep_policy_and_reject_housekeeping()
    test_second_wave_editorial_sources_keep_substance_and_reject_promotions()
    test_mskagency_sections_share_one_publisher_cap()
    print("source expansion quality tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
