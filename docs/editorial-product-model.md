# Editorial Product Model

News Dispatch is an AI-operated editorial briefing product.

It is not a CMS, not an admin panel, and not an internal dashboard.

The reader-facing product is a set of separate editorial dispatches, each with its own scope, tone, source model and publication rules.

## Core reader need

The product exists to make it comfortable to understand what is happening:

- in technology;
- in AI;
- in hardware and consumer electronics;
- in apps and platforms;
- in finance and consumer economics;
- in Russia;
- in Moscow;
- in work-relevant markets;
- in digital assets infrastructure;
- in gear, EDC, watches, bags and material culture;
- in science, research and broader intellectual context;
- in communities, forums, social networks, comments and unofficial channels.

The output should feel like a serious technology and culture publication calibrated to a specific reader profile, while remaining safe for public publication.

## Dispatch separation

Do not merge all interests into one giant daily text.

Use separate dispatches:

1. General Dispatch
   - world, Russia, Moscow, technology, AI, hardware, apps, consumer electronics, culture, science, media and broader context.

2. Work Dispatch
   - public external intelligence on markets, products, competitors, regulation, vendors, tools, UX, organizational patterns and technology shifts.
   - It may be calibrated by private context outside the repository, but must not disclose that context.

3. Digital Assets Infrastructure Dispatch
   - regulation, restrictions, market structure, infrastructure, custody, compliance, security, public competitors, vendors and integrations.

4. Gear & Material Culture Dispatch
   - EDC, bags, watches, tools, office gear, consumer devices, audio, materials, ownership, service, repairability and buying criteria.

5. Finance Dispatch
   - rates, banking products, consumer economics, subscriptions, liquidity, household costs, large purchases and financial environment.

6. Horizon Dispatch
   - science, research, systems thinking, materials, robotics, biotech, cognition, HCI, energy and future signals.

## Public-safe personalization

Private context may influence:

- topic selection;
- prioritization;
- what is considered important;
- what gets ignored;
- what gets monitored over time;
- examples chosen for explanation.

Private context must not appear in the public text.

Do not publish:

- our product;
- our company;
- our team;
- internal roadmap;
- internal metrics;
- internal partners;
- private vendor assessments;
- private documents;
- private infrastructure;
- private personal context.

Use neutral editorial framing.

## No advertising policy

News Dispatch must not contain advertising, affiliate-driven placement, paid promotion, hidden sponsorship, or unsupported recommendations.

Recommendations are allowed only as editorial assessments when they are:

- evidence-based;
- clearly reasoned;
- source-backed;
- scenario-specific;
- free from commercial incentive.

Do not recommend a product, service or vendor just because it is new, popular or commercially attractive.

Do not write promotional copy.

## Rumors and opinions

Unverified information is allowed only in a separate section.

Use the section title:

```text
Слухи и мнения
```

This section may include signals from:

- communities;
- forums;
- comments;
- Telegram channels;
- Reddit;
- social networks;
- messengers;
- public chats;
- YouTube comments;
- marketplace reviews;
- rumor-driven media.

Rules:

- clearly mark it as unverified;
- never present rumor as fact;
- describe why it matters;
- show confidence level;
- separate repeated patterns from isolated claims;
- avoid defamatory or personal claims;
- do not publish private chat content.

## Public opinion layer

Use the section title:

```text
Мнение людей
```

This is a synthesized view of public reaction.

It should answer:

- what people seem to like;
- what annoys people;
- what fears repeat;
- what trade-offs people discuss;
- whether sentiment is broad or niche;
- what is still anecdotal.

Do not overstate consensus.

Use formulations such as:

- "в обсуждениях повторяется";
- "часть пользователей считает";
- "заметный мотив в комментариях";
- "это пока слабый сигнал";
- "нет достаточных данных для вывода".

## Tone

Target tone:

- Russian-first;
- alive and technological;
- closer to The Verge / Wired than to a corporate report;
- analytical but readable;
- no bureaucratic phrasing;
- no internal system language;
- no raw technical scaffolding in public text.

## Reader-facing issue structure

A strong dispatch should include:

1. Title.
2. Lead.
3. Main points.
4. What happened.
5. Why it matters.
6. Analysis.
7. Rumors and opinions.
8. Public opinion.
9. Media and materials.
10. Sources.
11. What to watch next.

## Publication rule

Only this status is publishable:

```yaml
status: "published"
```

Draft, review and sample materials must not appear on the public site.
