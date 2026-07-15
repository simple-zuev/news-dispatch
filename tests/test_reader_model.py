#!/usr/bin/env python3
"""Regression tests for the public reader item model contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODEL_PATH = TOOLS / "reader_model.py"
TEXT_PATH = TOOLS / "reader_text.py"

sys.path.insert(0, str(TOOLS))

model_spec = importlib.util.spec_from_file_location("reader_model", MODEL_PATH)
assert model_spec is not None and model_spec.loader is not None
reader_model = importlib.util.module_from_spec(model_spec)
sys.modules["reader_model"] = reader_model
model_spec.loader.exec_module(reader_model)

text_spec = importlib.util.spec_from_file_location("reader_text", TEXT_PATH)
assert text_spec is not None and text_spec.loader is not None
reader_text = importlib.util.module_from_spec(text_spec)
sys.modules["reader_text"] = reader_text
text_spec.loader.exec_module(reader_text)


def sample_item() -> dict[str, object]:
    return {
        "item_key": "sample-1",
        "feed_id": "fca-feed",
        "feed_title": "Financial Conduct Authority",
        "configured_stream": "crypto-finance",
        "routed_stream": "crypto-finance",
        "source_class": "regulator",
        "source_type": "official",
        "title": "FCA updates crypto rules",
        "source_original_title": "FCA updates crypto rules",
        "reader_title_ru": "FCA описала новые правила для криптоактивов",
        "reader_excerpt_ru": "Регулятор описал публичные правила и следующий этап консультаций.",
        "url": "https://example.com/fca-crypto-rules",
        "published": "2026-07-02T09:00:00+00:00",
        "selected": True,
        "source_rule_status": "accepted_by_source_rules",
        "final_score": 12.3,
        "relevance_score": 0.91,
    }


def test_public_reader_item_matches_legacy_render_dict() -> None:
    row = sample_item()
    model = reader_model.from_ranking_item(row)
    assert model.to_render_dict() == reader_text.build_public_item(row)
    assert model.summary == model.excerpt
    assert model.why_it_matters
    assert model.published_at == "2026-07-02T09:00:00+00:00"
    assert model.story_key


def test_public_reader_item_exposes_only_public_keys() -> None:
    payload = reader_model.from_ranking_item(sample_item()).to_render_dict()
    assert set(payload) == set(reader_model.PUBLIC_RENDER_KEYS)
    assert not (set(payload) & reader_model.FORBIDDEN_PUBLIC_KEYS)
    assert "source_rule_status" not in payload
    assert "final_score" not in payload
    assert "feed_id" not in payload


def test_public_render_dict_rejects_diagnostic_keys() -> None:
    try:
        reader_model.assert_public_render_dict({"title": "x", "final_score": "1.0"})
    except ValueError as exc:
        assert "forbidden public keys" in str(exc)
    else:
        raise AssertionError("diagnostic field was accepted into public payload")


def test_public_reader_item_preserves_original_title_only_when_distinct() -> None:
    row = sample_item()
    model = reader_model.from_ranking_item(row)
    assert model.title == "FCA описала новые правила для криптоактивов"
    assert model.original_title == "FCA updates crypto rules"

    same_title_row = sample_item()
    same_title_row["source_original_title"] = "FCA описала новые правила для криптоактивов"
    same_title_model = reader_model.from_ranking_item(same_title_row)
    assert same_title_model.original_title == ""


def test_public_excerpt_sanitizes_guarded_diagnostic_words_in_source_copy() -> None:
    row = sample_item()
    row["reader_excerpt_ru"] = ""
    row["source_excerpt"] = "The report reviews crypto coverage and a publication threshold."
    payload = reader_text.build_public_item(row)
    assert payload["excerpt"] == "The report reviews crypto reporting and a publication limit."


def main() -> int:
    test_public_reader_item_matches_legacy_render_dict()
    test_public_reader_item_exposes_only_public_keys()
    test_public_render_dict_rejects_diagnostic_keys()
    test_public_reader_item_preserves_original_title_only_when_distinct()
    test_public_excerpt_sanitizes_guarded_diagnostic_words_in_source_copy()
    print("reader model tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
