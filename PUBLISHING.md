# Publishing Workflow

News Dispatch follows a public-safe editorial workflow.

The repository is not a place for private drafts. Every committed file must be safe for public disclosure.

## Workflow

```text
PUBLIC_SAFE_DRAFT
-> FACT_CHECK
-> PRIVACY_CHECK
-> EDITORIAL_REVIEW
-> PUBLISHABLE
-> ARCHIVED
```

## Rules

1. Drafts committed to Git must already be public-safe.
2. Private calibration, raw notes, internal analysis, sensitive project context, and unredacted materials stay outside the repository.
3. No dispatch is publishable until the privacy checklist is complete.
4. All high-review streams require strict publication review.
5. Commit messages must be public-safe.
6. File names and branch names must be public-safe.

## Minimal publication checklist

Before marking a dispatch as `publishable`:

- [ ] Front matter exists.
- [ ] `publication_scope: "public"` is present.
- [ ] `private_context_used: false` is present.
- [ ] `contains_personal_data: false` is present.
- [ ] `contains_internal_company_data: false` is present.
- [ ] `contains_confidential_strategy: false` is present.
- [ ] `contains_nonpublic_sources: false` is present.
- [ ] Material claims have public sources.
- [ ] Community sentiment is separated from facts.
- [ ] No investment, legal, tax, or compliance advice is presented as instruction.
- [ ] No operational evasion guidance is present.
- [ ] Images have no sensitive metadata or private UI.
- [ ] The piece remains useful without knowing private context.

## Public-safe commit examples

Good:

```text
docs: add digital assets infrastructure stream policy
templates: add public-safe dispatch template
dispatch: add daily public-source brief 2026-06-03
```

Avoid:

```text
notes: add our product strategy
digest: add vendor shortlist for internal review
work: update roadmap implications
```

## Publishing targets

Possible future targets:

- GitHub Pages;
- static export;
- Home Lab mirror;
- email summary;
- Telegram summary via external automation.

Only `PUBLISHABLE` content may be exported to any public or semi-public channel.
