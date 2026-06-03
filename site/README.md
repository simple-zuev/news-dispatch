# News Dispatch Site

Static site layer for News Dispatch.

The site must render only public-safe dispatches.

## Principles

- No private data.
- No tracking scripts by default.
- No external fonts by default.
- No analytics by default.
- No embedded private images.
- No client-side dependencies unless explicitly reviewed.
- All content should remain readable as plain HTML and Markdown.

## Initial approach

Start with a small static site:

```text
site/
  index.html
  styles/main.css
```

Later options:

- GitHub Pages;
- static export;
- Home Lab mirror;
- Cloudflare Pages or another static host;
- generated pages from Markdown dispatches.

## Visual direction

The design should feel like a mature editorial briefing product:

- strong typography;
- calm layout;
- clear cards;
- source confidence labels;
- signal vs noise tables;
- decision criteria blocks;
- restrained color system;
- mobile-first reading.
