#!/usr/bin/env python3
"""Capture deterministic desktop and mobile screenshots of the public reader."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
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


def browser_command(browser: Path, profile_dir: Path) -> list[str]:
    return [
        str(browser),
        "--headless=new",
        "--disable-background-networking",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--remote-allow-origins=*",
        "--remote-debugging-port=0",
        f"--user-data-dir={profile_dir}",
        "about:blank",
    ]


def complete_png(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1000:
        return False
    with path.open("rb") as handle:
        handle.seek(-12, 2)
        return handle.read() == b"\x00\x00\x00\x00IEND\xaeB`\x82"


class WebSocketClient:
    def __init__(self, url: str, timeout: float) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise RuntimeError(f"unsupported DevTools WebSocket URL: {url}")
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
        self.socket.settimeout(timeout)
        self.buffer = b""
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        request = "\r\n".join(
            [
                f"GET {target} HTTP/1.1",
                f"Host: {parsed.hostname}:{parsed.port}",
                "Upgrade: websocket",
                "Connection: Upgrade",
                f"Sec-WebSocket-Key: {key}",
                "Sec-WebSocket-Version: 13",
                "Origin: http://127.0.0.1",
                "",
                "",
            ]
        )
        self.socket.sendall(request.encode("ascii"))
        response = self._read_headers()
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        expected_header = f"sec-websocket-accept: {expected}".lower()
        if not response.startswith("HTTP/1.1 101") or expected_header not in response.lower():
            self.close()
            raise RuntimeError("Chrome rejected the DevTools WebSocket connection")

    def _read_headers(self) -> str:
        data = self.buffer
        while b"\r\n\r\n" not in data:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("Chrome closed the DevTools handshake")
            data += chunk
        header, self.buffer = data.split(b"\r\n\r\n", 1)
        return header.decode("iso-8859-1")

    def _read_exact(self, size: int) -> bytes:
        data = self.buffer[:size]
        self.buffer = self.buffer[size:]
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise RuntimeError("Chrome closed the DevTools connection")
            data += chunk
        return data

    def send(self, payload: str, opcode: int = 1) -> None:
        data = payload.encode("utf-8")
        mask = os.urandom(4)
        length = len(data)
        if length < 126:
            header = bytes((0x80 | opcode, 0x80 | length))
        elif length < 65536:
            header = bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x80 | opcode, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
        self.socket.sendall(header + mask + masked)

    def receive(self) -> str:
        fragments = bytearray()
        while True:
            first, second = self._read_exact(2)
            finished = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 8:
                raise RuntimeError("Chrome closed the DevTools connection")
            if opcode == 9:
                self.send(payload.decode("utf-8", errors="ignore"), opcode=10)
                continue
            if opcode in (0, 1):
                fragments.extend(payload)
                if finished:
                    return fragments.decode("utf-8")

    def close(self) -> None:
        try:
            self.socket.close()
        except OSError:
            pass

    def __enter__(self) -> WebSocketClient:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class DevToolsClient:
    def __init__(self, websocket: WebSocketClient) -> None:
        self.websocket = websocket
        self.request_id = 0
        self.events: list[dict[str, object]] = []

    def command(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        self.request_id += 1
        request_id = self.request_id
        self.websocket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.websocket.receive())
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(f"DevTools {method} failed: {message['error']}")
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)

    def wait_for_event(self, method: str) -> None:
        while True:
            for index, event in enumerate(self.events):
                if event.get("method") == method:
                    self.events.pop(index)
                    return
            message = json.loads(self.websocket.receive())
            if message.get("method") == method:
                return
            if "method" in message:
                self.events.append(message)


def devtools_websocket_url(profile_dir: Path, process: subprocess.Popen[bytes], deadline: float) -> str:
    active_port = profile_dir / "DevToolsActivePort"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"browser exited with {process.returncode}")
        if active_port.is_file():
            port = active_port.read_text(encoding="utf-8").splitlines()[0]
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
                    targets = json.load(response)
                for target in targets:
                    if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                        return str(target["webSocketDebuggerUrl"])
            except (OSError, ValueError, urllib.error.URLError):
                pass
        time.sleep(0.05)
    raise RuntimeError("browser timed out before DevTools became ready")


def run_browser_capture(
    browser: Path,
    url: str,
    output: Path,
    viewport: Viewport,
    profile_dir: Path,
    timeout: float = 45.0,
) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(browser_command(browser, profile_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + timeout
    try:
        websocket_url = devtools_websocket_url(profile_dir, process, deadline)
        remaining = max(1.0, deadline - time.monotonic())
        with WebSocketClient(websocket_url, remaining) as websocket:
            devtools = DevToolsClient(websocket)
            devtools.command("Page.enable")
            devtools.command(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": viewport.width,
                    "height": viewport.height,
                    "deviceScaleFactor": 1,
                    "mobile": viewport.name == "mobile",
                    "screenWidth": viewport.width,
                    "screenHeight": viewport.height,
                },
            )
            devtools.command("Page.navigate", {"url": url})
            devtools.wait_for_event("Page.loadEventFired")
            devtools.command(
                "Runtime.evaluate",
                {
                    "expression": "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))",
                    "awaitPromise": True,
                    "returnByValue": True,
                },
            )
            metrics = devtools.command("Page.getLayoutMetrics")
            layout = metrics.get("cssLayoutViewport") or metrics.get("layoutViewport") or {}
            actual_width = round(float(layout.get("clientWidth", 0)))
            if actual_width != viewport.width:
                raise RuntimeError(f"viewport mismatch: expected {viewport.width}px, got {actual_width}px")
            screenshot = devtools.command(
                "Page.captureScreenshot",
                {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
            )
            output.write_bytes(base64.b64decode(str(screenshot["data"])))
            if not complete_png(output):
                raise RuntimeError("browser returned an incomplete PNG")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def capture_with_retry(
    browser: Path,
    url: str,
    output: Path,
    viewport: Viewport,
    profile_root: Path,
    attempts: int = 2,
) -> None:
    last_error: RuntimeError | None = None
    for attempt in range(1, attempts + 1):
        output.unlink(missing_ok=True)
        profile_dir = profile_root / f"attempt-{attempt}"
        try:
            run_browser_capture(browser, url, output, viewport, profile_dir)
            return
        except RuntimeError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


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
                    profile_root = Path(tmp) / f"{route.name}-{viewport.name}"
                    try:
                        capture_with_retry(browser, url, output, viewport, profile_root)
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
