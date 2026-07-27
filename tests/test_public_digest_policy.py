#!/usr/bin/env python3
"""Regression tests for the public analytical-digest contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from digest_policy import digest_quality_findings, is_public_digest  # noqa: E402


def strong_digest() -> tuple[dict[str, object], str]:
    metadata: dict[str, object] = {
        "title": "Стейблкоины становятся расчётной инфраструктурой",
        "status": "published",
        "public_safe": True,
        "reader_collection": "digests",
        "issue_type": "market-structure-note",
        "editorial_review": "limited_publication",
        "digest_thesis": (
            "Стейблкоины переходят из крипторынка в расчётную инфраструктуру, "
            "поэтому правила резервов и посредников важнее движения цены."
        ),
        "reader_value": (
            "Читатель увидит, какие элементы режима подтверждены официально, "
            "а какие сценарии пока остаются отраслевыми предположениями."
        ),
        "summary": (
            "Официальный консультационный контур и рыночные инициативы показывают "
            "переход стейблкоинов к валютным и корпоративным расчётам."
        ),
        "sources": ["https://example.com/official", "https://example.com/market"],
    }
    body = """
## Лид
Тезис.
## Главное
Факты.
## Почему это важно
Механизм влияния.
## Анализ
Границы вывода.
## Что наблюдать дальше
Следующие подтверждения.
## Итог
Вывод.
"""
    return metadata, body


def test_strong_digest_passes_contract() -> None:
    metadata, body = strong_digest()
    assert digest_quality_findings(metadata, body) == []
    assert is_public_digest(metadata, body)


def test_published_automatic_radar_is_not_a_digest_without_declaration() -> None:
    metadata, body = strong_digest()
    metadata.pop("reader_collection")
    metadata["title"] = "Автоматический ежедневный радар — 2026-07-27"
    assert digest_quality_findings(metadata, body) == []
    assert not is_public_digest(metadata, body)


def test_declared_digest_fails_without_thesis_value_and_editorial_review() -> None:
    metadata, body = strong_digest()
    metadata["title"] = "Общий выпуск — всё за день"
    metadata["digest_thesis"] = ""
    metadata["reader_value"] = ""
    metadata["editorial_review"] = "automated_radar_public_sources_v1"
    findings = digest_quality_findings(metadata, body)
    assert "digest requires a non-automated editorial_review" in findings
    assert "digest title must state a specific analytical subject" in findings
    assert "digest_thesis must provide a specific analytical conclusion" in findings
    assert "reader_value must explain what the reader gains" in findings
    assert not is_public_digest(metadata, body)


def test_declared_digest_requires_sources_and_analytical_sections() -> None:
    metadata, _body = strong_digest()
    metadata["sources"] = ["https://example.com/only-one"]
    findings = digest_quality_findings(metadata, "## Лид\nКороткий текст.")
    assert "digest requires at least two distinct public sources" in findings
    assert any(finding.startswith("digest body missing sections:") for finding in findings)
    assert "digest body missing a what-to-watch-next section" in findings


def main() -> int:
    test_strong_digest_passes_contract()
    test_published_automatic_radar_is_not_a_digest_without_declaration()
    test_declared_digest_fails_without_thesis_value_and_editorial_review()
    test_declared_digest_requires_sources_and_analytical_sections()
    print("public digest policy tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
