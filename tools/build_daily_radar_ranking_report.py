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

REPORT_PATH = VALIDATION_DIR / "daily-radar-ranking-latest.json"


def phrase_hits(haystack: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase and daily_radar.contains_phrase(haystack, phrase)]


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


def row_for(feed: daily_radar.Feed, node: ET.Element, now: datetime, selected_keys: set[str]) -> dict[str, object] | None:
    title = clean_text(daily_radar.text_of(node, ("title",)))
    url = clean_text(daily_radar.link_of(node), 500)
    if not title or not url:
        return None

    summary = clean_text(daily_radar.text_of(node, ("description", "summary", "content")))
    guid = clean_text(daily_radar.text_of(node, ("guid", "id")), 500) or url
    item_key = hashlib.sha256((url or guid or title).encode("utf-8")).hexdigest()[:16]
    published = daily_radar.parse_date(daily_radar.text_of(node, ("pubDate", "published", "updated", "date")), now)
    evidence = source_rule_evidence(feed, title, summary)

    routed_stream = ""
    final_score = 0.0
    selected = item_key in selected_keys

    if evidence["source_rule_status"] == "accepted_by_source_rules":
        routed_stream = daily_radar.classify(feed, title, summary)
        final_score = daily_radar.item_score(feed, title, summary, published, now)

    if selected:
        reason = "selected_top_ranked"
    elif evidence["source_rule_status"] != "accepted_by_source_rules":
        reason = "filtered_by_source_rules"
    else:
        reason = "not_selected_after_ranking"

    return {
        "item_key": item_key,
        "feed_id": feed.id,
        "feed_title": feed.title,
        "configured_stream": feed.stream,
        "routed_stream": routed_stream,
        "source_class": feed.source_class,
        "source_type": feed.source_type,
        "language": feed.language,
        "translation_required": feed.translation_required,
        "title": title,
        "url": url,
        "published": published.isoformat(),
        "final_score": final_score,
        "selected": selected,
        "selection_reason": reason,
        **evidence,
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
            bool(row.get("selected")),
            float(row.get("final_score", 0.0)),
            float(row.get("relevance_score", 0.0)),
            str(row.get("published", "")),
        ),
        reverse=True,
    )
    if max_rows:
        rows = rows[:max_rows]

    report = {
        "date": date.today().isoformat(),
        "report_type": "daily_radar_ranking",
        "source": repo_path(daily_radar.CONFIG_PATH),
        "selected_keys_count": len(selected_keys),
        "items": rows,
        "fetch_errors": errors,
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
