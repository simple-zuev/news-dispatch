# Privacy Policy for News Dispatch

News Dispatch is designed as an anonymized editorial system.

The project may be personally calibrated, but published content must not expose private context.

## Non-negotiable rule

Personalization belongs in selection, weighting, and framing — not in public disclosure.

A reader should understand the material as a professional analytical publication, not as a map of a private person's assets, home, work, habits, finances, infrastructure, or relationships.

## Prohibited content

Do not commit or publish:

- personal addresses;
- phone numbers;
- private email addresses unless explicitly public and necessary;
- private names of friends, family, colleagues, contractors, or contacts;
- exact financial balances, expenses, subscriptions, account data;
- private inventory lists;
- home infrastructure topology, raw IP addresses, VPN details, internal domains, hostnames;
- API tokens, passwords, SSH keys, OAuth secrets, cookies;
- screenshots containing private UI, accounts, chats, maps, locations, transaction data;
- EXIF metadata from personal photos;
- private Google Drive, Gmail, Calendar, GitHub, Home Lab, or device data;
- medical, intimate, legal, employment, or identity-sensitive details.

## Safe public framing

Unsafe:

> The user owns X, uses Y, has Z in the table, and spends N.

Safe:

> For a technically advanced reader with a hybrid digital workflow, this signal matters because...

Unsafe:

> In the user's Home Lab at [host/IP], the service should...

Safe:

> For privacy-conscious local infrastructure, the safer pattern is...

Unsafe:

> The user's current purchase list contains...

Safe:

> For consumer hardware evaluation, the relevant criteria are scenario fit, long-term ownership data, repairability, and total cost of ownership.

## Privacy gate before publication

Before content is considered publishable, it must pass:

1. Personal identifier scan.
2. Secrets and token scan.
3. Infrastructure detail scan.
4. Finance and purchase specificity scan.
5. Work/project confidentiality scan.
6. Metadata and image safety check.
7. Editorial anonymization review.

## Public vs private layers

The repository may contain editorial scaffolding, templates, and anonymized drafts.

If a public site is created later, the public layer must include only:

- anonymized dispatches;
- public sources;
- generated visual cards without sensitive metadata;
- editorial taxonomies;
- non-sensitive style and layout files.

Private source notes, personalization filters, raw prompts, private documents, and operational context must remain outside any public branch or public mirror.

## Redaction principle

When in doubt, remove the specific detail and keep the abstract pattern.

Specific detail is rarely necessary for a useful public analytical dispatch.
