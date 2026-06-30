"""Fast Regex - Rust-accelerated regex with Python fallback
===========================================================
Provides drop-in replacement for Python's re.compile with Rust acceleration
when available, falling back to standard library otherwise.

Usage:
    from whitemagic.utils.fast_regex import compile as re_compile

    pattern = re_compile(r"\\w+")
    if pattern.search(text):
        ...
"""
# ruff: noqa: BLE001

import logging
import re
from typing import Any

from whitemagic.utils.rust_helper import is_rust_available

logger = logging.getLogger(__name__)


class FastRegexPattern:
    """Wrapper that uses Rust regex when available, Python re fallback otherwise."""

    def __init__(self, pattern: str, flags: int = 0):
        self.pattern = pattern
        self.flags = flags
        self._rust_pattern = None
        self._py_pattern = re.compile(pattern, flags)
        if is_rust_available() and flags == 0:
            try:
                import whitemagic_rs as rs

                if hasattr(rs, "Regex"):
                    self._rust_pattern = rs.Regex(pattern)
            except Exception as e:
                logger.debug(
                    "Rust regex init failed for {pattern!r}: %s", e, exc_info=True
                )

    def search(self, text: str) -> re.Match | None:
        """Search for pattern in text."""
        if self._rust_pattern is not None:
            try:
                m = self._rust_pattern.search(text)
                if m:
                    return re.Match(m)  # type: ignore[call-arg]
            except Exception as e:
                logger.debug(
                    "Rust regex search failed for {self.pattern!r}: %s",
                    e,
                    exc_info=True,
                )
        return self._py_pattern.search(text)

    def match(self, text: str) -> re.Match | None:
        """Match pattern at start of text."""
        return self._py_pattern.match(text)

    def findall(self, text: str) -> list:
        """Find all matches."""
        if self._rust_pattern is not None:
            try:
                return self._rust_pattern.findall(text)
            except Exception as e:
                logger.debug(
                    "Rust regex findall failed for {self.pattern!r}: %s",
                    e,
                    exc_info=True,
                )
        return self._py_pattern.findall(text)

    def finditer(self, text: str):
        """Find all matches as iterator."""
        return self._py_pattern.finditer(text)

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Substitute matches."""
        return self._py_pattern.sub(repl, text, count)

    def split(self, text: str, maxsplit: int = 0) -> list:
        """Split by pattern."""
        return self._py_pattern.split(text, maxsplit)


def compile(pattern: str, flags: int = 0) -> Any:
    """Compile regex pattern with Rust acceleration when available.

    Args:
        pattern: Regex pattern string
        flags: re.IGNORECASE, re.MULTILINE, etc.

    Returns:
        Compiled pattern object (FastRegexPattern or re.Pattern)
    """
    if is_rust_available() and flags == 0:
        return FastRegexPattern(pattern, flags)
    return re.compile(pattern, flags)


# Convenience exports
IGNORECASE = re.IGNORECASE
MULTILINE = re.MULTILINE
DOTALL = re.DOTALL
