#!/usr/bin/env python3
"""Build the complete News Dispatch static reader site."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
VALIDATION_DIR = ROOT / "validation"
RANKING_REPORT = VALIDATION_DIR / "daily-radar-ranking-latest.json"
READER_POLICY_REPORT = VALIDATION_DIR / "reader-policy-latest.json"

OFFLINE_RANKING_FIXTURE = {
    "date": "2026-06-28",
    "report_type": "daily_radar_ranking",
    "source": "offline-validation-fixture",
    "selected_keys_count": 1,
    "fetch_errors": [],
    "items": [
        {
            "item_key": "fixture-selected",
            "feed_id": "fixture-feed",
            "feed_title": "Fixture Regulator",
            "configured_stream": "crypto-finance",
            "routed_stream": "crypto-finance",
            "source_class": "regulator",
            "source_type": "official",
            "language": "en",
            "translation_required": True,
            "title": "Central bank updates digital asset rules",
            "source_original_title": "Central bank updates digital asset rules",
            "source_excerpt": "The central bank published an update on digital asset rules, including supervisory expectations and custody requirements.",
            "source_excerpt_language": "en",
            "url": "https://example.com/fixture",
            "published": "2026-06-28T00:00:00+00:00",
            "final_score": 1.25,
            "relevance_score": 0.82,
            "min_relevance_score": 0.45,
            "include_hits": ["central bank", "digital asset"],
            "exclude_hits": [],
            "boost_hits": ["central bank"],
            "penalty_hits": [],
            "stream_keyword_hits": ["digital asset"],
            "source_rule_status": "accepted_by_source_rules",
            "selected": True,
            "selection_reason": "selected_top_ranked",
        },
        {
            "item_key": "fixture-rejected",
            "feed_id": "fixture-feed",
            "feed_title": "Fixture Source",
            "configured_stream": "finance",
            "routed_stream": "",
            "source_class": "public_media",
            "source_type": "media",
            "language": "en",
            "translation_required": True,
            "title": "Sports item",
            "url": "https://example.com/rejected",
            "published": "2026-06-28T00:00:00+00:00",
            "final_score": 0.0,
            "relevance_score": 0.0,
            "min_relevance_score": 0.45,
            "include_hits": [],
            "exclude_hits": ["sports"],
            "boost_hits": [],
            "penalty_hits": [],
            "stream_keyword_hits": [],
            "source_rule_status": "rejected_by_exclude_keywords",
            "selected": False,
            "selection_reason": "filtered_by_source_rules",
        },
    ],
}


def repo_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run_tool(script: str, *args: str) -> None:
    command = [sys.executable, f"tools/{script}", *args]
    print("[build-site] running:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_to_site(source: Path, name: str | None = None) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing build artifact: {repo_path(source)}")
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    target = SITE_DIR / (name or source.name)
    shutil.copyfile(source, target)
    print(f"[build-site] copied {repo_path(source)} -> {repo_path(target)}")


def build_ranking(args: argparse.Namespace) -> None:
    if args.ranking_mode == "skip":
        print("[build-site] skipping radar ranking report")
        return
    if args.ranking_mode == "fixture":
        write_json(RANKING_REPORT, OFFLINE_RANKING_FIXTURE)
        print(f"[build-site] wrote offline fixture {repo_path(RANKING_REPORT)}")
    else:
        run_tool("build_daily_radar_ranking_report.py", "--timeout", str(args.ranking_timeout), "--max-rows", str(args.ranking_max_rows))
    copy_to_site(RANKING_REPORT)


def build_reader_policy() -> None:
    run_tool("build_reader_policy.py")
    copy_to_site(READER_POLICY_REPORT)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking-mode", choices=("fixture", "live", "skip"), default="fixture")
    parser.add_argument("--ranking-timeout", type=int, default=8)
    parser.add_argument("--ranking-max-rows", type=int, default=200)
    parser.add_argument("--media-mode", choices=("skip", "live"), default="skip")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--skip-privacy-scan", action="store_true")
    return parser.parse_args(argv)


def build(args: argparse.Namespace) -> int:
    build_ranking(args)
    run_tool("filter_public_source_items.py")
    build_reader_policy()
    history_args = ("--reset",) if args.ranking_mode == "fixture" else ()
    run_tool("build_public_reader_history.py", *history_args)
    if not args.skip_validation:
        run_tool("validate_public_digests.py")
        run_tool("validate_reader_model.py")
    run_tool("render_site.py")
    run_tool("build_radar_pages.py")
    run_tool("build_news_pages.py")
    run_tool("build_sources_page.py")
    run_tool("build_today_page.py")
    run_tool("enhance_site.py")
    if args.media_mode == "live":
        run_tool("enrich_media_registry.py")
    else:
        print("[build-site] skipping remote media enrichment")
    run_tool("validate_media_registry.py")
    run_tool("apply_media_previews.py")
    run_tool("apply_reader_sections.py")
    run_tool("apply_reader_structure.py")
    run_tool("apply_editorial_home_layout.py")
    run_tool("apply_today_link.py")
    run_tool("apply_empty_states.py")
    run_tool("apply_reader_title_quality.py")
    if not args.skip_validation:
        run_tool("validate_reader_output.py")
        run_tool("validate_render_visibility.py")
    if not args.skip_privacy_scan:
        run_tool("privacy_scan.py")
    print("[build-site] complete")
    return 0


def main(argv: list[str] | None = None) -> int:
    return build(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
