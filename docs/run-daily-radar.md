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
radar artifact validation
```

The run is valid only if every step exits successfully.

## Publication boundary

A successful Daily Radar run does not publish anything. It only prepares signal, review and candidate artifacts under `signals/`, `data/` and `validation/`.

Promotion to `dispatches/` is manual and must use `templates/promotion-checklist.md`.
