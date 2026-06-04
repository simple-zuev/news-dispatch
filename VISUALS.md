# Visual Materials Model

News Dispatch uses visual materials only when they help understanding.

Visuals are not decoration. Every chart, diagram, image, video or material card must explain, compare, verify, or deepen the story.

## Visual types

- chart: numeric comparison, trend, ranking, share, distribution.
- diagram: process, system, flow, architecture, relationship.
- image: object, interface, device, place, product or material reference.
- video: review, presentation, interview, demonstration, lecture.
- material: official page, PDF, research paper, dataset, specification, documentation.

## Required fields

Every visual item needs:

- id
- type
- title
- reason
- alt
- source
- source_url
- rights

## Rights policy

Allowed rights values:

- own
- official
- generated
- external-link-only

Do not copy unknown images into the repository.

If rights are unclear, use a link card instead of embedding the image.

## Reader-facing rule

Public pages should show visual materials as clear editorial cards:

- type label;
- title;
- short reason;
- source;
- link.

Raw URLs should not be used as visible body text.

## First implementation stage

The first implementation should support:

1. source cards;
2. media cards;
3. visual cards;
4. local generated SVG charts and diagrams;
5. validation that every visual has title, reason, source and alt text.

## Editorial rule

A visual is included only if it answers one of these questions:

- What changed?
- How does it work?
- How large is the effect?
- What should be compared?
- What is the evidence?
- What should the reader inspect directly?
