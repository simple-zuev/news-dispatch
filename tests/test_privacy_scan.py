#!/usr/bin/env python3
"""Regression checks for public-safety scanner false positives."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE_PATH = TOOLS / "privacy_scan.py"

sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("privacy_scan", MODULE_PATH)
assert spec is not None and spec.loader is not None
privacy_scan = importlib.util.module_from_spec(spec)
sys.modules["privacy_scan"] = privacy_scan
spec.loader.exec_module(privacy_scan)


def scan_text(text: str) -> tuple[list[str], list[str]]:
    path = ROOT / "validation" / ".tmp-privacy-scan-test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        return privacy_scan.scan_file(path)
    finally:
        path.unlink(missing_ok=True)


def test_phone_like_ignores_url_digit_fragments() -> None:
    url = "https://www.rbc.ru/sport/28/06/2026/6a41522e9a79477751613cda"
    blockers, warnings = scan_text(f'- "{url}"\n')
    assert blockers == []
    assert warnings == []


def test_phone_like_still_blocks_visible_phone() -> None:
    visible_number = "+" + "7" + " " + "999" + " " + "123" + " " + "45" + " " + "67"
    blockers, _warnings = scan_text(f"Contact: {visible_number}\n")
    assert any("phone_like" in item for item in blockers)


def test_public_private_keys_security_coverage_is_allowed() -> None:
    blockers, warnings = scan_text("- Private keys, not smart contracts, caused crypto hack losses.\n")
    assert blockers == []
    assert warnings == []


def test_public_private_keys_url_is_allowed() -> None:
    url = "https://www.coindesk.com/tech/private-keys-not-smart-contracts-caused-hack-losses"
    blockers, warnings = scan_text(f'- "{url}"\n')
    assert blockers == []
    assert warnings == []


def test_private_key_assignment_is_still_blocked() -> None:
    blockers, _warnings = scan_text("private_key: should-not-be-public\n")
    assert any("possible_secret_keyword" in item for item in blockers)


def main() -> int:
    test_phone_like_ignores_url_digit_fragments()
    test_phone_like_still_blocks_visible_phone()
    test_public_private_keys_security_coverage_is_allowed()
    test_public_private_keys_url_is_allowed()
    test_private_key_assignment_is_still_blocked()
    print("privacy scan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
