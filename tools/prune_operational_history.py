#!/usr/bin/env python3
"""Prune old, reproducible Daily Radar artifacts within strict path boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SIGNALS_DIR = ROOT / "signals"
AUTO_DISPATCH_DIR = ROOT / "validation" / "auto-dispatches"
REPORT_PATH = ROOT / "validation" / "operational-retention-latest.json"

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DRAFT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-auto-radar-draft\.md$")


@dataclass(frozen=True)
class RetentionCandidate:
    path: Path
    kind: str
    artifact_date: date


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def signal_candidates(signals_dir: Path) -> Iterable[RetentionCandidate]:
    if not signals_dir.exists():
        return
    for day_dir in sorted(signals_dir.iterdir()):
        if not day_dir.is_dir() or not DATE_DIR_RE.fullmatch(day_dir.name):
            continue
        artifact_date = parse_date(day_dir.name)
        if artifact_date is not None:
            yield RetentionCandidate(day_dir, "signals", artifact_date)


def auto_dispatch_candidates(auto_dispatch_dir: Path) -> Iterable[RetentionCandidate]:
    if not auto_dispatch_dir.exists():
        return
    for path in sorted(auto_dispatch_dir.rglob("*.md")):
        match = DRAFT_RE.fullmatch(path.name)
        if not match:
            continue
        artifact_date = parse_date(match.group(1))
        if artifact_date is not None:
            yield RetentionCandidate(path, "auto_dispatch", artifact_date)


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def candidate_label(candidate: RetentionCandidate, signals_dir: Path, auto_dispatch_dir: Path) -> str:
    root = signals_dir if candidate.kind == "signals" else auto_dispatch_dir
    prefix = "signals" if candidate.kind == "signals" else "validation/auto-dispatches"
    relative = candidate.path.resolve().relative_to(root.resolve())
    return f"{prefix}/{relative.as_posix()}"


def delete_candidate(candidate: RetentionCandidate, signals_dir: Path, auto_dispatch_dir: Path) -> None:
    allowed_root = signals_dir if candidate.kind == "signals" else auto_dispatch_dir
    if not within(candidate.path, allowed_root):
        raise ValueError(f"retention path escaped allowed root: {candidate.path}")
    if candidate.kind == "signals":
        for child in sorted(candidate.path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        candidate.path.rmdir()
    else:
        candidate.path.unlink()


def remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def prune(
    *,
    signals_dir: Path,
    auto_dispatch_dir: Path,
    reference: date,
    retention_days: int,
    apply: bool,
) -> dict[str, object]:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    if signals_dir.name != "signals":
        raise ValueError("signals_dir must point to a directory named signals")
    if auto_dispatch_dir.name != "auto-dispatches":
        raise ValueError("auto_dispatch_dir must point to a directory named auto-dispatches")
    cutoff = reference - timedelta(days=retention_days)
    candidates = [
        candidate
        for candidate in [*signal_candidates(signals_dir), *auto_dispatch_candidates(auto_dispatch_dir)]
        if candidate.artifact_date < cutoff
    ]
    deleted: list[str] = []
    errors: list[str] = []
    for candidate in candidates:
        label = candidate_label(candidate, signals_dir, auto_dispatch_dir)
        if not apply:
            continue
        try:
            delete_candidate(candidate, signals_dir, auto_dispatch_dir)
            deleted.append(label)
        except (OSError, ValueError) as exc:
            errors.append(f"{label}: {exc}")
    if apply:
        remove_empty_dirs(auto_dispatch_dir)

    counts = {
        "signals": sum(candidate.kind == "signals" for candidate in candidates),
        "auto_dispatches": sum(candidate.kind == "auto_dispatch" for candidate in candidates),
    }
    return {
        "report_type": "operational_retention",
        "reference_date": reference.isoformat(),
        "retention_days": retention_days,
        "cutoff_date": cutoff.isoformat(),
        "mode": "apply" if apply else "dry_run",
        "candidate_counts": counts,
        "candidate_paths": [
            candidate_label(candidate, signals_dir, auto_dispatch_dir)
            for candidate in candidates
        ],
        "deleted_count": len(deleted),
        "deleted_paths": deleted,
        "errors": errors,
        "protected_roots": ["dispatches", "sources", "site"],
        "passed": not errors,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-date", default=date.today().isoformat())
    parser.add_argument("--retention-days", type=int, default=14)
    parser.add_argument("--signals-dir", default=str(SIGNALS_DIR))
    parser.add_argument("--auto-dispatch-dir", default=str(AUTO_DISPATCH_DIR))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    reference = parse_date(args.reference_date)
    if reference is None:
        print("Operational retention failed: invalid reference date", file=sys.stderr)
        return 2
    try:
        report = prune(
            signals_dir=Path(args.signals_dir),
            auto_dispatch_dir=Path(args.auto_dispatch_dir),
            reference=reference,
            retention_days=args.retention_days,
            apply=args.apply,
        )
    except ValueError as exc:
        print(f"Operational retention failed: {exc}", file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    action = "deleted" if args.apply else "would delete"
    counts = report["candidate_counts"]
    print(
        f"Operational retention {action}: "
        f"{counts['signals']} signal day(s), "
        f"{counts['auto_dispatches']} auto-dispatch draft(s)"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
