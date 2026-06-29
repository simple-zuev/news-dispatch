#!/usr/bin/env python3
"""Regression tests for source governance reporting."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
MODULE_PATH = TOOLS_DIR / "source_governance.py"

sys.path.insert(0, str(TOOLS_DIR))
spec = importlib.util.spec_from_file_location("source_governance", MODULE_PATH)
assert spec is not None and spec.loader is not None
source_governance = importlib.util.module_from_spec(spec)
sys.modules["source_governance"] = source_governance
spec.loader.exec_module(source_governance)


def test_report_has_required_sections() -> None:
    report = source_governance.build_report()
    assert report["status"] == "pre-publication source governance artifact"
    assert report["total_sources"] > 0
    assert report["enabled_sources"] > 0
    assert isinstance(report["streams"], list) and report["streams"]
    assert isinstance(report["feeds"], list) and report["feeds"]
    assert isinstance(report["risk_counts"], dict)
    assert isinstance(report["recommendations"], list)


def test_each_stream_has_coverage_metrics() -> None:
    report = source_governance.build_report()
    for row in report["streams"]:
        assert row["total_sources"] >= row["enabled_sources"]
        assert row["enabled_sources"] >= 0
        assert row["enabled_official_sources"] >= 0
        assert row["enabled_high_trust_sources"] >= row["enabled_official_sources"]
        assert isinstance(row["enabled_class_counts"], dict)


def test_public_media_is_flagged_for_corroboration() -> None:
    report = source_governance.build_report()
    public_media_feeds = [
        row for row in report["feeds"]
        if row["enabled"] and row["source_class"] == "public_media"
    ]
    assert public_media_feeds, "expected at least one enabled public_media feed in current source mix"
    for row in public_media_feeds:
        assert "public_media_needs_corroboration" in row["risk_flags"]


def test_markdown_report_is_pre_publication_artifact() -> None:
    report = source_governance.build_report()
    text = source_governance.render_markdown(report)
    assert "Status: pre-publication source governance artifact." in text
    assert "## Stream coverage" in text
    assert "## Recommendations" in text


def main() -> int:
    test_report_has_required_sections()
    test_each_stream_has_coverage_metrics()
    test_public_media_is_flagged_for_corroboration()
    test_markdown_report_is_pre_publication_artifact()
    print("source governance regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
