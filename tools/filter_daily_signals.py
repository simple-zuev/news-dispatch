#!/usr/bin/env python3
"""Filter low-value Daily Radar signals created in the current run.

This script is intentionally conservative:
- it reads validation/daily-radar-latest.json;
- it only examines signal paths listed in that report;
- it deletes low-value signal files from the current run;
- it updates reports so they stay consistent with the committed signals;
- it does not fetch external resources.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "daily-radar-latest.json"
SUMMARY_PATH = ROOT / "validation" / "daily-radar-filter-summary.json"
MEDIA_LIMIT = 4

GLOBAL_TITLE_DENY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(deal|deals|discount|sale|coupon|price\s+cut|slashed|woot|record-low\s+price|now\s+just|prime\s+day)\b", re.I), "deal_or_discount"),
    (re.compile(r"\breview\b", re.I), "review_or_buying_guide"),
]

CONSUMER_PRICE_DEAL_DENY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(now\s+just|just|only|drops?\s+to|down\s+to|from\s+(?:\$|£|€)|save|saving|off)\b.{0,80}(?:\$|£|€)\s?\d{2,}", re.I), "deal_or_discount"),
    (re.compile(r"(?:\$|£|€)\s?\d{2,}.{0,80}\b(now\s+just|just|only|drops?\s+to|down\s+to|save|saving|off)\b", re.I), "deal_or_discount"),
]

CONSUMER_DEAL_STREAMS = {"gear-style-edc", "tech-hardware-software"}

STREAM_DENY: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "ai": [
        (re.compile(r"\b(radio|sunscreen|wall\s+modules|movie\s+player|phone\s+due\s+to\s+ram\s+prices|lights\s+into\s+its\s+ecosystem)\b", re.I), "not_ai"),
    ],
    "tech-hardware-software": [
        (re.compile(r"\b(baseball|sports|pro\s+sports|after\s+the\s+whistle|friday\s+night\s+baseball)\b", re.I), "sports_or_entertainment"),
        (re.compile(r"\b(steam\s+game|video\s+games|pc\s+gaming|conspicuous\s+consumption|congratulations\s+on\s+your\s+purchase)\b", re.I), "gaming_culture_not_tech_signal"),
        (re.compile(r"\b(fda|moderna|mrna|sunscreen|healthy|heart-protecting|nutrient)\b", re.I), "medical_or_health_not_tech"),
        (re.compile(r"\b(child\s+safety|children|developer\s+academy|language\s+learners|cherokee)\b", re.I), "social_or_education_not_tech"),
        (re.compile(r"\bsolarpunk\b", re.I), "culture_not_tech"),
    ],
    "science-discovery": [
        (re.compile(r"\b(think\s+you.?re\s+eating\s+healthy|heart-protecting\s+nutrient)\b", re.I), "wellness_not_science_discovery"),
    ],
    "gear-style-edc": [
        (re.compile(r"\b(grinch|sequel|movie|film)\b", re.I), "entertainment_not_gear"),
    ],
}

LOW_INFORMATION_TITLES = {
    "3dnews",
    "cbr news",
    "rbc finance",
    "kommersant finance",
    "miacr",
    "ruonia",
    "g8",
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


def normalize_title(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-z0-9а-я]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def has_enough_context(title: str) -> bool:
    normalized = normalize_title(title)
    if not normalized:
        return False
    if normalized in LOW_INFORMATION_TITLES:
        return False
    tokens = normalized.split()
    if len(tokens) <= 2:
        return False
    letters = re.findall(r"[a-zа-я]", normalized)
    if len(letters) < 12:
        return False
    return True


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


def signal_stream(path: Path, meta: dict[str, Any]) -> str:
    streams = list_value(meta, "streams")
    if streams:
        return streams[0]
    return path.parts[2] if len(path.parts) > 2 else "unknown"


def deny_reason_for_signal(title: str, stream: str, domains: str = "", path_text: str = "") -> str | None:
    """Return a conservative reject reason for one signal, or None if it should stay."""
    haystack = f"{title} {domains} {path_text}"
    if not has_enough_context(title):
        return "low_information_title"
    for pattern, reason in GLOBAL_TITLE_DENY:
        if pattern.search(title):
            return reason
    if stream in CONSUMER_DEAL_STREAMS:
        for pattern, reason in CONSUMER_PRICE_DEAL_DENY:
            if pattern.search(title):
                return reason
    for pattern, reason in STREAM_DENY.get(stream, []):
        if pattern.search(haystack):
            return reason
    return None


def deny_reason(path: Path) -> tuple[str | None, str]:
    full_path = ROOT / path
    if not full_path.exists():
        return None, "unknown"
    text = full_path.read_text(encoding="utf-8")
    meta = parse_front_matter(text)
    title = str(meta.get("title", ""))
    stream = signal_stream(path, meta)
    domains = " ".join(list_value(meta, "domains"))
    reason = deny_reason_for_signal(title=title, stream=stream, domains=domains, path_text=path.as_posix())
    return reason, stream


def update_report(report: dict[str, Any], removed: dict[str, dict[str, str]]) -> dict[str, Any]:
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
    filtered.extend({"path": path, **metadata} for path, metadata in sorted(removed.items()))
    report["filtered_signals"] = filtered
    return report


def stream_counts(paths: list[Path]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in paths:
        full_path = ROOT / path
        if not full_path.exists():
            continue
        meta = parse_front_matter(full_path.read_text(encoding="utf-8"))
        counts[signal_stream(path, meta)] += 1
    return dict(sorted(counts.items()))


def write_summary(report: dict[str, Any], original_paths: list[Path], kept_paths: list[Path], removed: dict[str, dict[str, str]]) -> None:
    by_reason = Counter(item["reason"] for item in removed.values())
    by_stream = Counter(item["stream"] for item in removed.values())
    summary = {
        "date": report.get("date", ""),
        "generated_count": len(original_paths),
        "kept_count": len(kept_paths),
        "filtered_count": len(removed),
        "filtered_by_reason": dict(sorted(by_reason.items())),
        "filtered_by_stream": dict(sorted(by_stream.items())),
        "remaining_by_stream": stream_counts(kept_paths),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not REPORT_PATH.exists():
        print("No Daily Radar report found; nothing to filter.")
        return 0
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    original_paths = target_signal_paths(report)
    removed: dict[str, dict[str, str]] = {}
    for relative in original_paths:
        reason, stream = deny_reason(relative)
        if not reason:
            continue
        full_path = ROOT / relative
        if full_path.exists():
            full_path.unlink()
            removed[relative.as_posix()] = {"reason": reason, "stream": stream}

    kept_paths = [path for path in original_paths if path.as_posix() not in removed]
    if removed:
        report = update_report(report, removed)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Filtered {len(removed)} Daily Radar signal(s).")
        for path, metadata in sorted(removed.items()):
            print(f"- {path}: {metadata['reason']}")
    else:
        print("No Daily Radar signals filtered.")
    write_summary(report, original_paths, kept_paths, removed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
