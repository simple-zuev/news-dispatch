# News Dispatch

**News Dispatch** is a privacy-first editorial workspace for multi-domain analytical dispatches.

It is designed for anonymized, publishable briefings across technology, product, finance, culture, gear, home, science, cities, creative tools, and adjacent domains.

## Core idea

News Dispatch is not a personal diary, not a raw notes dump, and not a private inventory.

It is an editorial system for turning external signals into structured analytical dispatches:

```text
signal -> verification -> context -> mechanism -> second-order effects -> decision criteria -> what would change the view -> new knowledge
```

## Privacy model

Personal context may influence topic selection and relevance, but it must not appear as personal disclosure.

Do not publish:

- private names, contacts, phones, emails, addresses;
- IP addresses, tokens, keys, internal URLs, secrets;
- personal inventories, expenses, exact home/work infrastructure details;
- raw notes copied from private documents;
- sensitive operational context.

Use neutral editorial framing instead:

- `for a technically advanced reader`;
- `for a hybrid work setup`;
- `for urban everyday use`;
- `for a privacy-conscious home environment`;
- `for a product decision-maker`.

## Repository structure

```text
news-dispatch/
  README.md
  PRIVACY.md
  EDITORIAL_STANDARD.md
  SOURCE_POLICY.md
  STYLE_GUIDE.md
  PUBLISHING.md
  SECURITY.md

  streams/
    README.md

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

- Technology & digital systems
- Work & product intelligence
- Finance & consumer economics
- Home, environment & infrastructure
- Gear, carry & material culture
- City, culture & media
- Audio, DJ & creative technology
- Horizon notes: science, systems, futures

## Status

Initial private Git MVP scaffold.

Next steps:

1. Add first anonymized dispatch template instance.
2. Run privacy check before any publishing.
3. Decide whether the public layer will be GitHub Pages, static export, or Home Lab mirror.
