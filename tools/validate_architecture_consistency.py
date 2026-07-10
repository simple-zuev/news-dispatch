#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VALIDATE = ROOT / ".github" / "workflows" / "validate.yml"
PAGES = ROOT / ".github" / "workflows" / "pages.yml"
PUBLIC_READER_PREVIEW = ROOT / ".github" / "workflows" / "public-reader-preview.yml"
REGRESSION = ROOT / ".github" / "workflows" / "regression-tests.yml"
DAILY_RADAR = ROOT / ".github" / "workflows" / "daily-radar.yml"
RUN_DAILY = ROOT / "tools" / "run_daily_radar_safe.py"
BUILD_SITE = ROOT / "tools" / "build_site.py"
ARCH_DOC = ROOT / "docs" / "architecture-consistency-audit.md"
SYNTHESIS_GATE = ROOT / "docs" / "synthesis-publication-gate.md"
DISPATCHES = ROOT / "dispatches"

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_contains(errors: list[str], label: str, text: str, needle: str) -> None:
    if needle not in text:
        errors.append(f"{label} missing required text: {needle}")


def require_absent(errors: list[str], label: str, text: str, needle: str) -> None:
    if needle in text:
        errors.append(f"{label} must not contain: {needle}")


def main() -> int:
    errors: list[str] = []

    for path in (VALIDATE, PAGES, PUBLIC_READER_PREVIEW, REGRESSION, DAILY_RADAR, RUN_DAILY, BUILD_SITE, ARCH_DOC, SYNTHESIS_GATE):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    if errors:
        return report(errors)

    validate = read(VALIDATE)
    require_contains(errors, "validate workflow", validate, "python -m py_compile tools/*.py tests/*.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_stream_registry.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_architecture_consistency.py")
    require_contains(errors, "validate workflow", validate, "python tests/test_filter_daily_signals.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_front_matter.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_source_rules.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_daily_radar_branch_policy.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_synthesis_publication_gate.py")
    require_contains(errors, "validate workflow", validate, "python tools/validate_published.py")
    require_contains(errors, "validate workflow", validate, "python tools/build_site.py --ranking-mode fixture --media-mode skip")

    pages = read(PAGES)
    require_contains(errors, "pages workflow", pages, "python tools/validate_front_matter.py")
    require_contains(errors, "pages workflow", pages, "python tools/validate_source_rules.py")
    require_contains(errors, "pages workflow", pages, "python tools/validate_published.py")
    require_contains(errors, "pages workflow", pages, "python3 tools/build_site.py --ranking-mode live --media-mode skip")
    require_contains(errors, "pages workflow", pages, "python3 tools/validate_reader_output.py")
    require_contains(errors, "pages workflow", pages, "python3 tools/validate_render_visibility.py")
    require_contains(errors, "pages workflow", pages, "python3 tools/privacy_scan.py")
    require_contains(errors, "pages workflow", pages, "uses: actions/configure-pages")
    require_contains(errors, "pages workflow", pages, "uses: actions/upload-pages-artifact")
    require_contains(errors, "pages workflow", pages, "uses: actions/deploy-pages")

    public_reader_preview = read(PUBLIC_READER_PREVIEW)
    require_contains(errors, "public reader preview workflow", public_reader_preview, "pull_request:")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/build_site.py --ranking-mode fixture --media-mode skip")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/validate_reader_output.py")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/validate_render_visibility.py")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/privacy_scan.py")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tests/public_html_scan.py site")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/build_public_reader_preview_report.py")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "python3 tools/capture_public_reader_screenshots.py")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "github.event.pull_request.head.sha || github.sha")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "if: always() && steps.build.outcome == 'success'")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "if-no-files-found: error")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "steps.public_html.outcome == 'failure'")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "name: public-reader-site-preview")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "name: public-reader-preview-qa")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "name: public-reader-preview-screenshots")
    require_contains(errors, "public reader preview workflow", public_reader_preview, "steps.upload_screenshots.outputs.artifact-url")
    require_absent(errors, "public reader preview workflow", public_reader_preview, "actions/deploy-pages")
    require_absent(errors, "public reader preview workflow", public_reader_preview, "upload-pages-artifact")

    regression = read(REGRESSION)
    require_contains(errors, "regression workflow", regression, "python tests/run_regression_tests.py")

    daily = read(DAILY_RADAR)
    require_contains(errors, "daily radar workflow", daily, "DAILY_RADAR_BRANCH: automation/daily-radar")
    require_contains(errors, "daily radar workflow", daily, "python tools/run_daily_radar_safe.py")
    require_contains(errors, "daily radar workflow", daily, "python tools/privacy_scan.py")
    require_contains(errors, "daily radar workflow", daily, "git add signals data validation")
    require_contains(errors, "daily radar workflow", daily, "gh pr create")
    require_absent(errors, "daily radar workflow", daily, "git add dispatches")
    require_absent(errors, "daily radar workflow", daily, "--delete-branch")

    run_daily = read(RUN_DAILY)
    require_contains(errors, "run daily radar orchestrator", run_daily, "tools/validate_feeds.py")
    require_contains(errors, "run daily radar orchestrator", run_daily, "tools/validate_candidate_dispatch.py")
    require_contains(errors, "run daily radar orchestrator", run_daily, "tools/validate_radar_artifacts.py")

    build_site = read(BUILD_SITE)
    require_contains(errors, "site build orchestrator", build_site, "validate_media_registry.py")
    require_contains(errors, "site build orchestrator", build_site, "validate_reader_output.py")
    require_contains(errors, "site build orchestrator", build_site, "validate_render_visibility.py")
    require_contains(errors, "site build orchestrator", build_site, "privacy_scan.py")

    arch_doc = read(ARCH_DOC)
    require_contains(errors, "architecture audit document", arch_doc, "CI execution graph")
    require_contains(errors, "architecture audit document", arch_doc, "Publication boundary")
    require_contains(errors, "architecture audit document", arch_doc, "Validator coverage classes")

    offenders = sorted(path.relative_to(ROOT).as_posix() for path in DISPATCHES.rglob("*auto-radar-draft.md"))
    if offenders:
        errors.append("auto radar drafts must not be in dispatches/: " + ", ".join(offenders))

    return report(errors)

def report(errors: list[str]) -> int:
    if errors:
        print("Architecture consistency validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Architecture consistency validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
