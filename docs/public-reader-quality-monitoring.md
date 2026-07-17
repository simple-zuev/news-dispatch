# Public reader quality monitoring

The public reader keeps a bounded 14-day history and evaluates the latest seven days after each Pages build.

`tools/build_public_reader_quality_report.py` writes:

- `validation/public-reader-quality-latest.json` for automation;
- `validation/public-reader-quality-latest.md` for review in GitHub Actions.

The report tracks stream and independent-publisher diversity, duplicate-story share, source concentration, Russian reader-title coverage, and useful-summary coverage. It also compares configured publisher counts with the working target of eight independent sources per stream.

A new cache starts in `collecting` status until it spans seven calendar days. Advisory alerts do not block Pages deployment; existing freshness, privacy, reader-policy, and rendering gates remain responsible for fail-closed publication safety.

The Pages workflow uploads the report as the `public-reader-quality-report` artifact. Review it before expanding another source batch or changing ranking rules. New sources should be added in probation batches of no more than three and must pass live feed, relevance, noise, and duplication checks.
