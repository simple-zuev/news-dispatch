#!/usr/bin/env python3
"""Build an explainability report for Daily Radar source-rule ranking.

This tool is diagnostic. It does not write signal files and does not publish
reader-facing conclusions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
from datetime import date, datetime, timezone
from xml.etree import ElementTree as ET

import daily_radar
from core import ROOT, VALIDATION_DIR, clean_text, read_json, repo_path, write_json
from reader_text import build_reader_fields, clean_source_excerpt, public_items_same_story

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"

SOURCE_ROW_CAPS = {
    "openai-news": 20,
    "arxiv-cs-ai": 8,
    "google-security-blog": 16,
    "huggingface-blog": 12,
    "mskagency-transport": 16,
    "mskagency-culture": 12,
    "nature-news": 16,
    "science-news": 12,
    "field-mag-gear": 12,
    "core77-design": 12,
    "ria-moscow-city": 12,
    "big-city-moscow": 10,
}

RANKING_SELECTION_LIMIT = 18
RANKING_SELECTION_MIN_SCORE = 10.0
RANKING_SELECTION_STREAM_CAP = 4
RANKING_SELECTION_DEFAULT_SOURCE_CAP = 3
RANKING_SELECTION_DEFAULT_PUBLISHER_CAP = 3
RANKING_SELECTION_SOURCE_CAPS = {
    "openai-news": 2,
    "arxiv-cs-ai": 1,
    "google-security-blog": 2,
    "huggingface-blog": 1,
    "nature-news": 2,
    "science-news": 1,
    "quanta-magazine": 1,
    "field-mag-gear": 1,
    "tomshardware": 2,
    "science-daily": 1,
    "core77-design": 1,
    "ria-moscow-city": 1,
    "big-city-moscow": 1,
}
RANKING_SELECTION_PUBLISHER_CAPS = {
    "bank-of-canada": 1,
    "cftc": 2,
    "mskagency": 1,
}
WEAK_STREAM_MIN_RELEVANCE = {
    "gear-style-edc": 0.5,
    "moscow-city": 0.5,
    "dj-audio-creative": 0.5,
}
GENERAL_SPECIAL_USE_STREAM = "general"

PRODUCT_CARD_PATTERNS = (
    "official image",
    "official images",
    "where to buy",
    "now available",
    "colorway",
    "release date",
    "retail price",
)

EDC_RELEVANCE_TERMS = (
    "material",
    "design",
    "industry",
    "market",
    "supply",
    "repair",
    "sustainable",
    "technical apparel",
    "manufacturing",
    "collaboration",
)

HIGH_SIGNAL_CRYPTO_TERMS = (
    "mica",
    "stablecoin",
    "sec",
    "fca",
    "esma",
    "cftc",
    "enforcement",
    "market structure",
    "custody",
    "aml",
    "digital asset",
    "crypto-assets",
)

MARKET_FORECAST_TERMS = (
    "price target",
    "price targets",
    "forecast",
    "forecasts",
    "prediction",
    "predictions",
    "estimate",
    "estimates",
    "outlook",
    "12-month",
    "year-end",
    "slashes",
    "analyst",
    "strategist",
)

MARKET_IMPACT_TERMS = (
    "regulation",
    "regulatory",
    "rules",
    "enforcement",
    "lawsuit",
    "filing",
    "sec",
    "fca",
    "esma",
    "cftc",
    "mica",
    "stablecoin",
    "custody",
    "exchange",
    "liquidity",
    "etf",
    "infrastructure",
    "settlement",
    "clearing",
    "bank",
    "central bank",
)

CRYPTO_SELECTION_PRIORITY_TERMS = MARKET_IMPACT_TERMS + (
    "bank of england",
    "joint regulation",
    "systemic stablecoin",
    "market statistics",
    "legislature",
    "regulations",
    "passes crypto",
    "euro stablecoin",
    "credit agricole",
    "crédit agricole",
)

GENERIC_ROUNDUP_TERMS = (
    "here's what happened",
    "what happened in crypto today",
    "daily roundup",
    "market recap",
)


def phrase_hits(haystack: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase and daily_radar.contains_phrase(haystack, phrase)]


def contains_any(haystack: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in haystack for phrase in phrases)


def is_market_forecast(feed: daily_radar.Feed, title: str) -> bool:
    if feed.stream not in {"finance", "crypto-finance"}:
        return False
    haystack = daily_radar.normalized_haystack(title, "")
    return contains_any(haystack, MARKET_FORECAST_TERMS)


def has_market_impact_context(feed: daily_radar.Feed, title: str) -> bool:
    haystack = daily_radar.normalized_haystack(title, "")
    return feed.source_class == "official_source" or contains_any(haystack, MARKET_IMPACT_TERMS)


def selection_score(feed: daily_radar.Feed, title: str, evidence: dict[str, object], final_score: float) -> tuple[float, list[str]]:
    score = final_score
    adjustments: list[str] = []
    haystack = daily_radar.normalized_haystack(title, "")

    if feed.id == "arxiv-cs-ai":
        score *= 0.58
        adjustments.append("research_preprint_downweighted")

    if feed.stream == "gear-style-edc" and contains_any(haystack, PRODUCT_CARD_PATTERNS) and not contains_any(haystack, EDC_RELEVANCE_TERMS):
        score *= 0.45
        adjustments.append("product_card_downweighted")

    if feed.stream == "crypto-finance" and (
        feed.source_class == "official_source" or contains_any(haystack, HIGH_SIGNAL_CRYPTO_TERMS)
    ):
        score += 0.8
        adjustments.append("crypto_regulatory_signal_boost")

    if is_market_forecast(feed, title):
        adjustments.append("third_party_market_forecast_labeled")
        if not has_market_impact_context(feed, title):
            score *= 0.55
            adjustments.append("market_forecast_downweighted")

    if feed.source_class == "official_source":
        score += 0.25
        adjustments.append("official_source_boost")

    if evidence["source_rule_status"] != "accepted_by_source_rules":
        score = 0.0

    return round(max(0.0, score), 3), adjustments


def source_rule_evidence(feed: daily_radar.Feed, title: str, summary: str) -> dict[str, object]:
    haystack = daily_radar.normalized_haystack(title, summary)
    include_hits = phrase_hits(haystack, feed.include_keywords)
    exclude_hits = phrase_hits(haystack, feed.exclude_keywords)
    boost_hits = phrase_hits(haystack, feed.boost_keywords)
    penalty_hits = phrase_hits(haystack, feed.penalty_keywords)
    stream_hits = phrase_hits(haystack, daily_radar.KEYWORDS.get(feed.stream, ()))

    if exclude_hits:
        score = 0.0
        status = "rejected_by_exclude_keywords"
    else:
        score = 0.35
        score += min(len(include_hits), 4) * 0.16
        score += min(len(boost_hits), 3) * 0.08
        score += min(len(stream_hits), 4) * 0.06
        score -= min(len(penalty_hits), 3) * 0.12
        if feed.include_keywords and not include_hits:
            score -= 0.2
        score = round(max(0.0, min(1.0, score)), 3)
        status = "accepted_by_source_rules" if score >= feed.min_relevance_score else "rejected_below_min_relevance"

    return {
        "relevance_score": score,
        "min_relevance_score": feed.min_relevance_score,
        "include_hits": include_hits,
        "exclude_hits": exclude_hits,
        "boost_hits": boost_hits,
        "penalty_hits": penalty_hits,
        "stream_keyword_hits": stream_hits[:12],
        "source_rule_status": status,
    }


def selected_keys_from_latest_report() -> set[str]:
    data = read_json(daily_radar.REPORT_PATH, default={})
    keys: set[str] = set()
    for group in data.get("generated", []):
        for raw_path in group.get("signals", []):
            name = (ROOT / str(raw_path)).name
            if "-" in name:
                keys.add(name.split("-", 1)[0])
    return keys


def row_stream(row: dict[str, object]) -> str:
    return str(row.get("routed_stream") or row.get("configured_stream") or "")


def row_publisher(row: dict[str, object]) -> str:
    return str(row.get("publisher_id") or row.get("feed_id") or "unknown")


def row_score(row: dict[str, object]) -> float:
    try:
        return float(row.get("selection_score", row.get("final_score", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def row_relevance(row: dict[str, object]) -> float:
    try:
        return float(row.get("relevance_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def current_selection_priority(row: dict[str, object]) -> float:
    priority = row_score(row)
    text_parts = [
        str(row.get("title") or ""),
        str(row.get("feed_title") or ""),
        str(row.get("feed_id") or ""),
    ]
    for key in ("include_hits", "boost_hits", "stream_keyword_hits"):
        value = row.get(key)
        if isinstance(value, list):
            text_parts.extend(str(part) for part in value)
    haystack = daily_radar.normalized_haystack(" ".join(text_parts), "")
    stream = row_stream(row)

    if str(row.get("market_signal_type") or "") == "third_party_forecast":
        priority -= 1.25
    if contains_any(haystack, GENERIC_ROUNDUP_TERMS):
        priority -= 1.0
    if stream == "crypto-finance" and contains_any(haystack, CRYPTO_SELECTION_PRIORITY_TERMS):
        priority += 0.65
    if stream in {"finance", "crypto-finance"} and str(row.get("source_class") or "") == "official_source":
        priority += 0.45

    return round(priority, 3)


def selection_source_cap(row: dict[str, object]) -> int:
    return RANKING_SELECTION_SOURCE_CAPS.get(
        str(row.get("feed_id") or ""),
        RANKING_SELECTION_DEFAULT_SOURCE_CAP,
    )


def selection_publisher_cap(row: dict[str, object]) -> int:
    return RANKING_SELECTION_PUBLISHER_CAPS.get(
        row_publisher(row),
        RANKING_SELECTION_DEFAULT_PUBLISHER_CAP,
    )


def eligible_for_current_selection(row: dict[str, object]) -> bool:
    if row.get("source_rule_status") != "accepted_by_source_rules":
        return False
    stream = row_stream(row)
    if not stream or stream == GENERAL_SPECIAL_USE_STREAM:
        return False
    if row_score(row) < RANKING_SELECTION_MIN_SCORE:
        return False
    min_relevance = WEAK_STREAM_MIN_RELEVANCE.get(stream)
    if min_relevance is not None and row_relevance(row) < min_relevance:
        return False
    return True


def apply_current_selection(rows: list[dict[str, object]], limit: int = RANKING_SELECTION_LIMIT) -> dict[str, object]:
    """Mark a balanced current-run reader selection.

    The diagnostic report used to mark selected rows only when they happened to
    match keys from the latest generated Daily Radar artifact. That is useful
    provenance, but it can collapse the current live report to a handful of
    stale matches. Current selection is therefore computed from accepted,
    machine-gated rows after caps and scoring have already been applied.
    """

    for row in rows:
        if row.get("source_rule_status") == "accepted_by_source_rules":
            row["selected"] = False
            row["selection_reason"] = "not_selected_after_current_ranking"

    candidates = sorted(
        [row for row in rows if eligible_for_current_selection(row)],
        key=current_selection_priority,
        reverse=True,
    )
    selected: list[dict[str, object]] = []
    source_counts: dict[str, int] = {}
    publisher_counts: dict[str, int] = {}
    stream_counts: dict[str, int] = {}
    capped_sources: dict[str, int] = {}
    capped_publishers: dict[str, int] = {}
    capped_streams: dict[str, int] = {}
    story_duplicate_skips = 0

    def can_add(row: dict[str, object]) -> bool:
        nonlocal story_duplicate_skips
        feed_id = str(row.get("feed_id") or "unknown")
        publisher_id = row_publisher(row)
        stream = row_stream(row)
        if any(public_items_same_story(row, existing) for existing in selected):
            story_duplicate_skips += 1
            return False
        if source_counts.get(feed_id, 0) >= selection_source_cap(row):
            capped_sources[feed_id] = capped_sources.get(feed_id, 0) + 1
            return False
        if publisher_counts.get(publisher_id, 0) >= selection_publisher_cap(row):
            capped_publishers[publisher_id] = capped_publishers.get(publisher_id, 0) + 1
            return False
        if stream_counts.get(stream, 0) >= RANKING_SELECTION_STREAM_CAP:
            capped_streams[stream] = capped_streams.get(stream, 0) + 1
            return False
        return True

    def add(row: dict[str, object]) -> None:
        selected.append(row)
        feed_id = str(row.get("feed_id") or "unknown")
        publisher_id = row_publisher(row)
        stream = row_stream(row)
        source_counts[feed_id] = source_counts.get(feed_id, 0) + 1
        publisher_counts[publisher_id] = publisher_counts.get(publisher_id, 0) + 1
        stream_counts[stream] = stream_counts.get(stream, 0) + 1
        row["selected"] = True
        row["selection_reason"] = "selected_current_balanced_ranking"

    seen: set[str] = set()
    for stream in sorted({row_stream(row) for row in candidates}):
        stream_rows = [row for row in candidates if row_stream(row) == stream]
        if stream_rows and len(selected) < limit and can_add(stream_rows[0]):
            add(stream_rows[0])
            seen.add(str(stream_rows[0].get("item_key") or ""))

    for row in candidates:
        if len(selected) >= limit:
            break
        key = str(row.get("item_key") or "")
        if key and key in seen:
            continue
        if can_add(row):
            add(row)
            seen.add(key)

    return {
        "selection_limit": limit,
        "selection_min_score": RANKING_SELECTION_MIN_SCORE,
        "selection_stream_cap": RANKING_SELECTION_STREAM_CAP,
        "selection_source_caps": RANKING_SELECTION_SOURCE_CAPS,
        "selection_default_source_cap": RANKING_SELECTION_DEFAULT_SOURCE_CAP,
        "selection_publisher_caps": RANKING_SELECTION_PUBLISHER_CAPS,
        "selection_default_publisher_cap": RANKING_SELECTION_DEFAULT_PUBLISHER_CAP,
        "weak_stream_min_relevance": WEAK_STREAM_MIN_RELEVANCE,
        "eligible_current_selection_rows": len(candidates),
        "selected_count": len(selected),
        "selected_by_stream": stream_counts,
        "selected_by_source": source_counts,
        "selected_by_publisher": publisher_counts,
        "selection_capped_sources": capped_sources,
        "selection_capped_publishers": capped_publishers,
        "selection_capped_streams": capped_streams,
        "story_duplicate_skips": story_duplicate_skips,
    }


def row_for(feed: daily_radar.Feed, node: ET.Element, now: datetime, selected_keys: set[str]) -> dict[str, object] | None:
    title = clean_text(daily_radar.text_of(node, ("title",)))
    url = clean_text(daily_radar.link_of(node), 500)
    if not title or not url:
        return None

    raw_summary = daily_radar.text_of(node, ("description", "summary", "content"))
    summary = clean_text(raw_summary)
    source_excerpt = clean_source_excerpt(raw_summary, max_len=360)
    guid = clean_text(daily_radar.text_of(node, ("guid", "id")), 500) or url
    item_key = hashlib.sha256((url or guid or title).encode("utf-8")).hexdigest()[:16]
    raw_published = daily_radar.text_of(node, ("pubDate", "published", "updated", "date")).strip()
    if not raw_published:
        return None
    published = daily_radar.parse_date(raw_published, now)
    evidence = source_rule_evidence(feed, title, summary)

    routed_stream = ""
    final_score = 0.0
    reviewed_signal_match = item_key in selected_keys

    if evidence["source_rule_status"] == "accepted_by_source_rules":
        routed_stream = daily_radar.classify(feed, title, summary)
        final_score = daily_radar.item_score(feed, title, summary, published, now)
    adjusted_score, adjustments = selection_score(feed, title, evidence, final_score)
    market_signal_type = "third_party_forecast" if is_market_forecast(feed, title) else "source_reported"

    if evidence["source_rule_status"] != "accepted_by_source_rules":
        reason = "filtered_by_source_rules"
    else:
        reason = "not_selected_after_current_ranking"

    row: dict[str, object] = {
        "item_key": item_key,
        "feed_id": feed.id,
        "publisher_id": feed.publisher_id,
        "feed_title": feed.title,
        "configured_stream": feed.stream,
        "routed_stream": routed_stream,
        "source_class": feed.source_class,
        "source_type": feed.source_type,
        "language": feed.language,
        "translation_required": feed.translation_required,
        "title": title,
        "url": url,
        "source_excerpt": source_excerpt,
        "source_excerpt_language": feed.language,
        "source_original_title": title,
        "source_original_url": url,
        "published": published.isoformat(),
        "final_score": final_score,
        "selection_score": adjusted_score,
        "ranking_adjustments": adjustments,
        "market_signal_type": market_signal_type,
        "selected": False,
        "selection_reason": reason,
        "reviewed_signal_match": reviewed_signal_match,
        **evidence,
    }
    row.update(build_reader_fields(row))
    return row


def apply_source_caps(rows: list[dict[str, object]], max_rows: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    kept: list[dict[str, object]] = []
    source_counts: dict[str, int] = {}
    capped_counts: dict[str, int] = {}

    for row in rows:
        feed_id = str(row.get("feed_id") or "")
        cap = SOURCE_ROW_CAPS.get(feed_id)
        source_counts[feed_id] = source_counts.get(feed_id, 0) + 1
        if cap is not None and source_counts[feed_id] > cap:
            capped_counts[feed_id] = capped_counts.get(feed_id, 0) + 1
            continue
        kept.append(row)
        if max_rows and len(kept) >= max_rows:
            break

    return kept, {
        "source_row_caps": SOURCE_ROW_CAPS,
        "capped_rows": capped_counts,
        "reported_rows_before_caps": len(rows),
        "reported_rows_after_caps": len(kept),
    }


def build(timeout: int, max_rows: int, dry_run: bool) -> int:
    feeds, _ = daily_radar.load_config(daily_radar.CONFIG_PATH)
    selected_keys = selected_keys_from_latest_report()
    now = datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    errors: list[str] = []

    for feed in feeds:
        try:
            payload = daily_radar.download(feed.url, timeout)
            root = ET.fromstring(payload)
            for node in daily_radar.feed_nodes(root):
                row = row_for(feed, node, now, selected_keys)
                if row is not None:
                    rows.append(row)
        except (urllib.error.URLError, TimeoutError, ET.ParseError, UnicodeError, OSError) as exc:
            errors.append(f"{feed.id}: {exc.__class__.__name__}: {exc}")
        except Exception as exc:
            errors.append(f"{feed.id}: {exc.__class__.__name__}: {exc}")

    rows = sorted(
        rows,
        key=lambda row: (
            float(row.get("selection_score", row.get("final_score", 0.0))),
            bool(row.get("selected")),
            float(row.get("relevance_score", 0.0)),
            str(row.get("published", "")),
        ),
        reverse=True,
    )
    rows, ranking_diagnostics = apply_source_caps(rows, max_rows)
    selection_diagnostics = apply_current_selection(rows)
    ranking_diagnostics["current_selection"] = selection_diagnostics

    report = {
        "date": date.today().isoformat(),
        "report_type": "daily_radar_ranking",
        "source": repo_path(daily_radar.CONFIG_PATH),
        "selected_keys_count": len(selected_keys),
        "selected_count": selection_diagnostics["selected_count"],
        "items": rows,
        "fetch_errors": errors,
        "ranking_diagnostics": ranking_diagnostics,
    }

    if dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    write_json(REPORT_PATH, report)
    print(f"wrote {repo_path(REPORT_PATH)} with {len(rows)} item(s)")
    if errors:
        print(f"fetch warnings: {len(errors)}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--max-rows", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return build(args.timeout, args.max_rows, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
