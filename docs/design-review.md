# Design Review and Roadmap

News Dispatch should look like a serious editorial product, not a generated documentation site.

## Current assessment

The current visual direction is promising:

- strong editorial masthead;
- calm paper-like background;
- serif-led identity;
- minimal dependencies;
- no trackers or external fonts;
- good fit for long-form analytical dispatches.

The current weak points:

- navigation is still too primitive;
- buttons need a cleaner system of primary and secondary actions;
- cards need stronger hierarchy and better metadata treatment;
- stream pages need editorial identity, not only lists;
- article pages need reading aids: lead block, source block, section rhythm, and signal cards;
- mobile typography needs continued testing;
- sample content should eventually be separated from real issues or clearly labeled.

## Button system

Use three levels:

1. Primary action: main navigation target, filled button.
2. Secondary actions: outline buttons.
3. Text links: inline reading/navigation.

Rules:

- button groups must use flex layout with `gap`;
- buttons must wrap cleanly on mobile;
- only one primary action per hero block;
- avoid multiple equally black buttons unless the actions are equally important.

## Editorial layout direction

Preferred direction:

- magazine-like homepage;
- latest issue emphasis;
- stream index below the latest issue;
- compact dispatch archive;
- article pages with wide hero and narrow readable body;
- metadata and source confidence displayed as editorial labels, not raw YAML fields.

## Article page improvements

Next iterations should add:

- issue panel component;
- signal cards;
- source map;
- confidence labels;
- fact / inference / community / weak-signal badges;
- data gaps block;
- misread-risk block;
- related dispatches;
- previous / next navigation.

## Homepage improvements

Next iterations should add:

- featured dispatch block;
- latest dispatches grid;
- stream navigation;
- short editorial standard statement;
- RSS and archive links in a quieter utility zone;
- no overexposure of publication-boundary language on the first screen.

## Visual references by principle

Do not copy specific brands. Use principles from strong editorial products:

- strong typographic contrast;
- controlled whitespace;
- restrained color palette;
- section rhythm;
- sharp metadata hierarchy;
- card systems with clear scan paths;
- reader-first long-form typography.

## Language rule

Public-facing UI is Russian-first.

English is allowed for:

- project name;
- URLs;
- technical terms;
- RSS / OpenGraph / front matter;
- source and product names.

## Privacy and publication rule

Never make the design imply private personalization.

The product can be calibrated by private interests outside the repository, but the public site must read as independent editorial analysis.
