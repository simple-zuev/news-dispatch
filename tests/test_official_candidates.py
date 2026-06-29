#!/usr/bin/env python3
"""Regression checks for official candidate registry."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_official_candidates.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("validate_official_candidates", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules["validate_official_candidates"] = module
spec.loader.exec_module(module)


def test_registry_validates() -> None:
    assert module.validate() == []


def test_gap_streams_are_represented() -> None:
    data = module.load_json(module.CANDIDATES_PATH)
    streams = {item["stream"] for item in data["candidates"]}
    assert {"crypto-finance", "moscow-city", "science-discovery", "dj-audio-creative", "gear-style-edc"} <= streams


def test_candidate_lifecycle_consistency() -> None:
    data = module.load_json(module.CANDIDATES_PATH)
    production_ids = module.feed_ids()
    for item in data["candidates"]:
        assert item["promotion_target"] == "sources/feeds.json"
        if item["status"] == "promoted":
            assert item["id"] in production_ids
            assert item["candidate_url_status"] == "verified"
        else:
            assert item["id"] not in production_ids


def main() -> int:
    test_registry_validates()
    test_gap_streams_are_represented()
    test_candidate_lifecycle_consistency()
    print("official candidate tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
