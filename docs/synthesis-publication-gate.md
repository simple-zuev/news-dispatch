# Synthesis publication gate

This document defines the editorial gate between generated Daily Radar artifacts and published dispatches.

## Core boundary

A signal is not a dispatch.

A signal confirms that a public source item appeared in a configured feed. It does not confirm context, impact, causality, completeness, market effect, regulatory consequence or editorial interpretation.

`validation/candidate-dispatch-latest.md` and `validation/auto-dispatches/` are source workspaces. They must not be copied, moved or automatically promoted into `dispatches/` as-is.

Daily Radar generation, review artifacts and draft-only auto-dispatch files are not publication approval by themselves.

Autonomous digests may be reader-visible through `site/today.html`, or stored in `dispatches/` only when they pass machine safety/source/quality gates. Human approval is not required for routine autonomous daily publication.

## Required synthesis frame

Before a candidate can become a published dispatch, each material analytical item must include:

- fact;
- source;
- why it matters;
- affected actors;
- possible effect;
- uncertainty;
- what to monitor next.

The preferred editorial form is: Thesis -> Argument -> Consequence/Risk.

## Claim separation

The editor must separate fact, trend, assessment, hypothesis and unconfirmed signal.

Rumors, Telegram posts, forum claims, X/Twitter posts, anonymous comments and market chatter can be used only as unconfirmed weak signals. They must not be presented as confirmed facts.

For finance, crypto-finance, regulation, sanctions, legal, AML/CFT, taxation, security and compliance-sensitive topics, high-impact claims require a primary source or an explicit limitation.

## Publication checklist

Before promotion to `dispatches/`, check:

- stream/category is valid;
- source governance is available;
- privacy scan has no blockers;
- no sensitive work, client, partner, employee, strategy, metric, security or compliance details are included;
- no investment advice, trade recommendation or price forecast is presented as fact;
- facts, trends, assessments, hypotheses and unconfirmed signals are separated;
- uncertainties and verification gaps are explicit;
- monitoring signals are listed;
- front matter follows the dispatch contract;
- publication validation passes.

## Autonomous daily rule

The desired operating model is zero-touch daily reading:

- no daily human approval gate;
- no manual publish decision for routine autonomous daily digest;
- weak or unverified items are labelled, downgraded, withheld or kept operational-only;
- failed gates produce a safe Today fallback that says `digest withheld by automated gate` and lists reasons.

An autonomous digest must show verification gaps and keep source-reported claims separate from confirmed facts.

## Promotion rule

Manual promotion from `validation/auto-dispatches/` or `validation/candidate-dispatch-latest.md` into `dispatches/` remains a separate editorial action. Autonomous publication is allowed only for a newly generated digest that carries machine-gate metadata and passes validation; it is not a raw copy of a draft workspace file.
