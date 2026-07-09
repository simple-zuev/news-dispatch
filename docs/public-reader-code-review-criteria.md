# Public Reader Code Review Criteria

Public reader changes must be reviewed as product architecture, not only as passing CI.

Required checks:

- source filtering happens before reader policy and rendering;
- preview and production Pages run content quality validation;
- generated site and validation artifacts are not committed;
- public pages do not expose diagnostic fields, comment-feed URLs, raw timestamps, ranking scores, or source-rule internals;
- PR preview artifacts are inspected before merge;
- production Pages is checked after deploy when the change affects reader output.

When a live defect is found, prefer fixing the source or rendering contract instead of masking bad output in generated HTML.
