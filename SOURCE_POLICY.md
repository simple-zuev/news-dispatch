# Source Policy

News Dispatch uses public sources only.

Private documents, closed chats, internal notes, confidential conversations, private dashboards, internal repositories, private spreadsheets, and non-public operational data must not be used as cited sources in publishable dispatches.

Machine-readable source governance lives in `data/source_rules.json` and is validated by `tools/validate_source_rules.py` in CI. This document is the human-readable policy layer; the JSON file is the structured rule layer used by tooling.

## Source classes

| Class | Source type | Use |
|---|---|---|
| A | Regulator, law, official document, primary company source | Fact base |
| B | Reliable business or technology media | Context and corroboration |
| C | Industry media, expert reports, analyst notes | Interpretation |
| D | Public tender, hiring signal, patent, GitHub, public on-chain data | Early signal |
| E | Social media, Telegram, forums, Reddit, comments | Sentiment or weak signal only |
| M | Vendor marketing, landing pages, sponsored materials | Claim to verify, not proof |

## Source governance rules

Source sufficiency depends on stream, claim type and publication mode.

Strict streams — currently `finance` and `crypto-finance` — require stronger evidence for high-impact claims. For these streams, high-impact conclusions should normally have a primary source or official record plus independent corroboration. If this is not available, the issue should stay `draft_only`, be marked `limited_publication`, or avoid the strong claim.

AI, technology, hardware, research and science streams must distinguish release, research result, benchmark, vendor claim and editorial inference. A vendor release is not independent validation. A lab or research signal is not commercial availability. A media-reported accusation is not an established incident unless supported by primary material or independent confirmation.

Consumer, gear, city and community-oriented material must distinguish practical listing facts, user experience, availability, repeated defect patterns and subjective preference. Isolated complaints should not become broad conclusions.

## Required distinction

Every important claim should be marked or written so that the reader can distinguish:

- fact;
- release;
- research;
- review;
- benchmark;
- user review;
- community signal;
- rumor;
- forecast;
- marketing claim;
- editorial inference.

## Community evidence

Community evidence is valuable but must not be presented as fact.

Classify it as:

- isolated complaint;
- repeated defect pattern;
- software or firmware regression;
- compatibility issue;
- bad batch signal;
- long-term ownership signal;
- subjective preference;
- local market availability issue.

Only repeated and mechanism-consistent patterns should affect a dispatch position.

## Research sources

For scientific and technical research, state whether the work is:

- peer-reviewed;
- preprint;
- corporate lab report;
- benchmark report;
- survey;
- unknown.

If the status is unclear, mark confidence as `medium` or lower.

## Financial and regulated topics

For finance, regulation, crypto, digital assets, sanctions, AML/CFT, taxation, legal, security, and compliance-sensitive topics:

- use primary sources when possible;
- separate facts from legal or editorial inference;
- avoid operational instructions;
- avoid investment, legal, tax, compliance, or evasion advice;
- include data gaps and limitations.

## Source sufficiency

High-impact claims should ideally have:

1. One primary source or official record.
2. One independent secondary source.
3. Clear confidence level.
4. Statement of what remains unverified.

If this is not possible, label the claim as hypothesis, weak signal, or editorial inference.
