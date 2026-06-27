# ruff: noqa: BLE001
"""
Token Optimizer — Minimize token usage for AI interactions.

Combines query caching, local reasoning, and context compression
to reduce the number of tokens sent to AI APIs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CachedQuery:
    """A cached query result."""
    query_hash: str
    query: str
    result: str
    tokens_saved: int
    timestamp: float
    hits: int = 0


class QueryCache:
    """LRU-style cache for query results."""

    def __init__(self, max_entries: int = 500) -> None:
        self._cache: dict[str, CachedQuery] = {}
        self._max_entries = max_entries
        self._total_hits = 0
        self._total_tokens_saved = 0

    @staticmethod
    def _hash(query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def get(self, query: str) -> CachedQuery | None:
        h = self._hash(query)
        entry = self._cache.get(h)
        if entry:
            entry.hits += 1
            self._total_hits += 1
            self._total_tokens_saved += entry.tokens_saved
            return entry
        return None

    def set(self, query: str, result: str, tokens_saved: int) -> None:
        h = self._hash(query)
        if len(self._cache) >= self._max_entries:
            oldest = min(self._cache.values(), key=lambda c: c.timestamp)
            del self._cache[oldest.query_hash]
        self._cache[h] = CachedQuery(
            query_hash=h,
            query=query,
            result=result,
            tokens_saved=tokens_saved,
            timestamp=time.time(),
        )

    def stats(self) -> dict[str, Any]:
        return {
            "cached_queries": len(self._cache),
            "total_hits": self._total_hits,
            "total_tokens_saved": self._total_tokens_saved,
        }


class TokenBudget:
    """Tracks token budget and savings."""

    def __init__(self) -> None:
        self.total_saved = 0
        self.total_used = 0
        self.history: list[dict[str, int]] = []

    def save(self, tokens: int) -> None:
        self.total_saved += tokens

    def use(self, tokens: int) -> None:
        self.total_used += tokens

    def net_savings(self) -> int:
        return self.total_saved - self.total_used

    def report(self) -> str:
        return (
            f"Token Budget Report:\n"
            f"  Total saved: {self.total_saved:,}\n"
            f"  Total used: {self.total_used:,}\n"
            f"  Net savings: {self.net_savings():,}"
        )


class ContextCompressor:
    """Compress context by extracting relevant lines."""

    def extract_relevant_lines(
        self, content: str, keywords: list[str], context_lines: int = 3
    ) -> tuple[str, int]:
        if not content or not keywords:
            return content, 0

        lines = content.splitlines()
        relevant_indices: set[int] = set()
        kw_lower = [k.lower() for k in keywords]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(k in line_lower for k in kw_lower):
                for j in range(max(0, i - context_lines), min(len(lines), i + context_lines + 1)):
                    relevant_indices.add(j)

        if not relevant_indices:
            return content[:500] + "\n...[no keyword matches]...", len(content) // 4

        relevant = [lines[i] for i in sorted(relevant_indices)]
        extracted = "\n".join(relevant)
        saved = (len(content) - len(extracted)) // 4
        return extracted, max(saved, 0)


class TokenOptimizer:
    """Main optimizer combining all strategies."""

    def __init__(self) -> None:
        self.budget = TokenBudget()
        self.cache = QueryCache()
        self.compressor = ContextCompressor()

    def optimize_query(self, query: str, context: str = "") -> tuple[str, str, int]:
        """Optimize a query before sending to AI.

        Returns: (optimized_query, optimized_context, tokens_saved)
        """
        tokens_saved = 0

        cached = self.cache.get(query)
        if cached:
            self.budget.save(cached.tokens_saved)
            return query, f"[CACHED] {cached.result}", cached.tokens_saved

        try:
            from whitemagic.agentic.local_reasoning import reason_locally
            result = reason_locally(query)
            if result.insights and not result.ready_for_ai:
                self.cache.set(query, result.summary, result.total_tokens_saved)
                self.budget.save(result.total_tokens_saved)
                return query, f"[LOCAL] {result.summary}", result.total_tokens_saved
            tokens_saved += result.total_tokens_saved
        except Exception:
            pass

        if context:
            keywords = [w for w in query.split() if len(w) > 3]
            compressed, saved = self.compressor.extract_relevant_lines(context, keywords)
            context = compressed
            tokens_saved += saved

        self.budget.save(tokens_saved)
        return query, context, tokens_saved

    def record_usage(self, tokens_used: int) -> None:
        self.budget.use(tokens_used)

    def report(self) -> str:
        cache_stats = self.cache.stats()
        return (
            f"{self.budget.report()}\n\n"
            f"Cache Stats:\n"
            f"  Cached queries: {cache_stats['cached_queries']}\n"
            f"  Cache hits: {cache_stats['total_hits']}\n"
            f"  Tokens saved via cache: {cache_stats['total_tokens_saved']:,}"
        )


_optimizer: TokenOptimizer | None = None


def get_token_optimizer() -> TokenOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = TokenOptimizer()
    return _optimizer


def optimize_for_ai(query: str, context: str = "") -> tuple[str, str, int]:
    return get_token_optimizer().optimize_query(query, context)
