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


def test_safe_signal_path_does_not_hide_visible_phone() -> None:
    path = "signals/2026-07-21/gear-style-edc/ad41f85121645502-photo-report.md"
    visible_number = "+" + "7" + " " + "999" + " " + "123" + " " + "45" + " " + "67"
    blockers, _warnings = scan_text(f"Signal: `{path}`; contact: {visible_number}\n")
    assert any("phone_like" in item for item in blockers)


def test_allowlisted_text_does_not_hide_visible_phone() -> None:
    visible_number = "+" + "7" + " " + "999" + " " + "123" + " " + "45" + " " + "67"
    blockers, _warnings = scan_text(f"example.com contact: {visible_number}\n")
    assert any("phone_like" in item for item in blockers)


def test_allowlisted_text_does_not_hide_secret_assignment() -> None:
    blockers, _warnings = scan_text('api_key: "should-not-ship" # example.com\n')
    assert any("secret_value_assignment" in item for item in blockers)


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
    assert any("secret_value_assignment" in item for item in blockers)


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
    assert any("secret_value_assignment" in item for item in blockers)


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
    assert any("secret_value_assignment" in item for item in blockers)


def test_public_security_report_context_is_allowed() -> None:
    line = "The matched title was `Protecting Cookies with Device Bound Session Credentials`.\n"
    blockers, warnings = scan_text(line)
    assert blockers == []
    assert warnings == []


def test_generated_item_key_hash_is_not_phone_like() -> None:
    blockers, warnings = scan_text('"item_key": "dc83334887059a31",\n')
    assert blockers == []
    assert warnings == []


def test_markdown_signal_path_hash_is_not_phone_like() -> None:
    path = "signals/2026-07-21/gear-style-edc/ad41f85121645502-photo-report-tudor-and-red-bull-take-to-the-skies.md"
    blockers, warnings = scan_text(f"- Signal path: `{path}`\n")
    assert blockers == []
    assert warnings == []


def test_public_security_vocabulary_is_not_a_secret() -> None:
    lines = (
        '"title": "API keys, passwords, OAuth tokens and cookies in browser security"',
        '"source_excerpt": "How bearer credentials and private keys are protected"',
        '<h3>Password managers and secret-key rotation</h3>',
        '- API key: why browser extensions need safer credential storage',
    )
    blockers, warnings = scan_text("\n".join(lines) + "\n")
    assert blockers == []
    assert warnings == []


def test_structured_secret_assignments_are_blocked() -> None:
    assignments = (
        'api_key: "should-not-ship"',
        'export ACCESS_TOKEN=should-not-ship',
        'refresh-token: "should-not-ship"',
        'auth_token: "should-not-ship"',
        'secret-key: "should-not-ship"',
        '"client_secret": "should-not-ship",',
        'password: "should-not-ship"',
        'passwd: "should-not-ship"',
        'private_key: "should-not-ship"',
        'oauth: "should-not-ship"',
        'cookie: "should-not-ship"',
        'bearer: "should-not-ship"',
        '{"password": "should-not-ship"}',
    )
    for assignment in assignments:
        blockers, _warnings = scan_text(assignment + "\n")
        assert any("secret_value_assignment" in item for item in blockers), assignment
        assert sum("secret_value_assignment" in item for item in blockers) == 1, assignment


def test_credential_headers_and_url_values_are_blocked() -> None:
    samples = (
        ("Authorization: Bearer should-not-ship", "authorization_header"),
        ("Set-Cookie: sessionid=should-not-ship", "set_cookie_header"),
        ("https://example.test/feed?api_key=should-not-ship", "secret_in_url"),
    )
    for line, finding_name in samples:
        blockers, _warnings = scan_text(line + "\n")
        assert any(finding_name in item for item in blockers), line


def test_known_secret_token_shape_is_blocked() -> None:
    fake_tokens = (
        "ghp_" + "A" * 36,
        "sk-proj-" + "A" * 32,
    )
    for fake_token in fake_tokens:
        blockers, _warnings = scan_text(f"token value: {fake_token}\n")
        assert any("known_secret_token" in item for item in blockers), fake_token[:8]


def test_sk_brand_names_are_not_secret_tokens() -> None:
    lines = (
        '"title": "Samsung, SK Hynix and Micron expand memory production"',
        '"url": "https://example.test/sk-telecom-named-as-korean-carrier"',
    )
    blockers, warnings = scan_text("\n".join(lines) + "\n")
    assert blockers == []
    assert warnings == []


def test_visible_email_is_still_blocked() -> None:
    address = "person" + "@" + "private.test"
    blockers, _warnings = scan_text(f"Contact: {address}\n")
    assert any("email_address" in item for item in blockers)


def test_item_key_does_not_hide_visible_phone() -> None:
    visible_number = "+" + "7" + " " + "999" + " " + "123" + " " + "45" + " " + "67"
    blockers, _warnings = scan_text(f'"item_key": "7875284855626048", "contact": "{visible_number}"\n')
    assert any("phone_like" in item for item in blockers)


def main() -> int:
    test_phone_like_ignores_url_digit_fragments()
    test_phone_like_still_blocks_visible_phone()
    test_safe_signal_path_does_not_hide_visible_phone()
    test_allowlisted_text_does_not_hide_visible_phone()
    test_allowlisted_text_does_not_hide_secret_assignment()
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
    test_markdown_signal_path_hash_is_not_phone_like()
    test_public_security_vocabulary_is_not_a_secret()
    test_structured_secret_assignments_are_blocked()
    test_credential_headers_and_url_values_are_blocked()
    test_known_secret_token_shape_is_blocked()
    test_sk_brand_names_are_not_secret_tokens()
    test_visible_email_is_still_blocked()
    test_item_key_does_not_hide_visible_phone()
    print("privacy scan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
