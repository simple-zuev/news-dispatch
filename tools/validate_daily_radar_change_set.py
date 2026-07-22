#!/usr/bin/env python3
"""Validate staged Daily Radar changes before the automation branch is pushed."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETENTION_REPORT = ROOT / "validation" / "operational-retention-latest.json"

SIGNAL_RE = re.compile(r"^signals/(\d{4}-\d{2}-\d{2})/[a-z0-9-]+/[^/]+\.md$")
AUTO_DRAFT_RE = re.compile(
    r"^validation/auto-dispatches/(archive/)?[a-z0-9-]+/(\d{4}-\d{2}-\d{2})-auto-radar-draft\.md$"
)
LATEST_VALIDATION_FILES = {
    "validation/auto-dispatch-latest.json",
    "validation/candidate-dispatch-latest.md",
    "validation/daily-radar-filter-summary.json",
    "validation/daily-radar-latest.json",
    "validation/operational-retention-latest.json",
    "validation/reviewed-radar-latest.md",
    "validation/source-governance-latest.json",
    "validation/source-governance-latest.md",
    "validation/source-health-latest.json",
}
STATE_FILE = "data/daily-radar-seen.json"


@dataclass(frozen=True)
class Change:
    status: str
    path: str


@dataclass(frozen=True)
class Limits:
    max_changed_files: int = 400
    max_deleted_files: int = 300
    max_signal_writes: int = 80
    max_validation_writes: int = 24


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def staged_changes(root: Path) -> list[Change]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--no-renames"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    changes: list[Change] = []
    for raw in result.stdout.splitlines():
        status, separator, path = raw.partition("\t")
        if not separator or not status or not path:
            raise ValueError(f"unrecognized staged diff row: {raw}")
        changes.append(Change(status=status, path=path))
    return changes


def retention_dates(path: Path) -> tuple[date, date]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    reference = parse_date(str(payload.get("reference_date", "")))
    cutoff = parse_date(str(payload.get("cutoff_date", "")))
    if reference is None or cutoff is None:
        raise ValueError("retention report has invalid reference_date or cutoff_date")
    if payload.get("mode") != "apply" or payload.get("passed") is not True:
        raise ValueError("retention report must describe a successful apply run")
    if payload.get("errors"):
        raise ValueError("retention report contains errors")
    return reference, cutoff


def validate_change(
    change: Change,
    *,
    reference: date,
    cutoff: date,
) -> list[str]:
    issues: list[str] = []
    if change.status not in {"A", "M", "D"}:
        return [f"unsupported git status {change.status}: {change.path}"]

    signal_match = SIGNAL_RE.fullmatch(change.path)
    if signal_match:
        artifact_date = parse_date(signal_match.group(1))
        if artifact_date is None:
            return [f"invalid signal date: {change.path}"]
        if change.status == "D" and artifact_date >= cutoff:
            issues.append(f"fresh signal deletion is not allowed: {change.path}")
        if change.status in {"A", "M"} and artifact_date != reference:
            issues.append(f"signal write must use reference date {reference}: {change.path}")
        return issues

    draft_match = AUTO_DRAFT_RE.fullmatch(change.path)
    if draft_match:
        archived = bool(draft_match.group(1))
        artifact_date = parse_date(draft_match.group(2))
        if artifact_date is None:
            return [f"invalid auto-dispatch date: {change.path}"]
        if change.status == "D" and artifact_date >= cutoff:
            issues.append(f"fresh auto-dispatch deletion is not allowed: {change.path}")
        if change.status in {"A", "M"} and (archived or artifact_date != reference):
            issues.append(f"auto-dispatch write must be current and unarchived: {change.path}")
        return issues

    if change.path == STATE_FILE:
        if change.status == "D":
            issues.append(f"Daily Radar state cannot be deleted: {change.path}")
        return issues

    if change.path in LATEST_VALIDATION_FILES:
        if change.status == "D":
            issues.append(f"latest validation report cannot be deleted: {change.path}")
        return issues

    return [f"path is outside the Daily Radar generated boundary: {change.path}"]


def validate_changes(
    changes: list[Change],
    *,
    reference: date,
    cutoff: date,
    limits: Limits,
) -> dict[str, object]:
    issues: list[str] = []
    for change in changes:
        issues.extend(validate_change(change, reference=reference, cutoff=cutoff))

    deleted = sum(change.status == "D" for change in changes)
    signal_writes = sum(
        change.status in {"A", "M"} and SIGNAL_RE.fullmatch(change.path) is not None
        for change in changes
    )
    validation_writes = sum(
        change.status in {"A", "M"} and change.path.startswith("validation/")
        for change in changes
    )
    if len(changes) > limits.max_changed_files:
        issues.append(f"changed file count {len(changes)} exceeds {limits.max_changed_files}")
    if deleted > limits.max_deleted_files:
        issues.append(f"deleted file count {deleted} exceeds {limits.max_deleted_files}")
    if signal_writes > limits.max_signal_writes:
        issues.append(f"signal write count {signal_writes} exceeds {limits.max_signal_writes}")
    if validation_writes > limits.max_validation_writes:
        issues.append(f"validation write count {validation_writes} exceeds {limits.max_validation_writes}")

    counts_by_status = {
        status: sum(change.status == status for change in changes)
        for status in ("A", "M", "D")
    }
    counts_by_root: dict[str, int] = {}
    for change in changes:
        root = change.path.split("/", 1)[0]
        counts_by_root[root] = counts_by_root.get(root, 0) + 1
    return {
        "report_type": "daily_radar_change_set",
        "passed": not issues,
        "reference_date": reference.isoformat(),
        "cutoff_date": cutoff.isoformat(),
        "changed_files": len(changes),
        "deleted_files": deleted,
        "signal_writes": signal_writes,
        "validation_writes": validation_writes,
        "counts_by_status": counts_by_status,
        "counts_by_root": counts_by_root,
        "limits": {
            "max_changed_files": limits.max_changed_files,
            "max_deleted_files": limits.max_deleted_files,
            "max_signal_writes": limits.max_signal_writes,
            "max_validation_writes": limits.max_validation_writes,
        },
        "issues": issues,
    }


def markdown_report(report: dict[str, object]) -> str:
    status = "PASS" if report["passed"] else "BLOCKED"
    roots = report["counts_by_root"]
    root_summary = ", ".join(f"{key}: {value}" for key, value in sorted(roots.items())) or "none"
    lines = [
        "## Daily Radar change-set guard",
        "",
        f"- Status: **{status}**",
        f"- Reference / cutoff: `{report['reference_date']}` / `{report['cutoff_date']}`",
        f"- Changed / deleted files: **{report['changed_files']}** / **{report['deleted_files']}**",
        f"- Signal / validation writes: **{report['signal_writes']}** / **{report['validation_writes']}**",
        f"- Roots: {root_summary}",
    ]
    issues = report["issues"]
    if issues:
        lines.extend(["", "Blocking issues:"])
        lines.extend(f"- {issue}" for issue in issues)
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--retention-report", default=str(RETENTION_REPORT))
    parser.add_argument("--markdown-output")
    parser.add_argument("--max-changed-files", type=int, default=400)
    parser.add_argument("--max-deleted-files", type=int, default=300)
    parser.add_argument("--max-signal-writes", type=int, default=80)
    parser.add_argument("--max-validation-writes", type=int, default=24)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root).resolve()
    try:
        reference, cutoff = retention_dates(Path(args.retention_report))
        report = validate_changes(
            staged_changes(root),
            reference=reference,
            cutoff=cutoff,
            limits=Limits(
                max_changed_files=args.max_changed_files,
                max_deleted_files=args.max_deleted_files,
                max_signal_writes=args.max_signal_writes,
                max_validation_writes=args.max_validation_writes,
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"Daily Radar change-set guard failed: {exc}", file=sys.stderr)
        return 2

    rendered = markdown_report(report)
    print(rendered, end="")
    if args.markdown_output:
        output = Path(args.markdown_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
