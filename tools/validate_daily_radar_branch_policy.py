#!/usr/bin/env python3
from pathlib import Path

POLICY = Path("docs/daily-radar-automation-branch-policy.md")
WORKFLOW = Path(".github/workflows/daily-radar.yml")

REQUIRED_POLICY_TOKENS = [
    "`automation/daily-radar` is a persistent automation branch.",
    "Do not delete `automation/daily-radar` after merging Daily Radar PRs.",
    "Do not use `gh pr merge --delete-branch` for Daily Radar PRs.",
    "Merge Daily Radar PRs with `gh pr merge <PR> --squash` only.",
    "git push origin main:automation/daily-radar",
    "Publication to `dispatches/` remains separate from Daily Radar signal generation.",
]

def req(ok: bool, msg: str) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {msg}")

def main() -> None:
    req(POLICY.exists(), f"missing policy file: {POLICY}")
    req(WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}")

    policy = POLICY.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for token in REQUIRED_POLICY_TOKENS:
        req(token in policy, f"policy missing token: {token}")

    req("DAILY_RADAR_BRANCH: automation/daily-radar" in workflow, "workflow must keep persistent automation branch name")
    req("gh pr create" in workflow, "workflow must create Daily Radar PRs")
    req("--delete-branch" not in workflow, "Daily Radar workflow must not delete the persistent automation branch")
    req("git add signals data validation" in workflow, "Daily Radar workflow must stage only Daily Radar artifact roots")
    req("git add dispatches" not in workflow, "Daily Radar workflow must not stage dispatches for publication")

    print("Daily Radar automation branch policy validation: OK")

if __name__ == "__main__":
    main()
