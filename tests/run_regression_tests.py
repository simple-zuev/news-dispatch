#!/usr/bin/env python3
"""Run repository regression tests without external dependencies."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "tests"
RUNNER = Path(__file__).resolve()


def regression_tests() -> list[Path]:
    return [
        path
        for path in sorted(TEST_DIR.glob("test_*.py"))
        if path.resolve() != RUNNER
    ]


def main() -> int:
    tests = regression_tests()
    if not tests:
        print("No regression tests found.")
        return 1

    for test_path in tests:
        print(f"Running {test_path.relative_to(ROOT)}")
        result = subprocess.run([sys.executable, str(test_path)], cwd=ROOT)
        if result.returncode != 0:
            print(f"Regression test failed: {test_path.relative_to(ROOT)}")
            return result.returncode

    print(f"Regression tests passed: {len(tests)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
