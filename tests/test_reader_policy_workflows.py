#!/usr/bin/env python3
"""Regression checks for reader policy artifact workflow contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PUBLIC_READER_PREVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "public-reader-preview.yml"
BUILD_SITE = ROOT / "tools" / "build_site.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_ordered(text: str, markers: list[str]) -> None:
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions), markers


def test_build_site_keeps_public_filter_model_gate_before_rendering() -> None:
    text = read(BUILD_SITE)
    build_body = text[text.index("def build(args") :]
    assert_ordered(
        build_body,
        [
            "build_ranking(args)",
            'run_tool("filter_public_source_items.py")',
            "build_reader_policy()",
            'run_tool("build_public_reader_history.py"',
            'run_tool("validate_reader_model.py")',
            'run_tool("render_site.py")',
            'run_tool("build_news_pages.py")',
            'run_tool("build_today_page.py")',
            'run_tool("apply_reader_title_quality.py")',
        ],
    )
    assert "copy_to_site(READER_POLICY_REPORT)" in text
    assert "copy_to_site(RANKING_REPORT)" in text


def test_validate_uses_deterministic_site_orchestrator() -> None:
    text = read(VALIDATE_WORKFLOW)
    assert "run: python tools/build_site.py --ranking-mode fixture --media-mode skip" in text
    assert "path: validation/reader-policy-latest.json" in text
    assert "path: validation/daily-radar-ranking-latest.json" in text


def test_pages_uses_live_site_orchestrator() -> None:
    text = read(PAGES_WORKFLOW)
    assert 'cron: "0 1,7,13,19 * * *"' in text
    assert "run: python3 tools/build_site.py --ranking-mode live --media-mode skip" in text
    assert "uses: actions/configure-pages" in text
    assert "uses: actions/upload-pages-artifact" in text
    assert "uses: actions/deploy-pages" in text
    assert "run: python3 tools/validate_reader_output.py" in text
    assert "run: python3 tools/validate_render_visibility.py" in text
    assert "run: python3 tools/privacy_scan.py" in text
    assert "run: python3 tools/validate_public_reader_content_quality.py" in text
    assert "run: python3 tools/validate_public_reader_freshness.py" in text
    assert "run: python3 tools/build_public_reader_quality_report.py" in text
    assert "uses: actions/cache/restore@v6" in text
    assert "uses: actions/cache/save@v6" in text
    assert "name: public-reader-quality-report" in text
    assert "path: validation/public-reader-history-latest.json" in text
    assert "public-reader-history-${{ github.run_id }}" in text
    assert_ordered(
        text,
        [
            "run: python3 tools/build_site.py --ranking-mode live --media-mode skip",
            "run: python3 tools/validate_reader_output.py",
            "run: python3 tools/validate_render_visibility.py",
            "run: python3 tools/privacy_scan.py",
            "run: python3 tools/validate_public_reader_content_quality.py",
            "run: python3 tools/validate_public_reader_freshness.py",
            "run: python3 tools/build_public_reader_quality_report.py",
            "uses: actions/configure-pages",
        ],
    )
    assert "path: site/" in text
    for action in [
        "actions/checkout@v7",
        "actions/setup-python@v6",
        "actions/configure-pages@v6",
        "actions/upload-pages-artifact@v5",
        "actions/deploy-pages@v5",
    ]:
        assert action in text


def test_public_reader_preview_uploads_pr_artifacts_without_deploying() -> None:
    text = read(PUBLIC_READER_PREVIEW_WORKFLOW)
    assert "pull_request:" in text
    for path_filter in [
        '"tools/**"',
        '"site/styles/**"',
        '"tests/**"',
        '"docs/public-reader-*.md"',
        '"sources/**"',
        '"dispatches/**"',
        '".github/workflows/public-reader-preview.yml"',
    ]:
        assert path_filter in text
    assert "group: public-reader-preview-${{ github.event.pull_request.number || github.ref }}" in text
    assert "cancel-in-progress: true" in text
    assert "id: build" in text
    assert "run: python3 tools/build_site.py --ranking-mode fixture --media-mode skip" in text
    assert "run: python3 tools/validate_reader_output.py" in text
    assert "run: python3 tools/validate_render_visibility.py" in text
    assert "run: python3 tools/privacy_scan.py" in text
    assert "run: python3 tests/public_html_scan.py site" in text
    assert "run: python3 tools/build_public_reader_preview_report.py" in text
    assert 'commit-sha "${{ github.event.pull_request.head.sha || github.sha }}"' in text
    assert "run: python3 tools/validate_public_reader_content_quality.py" in text
    assert "run: python3 tools/build_public_reader_quality_report.py" in text
    assert "run: python3 tools/capture_public_reader_screenshots.py" in text
    assert "name: Verify preview artifact files" in text
    assert "if: always() && steps.build.outcome == 'success'" in text
    assert "name: public-reader-site-preview" in text
    assert "name: public-reader-preview-qa" in text
    assert "name: public-reader-preview-screenshots" in text
    assert "validation/public-reader-preview-report.md" in text
    assert "validation/daily-radar-ranking-latest.json" in text
    assert "validation/reader-policy-latest.json" in text
    assert "validation/reader-model-latest.json" in text
    assert "validation/public-reader-content-quality-latest.json" in text
    assert "validation/public-reader-quality-latest.json" in text
    assert "validation/public-reader-quality-latest.md" in text
    assert "validation/public-reader-preview-screenshots/index.html" in text
    assert "validation/public-reader-preview-screenshots/sources-mobile.png" in text
    assert text.count("if-no-files-found: error") == 3
    assert "SITE_ARTIFACT_URL: ${{ steps.upload_site.outputs.artifact-url }}" in text
    assert "QA_ARTIFACT_URL: ${{ steps.upload_qa.outputs.artifact-url }}" in text
    assert "SCREENSHOT_ARTIFACT_URL: ${{ steps.upload_screenshots.outputs.artifact-url }}" in text
    for step_id in [
        "build",
        "reader_output",
        "render_visibility",
        "privacy",
        "public_html",
        "preview-qa",
        "content-quality",
        "quality-report",
        "screenshot_capture",
        "preview_files",
        "upload_site",
        "upload_qa",
        "upload_screenshots",
        "preview_summary",
    ]:
        assert f"steps.{step_id}.outcome == 'failure'" in text
    assert_ordered(
        text,
        [
            "name: Build public reader preview",
            "name: Capture public reader screenshots",
            "name: Verify preview artifact files",
            "name: Upload public reader site preview",
            "name: Upload public reader QA report",
            "name: Upload public reader screenshots",
            "name: Publish preview review links",
            "name: Fail when preview QA failed",
        ],
    )
    assert "actions/deploy-pages" not in text
    assert "upload-pages-artifact" not in text
    for action in ["actions/checkout@v7", "actions/setup-python@v6", "actions/upload-artifact@v7"]:
        assert action in text
    assert text.count("uses: actions/upload-artifact@v7") == 3


def main() -> int:
    test_build_site_keeps_public_filter_model_gate_before_rendering()
    test_validate_uses_deterministic_site_orchestrator()
    test_pages_uses_live_site_orchestrator()
    test_public_reader_preview_uploads_pr_artifacts_without_deploying()
    print("reader policy workflow tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
