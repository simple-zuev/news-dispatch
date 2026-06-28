# Regression tests

This repository keeps lightweight regression checks under `tests/`.

The PR-only `Regression Tests` workflow runs `python tests/run_regression_tests.py`.
The runner executes the current regression scripts in a fixed order and exits on the first failure.

Scope:
- Daily Radar signal filtering checks.
- Daily Radar semantic routing checks.

Boundary:
- No network access is required.
- No site publication is triggered.
- No generated radar or dispatch content is modified by the tests.
