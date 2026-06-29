#!/usr/bin/env python3
"""Regression tests for automatic dispatch draft workspace boundaries."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
MODULE_PATH = TOOLS_DIR / "build_auto_dispatches.py"

sys.path.insert(0, str(TOOLS_DIR))
spec = importlib.util.spec_from_file_location("build_auto_dispatches", MODULE_PATH)
assert spec is not None and spec.loader is not None
build_auto_dispatches = importlib.util.module_from_spec(spec)
sys.modules["build_auto_dispatches"] = build_auto_dispatches
spec.loader.exec_module(build_auto_dispatches)


def test_auto_dispatch_output_stays_outside_dispatches() -> None:
    path = build_auto_dispatches.output_path("crypto-finance", "2026-06-29")
    relative = path.relative_to(ROOT).as_posix()
    assert relative == "validation/auto-dispatches/crypto-finance/2026-06-29-auto-radar-draft.md"
    assert not relative.startswith("dispatches/")


def test_auto_dispatch_report_stays_in_validation() -> None:
    relative = build_auto_dispatches.REPORT_PATH.relative_to(ROOT).as_posix()
    assert relative == "validation/auto-dispatch-latest.json"


def main() -> int:
    test_auto_dispatch_output_stays_outside_dispatches()
    test_auto_dispatch_report_stays_in_validation()
    print("build_auto_dispatches regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
