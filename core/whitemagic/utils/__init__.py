"""WhiteMagic Utilities Package."""
from __future__ import annotations

from typing import Any

_CORE_EXPORTS = {
    "clean_markdown",
    "create_frontmatter",
    "create_preview",
    "format_size",
    "normalize_tags",
    "now_iso",
    "parse_datetime",
    "parse_frontmatter",
    "serialize_frontmatter",
    "slugify",
    "split_frontmatter",
    "summarize_text",
    "truncate_text",
}
_FILEIO_EXPORTS = {"atomic_write", "file_lock"}
_METRICS_EXPORTS = {"get_tracker", "track_metric"}


def __getattr__(name: str) -> Any:
    if name in _CORE_EXPORTS:
        from . import core as _core
        value = getattr(_core, name)
        globals()[name] = value
        return value
    if name in _FILEIO_EXPORTS:
        from . import fileio as _fileio
        value = getattr(_fileio, name)
        globals()[name] = value
        return value
    if name in _METRICS_EXPORTS:
        from .. import metrics as _metrics
        value = getattr(_metrics, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "atomic_write",
    "clean_markdown",
    "create_frontmatter",
    "create_preview",
    "file_lock",
    "format_size",
    "get_tracker",
    "normalize_tags",
    "now_iso",
    "parse_datetime",
    "parse_frontmatter",
    "serialize_frontmatter",
    "slugify",
    "split_frontmatter",
    "summarize_text",
    "track_metric",
    "truncate_text",
]
