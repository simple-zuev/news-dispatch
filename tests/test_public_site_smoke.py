#!/usr/bin/env python3
"""Regression tests for deployed public site smoke checks."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_public_site_smoke.py"

sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("validate_public_site_smoke", MODULE_PATH)
assert spec is not None and spec.loader is not None
smoke = importlib.util.module_from_spec(spec)
sys.modules["validate_public_site_smoke"] = smoke
spec.loader.exec_module(smoke)


def test_smoke_blocks_comment_feed_links() -> None:
    page = smoke.FetchedPage(
        page="",
        url="https://example.test/",
        body='<html><body><h1>Последние новости</h1><a href="/feeds/1/comments/default">Открыть источник</a></body></html>',
    )
    issues = smoke.check_page(page)
    assert "forbidden marker visible" in str(issues)
    assert "/comments/default" in str(issues)


def test_smoke_blocks_security_regulatory_fallback() -> None:
    page = smoke.FetchedPage(
        page="",
        url="https://example.test/",
        body="<html><body><h1>Последние новости</h1><h3>Google Security Blog: регуляторика и надзор</h3><a>Открыть источник</a></body></html>",
    )
    issues = smoke.check_page(page)
    assert "Google Security Blog: регуляторика и надзор" in str(issues)


def test_smoke_accepts_normal_reader_page() -> None:
    page = smoke.FetchedPage(
        page="",
        url="https://example.test/",
        body="<html><body><h1>Последние новости</h1><h3>Google описывает постквантовую защиту Android</h3><a>Открыть источник</a></body></html>",
    )
    assert smoke.check_page(page) == []


def test_status_accepts_fresh_build_and_content() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    payload = {
        "generated_at": (reference - timedelta(hours=2)).isoformat(),
        "latest_public_item_at": (reference - timedelta(hours=4)).isoformat(),
    }
    assert smoke.status_issues(
        payload,
        reference=reference,
        max_build_age_hours=9,
        max_content_age_hours=36,
    ) == []


def test_status_blocks_stale_build_and_content() -> None:
    reference = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    payload = {
        "generated_at": (reference - timedelta(hours=10)).isoformat(),
        "latest_public_item_at": (reference - timedelta(hours=40)).isoformat(),
    }
    issues = smoke.status_issues(
        payload,
        reference=reference,
        max_build_age_hours=9,
        max_content_age_hours=36,
    )
    assert "published build is stale" in str(issues)
    assert "published reader content is stale" in str(issues)


def main() -> int:
    test_smoke_blocks_comment_feed_links()
    test_smoke_blocks_security_regulatory_fallback()
    test_smoke_accepts_normal_reader_page()
    test_status_accepts_fresh_build_and_content()
    test_status_blocks_stale_build_and_content()
    print("public site smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
