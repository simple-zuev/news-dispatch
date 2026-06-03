# GitHub Pages Setup

News Dispatch supports two preview modes.

## Mode A — local artifact preview

Use this while the repository remains private.

1. Open `Actions`.
2. Open the latest successful `Validate News Dispatch` run.
3. Download the `news-dispatch-site` artifact.
4. Unzip it locally.
5. Open `index.html` or `dispatches.html`.

This mode does not publish the site.

## Mode B — GitHub Pages

GitHub Pages support depends on repository visibility and account plan.

For GitHub Free, Pages is available for public repositories. Private repositories require a plan that supports Pages for private repositories.

To publish with GitHub Pages:

1. Confirm the repository is suitable for public publication.
2. Open `Settings -> Pages`.
3. Set `Source` to `GitHub Actions`.
4. Run `Actions -> Deploy News Dispatch Pages -> Run workflow`.

Expected project URL:

```text
https://simple-zuev.github.io/news-dispatch/
```

## Recommendation

Keep using artifact preview until visual design, stream structure, and publication rules are stable. Enable GitHub Pages only after that checkpoint.
