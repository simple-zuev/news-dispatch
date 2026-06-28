#!/usr/bin/env python3
"""Regression checks for zero-touch/autopilot project doctrine."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_readme_declares_autopilot_model() -> None:
    text = read("README.md")
    assert "zero-touch" in text
    assert "autopilot" in text
    assert "policy gates" in text


def test_editorial_workflow_is_not_manual_promotion_model() -> None:
    text = read("docs/editorial-workflow.md")
    assert "manual review is an override/audit path" in text
    assert "routine manual source selection" in text
    assert "promotion decision is manual" not in text
    assert "policy gate" in text


def test_autopilot_architecture_defines_lifecycle() -> None:
    text = read("docs/autopilot-architecture.md")
    for state in ["discovered", "probation", "active", "degraded", "suspended", "rejected"]:
        assert state in text
    assert "human review is not part of the normal operating path" in text


def main() -> int:
    test_readme_declares_autopilot_model()
    test_editorial_workflow_is_not_manual_promotion_model()
    test_autopilot_architecture_defines_lifecycle()
    print("autopilot doctrine tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
