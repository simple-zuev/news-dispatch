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
    viewport = screenshots.Viewport("mobile", 390, 844)
    command = screenshots.browser_command(
        Path("/tmp/chrome"),
        "http://127.0.0.1:8765/today.html",
        Path("/tmp/today-mobile.png"),
        viewport,
        Path("/tmp/profile"),
    )
    assert "--headless=new" in command
    assert "--force-device-scale-factor=1" in command
    assert "--window-size=390,844" in command
    assert "--screenshot=/tmp/today-mobile.png" in command
    assert command[-1] == "http://127.0.0.1:8765/today.html"


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


def main() -> int:
    test_reader_routes_and_viewports_are_complete()
    test_browser_command_is_deterministic()
    test_gallery_and_manifest_include_every_capture()
    test_complete_png_requires_final_iend_chunk()
    print("public reader screenshot tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
