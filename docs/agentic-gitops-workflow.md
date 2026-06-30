# Agentic GitOps Workflow

This workflow keeps News Dispatch agent work small, reviewable and separated
from publication and Daily Radar automation.

## Roles

- User: defines the task, branch, scope, approval level and whether publication,
  commit, push, PR creation or merge is allowed.
- ChatGPT: helps shape intent, prepare task prompts and decide whether Codex
  should run a patch.
- Codex: edits the repository, runs tests and validators, reports risks and
  stops when scope or validation is unclear.
- GitHub Actions: runs CI and deployment checks after a PR or workflow event.
- PR review: confirms the patch matches the task, passes policy boundaries and
  is safe to merge.

## Lifecycle

```text
task -> Codex patch -> tests -> PR -> CI -> review -> merge
```

1. The user gives a scoped task and branch.
2. Codex applies the smallest useful patch.
3. Codex runs targeted tests, regression tests and relevant validators.
4. A PR is opened only when the task explicitly asks for it.
5. GitHub Actions runs CI.
6. Review confirms the change is correct and public-safe.
7. Merge happens only after approval.

## Merge Rules

- Feature PR: squash merge is allowed, and deleting the feature branch after
  merge is allowed.
- Daily Radar PR from `automation/daily-radar`: squash merge only. Do not delete
  the branch.
- Never merge Daily Radar PRs with `--delete-branch`.
- Do not delete, recreate or force-push `automation/daily-radar` unless the task
  explicitly asks for Daily Radar branch maintenance.

## Publication Rule

Publication to `dispatches/` requires explicit user approval. Signal collection,
reviewed radar output and draft-only auto-dispatch material do not authorize
publication by themselves.

## Agent Handoff

Every Codex handoff should include:

- changed files;
- test and validator results;
- known risks or skipped checks;
- ready/not ready status.
