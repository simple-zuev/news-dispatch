#!/usr/bin/env python3
"""Regression checks for reader-facing site status payload."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "build_site_status.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("build_site_status", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_site_status = importlib.util.module_from_spec(spec)
sys.modules["build_site_status"] = build_site_status
spec.loader.exec_module(build_site_status)


def test_payload_has_feed_health_counts() -> None:
    payload = build_site_status.status_payload()
    assert "feed_total" in payload
    assert "feed_ok" in payload
    assert "feed_disabled" in payload
    assert "feed_error" in payload
    assert isinstance(payload["feed_total"], int)
    assert payload["feed_total"] >= payload["feed_ok"]
    assert "ranking_date" in payload
    assert "latest_public_item_at" in payload


def test_block_renders_feed_health_labels() -> None:
    payload = {
        "radar_date": "2026-06-28",
        "generated_at": "2026-06-28T00:00:00Z",
        "signals": 1,
        "streams_with_signals": 1,
        "published_materials": 0,
        "drafts_to_review": 0,
        "media_candidates": 0,
        "feed_total": 4,
        "feed_ok": 3,
        "feed_disabled": 1,
        "feed_error": 0,
    }
    rendered = build_site_status.block(payload)
    assert "Источники OK: 3/4" in rendered
    assert "Отключённые источники: 1" in rendered
    assert "Ошибки источников: 0" in rendered


def main() -> int:
    test_payload_has_feed_health_counts()
    test_block_renders_feed_health_labels()
    print("site status tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
