#!/usr/bin/env python3
"""Regression tests for the staged Daily Radar change-set guard."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "validate_daily_radar_change_set.py"

spec = importlib.util.spec_from_file_location("validate_daily_radar_change_set", MODULE_PATH)
assert spec is not None and spec.loader is not None
guard = importlib.util.module_from_spec(spec)
sys.modules["validate_daily_radar_change_set"] = guard
spec.loader.exec_module(guard)

REFERENCE = date(2026, 7, 22)
CUTOFF = date(2026, 7, 8)


def validate(changes: list[guard.Change], limits: guard.Limits | None = None) -> dict[str, object]:
    return guard.validate_changes(
        changes,
        reference=REFERENCE,
        cutoff=CUTOFF,
        limits=limits or guard.Limits(),
    )


def test_expected_incremental_change_set_passes() -> None:
    changes = [
        guard.Change("A", "signals/2026-07-22/ai/0123456789abcdef-example.md"),
        guard.Change("D", "signals/2026-07-07/ai/fedcba9876543210-expired.md"),
        guard.Change("M", "data/daily-radar-seen.json"),
        guard.Change("M", "validation/daily-radar-latest.json"),
        guard.Change("A", "validation/auto-dispatches/ai/2026-07-22-auto-radar-draft.md"),
        guard.Change("D", "validation/auto-dispatches/archive/ai/2026-07-07-auto-radar-draft.md"),
    ]
    report = validate(changes)
    assert report["passed"] is True
    assert report["changed_files"] == 6
    assert report["issues"] == []


def test_protected_or_unknown_paths_are_blocked() -> None:
    for path in (
        "dispatches/ai/2026-07-22-auto.md",
        "sources/feeds.json",
        ".github/workflows/daily-radar.yml",
        "data/unexpected-state.json",
        "validation/unexpected-report.json",
    ):
        report = validate([guard.Change("M", path)])
        assert report["passed"] is False, path
        assert any("outside" in issue for issue in report["issues"]), path


def test_fresh_or_boundary_deletions_are_blocked() -> None:
    changes = [
        guard.Change("D", "signals/2026-07-08/ai/0123456789abcdef-boundary.md"),
        guard.Change("D", "validation/auto-dispatches/ai/2026-07-21-auto-radar-draft.md"),
    ]
    report = validate(changes)
    assert report["passed"] is False
    assert len(report["issues"]) == 2


def test_non_current_writes_are_blocked() -> None:
    changes = [
        guard.Change("A", "signals/2026-07-21/ai/0123456789abcdef-old.md"),
        guard.Change("A", "validation/auto-dispatches/archive/ai/2026-07-22-auto-radar-draft.md"),
    ]
    report = validate(changes)
    assert report["passed"] is False
    assert len(report["issues"]) == 2


def test_size_limits_block_runaway_change_sets() -> None:
    changes = [
        guard.Change("A", f"signals/2026-07-22/ai/{index:016x}-item.md")
        for index in range(4)
    ]
    report = validate(
        changes,
        guard.Limits(
            max_changed_files=3,
            max_deleted_files=3,
            max_signal_writes=3,
            max_validation_writes=3,
        ),
    )
    assert report["passed"] is False
    assert any("changed file count" in issue for issue in report["issues"])
    assert any("signal write count" in issue for issue in report["issues"])


def test_state_and_latest_reports_cannot_be_deleted() -> None:
    changes = [
        guard.Change("D", "data/daily-radar-seen.json"),
        guard.Change("D", "validation/source-health-latest.json"),
    ]
    report = validate(changes)
    assert report["passed"] is False
    assert len(report["issues"]) == 2


def test_staged_diff_is_read_from_git_index() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
        path = root / "signals" / "2026-07-22" / "ai" / "0123456789abcdef-example.md"
        path.parent.mkdir(parents=True)
        path.write_text("generated\n", encoding="utf-8")
        subprocess.run(["git", "add", path.relative_to(root).as_posix()], cwd=root, check=True)
        assert guard.staged_changes(root) == [guard.Change("A", path.relative_to(root).as_posix())]


def main() -> int:
    test_expected_incremental_change_set_passes()
    test_protected_or_unknown_paths_are_blocked()
    test_fresh_or_boundary_deletions_are_blocked()
    test_non_current_writes_are_blocked()
    test_size_limits_block_runaway_change_sets()
    test_state_and_latest_reports_cannot_be_deleted()
    test_staged_diff_is_read_from_git_index()
    print("daily radar change-set guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
