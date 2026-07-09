#!/usr/bin/env python3
"""Regression tests for filtering non-article public source rows."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "filter_public_source_items.py"

sys.path.insert(0, str(ROOT / "tools"))

spec = importlib.util.spec_from_file_location("filter_public_source_items", MODULE_PATH)
assert spec is not None and spec.loader is not None
filter_public_source_items = importlib.util.module_from_spec(spec)
sys.modules["filter_public_source_items"] = filter_public_source_items
spec.loader.exec_module(filter_public_source_items)


def test_comment_feed_rows_are_removed_and_selection_count_recalculated() -> None:
    report = {
        "items": [
            {
                "item_key": "comment-feed",
                "url": "https://security.googleblog.com/feeds/123/comments/default",
                "source_original_url": "https://security.googleblog.com/feeds/123/comments/default",
                "selected": True,
            },
            {
                "item_key": "article",
                "url": "https://security.googleblog.com/2026/07/security-update.html",
                "selected": True,
            },
        ],
        "selected_keys_count": 2,
    }

    removed = filter_public_source_items.filter_report(report)

    assert removed == 1
    assert [item["item_key"] for item in report["items"]] == ["article"]
    assert report["selected_keys_count"] == 1
    assert report["public_source_filter"]["removed_comment_feed_items"] == 1


def test_regular_article_urls_are_not_removed() -> None:
    item = {"url": "https://security.googleblog.com/2026/07/security-update.html"}
    assert not filter_public_source_items.should_remove(item)


def test_main_updates_validation_and_site_report_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        validation = root / "validation" / "daily-radar-ranking-latest.json"
        site = root / "site" / "daily-radar-ranking-latest.json"
        payload = {
            "items": [
                {"item_key": "bad", "url": "https://example.com/feeds/comments/default", "selected": True},
                {"item_key": "good", "url": "https://example.com/article", "selected": False},
            ],
            "selected_keys_count": 1,
        }
        validation.parent.mkdir(parents=True)
        site.parent.mkdir(parents=True)
        validation.write_text(json.dumps(payload), encoding="utf-8")
        site.write_text(json.dumps(payload), encoding="utf-8")

        old_validation = filter_public_source_items.VALIDATION_PATH
        old_site = filter_public_source_items.SITE_PATH
        try:
            filter_public_source_items.VALIDATION_PATH = validation
            filter_public_source_items.SITE_PATH = site
            assert filter_public_source_items.main() == 0
        finally:
            filter_public_source_items.VALIDATION_PATH = old_validation
            filter_public_source_items.SITE_PATH = old_site

        validation_report = json.loads(validation.read_text(encoding="utf-8"))
        site_report = json.loads(site.read_text(encoding="utf-8"))
        for report in (validation_report, site_report):
            assert [item["item_key"] for item in report["items"]] == ["good"]
            assert report["selected_keys_count"] == 0
            assert report["public_source_filter"]["removed_comment_feed_items"] == 1


def main() -> int:
    test_comment_feed_rows_are_removed_and_selection_count_recalculated()
    test_regular_article_urls_are_not_removed()
    test_main_updates_validation_and_site_report_when_present()
    print("public source filter tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
