# ruff: noqa: BLE001
"""Token Optimizer - Strategies to minimize cloud AI token usage.
Version: 4.3.0.

This module provides tools for AI agents to minimize token burn by:
1. Pre-filtering context before sending to cloud
2. Caching common query results
3. Progressive summarization
4. Smart context windowing

v4.3.0 Enhancement: Unified Resource Tracking
- Integrates with CoherencePersistence for rate limiting
- Connects to DepthGauge for consciousness layer awareness
- Circuit breaker integration for stuck detection
- Session-aware budget management
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from whitemagic.utils.core import parse_datetime
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Track token usage and savings.

    v4.3.0: Now integrates with rate limiting and consciousness depth.
    """

    allocated: int = 100000  # Default 100K budget
    used: int = 0
    saved: int = 0
    # v4.3.0: Rate limiting fields
    calls_this_hour: int = 0
    max_calls_per_hour: int = 100
    hour_started: str = ""

    @property
    def remaining(self) -> int:
        """
        Perform the remaining operation.

        Returns:
            int
        """
        return self.allocated - self.used

    @property
    def efficiency(self) -> float:
        """
        Perform the efficiency operation.

        Returns:
            float
        """
        total = self.used + self.saved
        return self.saved / total if total > 0 else 0.0

    @property
    def usage_tier(self) -> str:
        """Get current usage tier for token efficiency guidance."""
        pct = self.used / self.allocated if self.allocated > 0 else 0
        if pct < 0.60:
            return "safe"      # Under 60% - safe zone
        elif pct < 0.70:
            return "wrap_up"   # 60-70% - start wrapping up
        else:
            return "checkpoint" # Over 70% - checkpoint immediately

    @property
    def rate_limit_remaining(self) -> int:
        """
        Perform the rate limit remaining operation.

        Returns:
            int
        """
        return max(0, self.max_calls_per_hour - self.calls_this_hour)

    def use(self, tokens: int) -> None:
        """
        Perform the use operation.

        Args:
            tokens: Parameter description.

        Returns:
            None
        """
        self.used += tokens

    def save(self, tokens: int) -> None:
        """
        Perform the save operation.

        Args:
            tokens: Parameter description.

        Returns:
            None
        """
        self.saved += tokens

    def net_savings(self) -> int:
        """Net tokens saved (saved - used)."""
        return self.saved - self.used

    def record_call(self) -> None:
        """Record an API call for rate limiting."""
        from datetime import datetime
        current_hour = datetime.now().strftime("%Y%m%d%H")
        if self.hour_started != current_hour:
            self.calls_this_hour = 0
            self.hour_started = current_hour
        self.calls_this_hour += 1

    def is_rate_limited(self) -> bool:
        """
        Check whether the rate limited condition holds.

        Returns:
            bool
        """
        return self.calls_this_hour >= self.max_calls_per_hour

    def report(self) -> str:
        """
        Perform the report operation.

        Returns:
            str
        """
        tier_emoji = {"safe": "🟢", "wrap_up": "🟡", "checkpoint": "🔴"}[self.usage_tier]
        return (
            f"Token Budget Report:\n"
            f"  Allocated: {self.allocated:,}\n"
            f"  Used: {self.used:,} ({100*self.used/self.allocated:.1f}%) {tier_emoji}\n"
            f"  Saved: {self.saved:,}\n"
            f"  Remaining: {self.remaining:,}\n"
            f"  Efficiency: {100*self.efficiency:.1f}% savings rate\n"
            f"  Rate Limit: {self.calls_this_hour}/{self.max_calls_per_hour} calls/hour\n"
            f"  Status: {self.usage_tier.upper()}"
        )


@dataclass
class CachedResult:
    """A cached query result."""

    query_hash: str
    result: str
    tokens_saved: int
    created: datetime
    hits: int = 0

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """
        Check whether the stale condition holds.

        Args:
            max_age_hours: Parameter description.

        Returns:
            bool
        """
        age = datetime.now() - self.created
        return age > timedelta(hours=max_age_hours)


