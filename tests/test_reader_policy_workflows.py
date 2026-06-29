#!/usr/bin/env python3
"""Regression checks for reader policy artifact workflow contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_ordered(text: str, markers: list[str]) -> None:
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions), markers


def test_validate_builds_policy_after_ranking_before_today() -> None:
    text = read(VALIDATE_WORKFLOW)
    assert_ordered(
        text,
        [
            "Build offline radar ranking fixture",
            "Build reader policy artifact",
            "Build Today Radar page",
        ],
    )
    assert "run: python tools/build_reader_policy.py" in text
    assert "path: validation/reader-policy-latest.json" in text


def test_pages_publishes_policy_next_to_today_and_ranking() -> None:
    text = read(PAGES_WORKFLOW)
    assert_ordered(
        text,
        [
            "Build radar ranking report",
            "Build reader policy artifact",
            "Build Today Radar page",
        ],
    )
    assert "cp validation/daily-radar-ranking-latest.json site/daily-radar-ranking-latest.json" in text
    assert "cp validation/reader-policy-latest.json site/reader-policy-latest.json" in text


def main() -> int:
    test_validate_builds_policy_after_ranking_before_today()
    test_pages_publishes_policy_next_to_today_and_ranking()
    print("reader policy workflow tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
