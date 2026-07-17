# Operational Retention

News Dispatch keeps reader-facing editorial material separately from
reproducible Daily Radar artifacts.

The guarded Daily Radar cycle retains:

- dated signal directories under `signals/` for 14 days;
- automatic radar drafts under `validation/auto-dispatches/` for 14 days;
- the latest top-level validation reports, which are overwritten on each run;
- up to 3000 seen-item identifiers in `data/daily-radar-seen.json`.

The retention tool never scans or deletes `dispatches/`, `sources/`, or `site/`.
Editorial dispatches therefore have no automatic expiry.

Preview a cleanup without deleting files:

```bash
python3 tools/prune_operational_history.py
```

Apply the bounded cleanup:

```bash
python3 tools/prune_operational_history.py --apply
```

Every run writes `validation/operational-retention-latest.json` with the cutoff,
candidate paths, deleted paths, and errors. The Daily Radar guarded runner
applies retention after building automatic drafts and before final artifact
validation.
