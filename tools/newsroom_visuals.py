#!/usr/bin/env python3
"""Small deterministic visuals for public newsroom pages."""

from __future__ import annotations

import html

STREAM_VISUALS = {
    "finance": ("Финансы", "macro-chart"),
    "crypto-finance": ("Криптофинансы", "ledger-grid"),
    "ai": ("ИИ", "neural-chip"),
    "tech-hardware-software": ("Железо и софт", "server-chip"),
    "gear-style-edc": ("EDC / стиль / вещи", "carry-grid"),
    "moscow-city": ("Москва", "city-lines"),
    "dj-audio-creative": ("DJ / аудио / креатив", "waveform"),
    "science-discovery": ("Наука", "orbit-field"),
    "general": ("Спецвыпуски", "dispatch-lines"),
}


def stream_visual(stream: str, *, variant: str = "card", class_name: str = "") -> str:
    slug = stream if stream in STREAM_VISUALS else "general"
    title, motif = STREAM_VISUALS[slug]
    classes = " ".join(
        part
        for part in [
            "stream-visual",
            f"stream-visual--{slug}",
            f"stream-visual--{variant}",
            f"stream-visual--{motif}",
            class_name,
        ]
        if part
    )
    label = f"Иллюстрация темы: {title}"
    return f"""<div class="{html.escape(classes, quote=True)}" role="img" aria-label="{html.escape(label, quote=True)}">
  <span class="visual-grid-line visual-grid-line--one"></span>
  <span class="visual-grid-line visual-grid-line--two"></span>
  <span class="visual-shape visual-shape--one"></span>
  <span class="visual-shape visual-shape--two"></span>
  <span class="visual-shape visual-shape--three"></span>
</div>"""


def visual_streams() -> list[str]:
    return list(STREAM_VISUALS)
