#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
VALIDATION_DIR = ROOT / "validation"
STATUS_JSON = SITE_DIR / "status.json"
INDEX_HTML = SITE_DIR / "index.html"
START = "<!-- site-status:start -->"
END = "<!-- site-status:end -->"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def status_payload() -> dict[str, Any]:
    radar = load_json(VALIDATION_DIR / "daily-radar-latest.json")
    auto = load_json(VALIDATION_DIR / "auto-dispatch-latest.json")
    dispatches = load_json(SITE_DIR / "dispatches.json")
    signals = 0
    streams = 0
    media = 0
    for item in radar.get("generated", []):
        rows = item.get("signals", []) if isinstance(item, dict) else []
        count = len(rows) if isinstance(rows, list) else 0
        signals += count
        media += int(item.get("media_count", 0) or 0) if isinstance(item, dict) else 0
        streams += 1 if count else 0
    published = dispatches.get("dispatches", []) if isinstance(dispatches.get("dispatches", []), list) else []
    drafts = auto.get("generated", []) if isinstance(auto.get("generated", []), list) else []
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "radar_date": str(radar.get("date", "")),
        "signals": signals,
        "streams_with_signals": streams,
        "media_candidates": media,
        "published_materials": len(published),
        "drafts_to_review": len(drafts),
    }


def block(payload: dict[str, Any]) -> str:
    radar_date = html.escape(str(payload.get("radar_date") or "нет данных"))
    generated_at = html.escape(str(payload.get("generated_at") or ""))
    return f"""{START}
<section class=\"panel site-status\" aria-label=\"Статус обновления\">
  <h2>Статус обновления</h2>
  <p>Последний радар: {radar_date}. Сборка статуса: {generated_at}.</p>
  <ul>
    <li>Свежие сигналы: {int(payload.get('signals', 0))}</li>
    <li>Темы с сигналами: {int(payload.get('streams_with_signals', 0))}</li>
    <li>Материалы на сайте: {int(payload.get('published_materials', 0))}</li>
    <li>Черновики к проверке: {int(payload.get('drafts_to_review', 0))}</li>
    <li>Медиа-превью из источников: {int(payload.get('media_candidates', 0))}</li>
  </ul>
  <p>Черновики не публикуются без редакционной проверки источников, дат и формулировок.</p>
</section>
{END}"""


def update_index(payload: dict[str, Any]) -> None:
    if not INDEX_HTML.exists():
        return
    text = INDEX_HTML.read_text(encoding="utf-8")
    html_block = block(payload)
    pattern = re.compile(rf"{re.escape(START)}.*?{re.escape(END)}", re.S)
    if pattern.search(text):
        text = pattern.sub(html_block, text)
    elif "<main>" in text:
        text = text.replace("<main>", f"<main>\n{html_block}", 1)
    else:
        text = text.replace("</header>", f"</header>\n{html_block}", 1)
    INDEX_HTML.write_text(text, encoding="utf-8")


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    payload = status_payload()
    STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_index(payload)
    print("Wrote site/status.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
