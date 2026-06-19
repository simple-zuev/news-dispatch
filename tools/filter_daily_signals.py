#!/usr/bin/env python3
"""Filter low-value Daily Radar signals created in the current run.

This script is intentionally conservative:
- it reads validation/daily-radar-latest.json;
- it only examines signal paths listed in that report;
- it deletes low-value signal files from the current run;
- it updates the report so it stays consistent with the committed signals;
- it does not fetch external resources.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "daily-radar-latest.json"
MEDIA_LIMIT = 4

GLOBAL_DENY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(deal|deals|discount|sale|coupon|save\s+\$|save\s+a|off\s+these|off\s+this|price\s+cut|slashed|woot)\b", re.I), "deal_or_discount"),
    (re.compile(r"\breview\b", re.I), "review_or_buying_guide"),
]

STREAM_DENY: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "ai": [
        (re.compile(r"\b(radio|sunscreen|wall\s+modules|movie\s+player|phone\s+due\s+to\s+ram\s+prices|lights\s+into\s+its\s+ecosystem)\b", re.I), "not_ai"),
    ],
    "tech-hardware-software": [
        (re.compile(r"\b(baseball|sports|pro\s+sports|after\s+the\s+whistle|friday\s+night\s+baseball)\b", re.I), "sports_or_entertainment"),
        (re.compile(r"\b(fda|moderna|mrna|sunscreen)\b", re.I), "medical_or_health_not_tech"),
        (re.compile(r"\b(child\s+safety|children|developer\s+academy|language\s+learners|cherokee)\b", re.I), "social_or_education_not_tech"),
        (re.compile(r"\bsolarpunk\b", re.I), "culture_not_tech"),
    ],
    "gear-style-edc": [
        (re.compile(r"\b(grinch|sequel|movie|film)\b", re.I), "entertainment_not_gear"),
    ],
}


def parse_front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    raw = text[4:end]
    meta: dict[str, Any] = {}
    list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  -") and list_key:
            meta.setdefault(list_key, [])
            if isinstance(meta[list_key], list):
                meta[list_key].append(line.split("-", 1)[1].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value:
            list_key = None
            meta[key] = value
        else:
            list_key = key
            meta[key] = []
    return meta


def list_value(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def relative_signal_path(value: str) -> Path | None:
    value = value.strip()
    marker = "signals/"
    if marker not in value:
        return None
    relative = value[value.find(marker) :]
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or path.parts[0] != "signals":
        return None
    return path


def target_signal_paths(report: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for item in report.get("generated", []):
        if not isinstance(item, dict):
            continue
        for signal in item.get("signals", []):
            path = relative_signal_path(str(signal))
            if path is not None:
                paths.append(path)
    return list(dict.fromkeys(paths))


def deny_reason(path: Path) -> str | None:
    full_path = ROOT / path
    if not full_path.exists():
        return None
    text = full_path.read_text(encoding="utf-8")
    meta = parse_front_matter(text)
    title = str(meta.get("title", ""))
    streams = list_value(meta, "streams")
    stream = streams[0] if streams else path.parts[2] if len(path.parts) > 2 else ""
    domains = " ".join(list_value(meta, "domains"))
    haystack = f"{title} {domains} {path.as_posix()}"

    for pattern, reason in GLOBAL_DENY:
        if pattern.search(haystack):
            return reason
    for pattern, reason in STREAM_DENY.get(stream, []):
        if pattern.search(haystack):
            return reason
    return None


def update_report(report: dict[str, Any], removed: dict[str, str]) -> dict[str, Any]:
    removed_keys = set(removed)
    for item in report.get("generated", []):
        if not isinstance(item, dict):
            continue
        kept_signals: list[str] = []
        for signal in item.get("signals", []):
            relative = relative_signal_path(str(signal))
            if relative is not None and relative.as_posix() in removed_keys:
                continue
            kept_signals.append(str(signal))
        item["signals"] = kept_signals
        item["count"] = len(kept_signals)
        item["media_count"] = min(MEDIA_LIMIT, len(kept_signals))
    filtered = report.get("filtered_signals", [])
    if not isinstance(filtered, list):
        filtered = []
    filtered.extend({"path": path, "reason": reason} for path, reason in sorted(removed.items()))
    report["filtered_signals"] = filtered
    return report


def main() -> int:
    if not REPORT_PATH.exists():
        print("No Daily Radar report found; nothing to filter.")
        return 0
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    removed: dict[str, str] = {}
    for relative in target_signal_paths(report):
        reason = deny_reason(relative)
        if not reason:
            continue
        full_path = ROOT / relative
        if full_path.exists():
            full_path.unlink()
            removed[relative.as_posix()] = reason

    if removed:
        report = update_report(report, removed)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Filtered {len(removed)} Daily Radar signal(s).")
        for path, reason in sorted(removed.items()):
            print(f"- {path}: {reason}")
    else:
        print("No Daily Radar signals filtered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
