"""Small shared HTML fragments for public reader pages."""

from __future__ import annotations

import html

NAV_ITEMS = (
    ("today", "today.html", "Сегодня"),
    ("news", "news/index.html", "Новости"),
    ("digests", "digests/index.html", "Дайджесты"),
    ("sources", "sources/index.html", "Источники"),
)


def public_skip_link(target: str = "main-content") -> str:
    return f'<a class="skip-link" href="#{html.escape(target, quote=True)}">К содержанию</a>'


def public_nav(prefix: str = "", current: str = "", extra_class: str = "") -> str:
    """Render one reader-facing navigation pattern for every public route."""
    classes = " ".join(part for part in ("top-nav", extra_class.strip()) if part)
    links = []
    for key, path, label in NAV_ITEMS:
        active = " is-current" if key == current else ""
        current_attr = ' aria-current="page"' if key == current else ""
        links.append(
            f'<a class="top-nav-link{active}" href="{html.escape(prefix + path, quote=True)}"{current_attr}>'
            f"{html.escape(label)}</a>"
        )
    return f'<nav class="{classes}" aria-label="Навигация">{"".join(links)}</nav>'
