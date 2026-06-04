# Content Operating Model

News Dispatch does not use a CMS or admin panel.

The operating model is content-as-code:

- GitHub is the source of truth.
- GPT acts as editor, researcher, production operator and release assistant.
- Markdown, MDX, data files and visual specifications are the editable content layer.
- GitHub Actions validate, build and publish the site.
- GitHub Pages serves the reader-facing site.

## Why no CMS

A CMS would add a separate interface, user roles, database state, migrations, plugin risk and manual content operations.

News Dispatch should remain simple, reproducible and AI-operable:

```text
research -> draft -> editorial review -> validation -> commit -> build -> publish
```

## Source of truth

All publishable content lives in the repository:

```text
content / dispatches / sources / media / visuals / data
```

Drafts may exist in the repository, but they must not be published unless they pass the publication gate.

## Publication gate

Only content with this status may appear on the public site:

```yaml
status: "published"
public_safe: true
publication_scope: "public"
```

Everything else is treated as non-public output:

```yaml
status: "draft"
status: "review"
status: "sample"
status: "archived"
```

## AI role

GPT may:

- create and edit dispatches;
- add sources and media cards;
- prepare charts and diagrams from structured data;
- update templates;
- run validation through GitHub Actions;
- publish by changing status to `published` after checks pass.

GPT must not:

- bypass publication gates;
- publish drafts as finished materials;
- expose private context;
- add unsourced claims;
- add media without rights and source metadata;
- treat raw URLs as reader-facing source blocks.

## Target architecture

Current implementation may use a lightweight static renderer.

The preferred future architecture is:

```text
Astro + MDX + content collections + GitHub Actions + GitHub Pages
```

No CMS is planned.

## Visual layer

Charts, diagrams, images, videos and materials are controlled by metadata, not by manual page editing.

Each visual item must have:

- type;
- title;
- reason;
- source;
- source URL;
- rights status;
- alt text.

Visuals are included only when they help understanding.
