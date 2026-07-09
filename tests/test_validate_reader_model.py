#!/usr/bin/env python3
"""Regression tests for model-level public reader validation."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_reader_model.py"

sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("validate_reader_model", MODULE_PATH)
assert spec is not None and spec.loader is not None
validate_reader_model = importlib.util.module_from_spec(spec)
sys.modules["validate_reader_model"] = validate_reader_model
spec.loader.exec_module(validate_reader_model)


def safe_item() -> dict[str, object]:
    return {
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


def unresolved_generic_item() -> dict[str, object]:
    item = safe_item()
    item["title"] = ""
    item["source_original_title"] = ""
    item["reader_title_ru"] = "Google Security Blog: регуляторика и надзор"
    return item


def policy_for(item: dict[str, object]) -> dict[str, object]:
    return {"decisions": [{"item_key": validate_reader_model.item_key(item), "decision": "reader_safe"}]}


def test_reader_model_validation_passes_safe_item() -> None:
    item = safe_item()
    report = validate_reader_model.validate({"items": [item]}, policy_for(item))
    assert report["passed"] is True
    assert report["checked_items"] == 1
    assert report["issues"] == []


def test_reader_model_validation_blocks_comment_feed_url() -> None:
    item = safe_item()
    item["url"] = "https://security.googleblog.com/feeds/123/comments/default"
    report = validate_reader_model.validate({"items": [item]}, policy_for(item))
    assert report["passed"] is False
    assert "comment feed URL" in str(report["blocking_issues"])


def test_reader_model_validation_passes_after_generic_title_cleanup() -> None:
    item = unresolved_generic_item()
    report = validate_reader_model.validate({"items": [item]}, policy_for(item), fail_on="critical")
    assert report["passed"] is True
    assert report["issues"] == []
    assert report["blocking_issues"] == []


def test_reader_model_validation_falls_back_to_selected_when_policy_is_absent() -> None:
    item = safe_item()
    report = validate_reader_model.validate({"items": [item]}, {"decisions": []})
    assert report["passed"] is True
    assert report["checked_items"] == 1


def test_reader_model_validator_writes_report_and_returns_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        ranking = tmpdir / "ranking.json"
        policy = tmpdir / "policy.json"
        output = tmpdir / "reader-model.json"
        item = safe_item()
        item["url"] = ""
        ranking.write_text(json.dumps({"items": [item]}), encoding="utf-8")
        policy.write_text(json.dumps(policy_for(item)), encoding="utf-8")

        rc = validate_reader_model.main(["--ranking", str(ranking), "--policy", str(policy), "--output", str(output)])

        assert rc == 1
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["passed"] is False
        assert "url is empty" in str(report["blocking_issues"])


def main() -> int:
    test_reader_model_validation_passes_safe_item()
    test_reader_model_validation_blocks_comment_feed_url()
    test_reader_model_validation_passes_after_generic_title_cleanup()
    test_reader_model_validation_falls_back_to_selected_when_policy_is_absent()
    test_reader_model_validator_writes_report_and_returns_failure()
    print("reader model validator tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
