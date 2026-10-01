#!/usr/bin/env python3
"""Regression checks for reader policy artifact workflow contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PUBLIC_READER_PREVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "public-reader-preview.yml"
BUILD_SITE = ROOT / "tools" / "build_site.py"
CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"
SETUP_PYTHON_ACTION = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0"
CACHE_RESTORE_ACTION = "actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0"
CACHE_SAVE_ACTION = "actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0"
UPLOAD_ARTIFACT_ACTION = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1"
CONFIGURE_PAGES_ACTION = "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0"
UPLOAD_PAGES_ACTION = "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0"
DEPLOY_PAGES_ACTION = "actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1"


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
            'run_tool("validate_public_digests.py")',
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
    assert f"uses: {CACHE_RESTORE_ACTION}" in text
    assert f"uses: {CACHE_SAVE_ACTION}" in text
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
        CHECKOUT_ACTION,
        SETUP_PYTHON_ACTION,
        CONFIGURE_PAGES_ACTION,
        UPLOAD_PAGES_ACTION,
        DEPLOY_PAGES_ACTION,
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
    for action in [CHECKOUT_ACTION, SETUP_PYTHON_ACTION, UPLOAD_ARTIFACT_ACTION]:
        assert action in text
    assert text.count(f"uses: {UPLOAD_ARTIFACT_ACTION}") == 3


def main() -> int:
    test_build_site_keeps_public_filter_model_gate_before_rendering()
    test_validate_uses_deterministic_site_orchestrator()
    test_pages_uses_live_site_orchestrator()
    test_public_reader_preview_uploads_pr_artifacts_without_deploying()
    print("reader policy workflow tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
