#!/usr/bin/env python3
"""Regression checks for reader policy artifact workflow contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
BUILD_SITE = ROOT / "tools" / "build_site.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_ordered(text: str, markers: list[str]) -> None:
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions), markers


def test_build_site_keeps_policy_after_ranking_before_today() -> None:
    text = read(BUILD_SITE)
    build_body = text[text.index("def build(args") :]
    assert_ordered(
        build_body,
        [
            "build_ranking(args)",
            "build_reader_policy()",
            'run_tool("build_today_page.py")',
        ],
    )
    assert "copy_to_site(READER_POLICY_REPORT)" in text
    assert "copy_to_site(RANKING_REPORT)" in text


def test_validate_uses_deterministic_site_orchestrator() -> None:
    text = read(VALIDATE_WORKFLOW)
    assert "run: python tools/build_site.py --ranking-mode fixture --media-mode skip" in text
    assert "path: validation/reader-policy-latest.json" in text
    assert "path: validation/daily-radar-ranking-latest.json" in text


def test_pages_uses_live_site_orchestrator() -> None:
    text = read(PAGES_WORKFLOW)
    assert "run: python tools/build_site.py --ranking-mode live --media-mode live" in text
    assert "path: site/" in text


def main() -> int:
    test_build_site_keeps_policy_after_ranking_before_today()
    test_validate_uses_deterministic_site_orchestrator()
    test_pages_uses_live_site_orchestrator()
    print("reader policy workflow tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
