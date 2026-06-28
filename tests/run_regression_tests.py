#!/usr/bin/env python3
"""Run repository regression tests without external dependencies."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    ROOT / "tests" / "test_filter_daily_signals.py",
    ROOT / "tests" / "test_daily_radar_semantic_routing.py",
]


def main() -> int:
    for test_path in TESTS:
        result = subprocess.run([sys.executable, str(test_path)], cwd=ROOT)
        if result.returncode != 0:
            print(f"Regression test failed: {test_path.relative_to(ROOT)}")
            return result.returncode
    print("Regression tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
