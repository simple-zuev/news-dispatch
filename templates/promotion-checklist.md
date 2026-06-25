# Promotion checklist

Use this checklist before moving any candidate artifact from `validation/` into `dispatches/`.

## Source boundary

- [ ] The item was produced from public sources only.
- [ ] No private context, internal company data, client data or confidential strategy is present.
- [ ] All key factual claims have source references.
- [ ] Primary sources are used for regulation, finance, crypto, security and legal-status claims when available.

## Editorial boundary

- [ ] The draft separates fact, trend, assessment, hypothesis and weak signal.
- [ ] Rumors, leaks, social posts or forum claims are explicitly marked as weak or unconfirmed signals.
- [ ] The draft includes uncertainty and follow-up checks.
- [ ] The draft is analytical, not an RSS recap or link list.

## Publication boundary

- [ ] Candidate/pre-publication language has been removed.
- [ ] The file is no longer a generated validation artifact.
- [ ] Front matter uses the correct stream and publication status.
- [ ] `contains_investment_advice` is false.
- [ ] `private_context_used` is false.
- [ ] `public_safe` is true.

## Final gate

- [ ] `tools/validate_published.py` passes.
- [ ] The issue is ready for reader-facing publication.
