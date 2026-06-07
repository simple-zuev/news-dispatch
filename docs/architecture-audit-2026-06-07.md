# Architecture Audit — 2026-06-07

## Scope

Audit target: topic-first News Dispatch architecture, Daily Radar automation, stream taxonomy, reader rendering pipeline and validation gates.

## Main findings

### 1. Stream definitions were duplicated

Before the refactor, stream definitions were spread across:

- `data/taxonomy.yml`;
- `tools/daily_radar.py`;
- `tools/apply_topic_streams.py`;
- `tools/validate_front_matter.py`;
- older render/enhance helpers.

This created drift risk: one tool could accept a stream while another rendered or validated a different set.

Resolution:

- Added `data/streams.json` as the shared stream registry.
- Added `tools/stream_registry.py` as the cached loader.
- Refactored `daily_radar.py`, `apply_topic_streams.py` and `validate_front_matter.py` to use the shared registry.
- Added `tools/validate_stream_registry.py`.

### 2. Mixed daily dispatch was the wrong default

The product should not mix finance, crypto, AI, hardware, EDC, Moscow, DJ/audio and science into one daily issue.

Resolution:

- Daily Radar now groups collected signals by stream.
- It writes topic dispatches under `dispatches/<stream>/`.
- Weak streams are downgraded to draft instead of being forced into a published issue.

### 3. Topic pages needed to be generated from the same taxonomy

The reader should expose topic shelves, not legacy abstract streams.

Resolution:

- `tools/apply_topic_streams.py` renders topic-first stream index and stream pages from `data/streams.json`.
- It updates homepage stream cards and sitemap entries.

### 4. Registry validation was missing

Changing feeds or streams could break automation silently.

Resolution:

- `tools/validate_stream_registry.py` validates stream registry structure, duplicate stream slugs, legacy mappings and feed stream mappings.
- Validate and Pages workflows now run registry checks before rendering.
- Daily Radar workflow runs registry checks before collecting feeds.

### 5. Reader output validation remains necessary

Even if Markdown is valid, generated HTML can lose reader map, section cards or media/source cards.

Resolution:

- `tools/validate_reader_output.py` remains in the build chain after render/enhance/postprocess.

## Current optimized pipeline

```text
streams.json / feeds.json
        ↓
validate_stream_registry.py
        ↓
daily_radar.py or manual dispatch
        ↓
validate_front_matter.py
        ↓
validate_published.py
        ↓
render_site.py
        ↓
enhance_site.py
        ↓
apply_topic_streams.py
        ↓
apply_media_previews.py
        ↓
apply_reader_sections.py
        ↓
validate_reader_output.py
        ↓
privacy_scan.py
        ↓
GitHub Pages
```

## Performance notes

The site is static and small. The expensive parts are network feed fetching and repeated HTML post-processing. Current optimizations:

- stream registry is cached with `lru_cache`;
- feed deduplication is hash-based;
- state file caps stored keys;
- stream pages are generated in one pass over dispatch metadata;
- no database, CMS, server runtime or client-side hydration is required.

Acceptable remaining inefficiency:

- `render_site.py` and `enhance_site.py` still have legacy stream assumptions in the base render layer. The topic postprocessor corrects the public reader pages and sitemap. This is safe, but future cleanup should move base rendering fully to `data/streams.json`.

## Next refactor candidates

1. Replace legacy stream constants in `render_site.py` with `stream_registry.py`.
2. Replace legacy stream constants in `enhance_site.py` with `stream_registry.py` directly.
3. Add stream-specific generated body templates for Daily Radar, starting with crypto-finance and finance.
4. Add validation for stream-specific forbidden language:
   - finance / crypto: no investment advice;
   - gear / Moscow: no hidden promotion;
   - science: distinguish paper / preprint / media retelling;
   - AI: distinguish demo / benchmark / shipped feature.
5. Add a source-health report for noisy or broken feeds.

## Operational conclusion

The architecture is now good enough for a usable MVP:

- separate topic digests;
- shared stream registry;
- feed registry validation;
- reader page validation;
- static deployment through GitHub Pages.

Further work should focus on source quality, stream-specific templates and live workflow runs, not on changing the fundamental architecture.
