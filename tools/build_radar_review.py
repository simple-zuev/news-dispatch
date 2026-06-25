#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "validation" / "daily-radar-latest.json"
OUT = ROOT / "validation" / "reviewed-radar-latest.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {"date": "", "generated": [], "fetch_errors": []}
    return json.loads(path.read_text(encoding="utf-8"))


def title_from_signal(path: str) -> str:
    full = ROOT / path
    if not full.exists():
        return path
    text = full.read_text(encoding="utf-8")
    match = re.search(r'^title:\s*"?(.*?)"?$', text, re.MULTILINE)
    return match.group(1).strip() if match else path


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
            lines.append(f"- **{title_from_signal(path)}**")
            lines.append(f"  - Signal path: `{path}`")
            lines.append("  - Confirmation: source-reported RSS/Atom appearance.")
            lines.append("  - Editorial status: needs grouping, context check and impact assessment.")
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
