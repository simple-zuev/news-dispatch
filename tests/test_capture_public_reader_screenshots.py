#!/usr/bin/env python3
"""Regression tests for public reader screenshot capture metadata."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "capture_public_reader_screenshots.py"

spec = importlib.util.spec_from_file_location("capture_public_reader_screenshots", MODULE_PATH)
assert spec is not None and spec.loader is not None
screenshots = importlib.util.module_from_spec(spec)
sys.modules["capture_public_reader_screenshots"] = screenshots
spec.loader.exec_module(screenshots)


def test_reader_routes_and_viewports_are_complete() -> None:
    assert [route.name for route in screenshots.ROUTES] == ["home", "news", "today", "digests", "sources"]
    assert [viewport.name for viewport in screenshots.VIEWPORTS] == ["desktop", "mobile"]
    filenames = {
        f"{route.name}-{viewport.name}.png"
        for route in screenshots.ROUTES
        for viewport in screenshots.VIEWPORTS
    }
    assert len(filenames) == 10


def test_browser_command_is_deterministic() -> None:
    command = screenshots.browser_command(
        Path("/tmp/chrome"),
        Path("/tmp/profile"),
    )
    assert "--headless=new" in command
    assert "--remote-debugging-port=0" in command
    assert "--remote-allow-origins=*" in command
    assert "--user-data-dir=/tmp/profile" in command
    assert not any(item.startswith("--window-size=") for item in command)
    assert command[-1] == "about:blank"


def test_capture_checks_public_navigation_overflow() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "top navigation overflows its mobile container" in source
    assert "source rubric navigation overflows its mobile container" in source


def test_gallery_and_manifest_include_every_capture() -> None:
    records = [
        screenshots.ScreenshotRecord(
            route=route.name,
            viewport=viewport.name,
            width=viewport.width,
            height=viewport.height,
            file=f"{route.name}-{viewport.name}.png",
            url=route.path,
        )
        for route in screenshots.ROUTES
        for viewport in screenshots.VIEWPORTS
    ]
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        screenshots.write_gallery(output_dir, records)
        gallery = (output_dir / "index.html").read_text(encoding="utf-8")
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert gallery.count('<figure class="shot">') == 10
        assert "home-desktop.png" in gallery
        assert "sources-mobile.png" in gallery
        assert manifest["report_type"] == "public_reader_preview_screenshots"
        assert len(manifest["screenshots"]) == 10


def test_complete_png_requires_final_iend_chunk() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capture.png"
        path.write_bytes(b"x" * 1200)
        assert not screenshots.complete_png(path)
        path.write_bytes(b"x" * 1200 + b"\x00\x00\x00\x00IEND\xaeB`\x82")
        assert screenshots.complete_png(path)


def test_capture_retries_once_with_a_clean_profile() -> None:
    original = screenshots.run_browser_capture
    calls: list[Path] = []

    def flaky_capture(
        browser: Path,
        url: str,
        output: Path,
        viewport: screenshots.Viewport,
        profile_dir: Path,
        timeout: float = 45.0,
    ) -> None:
        calls.append(profile_dir)
        if len(calls) == 1:
            raise RuntimeError("browser exited with -9")
        output.write_bytes(b"x" * 1200 + b"\x00\x00\x00\x00IEND\xaeB`\x82")

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "capture.png"
        screenshots.run_browser_capture = flaky_capture
        try:
            screenshots.capture_with_retry(
                Path("/tmp/chrome"),
                "http://127.0.0.1:8765/",
                output,
                screenshots.Viewport("mobile", 390, 844),
                Path(tmp) / "profile",
            )
        finally:
            screenshots.run_browser_capture = original
        assert screenshots.complete_png(output)
        assert len(calls) == 2
        assert calls[0].name == "attempt-1"
        assert calls[1].name == "attempt-2"


def main() -> int:
    test_reader_routes_and_viewports_are_complete()
    test_browser_command_is_deterministic()
    test_capture_checks_public_navigation_overflow()
    test_gallery_and_manifest_include_every_capture()
    test_complete_png_requires_final_iend_chunk()
    test_capture_retries_once_with_a_clean_profile()
    print("public reader screenshot tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
