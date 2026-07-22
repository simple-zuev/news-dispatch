#!/usr/bin/env python3
"""Regression guard for Daily Radar workflow publication boundaries."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "daily-radar.yml"
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
REGRESSION_WORKFLOW = ROOT / ".github" / "workflows" / "regression-tests.yml"
RUNNER = ROOT / "tools" / "run_daily_radar_safe.py"
CHANGE_SET_GUARD = ROOT / "tools" / "validate_daily_radar_change_set.py"


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


def test_daily_radar_uses_current_node24_actions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "actions/checkout@v7" in text
    assert "actions/setup-python@v6" in text
    assert "actions/checkout@v4" not in text
    assert "actions/setup-python@v5" not in text


def test_generated_only_prs_use_explicit_workflow_dispatch() -> None:
    radar = WORKFLOW.read_text(encoding="utf-8")
    assert "actions: write" in radar
    assert 'gh workflow run validate.yml --ref "${DAILY_RADAR_BRANCH}"' in radar
    assert 'gh workflow run regression-tests.yml --ref "${DAILY_RADAR_BRANCH}"' in radar
    assert radar.index("gh pr create") < radar.index("gh workflow run validate.yml")

    for path in (VALIDATE_WORKFLOW, REGRESSION_WORKFLOW):
        text = path.read_text(encoding="utf-8")
        assert "pull_request:" in text
        assert "workflow_dispatch:" in text
        assert "paths-ignore:" in text
        for generated_path in ('"signals/**"', '"data/**"', '"validation/**"'):
            assert generated_path in text


def test_dispatched_checks_report_status_on_automation_sha() -> None:
    expected_contexts = {
        VALIDATE_WORKFLOW: 'context="validate"',
        REGRESSION_WORKFLOW: 'context="regression-tests"',
    }
    for path, context in expected_contexts.items():
        text = path.read_text(encoding="utf-8")
        assert "statuses: write" in text
        assert "github.event_name == 'workflow_dispatch'" in text
        assert "github.ref_name == 'automation/daily-radar'" in text
        assert 'statuses/${GITHUB_SHA}' in text
        assert context in text


def test_guarded_runner_prunes_only_after_building_drafts() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    build = 'run([sys.executable, "tools/build_auto_dispatches.py"])'
    prune = 'run([sys.executable, "tools/prune_operational_history.py", "--apply"])'
    validate = 'run([sys.executable, "tools/validate_radar_artifacts.py"])'
    assert build in text
    assert prune in text
    assert validate in text
    assert text.index(build) < text.index(prune) < text.index(validate)


def test_daily_radar_validates_staged_change_set_before_push() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    stage = "git add signals data validation"
    guard = "python tools/validate_daily_radar_change_set.py"
    checkout = 'git checkout -B "${DAILY_RADAR_BRANCH}"'
    push = "git push --force-with-lease origin HEAD:${DAILY_RADAR_BRANCH}"
    assert CHANGE_SET_GUARD.exists()
    assert all(marker in text for marker in (stage, guard, checkout, push))
    assert text.index(stage) < text.index(guard) < text.index(checkout) < text.index(push)
    assert "cat /tmp/daily-radar-change-set.md >> \"$GITHUB_STEP_SUMMARY\"" in text
    assert "cat /tmp/daily-radar-change-set.md >> \"$body_file\"" in text


def main() -> int:
    test_daily_radar_does_not_push_to_main()
    test_daily_radar_uses_automation_pr_branch()
    test_daily_radar_uses_owner_qualified_pr_head()
    test_daily_radar_uses_current_node24_actions()
    test_generated_only_prs_use_explicit_workflow_dispatch()
    test_dispatched_checks_report_status_on_automation_sha()
    test_guarded_runner_prunes_only_after_building_drafts()
    test_daily_radar_validates_staged_change_set_before_push()
    print("daily radar workflow boundary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
