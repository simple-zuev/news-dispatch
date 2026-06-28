#!/usr/bin/env python3
"""Regression checks for the Content Intelligence signal contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "content-intelligence-signal.schema.json"

REQUIRED = {
    "id",
    "date",
    "stream",
    "source_title",
    "source_url",
    "source_class",
    "language",
    "original_title",
    "ru_title",
    "ru_summary",
    "claim_type",
    "confirmation_level",
    "relevance_score",
    "impact_score",
    "freshness_score",
    "novelty_score",
    "why_selected",
    "why_it_matters",
    "affected_actors",
    "possible_effects",
    "uncertainties",
    "watch_next",
    "public_safety_notes",
}

SCORE_FIELDS = {"relevance_score", "impact_score", "freshness_score", "novelty_score"}
ENUM_FIELDS = {"stream", "source_class", "claim_type", "confirmation_level"}


def load_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_has_required_reader_fields() -> None:
    schema = load_schema()
    required = set(schema.get("required", []))
    assert REQUIRED <= required
    properties = set(schema.get("properties", {}))
    assert REQUIRED <= properties


def test_scores_are_bounded() -> None:
    properties = load_schema()["properties"]
    assert isinstance(properties, dict)
    for field in SCORE_FIELDS:
        spec = properties[field]
        assert isinstance(spec, dict)
        assert spec.get("minimum") == 0
        assert spec.get("maximum") == 1


def test_core_enums_are_declared() -> None:
    properties = load_schema()["properties"]
    assert isinstance(properties, dict)
    for field in ENUM_FIELDS:
        spec = properties[field]
        assert isinstance(spec, dict)
        values = spec.get("enum", [])
        assert isinstance(values, list)
        assert values


def valid_sample() -> dict[str, object]:
    return {
        "id": "sample-20260628-ai-001",
        "date": "2026-06-28",
        "stream": "ai",
        "source_title": "Official Blog",
        "source_url": "https://example.com/source",
        "source_class": "official_source",
        "language": "en",
        "original_title": "Platform update changes model access",
        "ru_title": "Платформенное обновление меняет доступ к моделям",
        "ru_summary": "Публичный источник сообщил об изменении доступа к моделям; требуется проверить детали и затронутые сценарии.",
        "claim_type": "source_reported_claim",
        "confirmation_level": "source_reported",
        "relevance_score": 0.92,
        "impact_score": 0.74,
        "freshness_score": 0.88,
        "novelty_score": 0.69,
        "why_selected": "Сигнал связан с доступом к AI-платформам и может повлиять на продуктовые сценарии.",
        "why_it_matters": "Изменения платформенного доступа могут затронуть разработчиков, интеграторов и downstream-сервисы.",
        "affected_actors": ["developers", "platform users"],
        "possible_effects": ["изменение доступности функций", "пересмотр интеграционных сценариев"],
        "uncertainties": ["не проверены полные условия изменения", "нет независимого подтверждения"],
        "watch_next": ["official changelog", "developer reaction"],
        "public_safety_notes": ["только публичный источник", "без внутренних данных"],
    }


def validate_sample(sample: dict[str, object], schema: dict[str, object]) -> list[str]:
    errors: list[str] = []
    required = set(schema.get("required", []))
    missing = sorted(required - set(sample))
    if missing:
        errors.append("missing: " + ", ".join(missing))
    properties = schema.get("properties", {})
    assert isinstance(properties, dict)
    for field in SCORE_FIELDS:
        value = sample.get(field)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            errors.append(f"bad score: {field}")
    for field in ENUM_FIELDS:
        spec = properties[field]
        assert isinstance(spec, dict)
        allowed = spec.get("enum", [])
        if sample.get(field) not in allowed:
            errors.append(f"bad enum: {field}")
    return errors


def test_valid_sample_matches_contract() -> None:
    errors = validate_sample(valid_sample(), load_schema())
    assert errors == []


def main() -> int:
    test_schema_has_required_reader_fields()
    test_scores_are_bounded()
    test_core_enums_are_declared()
    test_valid_sample_matches_contract()
    print("content intelligence contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
