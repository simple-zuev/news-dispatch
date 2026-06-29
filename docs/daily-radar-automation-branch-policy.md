# Daily Radar automation branch policy

`automation/daily-radar` is a persistent automation branch.

Rules:

1. Do not delete `automation/daily-radar` after merging Daily Radar PRs.
2. Do not use `gh pr merge --delete-branch` for Daily Radar PRs.
3. Merge Daily Radar PRs with `gh pr merge <PR> --squash` only.
4. If the branch is accidentally deleted, recreate it from current `main` with `git push origin main:automation/daily-radar`.
5. Publication to `dispatches/` remains separate from Daily Radar signal generation.
