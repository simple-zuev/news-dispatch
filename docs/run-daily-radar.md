# Run Daily Radar

Use this runbook after pipeline or source changes to confirm the full Daily Radar chain.

## Expected command

```bash
python tools/run_daily_radar_safe.py
```

## Expected generated artifacts

The run must produce or update:

- `validation/daily-radar-latest.json`
- `validation/daily-radar-filter-summary.json`
- `validation/source-health-latest.json`
- `validation/reviewed-radar-latest.md`
- `validation/candidate-dispatch-latest.md`
- `validation/auto-dispatch-latest.json`
- `validation/auto-dispatches/<stream>/<date>-auto-radar-draft.md`

## Built-in validation

The runner executes:

```text
validate_feeds.py
Daily Radar collection
signal filtering
source health generation
reviewed radar generation
candidate dispatch generation
candidate dispatch validation
auto dispatch draft generation
radar artifact validation
```

The run is valid only if every step exits successfully.

## Publication boundary

A successful Daily Radar run does not publish anything. It only prepares signal, review, candidate and draft-only artifacts under `signals/`, `data/` and `validation/`.

Daily Radar must not write auto-generated radar drafts into `dispatches/`. New automatic draft outputs belong under `validation/auto-dispatches/`.

Promotion to `dispatches/` is manual and must use `templates/promotion-checklist.md`.

## Repository boundary

Use these directories consistently:

- `signals/` — public signal log from source feeds.
- `validation/` — operational reports and pre-publication workspace.
- `validation/auto-dispatches/` — generated draft-only radar drafts.
- `validation/auto-dispatches/archive/` — historical generated radar drafts migrated out of `dispatches/`.
- `dispatches/` — deliberate editorial dispatch files only.
- `site/` — generated reader output from `tools/build_site.py`.

The regression guard `tests/test_no_auto_drafts_in_dispatches.py` fails if `*auto-radar-draft.md` appears under `dispatches/` again.
