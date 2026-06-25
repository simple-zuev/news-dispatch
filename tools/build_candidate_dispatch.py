#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "validation" / "reviewed-radar-latest.md"
OUT = ROOT / "validation" / "candidate-dispatch-latest.md"


def read_review() -> str:
    if not REVIEW.exists():
        return ""
    return REVIEW.read_text(encoding="utf-8")


def main() -> int:
    review = read_review()
    lines = [
        "# Candidate Dispatch — pre-publication",
        "",
        "Status: candidate only. Not published. Do not move to dispatches/ without editorial review.",
        "",
        "## Главные темы-кандидаты",
        "",
        "Заполняется редактором после проверки reviewed radar report.",
        "",
        "## Что требует проверки",
        "",
        "- Первичные источники для финансовых, регуляторных, крипто- и security-сигналов.",
        "- Дедупликация связанных материалов.",
        "- Разделение факта, тренда, оценки, гипотезы и слабого сигнала.",
        "",
        "## Исходный reviewed radar",
        "",
    ]
    if review:
        lines.append(review)
    else:
        lines.append("Reviewed radar report is not available yet.")
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
