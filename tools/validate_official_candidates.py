#!/usr/bin/env python3
"""Validate pre-production official source candidates.

This registry is intentionally separate from sources/feeds.json. Candidates are
not consumed by Daily Radar until they are promoted through a reviewed source
configuration PR.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from stream_registry import stream_slugs

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "sources" / "official-candidates.json"
FEEDS_PATH = ROOT / "sources" / "feeds.json"

ALLOWED_STATUSES = {"candidate", "needs_verification", "rejected", "promoted"}
ALLOWED_URL_STATUSES = {"missing", "unverified", "verified", "rejected"}
ALLOWED_SOURCE_CLASSES = {"official_source", "research_media"}
REQUIRED_KEYS = {
    "id",
    "stream",
    "source_class",
    "status",
    "title",
    "candidate_url",
    "candidate_url_status",
    "rationale",
    "verification_requirements",
    "promotion_target",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def feed_ids() -> set[str]:
    data = load_json(FEEDS_PATH)
    return {str(feed.get("id", "")).strip() for feed in data.get("feeds", []) if isinstance(feed, dict)}


def validate() -> list[str]:
    errors: list[str] = []
    data = load_json(CANDIDATES_PATH)
    candidates = data.get("candidates", [])
    if data.get("status") != "pre-production source candidate registry":
        errors.append("sources/official-candidates.json: status must mark the registry as pre-production")
    if not isinstance(candidates, list) or not candidates:
        return errors + ["sources/official-candidates.json: candidates must be a non-empty list"]

    allowed_streams = stream_slugs()
    production_ids = feed_ids()
    seen_ids: set[str] = set()

    for index, candidate in enumerate(candidates):
        prefix = f"sources/official-candidates.json candidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{prefix}: candidate must be an object")
            continue

        missing = sorted(REQUIRED_KEYS - set(candidate))
        if missing:
            errors.append(f"{prefix}: missing keys: {', '.join(missing)}")

        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id:
            errors.append(f"{prefix}: id is empty")
        elif candidate_id in seen_ids:
            errors.append(f"{prefix}: duplicate candidate id {candidate_id!r}")
        elif candidate_id in production_ids:
            errors.append(f"{prefix}: candidate id {candidate_id!r} already exists in production feeds")
        seen_ids.add(candidate_id)

        stream = str(candidate.get("stream", "")).strip()
        if stream not in allowed_streams:
            errors.append(f"{prefix}: unknown stream {stream!r}")

        source_class = str(candidate.get("source_class", "")).strip()
        if source_class not in ALLOWED_SOURCE_CLASSES:
            errors.append(f"{prefix}: unsupported source_class {source_class!r}; candidates must target official or high-trust coverage")

        status = str(candidate.get("status", "")).strip()
        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}: invalid status {status!r}")

        url_status = str(candidate.get("candidate_url_status", "")).strip()
        if url_status not in ALLOWED_URL_STATUSES:
            errors.append(f"{prefix}: invalid candidate_url_status {url_status!r}")

        url = str(candidate.get("candidate_url", "")).strip()
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{prefix}: invalid candidate_url {url!r}")
            if url_status == "missing":
                errors.append(f"{prefix}: candidate_url_status cannot be 'missing' when candidate_url is set")
        elif url_status not in {"missing", "unverified"}:
            errors.append(f"{prefix}: empty candidate_url must be marked missing or unverified")

        rationale = str(candidate.get("rationale", "")).strip()
        if len(rationale) < 40:
            errors.append(f"{prefix}: rationale must explain the governance gap")

        requirements = candidate.get("verification_requirements", [])
        if not isinstance(requirements, list) or len(requirements) < 3:
            errors.append(f"{prefix}: verification_requirements must list at least three checks")
        elif not all(isinstance(item, str) and item.strip() for item in requirements):
            errors.append(f"{prefix}: verification_requirements must contain non-empty strings")

        if candidate.get("promotion_target") != "sources/feeds.json":
            errors.append(f"{prefix}: promotion_target must be sources/feeds.json")

        if status == "promoted" and candidate_id not in production_ids:
            errors.append(f"{prefix}: promoted candidate must exist in sources/feeds.json")
        if status != "promoted" and candidate_id in production_ids:
            errors.append(f"{prefix}: non-promoted candidate must not exist in sources/feeds.json")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Official source candidate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Official source candidate validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
