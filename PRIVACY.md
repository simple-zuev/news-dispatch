# Privacy Policy for News Dispatch

News Dispatch is a public-safe editorial system.

The repository may be private during development, but every committed byte must be treated as potentially public.

## Non-negotiable rule

Personalization belongs in selection, weighting, and editorial judgment — not in disclosure.

A reader should understand each dispatch as independent professional analysis, not as a map of a private person's assets, workplace, projects, finances, infrastructure, habits, or relationships.

## Public-by-default repository rule

Do not commit sensitive material and plan to redact it later.

Git history can preserve removed content. Branch names, commit messages, issues, pull requests, comments, deleted files, and metadata can also disclose context.

If it cannot be published, it must stay outside the repository.

## Prohibited content

Do not commit or publish:

- personal addresses;
- phone numbers;
- private email addresses;
- private names of friends, family, colleagues, contractors, clients, partners, or contacts;
- exact financial balances, expenses, account data, or private purchase inventories;
- private work, product, roadmap, metric, strategy, legal, compliance, commercial, or security context;
- private vendor, partner, contractor, or counterparty evaluations;
- home infrastructure topology, raw IP addresses, VPN details, internal domains, hostnames, private URLs;
- API tokens, passwords, SSH keys, OAuth secrets, cookies, credentials;
- screenshots containing private UI, accounts, chats, maps, locations, transaction data;
- EXIF metadata from personal photos;
- private Google Drive, Gmail, Calendar, GitHub, Home Lab, or device data;
- medical, intimate, legal, employment, or identity-sensitive details;
- raw prompts or private notes that reveal targeting logic.

## Neutral analytical framing

Do not identify the intended beneficiary of a conclusion.

Avoid:

- for our product;
- for our company;
- for our team;
- for teams building X;
- for operators of Y;
- for product teams in category Z;
- because the user has X;
- because the user's table says Y.

Use neutral analytical conclusions:

- the signal may indicate;
- the likely implication is;
- the observable mechanism is;
- pressure may increase around;
- the hypothesis should be tested against;
- the position changes if;
- a public evaluation criterion is.

## Privacy gate before publication

Before content is considered publishable, it must pass:

1. Personal identifier scan.
2. Secrets and token scan.
3. Infrastructure detail scan.
4. Finance and purchase specificity scan.
5. Work and project confidentiality scan.
6. Partner, contractor, vendor, and counterparty disclosure scan.
7. Metadata and image safety check.
8. Editorial anonymization review.
9. Commit message and file path review.

## Public-safe content

The repository may contain:

- anonymized dispatches;
- public source summaries;
- source policies;
- editorial standards;
- templates;
- taxonomies;
- non-sensitive style and layout files;
- generated visual assets without sensitive metadata.

Private source notes, personalization filters, raw prompts, private documents, and operational context must remain outside the repository.

## Redaction principle

When in doubt, remove the specific detail and keep the abstract pattern.

Specific detail is rarely necessary for useful public analysis.
