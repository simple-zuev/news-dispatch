#!/usr/bin/env python3
"""Shared utilities for the News Dispatch toolchain.

The project intentionally avoids heavy runtime dependencies.  This module keeps
small, predictable helpers in one place so renderers, validators, radar jobs and
future synthesis tools do not each maintain their own front-matter, slug and
text-cleaning implementations.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TypeVar

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
DISPATCH_DIR = ROOT / "dispatches"
SIGNALS_DIR = ROOT / "signals"
VALIDATION_DIR = ROOT / "validation"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"

T = TypeVar("T")

_EMPTY_SCALARS = {"", "[]", "null", "none", "None"}


@dataclass(frozen=True)
class FrontMatterDocument:
    """Markdown document split into front matter and body."""

    metadata: dict[str, Any]
    body: str
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


class NewsDispatchError(RuntimeError):
    """Base exception for expected News Dispatch tool failures."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def project_path(*parts: str | Path) -> Path:
    """Return an absolute path inside the repository root."""
    return ROOT.joinpath(*map(Path, parts))


def repo_path(path: str | Path, root: Path = ROOT) -> str:
    """Return a repository-relative POSIX path when possible."""
    resolved = Path(path)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, content: str) -> None:
    target = ensure_parent(path)
    target.write_text(content, encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NewsDispatchError(f"Invalid JSON in {repo_path(target)}: {exc}") from exc


def write_json(path: str | Path, value: Any, *, indent: int = 2) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=indent) + "\n")


def log(message: str, *, scope: str = "news-dispatch", stream: Any = None) -> None:
    prefix = f"[{scope}]"
    if stream:
        prefix += f"[{stream}]"
    print(f"{prefix} {message}")


def clean_text(value: Any, max_len: int = 280, *, strip_markdown: bool = False) -> str:
    """Normalize HTML/Markdown-ish text to a compact single-line string."""
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    if strip_markdown:
        text = re.sub(r"[`*_#>\[\]()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def slugify(value: Any, fallback: str = "item", *, max_len: int = 72, latin_only: bool = True) -> str:
    """Create a stable URL/file-name slug.

    By default the function keeps only latin letters and digits, matching the
    existing signal/dispatch naming convention.  Set ``latin_only=False`` for
    human-readable Cyrillic slugs in non-file contexts.
    """
    text = str(value or "").lower().replace("ё", "е")
    text = re.sub(r"[^a-z0-9а-я-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if latin_only:
        text = re.sub(r"[^a-z0-9-]+", "", text).strip("-")
    text = text[:max_len].strip("-")
    return text or fallback


def yaml_quote(value: Any) -> str:
    text = str(value or "")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_scalar(value: str) -> Any:
    """Parse the small YAML-like scalar subset used by this project."""
    raw = value.strip()
    if raw in _EMPTY_SCALARS:
        return [] if raw == "[]" else ""
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    return _unquote(raw)


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip() not in _EMPTY_SCALARS]
    scalar = str(value).strip()
    if scalar in _EMPTY_SCALARS:
        return []
    return [scalar]


def first_value(value: Any, default: str = "") -> str:
    values = ensure_list(value)
    return values[0] if values else default


def parse_front_matter(text: str) -> FrontMatterDocument:
    """Parse a Markdown file with a conservative YAML front-matter subset.

    Supported forms:
    - ``key: value`` scalars;
    - quoted string scalars;
    - booleans;
    - ``key:`` followed by indented ``- item`` list entries;
    - explicit empty list ``key: []``.
    """
    if not text.startswith("---\n"):
        return FrontMatterDocument({}, text, ("missing front matter delimiter",))
    end = text.find("\n---\n", 4)
    if end == -1:
        return FrontMatterDocument({}, text, ("missing closing front matter delimiter",))

    raw = text[4:end]
    body = text[end + 5 :]
    metadata: dict[str, Any] = {}
    errors: list[str] = []
    current_key: str | None = None

    for line_no, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  -"):
            if current_key is None:
                errors.append(f"line {line_no}: list item without key")
                continue
            metadata.setdefault(current_key, [])
            if not isinstance(metadata[current_key], list):
                metadata[current_key] = [str(metadata[current_key])]
            metadata[current_key].append(_unquote(line.split("-", 1)[1].strip()))
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: invalid front matter line")
            current_key = None
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        if not current_key:
            errors.append(f"line {line_no}: empty key")
            current_key = None
            continue
        raw_value = value.strip()
        if raw_value == "":
            metadata[current_key] = []
        else:
            metadata[current_key] = parse_scalar(raw_value)
            current_key = None

    return FrontMatterDocument(metadata, body, tuple(errors))


def parse_front_matter_file(path: str | Path) -> FrontMatterDocument:
    return parse_front_matter(read_text(path))


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return yaml_quote(value)


def format_front_matter(metadata: Mapping[str, Any]) -> str:
    """Serialize metadata to the project's YAML-like front matter."""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, (list, tuple)):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                lines.extend(f"  - {_format_scalar(item)}" for item in value)
        else:
            lines.append(f"{key}: {_format_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def unique_preserve_order(values: Iterable[T]) -> list[T]:
    seen: set[T] = set()
    result: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def coalesce(*values: Any, default: str = "") -> str:
    for value in values:
        if isinstance(value, list):
            value = first_value(value)
        if value not in (None, "", []):
            return str(value)
    return default


def require_paths(paths: Sequence[str | Path]) -> list[Path]:
    resolved = [Path(path) for path in paths]
    missing = [repo_path(path) for path in resolved if not path.exists()]
    if missing:
        raise NewsDispatchError("Missing path(s): " + ", ".join(missing))
    return resolved


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)
