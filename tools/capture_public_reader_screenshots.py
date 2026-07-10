#!/usr/bin/env python3
"""Capture deterministic desktop and mobile screenshots of the public reader."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
OUTPUT_DIR = ROOT / "validation" / "public-reader-preview-screenshots"

BROWSER_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)

MAC_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


@dataclass(frozen=True)
class ReaderRoute:
    name: str
    path: str
    required_file: str


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


@dataclass(frozen=True)
class ScreenshotRecord:
    route: str
    viewport: str
    width: int
    height: int
    file: str
    url: str


ROUTES = (
    ReaderRoute("home", "/", "index.html"),
    ReaderRoute("news", "/news/", "news/index.html"),
    ReaderRoute("today", "/today.html", "today.html"),
    ReaderRoute("digests", "/digests/", "digests/index.html"),
    ReaderRoute("sources", "/sources/", "sources/index.html"),
)

VIEWPORTS = (
    Viewport("desktop", 1440, 1000),
    Viewport("mobile", 390, 844),
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def find_browser(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"browser executable not found: {path}")

    for candidate in BROWSER_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return Path(found).resolve()
    if MAC_CHROME.is_file():
        return MAC_CHROME
    raise FileNotFoundError("Chrome or Chromium is required for public reader screenshots")


def validate_routes(site_dir: Path) -> None:
    missing = [route.required_file for route in ROUTES if not (site_dir / route.required_file).is_file()]
    if missing:
        raise FileNotFoundError("missing public reader routes: " + ", ".join(missing))


def browser_command(
    browser: Path,
    url: str,
    output: Path,
    viewport: Viewport,
    profile_dir: Path,
) -> list[str]:
    return [
        str(browser),
        "--headless=new",
        "--disable-background-networking",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=1200",
        f"--user-data-dir={profile_dir}",
        f"--window-size={viewport.width},{viewport.height}",
        f"--screenshot={output}",
        url,
    ]


def complete_png(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1000:
        return False
    with path.open("rb") as handle:
        handle.seek(-12, 2)
        return handle.read() == b"\x00\x00\x00\x00IEND\xaeB`\x82"


def run_browser_capture(command: list[str], output: Path, timeout: float = 45.0) -> None:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if complete_png(output):
                return
            if process.poll() is not None:
                break
            time.sleep(0.1)
        if process.poll() is None:
            raise RuntimeError(f"browser timed out after {timeout:.0f}s")
        stdout, stderr = process.communicate()
        detail = stderr.strip() or stdout.strip() or f"browser exited with {process.returncode}"
        raise RuntimeError(detail)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def capture(browser: Path, site_dir: Path, output_dir: Path) -> list[ScreenshotRecord]:
    validate_routes(site_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    handler = partial(QuietHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    records: list[ScreenshotRecord] = []

    try:
        with tempfile.TemporaryDirectory(prefix="news-dispatch-chrome-") as tmp:
            for route in ROUTES:
                for viewport in VIEWPORTS:
                    filename = f"{route.name}-{viewport.name}.png"
                    output = (output_dir / filename).resolve()
                    url = base_url + route.path
                    profile_dir = Path(tmp) / f"{route.name}-{viewport.name}"
                    try:
                        run_browser_capture(browser_command(browser, url, output, viewport, profile_dir), output)
                    except RuntimeError as exc:
                        raise RuntimeError(f"screenshot failed for {route.name}/{viewport.name}: {exc}") from exc
                    records.append(
                        ScreenshotRecord(
                            route=route.name,
                            viewport=viewport.name,
                            width=viewport.width,
                            height=viewport.height,
                            file=filename,
                            url=route.path,
                        )
                    )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    return records


def write_gallery(output_dir: Path, records: list[ScreenshotRecord]) -> None:
    cards = []
    for record in records:
        title = f"{record.route} · {record.viewport} · {record.width}x{record.height}"
        cards.append(
            "\n".join(
                [
                    '<figure class="shot">',
                    f'  <figcaption>{html.escape(title)}</figcaption>',
                    f'  <a href="{html.escape(record.file)}"><img src="{html.escape(record.file)}" alt="{html.escape(title)}"></a>',
                    "</figure>",
                ]
            )
        )
    gallery = "\n".join(cards)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Public Reader Preview Screenshots</title>
  <style>
    body {{ margin: 0; padding: 24px; background: #f7f7f5; color: #171717; font: 15px/1.45 system-ui, sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ margin: 0 0 24px; color: #666; }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; align-items: start; }}
    .shot {{ margin: 0; padding: 12px; background: #fff; border: 1px solid #ddd; border-radius: 6px; }}
    figcaption {{ margin-bottom: 10px; font-weight: 700; }}
    img {{ display: block; width: 100%; height: auto; border: 1px solid #e5e5e5; }}
  </style>
</head>
<body>
  <main>
    <h1>Public Reader Preview Screenshots</h1>
    <p>Fixture build with media skipped. Click a screenshot to inspect it at captured resolution.</p>
    <div class="gallery">
{gallery}
    </div>
  </main>
</body>
</html>
"""
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "report_type": "public_reader_preview_screenshots",
        "screenshots": [asdict(record) for record in records],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", default=str(SITE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--browser")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    site_dir = Path(args.site_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    browser = find_browser(args.browser)
    records = capture(browser, site_dir, output_dir)
    write_gallery(output_dir, records)
    print(f"Captured {len(records)} public reader screenshot(s) in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
