#!/usr/bin/env python3
"""Regression tests for public reader content quality fail modes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_public_reader_content_quality.py"

sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("validate_public_reader_content_quality", MODULE_PATH)
assert spec is not None and spec.loader is not None
content_quality = importlib.util.module_from_spec(spec)
sys.modules["validate_public_reader_content_quality"] = content_quality
spec.loader.exec_module(content_quality)


def test_advisory_issues_do_not_block_critical_mode() -> None:
    issues = ["weak source-topic headlines: Google Security Blog: регуляторика и надзор"]
    assert content_quality.blocking_issues(issues, fail_on="critical") == []
    assert content_quality.blocking_issues(issues, fail_on="any") == issues


def test_comment_feed_issue_blocks_critical_mode() -> None:
    issues = ["comment feed URL is visible: /comments/default"]
    assert content_quality.blocking_issues(issues, fail_on="critical") == issues


def test_missing_source_action_blocks_critical_mode() -> None:
    issues = ["news rows lack metadata or source action"]
    assert content_quality.blocking_issues(issues, fail_on="critical") == issues


def main() -> int:
    test_advisory_issues_do_not_block_critical_mode()
    test_comment_feed_issue_blocks_critical_mode()
    test_missing_source_action_blocks_critical_mode()
    print("content quality fail mode tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
