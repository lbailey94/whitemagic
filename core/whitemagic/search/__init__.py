"""Semantic search for WhiteMagic memories.

Note: Requires optional embedding dependencies (sentence-transformers, torch).
If unavailable, import will raise ImportError — use try/except for graceful degradation.
"""

from __future__ import annotations

try:
    from .semantic import SearchMode, SearchResult, SemanticSearcher
    _SEARCH_AVAILABLE = True
except ImportError:
    _SEARCH_AVAILABLE = False
    SearchMode = None  # type: ignore[misc,assignment]
    SearchResult = None  # type: ignore[misc,assignment]
    SemanticSearcher = None  # type: ignore[misc,assignment]

__all__ = ["SearchMode", "SearchResult", "SemanticSearcher"]
