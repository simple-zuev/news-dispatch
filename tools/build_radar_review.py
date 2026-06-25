#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "validation" / "daily-radar-latest.json"
OUT = ROOT / "validation" / "reviewed-radar-latest.md"

TOPICS = {
    "regulation": ("regulat", "license", "approval", "cbr", "реестр", "банк россии", "правил"),
    "market": ("bitcoin", "ether", "liquidation", "market", "markets", "pce", "ставк"),
    "ai-platforms": ("openai", "chatgpt", "llm", "anthropic", "ai"),
    "security": ("cyber", "crime", "security", "vulnerability", "operation"),
    "infrastructure": ("chip", "supercomputer", "hardware", "broadcom", "nvidia"),
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {"date": "", "generated": [], "fetch_errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def read_signal(path: str) -> str:
    full = ROOT / path
    return full.read_text(encoding="utf-8") if full.exists() else ""


def scalar(text: str, name: str) -> str:
    match = re.search(rf'^{name}:\s*"?(.*?)"?$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def first_list_value(text: str, name: str) -> str:
    block = re.search(rf'^{name}:\n((?:\s+-\s+.*\n?)*)', text, re.MULTILINE)
    if not block:
        return ""
    item = re.search(r'-\s+"?(.*?)"?\s*$', block.group(1), re.MULTILINE)
    return item.group(1).strip() if item else ""


def topic(title: str) -> str:
    low = title.lower()
    for name, words in TOPICS.items():
        if any(word in low for word in words):
            return name
    return "general-monitoring"


def next_check(stream: str, source_class: str) -> str:
    if source_class == "official_source":
        return "Check whether the notice changes rules, dates, registers, participants or reporting obligations."
    if stream in {"finance", "crypto-finance"}:
        return "Find primary-source confirmation and separate market movement from regulatory or infrastructure impact."
    if stream == "tech-hardware-software":
        return "Check vendor/source material and identify product, infrastructure or security impact."
    return "Check source reliability, duplicates and whether the item affects the stream agenda."


def signal_meta(path: str) -> dict[str, str]:
    text = read_signal(path)
    title = scalar(text, "title") or path
    source_class = scalar(text, "source_class")
    domain = first_list_value(text, "domains")
    source = first_list_value(text, "sources")
    return {
        "title": title,
        "source_class": source_class,
        "domain": domain,
        "source": source,
        "topic": topic(title),
    }


def main() -> int:
    data = load_json(REPORT)
    generated = [item for item in data.get("generated", []) if isinstance(item, dict)]
    total = sum(int(item.get("count", 0) or 0) for item in generated)
    lines = [
        f"# Reviewed Radar Report — {data.get('date', '')}",
        "",
        "Status: pre-publication review artifact.",
        "",
        "This file is generated from Daily Radar signals. It is not a published dispatch.",
        "",
        "## Summary",
        "",
        f"- Retained signals: {total}",
        f"- Streams with retained signals: {len(generated)}",
        f"- Fetch warnings: {len(data.get('fetch_errors', []))}",
        "",
    ]
    for item in generated:
        stream = str(item.get("stream", "unknown"))
        lines.extend([f"## {stream}", ""])
        for signal in item.get("signals", []) or []:
            path = str(signal)
            meta = signal_meta(path)
            lines.append(f"- **{meta['title']}**")
            lines.append(f"  - Topic: `{meta['topic']}`")
            lines.append(f"  - Source: `{meta['domain']}` / `{meta['source_class']}`")
            lines.append(f"  - Signal path: `{path}`")
            lines.append("  - Confirmation: source-reported RSS/Atom appearance.")
            lines.append("  - Editorial status: needs grouping, context check and impact assessment.")
            lines.append(f"  - Next check: {next_check(stream, meta['source_class'])}")
        lines.append("")
    errors = data.get("fetch_errors", [])
    if errors:
        lines.extend(["## Fetch warnings", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")
    lines.extend([
        "## Next review checks",
        "",
        "1. Deduplicate related items across sources.",
        "2. Separate fact, trend, hypothesis and weak signal.",
        "3. Add primary-source confirmation for finance, regulation, crypto and security claims.",
        "4. Promote only reviewed items into dispatch candidates.",
        "",
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
