# Daily Radar

Daily Radar is the automatic source-collection layer for News Dispatch.

It collects public RSS and Atom items, creates daily signals, builds one daily dispatch, runs checks, and deploys the static site.

## Files

- `sources/feeds.json` stores the feed registry.
- `tools/daily_radar.py` builds signals and the daily dispatch.
- `.github/workflows/daily-radar.yml` runs the job on a schedule and manually.
- `validation/daily-radar-latest.json` stores the latest run report.
- `data/daily-radar-seen.json` stores deduplication state.

## Safety model

The first version is conservative. It does not scrape full article text, does not use private context, does not rewrite rumors as facts, and does not add advertising logic.

If too few fresh items are collected, the generated dispatch is downgraded to draft.

## Checks

The workflow runs the same publication and reader checks as the normal site pipeline:

- front matter validation;
- published content validation;
- static render;
- site enhancement;
- media preview postprocess;
- reader section postprocess;
- reader output validation;
- privacy scan.

## Source tuning

To tune the radar, edit `sources/feeds.json`: add or remove feeds, change stream mapping, adjust priority, and add tags.

The next product step is to expose `signals/` as reader cards on the site and add more Moscow, Russia, finance, AI, infrastructure, and gear sources.