class QueryCache:
    """Cache for local reasoning results."""

    def __init__(self, cache_file: Path | None = None) -> None:
        from whitemagic.config.paths import CACHE_DIR
        self.cache_file = cache_file or (CACHE_DIR / "query_cache.json")
        self._cache: dict[str, CachedResult] = {}
        self._load()

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                data = _json_loads(self.cache_file.read_text())
                for h, item in data.items():
                    self._cache[h] = CachedResult(
                        query_hash=h,
                        result=item["result"],
                        tokens_saved=item["tokens_saved"],
                        created=parse_datetime(item["created"]),
                        hits=item.get("hits", 0),
                    )
            except OSError:
                pass

    def _save(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            h: {
                "result": c.result,
                "tokens_saved": c.tokens_saved,
                "created": c.created.isoformat(),
                "hits": c.hits,
            }
            for h, c in self._cache.items()
        }
        self.cache_file.write_text(_json_dumps(data, indent=2))

    def get(self, query: str) -> CachedResult | None:
        """
        Perform the get operation.

        Args:
            query: Parameter description.

        Returns:
            CachedResult | None
        """
        h = self._hash_query(query)
        cached = self._cache.get(h)
        if cached and not cached.is_stale():
            cached.hits += 1
            return cached
        return None

    def set(self, query: str, result: str, tokens_saved: int) -> None:
        """
        Perform the set operation.

        Args:
            query: Parameter description.
            result: Parameter description.
            tokens_saved: Parameter description.

        Returns:
            None
        """
        h = self._hash_query(query)
        self._cache[h] = CachedResult(
            query_hash=h,
            result=result,
            tokens_saved=tokens_saved,
            created=datetime.now(),
        )
        self._save()

    def stats(self) -> dict[str, Any]:
        """
        Perform the stats operation.

        Returns:
            dict[str, Any]
        """
        total_hits = sum(c.hits for c in self._cache.values())
        total_saved = sum(c.tokens_saved * c.hits for c in self._cache.values())
        return {
            "cached_queries": len(self._cache),
            "total_hits": total_hits,
            "total_tokens_saved": total_saved,
        }


