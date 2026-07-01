# Agent Operating Rules

These rules apply to Codex and other agents working in this repository.

## Scope

- Work only on the `news-dispatch` repository.
- Keep patches narrow and tied to the task.
- Avoid broad refactors unless the task explicitly asks for them.
- Do not touch `dispatches/` unless the task explicitly says publication.
- Do not change generated signals unless the task explicitly asks for signal
  generation or maintenance.
- Do not publish anything unless the task explicitly asks for publication.
- Routine autonomous daily digests may be reader-visible through `site/today.html`
  when machine safety/source/quality gates pass. Human approval is not required
  for that daily reader surface. Writing new Markdown into `dispatches/` still
  requires a task that explicitly allows publication.

## Daily Radar Boundary

- Do not delete `automation/daily-radar`.
- Daily Radar PRs from `automation/daily-radar` must never be merged with
  `--delete-branch`.
- Daily Radar PRs use squash merge only, without deleting the branch.
- Feature branches may be deleted after merge.
- Do not change the Daily Radar workflow unless the task explicitly asks for
  Daily Radar workflow work.

## GitOps Rules

- Do not commit, push, create a PR or merge unless explicitly instructed by the
  task.
- Before reporting ready, review the changed files and confirm the patch does
  not cross the requested scope.
- Stop after two failed attempts at the same fix or command and report the
  blocker instead of continuing to churn.

## Validation Rules

Before reporting ready, always run:

- targeted tests for the touched area;
- repository regression tests when the change can affect workflows, policy or
  routing;
- relevant validators for the changed surface.

For the local agent operating layer, run:

```bash
bash scripts/ops/local-agent-ready-check.sh
git diff --check
```

## Final Response

Always return:

- changed files;
- test results;
- risks;
- ready/not ready status.
