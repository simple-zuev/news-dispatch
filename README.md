# News Dispatch

**News Dispatch** is a public-safe editorial platform for multi-domain analytical dispatches.

It is designed for publishable, anonymized briefings across technology, product, finance, culture, gear, home, science, cities, creative tools, regulated markets, and adjacent domains.

## Core idea

News Dispatch is not a personal diary, not a raw notes dump, not a private inventory, and not a repository for internal drafts.

It is an editorial system for turning external signals into structured analytical dispatches:

```text
signal -> verification -> context -> mechanism -> second-order effects -> decision criteria -> what would change the view -> new knowledge
```

## Public-by-default rule

Everything committed to this repository must be safe for public disclosure.

This applies even when the repository is private.

Git history, branches, pull requests, issues, comments, file names, commit messages, and deleted files may become visible later. Therefore, private calibration, raw prompts, internal notes, sensitive work context, infrastructure details, personal inventories, and unpublished company or product information must stay outside this repository.

## Editorial anonymization

Personal or organizational context may influence topic selection, weighting, and editorial judgment, but it must not appear as personal or internal disclosure.

The text should not name the intended beneficiary of a conclusion.

Prefer neutral analytical language:

- the signal may indicate;
- the observable mechanism is;
- the likely implication is;
- pressure may increase around;
- the hypothesis should be tested against;
- the position changes if.

## Repository structure

```text
news-dispatch/
  README.md
  PUBLICATION_BOUNDARY.md
  PRIVACY.md
  EDITORIAL_STANDARD.md
  SOURCE_POLICY.md
  STYLE_GUIDE.md
  PUBLISHING.md
  SECURITY.md

  streams/
    README.md
    digital-assets-infrastructure/

  templates/
    dispatch.md
    privacy-check.md

  data/
    taxonomy.yml

  tools/
    privacy_scan.py

  site/
    README.md
```

## Editorial streams

News Dispatch can host multiple independent editorial streams:

- General multi-domain dispatches
- Work and product intelligence
- Finance and consumer economics
- Digital assets infrastructure
- Home, environment and infrastructure
- Gear, carry and material culture
- City, culture and media
- Audio, DJ and creative technology
- Horizon notes: science, systems, futures

## Status

Initial Git MVP scaffold.

Next steps:

1. Keep all repository content public-safe from the first draft.
2. Add missing policy and style files.
3. Add first anonymized dispatch template instance.
4. Run privacy check before any external publication.
5. Decide whether the public layer will be GitHub Pages, static export, or Home Lab mirror.