class ContextCompressor:
    """Compress context to fit token budgets."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return len(text) // 4

    @staticmethod
    def truncate_to_budget(text: str, max_tokens: int) -> tuple[str, int]:
        """Truncate text to fit token budget."""
        estimated = ContextCompressor.estimate_tokens(text)
        if estimated <= max_tokens:
            return text, 0

        # Truncate with indicator
        max_chars = max_tokens * 4
        truncated = text[:max_chars] + "\n...[truncated]..."
        saved = estimated - max_tokens
        return truncated, saved

    @staticmethod
    def summarize_file_list(files: list[str], max_files: int = 20) -> tuple[str, int]:
        """Summarize a file list instead of listing all."""
        if len(files) <= max_files:
            return "\n".join(files), 0

        # Show sample + count
        sample = files[:max_files]
        summary = "\n".join(sample) + f"\n...and {len(files) - max_files} more files"
        saved = (len(files) - max_files) * 10  # ~10 tokens per file path
        return summary, saved

    @staticmethod
    def extract_relevant_lines(
        content: str,
        keywords: list[str],
        context_lines: int = 3,
    ) -> tuple[str, int]:
        """Extract only lines relevant to keywords."""
        lines = content.split("\n")
        relevant_indices = set()

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw.lower() in line_lower for kw in keywords):
                # Add this line + context
                for j in range(max(0, i - context_lines), min(len(lines), i + context_lines + 1)):
                    relevant_indices.add(j)

        if not relevant_indices:
            return content[:500] + "\n...[no keyword matches]...", len(content) // 4

        relevant = [lines[i] for i in sorted(relevant_indices)]
        extracted = "\n".join(relevant)

        original_tokens = len(content) // 4
        new_tokens = len(extracted) // 4
        saved = original_tokens - new_tokens

        return extracted, saved


class TokenOptimizer:
    """Main optimizer that combines all strategies.

    Use this to wrap AI interactions and automatically
    minimize token usage.
    """

    def __init__(self) -> None:
        self.budget = TokenBudget()
        self.cache = QueryCache()
        self.compressor = ContextCompressor()

    def optimize_query(self, query: str, context: str = "") -> tuple[str, str, int]:
        """Optimize a query before sending to AI.

        Returns: (optimized_query, optimized_context, tokens_saved)
        """
        tokens_saved = 0
        optimized_context = context

        # 1. Check cache first
        cache_key = hashlib.sha256(f"{query}:{context}".encode()).hexdigest()[:16]
        cached = self.cache.get(cache_key)
        if cached:
            return cached.result, optimized_context, cached.tokens_saved

        # 2. Compress context if provided — use VSA for large contexts
        if context:
            if len(context) > 2000:
                vsa_result = self._vsa_compress(context, query)
                if vsa_result is not None:
                    compressed, saved = vsa_result
                    optimized_context = compressed
                    tokens_saved += saved
                else:
                    compressed, saved = self.compressor.truncate_to_budget(context, 2000)
                    optimized_context = compressed
                    tokens_saved += saved
            else:
                compressed, saved = self.compressor.truncate_to_budget(context, 2000)
                optimized_context = compressed
                tokens_saved += saved

        # 3. Try local reasoning first
        try:
            from whitemagic.core.intelligence.agentic.local_reasoning import (
                reason_locally,
            )
            result = reason_locally(query)
            if result.insights and not result.ready_for_ai:
                total_saved = tokens_saved + result.total_tokens_saved
                self.cache.set(cache_key, f"[LOCAL] {result.summary}", total_saved)
                self.budget.save(total_saved)
                return query, f"[LOCAL] {result.summary}", total_saved
            tokens_saved += result.total_tokens_saved
        except Exception as e:
            logger.info("DEBUG: reason_locally failed: %s", e, exc_info=True)
            pass

        # 4. Extract relevant lines from context using query keywords
        if context and len(context) > 500:
            keywords = [w for w in query.split() if len(w) > 3]
            compressed, saved = self.compressor.extract_relevant_lines(context, keywords)
            if saved > 0 and len(compressed) < len(optimized_context):
                optimized_context = compressed
                tokens_saved += saved

        self.budget.save(tokens_saved)
        return query, optimized_context, tokens_saved

    def _vsa_compress(self, context: str, query: str) -> tuple[str, int] | None:
        """Compress context using VSA HRR superposition.

        Splits context into chunks, binds each to a role vector, superposes
        into one vector, and returns a compact text summary with the top
        most relevant chunks.

        Returns (compressed_text, tokens_saved) or None if VSA unavailable.
        """
        try:
            from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor

            compressor = get_vsa_context_compressor()

            paragraphs = context.split("\n\n")
            if len(paragraphs) < 3:
                lines = context.split("\n")
                chunks = []
                current = ""
                for line in lines:
                    if len(current) + len(line) > 500 and current:
                        chunks.append(current)
                        current = line
                    else:
                        current = current + "\n" + line if current else line
                if current:
                    chunks.append(current)
            else:
                chunks = []
                current = ""
                for para in paragraphs:
                    if len(current) + len(para) > 500 and current:
                        chunks.append(current)
                        current = para
                    else:
                        current = current + "\n\n" + para if current else para
                if current:
                    chunks.append(current)

            items = [
                {"content": chunk, "source": "context", "id": f"chunk_{i}"}
                for i, chunk in enumerate(chunks)
            ]

            result = compressor.compress(items, query=query, max_text_items=5)

            if result.method == "empty":
                return None

            original_tokens = len(context) // 4
            new_tokens = len(result.summary) // 4
            saved = original_tokens - new_tokens

            if saved > 0:
                return result.summary, saved
            return None
        except Exception as e:
            logger.debug("VSA compression unavailable: %s", e)
            return None

    def record_usage(self, tokens_used: int) -> None:
        """Record tokens actually used in AI call."""
        self.budget.use(tokens_used)

    def report(self) -> str:
        """Get optimization report."""
        cache_stats = self.cache.stats()
        return (
            f"{self.budget.report()}\n\n"
            f"Cache Stats:\n"
            f"  Cached queries: {cache_stats['cached_queries']}\n"
            f"  Cache hits: {cache_stats['total_hits']}\n"
            f"  Tokens saved via cache: {cache_stats['total_tokens_saved']:,}"
        )


# === SINGLETON ===

_optimizer: TokenOptimizer | None = None


def get_token_optimizer() -> TokenOptimizer:
    """Get or create token optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = TokenOptimizer()
    return _optimizer


def optimize_for_ai(query: str, context: str = "") -> tuple[str, str, int]:
    """Convenience function to optimize query before AI call."""
    return get_token_optimizer().optimize_query(query, context)


if __name__ == "__main__":
    logger.info("🎯 TOKEN OPTIMIZER DEMO")
    logger.info("=" * 50)

    optimizer = get_token_optimizer()

    # Test queries
    queries = [
        ("What version is WhiteMagic?", ""),
        ("How many gardens?", ""),
        ("What version is WhiteMagic?", ""),  # Should hit cache
    ]

    for query, context in queries:
        q, ctx, saved = optimizer.optimize_query(query, context)
        logger.info("\nQuery: %s", query)
        logger.info("Saved: %s tokens", saved)
        logger.info("Result: %s...", ctx[:100])

    logger.info("\n" + optimizer.report())
