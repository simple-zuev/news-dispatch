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


def test_public_hashcat_password_cracking_topic_is_allowed() -> None:
    title = '"title": "Security engineer ports password cracker hashcat to Gameboy Advance"'
    blockers, warnings = scan_text(title + "\n")
    assert blockers == []
    assert warnings == []


def test_public_hashcat_password_cracking_url_is_allowed() -> None:
    url = "https://example.test/security-engineer-ports-password-cracker-hashcat"
    blockers, warnings = scan_text(f'"url": "{url}"\n')
    assert blockers == []
    assert warnings == []


def test_public_hashcat_signal_path_is_allowed() -> None:
    path = "signals/2026-07-19/tech-hardware-software/item-password-cracker-hashcat.md"
    blockers, warnings = scan_text(f"- Signal path: `{path}`\n")
    assert blockers == []
    assert warnings == []


def test_password_assignment_with_hashcat_context_is_still_blocked() -> None:
    blockers, _warnings = scan_text('password: "hashcat password cracking demo"\n')
    assert any("possible_secret_keyword" in item for item in blockers)


def test_public_security_title_with_cookies_and_credentials_is_allowed() -> None:
    title = '"title": "Protecting Cookies with Device Bound Session Credentials"'
    blockers, warnings = scan_text(title + "\n")
    assert blockers == []
    assert warnings == []


def test_public_security_source_original_title_is_allowed() -> None:
    title = '"source_original_title": "Protecting Cookies with Device Bound Session Credentials"'
    blockers, warnings = scan_text(title + "\n")
    assert blockers == []
    assert warnings == []


def test_public_security_news_original_metadata_is_allowed() -> None:
    line = '<p class="news-original"><strong>Оригинал:</strong> Protecting Cookies with Device Bound Session Credentials</p>'
    blockers, warnings = scan_text(line + "\n")
    assert blockers == []
    assert warnings == []


def test_cookie_secret_value_is_still_blocked() -> None:
    blockers, _warnings = scan_text('cookie: "sessionid=should-not-ship"\n')
    assert any("possible_secret_keyword" in item for item in blockers)


def test_public_security_report_context_is_allowed() -> None:
    line = "The matched title was `Protecting Cookies with Device Bound Session Credentials`.\n"
    blockers, warnings = scan_text(line)
    assert blockers == []
    assert warnings == []


def test_generated_item_key_hash_is_not_phone_like() -> None:
    blockers, warnings = scan_text('"item_key": "dc83334887059a31",\n')
    assert blockers == []
    assert warnings == []


def main() -> int:
    test_phone_like_ignores_url_digit_fragments()
    test_phone_like_still_blocks_visible_phone()
    test_public_private_keys_security_coverage_is_allowed()
    test_public_private_keys_url_is_allowed()
    test_private_key_assignment_is_still_blocked()
    test_public_hashcat_password_cracking_topic_is_allowed()
    test_public_hashcat_password_cracking_url_is_allowed()
    test_public_hashcat_signal_path_is_allowed()
    test_password_assignment_with_hashcat_context_is_still_blocked()
    test_public_security_title_with_cookies_and_credentials_is_allowed()
    test_public_security_source_original_title_is_allowed()
    test_public_security_news_original_metadata_is_allowed()
    test_cookie_secret_value_is_still_blocked()
    test_public_security_report_context_is_allowed()
    test_generated_item_key_hash_is_not_phone_like()
    print("privacy scan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
