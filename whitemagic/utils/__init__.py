"""Utility functions - export from whitemagic.utils directly."""

# Functions are in utils.py itself, not submodules
from whitemagic.utils import (
    serialize_frontmatter,
    split_frontmatter,
    normalize_tags
)

__all__ = ["serialize_frontmatter", "split_frontmatter", "normalize_tags"]
