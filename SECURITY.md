# Security Policy

News Dispatch treats the repository as public-by-default.

Security here means both technical secret safety and editorial safety.

## Never commit

- API keys;
- tokens;
- passwords;
- private keys;
- cookies;
- OAuth secrets;
- credentials;
- internal URLs;
- IP addresses;
- hostnames of private infrastructure;
- screenshots with private UI;
- raw exported private files;
- personal data;
- internal work or product context;
- non-public partner, vendor, contractor, client, or counterparty information.

## Sensitive topics

Extra care is required for:

- digital assets;
- finance;
- regulation;
- sanctions;
- AML/CFT;
- KYC/KYB;
- cybersecurity;
- infrastructure;
- legal and compliance topics;
- company and product strategy;
- vendor and partner evaluation.

Do not publish operational instructions that enable evasion of regulation, sanctions, AML/KYC controls, security systems, platform restrictions, or fraud detection.

## Commit hygiene

Commit messages, branch names, issue titles, PR bodies, comments, and deleted files are part of the disclosure surface.

They must be public-safe.

## Images

Before committing images:

- remove EXIF and metadata;
- check for private UI, accounts, chats, maps, locations, dashboards, file IDs, QR codes;
- prefer generated diagrams and analytical cards over screenshots;
- use public images only with source attribution and within a clear analytical context.

## Incident response

If sensitive information is committed:

1. Stop publishing immediately.
2. Do not assume deletion is enough.
3. Rotate exposed credentials if applicable.
4. Treat Git history as potentially exposed.
5. Document the incident in a private channel, not in this repository if it contains sensitive details.
6. Rebuild public-safe content from clean sources.
