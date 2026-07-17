#!/usr/bin/env python3
"""Regression tests for bounded operational-history retention."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "prune_operational_history.py"

spec = importlib.util.spec_from_file_location("prune_operational_history", MODULE_PATH)
assert spec is not None and spec.loader is not None
retention = importlib.util.module_from_spec(spec)
sys.modules["prune_operational_history"] = retention
spec.loader.exec_module(retention)


def write(path: Path, text: str = "generated") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture(root: Path) -> tuple[Path, Path, Path]:
    signals = root / "signals"
    auto = root / "validation" / "auto-dispatches"
    dispatches = root / "dispatches"
    write(signals / "2026-06-30" / "ai" / "old.md")
    write(signals / "2026-07-02" / "ai" / "boundary.md")
    write(signals / "2026-07-15" / "ai" / "fresh.md")
    write(signals / "not-a-date" / "keep.md")
    write(auto / "archive" / "ai" / "2026-06-30-auto-radar-draft.md")
    write(auto / "ai" / "2026-07-02-auto-radar-draft.md")
    write(auto / "ai" / "2026-07-15-auto-radar-draft.md")
    write(auto / "ai" / "manual-note.md")
    write(dispatches / "ai" / "2026-06-01-editorial.md", "protected")
    return signals, auto, dispatches


def test_dry_run_reports_without_deleting() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        signals, auto, dispatches = fixture(root)
        report = retention.prune(
            signals_dir=signals,
            auto_dispatch_dir=auto,
            reference=date(2026, 7, 16),
            retention_days=14,
            apply=False,
        )
        assert report["candidate_counts"] == {"signals": 1, "auto_dispatches": 1}
        assert (signals / "2026-06-30").exists()
        assert (auto / "archive" / "ai" / "2026-06-30-auto-radar-draft.md").exists()
        assert (dispatches / "ai" / "2026-06-01-editorial.md").read_text() == "protected"


def test_apply_deletes_only_expired_generated_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        signals, auto, dispatches = fixture(root)
        report = retention.prune(
            signals_dir=signals,
            auto_dispatch_dir=auto,
            reference=date(2026, 7, 16),
            retention_days=14,
            apply=True,
        )
        assert report["deleted_count"] == 2
        assert not (signals / "2026-06-30").exists()
        assert not (auto / "archive" / "ai" / "2026-06-30-auto-radar-draft.md").exists()
        assert (signals / "2026-07-02" / "ai" / "boundary.md").exists()
        assert (signals / "2026-07-15" / "ai" / "fresh.md").exists()
        assert (signals / "not-a-date" / "keep.md").exists()
        assert (auto / "ai" / "2026-07-02-auto-radar-draft.md").exists()
        assert (auto / "ai" / "manual-note.md").exists()
        assert (dispatches / "ai" / "2026-06-01-editorial.md").read_text() == "protected"


def test_non_positive_retention_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        signals, auto, _dispatches = fixture(root)
        try:
            retention.prune(
                signals_dir=signals,
                auto_dispatch_dir=auto,
                reference=date(2026, 7, 16),
                retention_days=0,
                apply=False,
            )
        except ValueError as exc:
            assert "positive" in str(exc)
        else:
            raise AssertionError("zero retention must be rejected")


def test_protected_directory_cannot_be_substituted() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        signals, auto, dispatches = fixture(root)
        try:
            retention.prune(
                signals_dir=dispatches,
                auto_dispatch_dir=auto,
                reference=date(2026, 7, 16),
                retention_days=14,
                apply=True,
            )
        except ValueError as exc:
            assert "named signals" in str(exc)
        else:
            raise AssertionError("dispatches must never be accepted as the signals root")
        assert (dispatches / "ai" / "2026-06-01-editorial.md").read_text() == "protected"
        assert (signals / "2026-06-30" / "ai" / "old.md").exists()


def main() -> int:
    test_dry_run_reports_without_deleting()
    test_apply_deletes_only_expired_generated_artifacts()
    test_non_positive_retention_is_rejected()
    test_protected_directory_cannot_be_substituted()
    print("operational retention tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
