#!/usr/bin/env python3
"""Regression guard: generated auto-radar drafts must not live in dispatches/."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_auto_radar_drafts_in_dispatches() -> None:
    offenders = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "dispatches").rglob("*auto-radar-draft.md")
    )
    assert offenders == [], "auto-radar drafts must stay outside dispatches/: " + ", ".join(offenders)


def main() -> int:
    test_no_auto_radar_drafts_in_dispatches()
    print("no auto-radar drafts in dispatches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
