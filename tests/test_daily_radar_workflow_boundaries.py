#!/usr/bin/env python3
"""Regression guard for Daily Radar workflow publication boundaries."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily-radar.yml"
RUNNER = ROOT / "tools" / "run_daily_radar_safe.py"


def test_daily_radar_does_not_push_to_main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    forbidden = [
        "HEAD:main",
        "git push origin main",
        "git push origin HEAD:main",
    ]
    offenders = [marker for marker in forbidden if marker in text]
    assert offenders == [], "Daily Radar must not push generated artifacts directly to main: " + ", ".join(offenders)


def test_daily_radar_uses_automation_pr_branch() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull-requests: write" in text
    assert "DAILY_RADAR_BRANCH: automation/daily-radar" in text
    assert "git push --force-with-lease origin HEAD:${DAILY_RADAR_BRANCH}" in text
    assert "gh pr create" in text


def test_daily_radar_uses_owner_qualified_pr_head() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "DAILY_RADAR_PR_HEAD: ${{ github.repository_owner }}:${{ env.DAILY_RADAR_BRANCH }}" in text
    assert '--head "${DAILY_RADAR_PR_HEAD}"' in text


def test_guarded_runner_prunes_only_after_building_drafts() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    build = 'run([sys.executable, "tools/build_auto_dispatches.py"])'
    prune = 'run([sys.executable, "tools/prune_operational_history.py", "--apply"])'
    validate = 'run([sys.executable, "tools/validate_radar_artifacts.py"])'
    assert build in text
    assert prune in text
    assert validate in text
    assert text.index(build) < text.index(prune) < text.index(validate)


def main() -> int:
    test_daily_radar_does_not_push_to_main()
    test_daily_radar_uses_automation_pr_branch()
    test_daily_radar_uses_owner_qualified_pr_head()
    test_guarded_runner_prunes_only_after_building_drafts()
    print("daily radar workflow boundary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
