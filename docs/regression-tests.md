# Regression tests

This repository keeps lightweight regression checks under `tests/`.

The `Regression Tests` workflow runs `python tests/run_regression_tests.py` for
ordinary pull requests and explicit automation-branch dispatches.
The runner executes the current regression scripts in a fixed order and exits on the first failure.

Daily Radar changes only `signals/`, `data/`, and `validation/`. Pull requests
containing only those generated paths skip the normal `pull_request` trigger,
because GitHub marks workflows created by `GITHUB_TOKEN` as approval-required.
The Daily Radar workflow dispatches both regression and validation checks on
the automation branch after it opens or updates the pull request. Each
dispatched workflow also publishes its final commit status on the automation
SHA so the result remains visible in the pull request.

Scope:
- Daily Radar signal filtering checks.
- Daily Radar semantic routing checks.

Boundary:
- No network access is required.
- No site publication is triggered.
- No generated radar or dispatch content is modified by the tests.
