# Public reader quality monitoring

The public reader keeps a bounded 14-day history and evaluates the latest seven days after each Pages build.

`tools/build_public_reader_quality_report.py` writes:

- `validation/public-reader-quality-latest.json` for automation;
- `validation/public-reader-quality-latest.md` for review in GitHub Actions.

The report tracks stream and independent-publisher diversity, duplicate-story share, source and stream concentration, low-output streams, Russian reader-title coverage, and useful-summary coverage. It also compares configured publisher counts with the working target of eight independent sources per stream.

The current reader selection reserves two slots per stream when at least two candidates pass freshness, source rules, deduplication and relevance gates. Unused floor slots are reported as `selection_floor_shortfalls`; they are never filled with below-threshold material.

A new cache records successful build dates and stays in `collecting` status until those observations span seven calendar days. Publication dates from older feed items do not mature a new monitoring window. Advisory alerts do not block Pages deployment; existing freshness, privacy, reader-policy, and rendering gates remain responsible for fail-closed publication safety.

History schema v2 retains only the balanced reader selection. Its first build intentionally drops the older unbalanced cache and reports that reset in `legacy_cache_reset`; the rolling quality window then rebuilds from curated daily output.

The Pages workflow uploads the report as the `public-reader-quality-report` artifact. Review it before expanding another source batch or changing ranking rules. New sources should be added in probation batches of no more than three and must pass live feed, relevance, noise, and duplication checks.
