#!/usr/bin/env python3
"""Run Daily Radar in guarded signal-collection mode.

This wrapper intentionally does not mutate repository source files at runtime.
Signal routing and feed enablement must be explicit in committed configuration.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "tools/daily_radar.py"])
    run([sys.executable, "tools/filter_daily_signals.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
