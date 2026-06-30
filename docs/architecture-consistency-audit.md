# Architecture consistency audit

This document defines structural consistency checks for News Dispatch.

The audit covers engineering boundaries, validation coverage and publication safety. It does not judge the semantic quality of individual news items.

## System layers

- sources and stream registry;
- Daily Radar collection;
- signal filtering;
- source health and source governance;
- reviewed radar;
- candidate dispatch;
- auto dispatch drafts;
- synthesis publication gate;
- published dispatches;
- static reader site;
- GitHub Pages deployment.

## CI execution graph

Pull request validation must run syntax checks, stream registry validation, architecture consistency validation, source rules, editorial policy gates, published content validation and deterministic site build.

Regression tests must run through `tests/run_regression_tests.py`, which executes every `tests/test_*.py` file.

Pages deployment must build the reader site through `tools/build_site.py` in live mode.

Daily Radar automation must run `tools/run_daily_radar_safe.py`, then `tools/privacy_scan.py`, then propose generated `signals/`, `data/` and `validation/` changes through `automation/daily-radar`.

## Publication boundary

Daily Radar must not publish directly to `dispatches/`.

Auto radar drafts belong under `validation/auto-dispatches/`.

Candidate dispatches and auto drafts are pre-publication artifacts.

Promotion to `dispatches/` is a separate editorial action governed by the synthesis publication gate.

The persistent automation branch `automation/daily-radar` must not be deleted after Daily Radar PR merges.

## Validator coverage classes

- direct CI: validator is called directly from a GitHub workflow;
- transitive CI: validator is called by a workflow-owned orchestrator such as `tools/build_site.py` or `tools/run_daily_radar_safe.py`;
- regression covered: behavior is checked through `tests/run_regression_tests.py`;
- manual diagnostic: tool is intentionally not a blocking CI gate;
- legacy or retirement candidate: tool must be reviewed before relying on it.

Structural validators should check system invariants only. Semantic editorial quality checks belong to a separate synthesis quality layer.
