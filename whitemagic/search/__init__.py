"""
WhiteMagic Semantic Search Module.

Provides semantic search capabilities using embeddings and similarity calculations.
Supports multiple search modes: keyword-only, semantic-only, and hybrid.

Example usage:
    >>> from whitemagic.search import semantic_search
    >>> results = await semantic_search(
    ...     query="How to debug async code",
    ...     manager=memory_manager,
    ...     k=10
    ... )
"""

from .semantic import SearchMode, SearchResult, SemanticSearcher, semantic_search

__all__ = ["semantic_search", "SemanticSearcher", "SearchMode", "SearchResult"]

__version__ = "2.2.8"
