# Contributing to News Dispatch

News Dispatch is a public-safe editorial radar. Contributions must preserve both technical correctness and editorial safety.

## Core principle

Everything in this repository is public by default.

Before opening a pull request, assume that the following will be visible forever:

- code;
- generated files;
- deleted files;
- commit messages;
- branch names;
- pull request titles and descriptions;
- review comments;
- issue text;
- file names and metadata.

Do not include private, internal, client, vendor, partner, security, compliance, roadmap, metric, credential, personal, medical, account or employment-sensitive information.

## Contribution scope

Good contributions improve one of these layers:

- public source collection;
- source-health and validation logic;
- signal filtering;
- dispatch synthesis;
- editorial quality gates;
- static site rendering;
- reader experience;
- documentation and runbooks;
- privacy and public-safety scanning.

Do not turn the project into:

- a private research notebook;
- an internal company memo system;
- a trading or investment recommendation tool;
- a legal, tax or compliance advice generator;
- a raw RSS mirror;
- a rumor feed.

## Development setup

The toolchain currently uses Python standard-library modules at runtime.

```bash
python --version
python -m pip install -r requirements.txt
python -m py_compile tools/*.py
```

Run the core validation steps before opening a PR:

```bash
python tools/validate_front_matter.py
python tools/validate_published.py
python tools/render_site.py
python tools/enhance_site.py
python tools/validate_reader_output.py
python tools/privacy_scan.py
```

For Daily Radar work, use:

```bash
python tools/run_daily_radar_safe.py
```

For draft synthesis from existing signals, use:

```bash
python tools/synthesize_dispatch.py --from-radar validation/daily-radar-latest.json --status draft --dry-run
```

## Branch and PR rules

Use a short, neutral branch name. Avoid branch names that include private context, sensitive project names, customer names, incidents or speculative claims.

Preferred PR shape:

```text
Summary:
- what changed
- why it changed
- what was intentionally left unchanged

Validation:
- commands run
- expected artifacts
- known limitations

Publication boundary:
- public sources only
- no private context
- no investment/legal advice
```

Open small PRs. Do not combine source changes, renderer changes, workflow changes and content publication in one large pull request unless the coupling is unavoidable.

## Editorial rules

Every analytical dispatch must distinguish:

- fact;
- source-reported claim;
- verified primary-source statement;
- editorial assessment;
- hypothesis;
- rumor or weak signal;
- marketing language;
- forecast.

Use primary sources for high-impact topics whenever possible: regulators, courts, official company releases, exchange notices, public filings, technical repositories or research papers.

For finance, crypto-finance, regulation, sanctions, taxation, AML/CFT, cybersecurity and compliance:

- avoid investment advice;
- avoid legal, tax or compliance advice;
- avoid price forecasts as fact;
- mark uncertain claims explicitly;
- use promotion checklists before publication.

## Front matter requirements

Dispatch files under `dispatches/` must include strict public-safety front matter. At minimum, keep these fields accurate:

```yaml
status: "draft"
publication_scope: "public"
public_safe: true
private_context_used: false
contains_personal_data: false
contains_internal_company_data: false
contains_confidential_strategy: false
contains_nonpublic_sources: false
contains_investment_advice: false
contains_legal_advice: false
source_mode: "public_sources_only"
```

Only `status: "published"` dispatches are exposed on the public site.

## Signal files

Signal files under `signals/YYYY-MM-DD/<stream>/` are not finished articles. They confirm that something appeared in a public source. They do not, by themselves, prove:

- full context;
- impact;
- legal effect;
- market effect;
- technical correctness;
- causality.

A dispatch may use signal files only after editorial grouping and source review.

## Promotion checklist

Before moving a draft toward publication, create or update a checklist under:

```text
validation/promotion-checklists/
```

The checklist should state one of:

```text
blocked from publication
limited publication approved
published review passed
```

A blocked checklist is a valid outcome. Do not publish weakly verified items merely to keep cadence.

## Static site rules

Renderer and site changes must preserve these invariants:

- drafts are not exposed as published dispatches;
- signal files are not reader-facing articles;
- candidate artifacts are not reader-facing articles;
- private or pre-publication labels must not leak into published pages;
- empty media/source arrays must not render broken cards.

## Workflow rules

Workflow changes are high-risk. Keep them minimal and explain:

- trigger changes;
- permissions changes;
- write paths;
- generated artifacts;
- whether the workflow can commit to `main`;
- whether it can publish to GitHub Pages.

Daily Radar may write signal and validation artifacts. It must not automatically publish analytical conclusions.

## Content safety checklist

Before merging content, verify:

- public sources only;
- source classes are marked correctly;
- facts, assessments, hypotheses and rumors are separated;
- no investment advice;
- no legal advice;
- no private context;
- no internal team/company/product language;
- no raw sensitive data;
- correct stream/category;
- promotion checklist exists for publication decisions.

## Code style

Use modern Python with type hints where useful. Prefer small functions, explicit data structures and predictable file writes.

Do not add third-party dependencies unless they are genuinely needed at runtime. If a dependency is added, update `requirements.txt` and document why it is needed.

Keep the code dependency-light: GitHub Actions should be able to run validators quickly and deterministically.

## Review expectations

A reviewer should be able to answer:

- What public problem does this change solve?
- What files can it write?
- Does it change publication behavior?
- Could it expose drafts, private context or candidate artifacts?
- Does it preserve existing validation and Pages behavior?
- What manual checks remain?

If any answer is unclear, the PR should stay open.
