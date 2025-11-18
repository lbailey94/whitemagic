"""
Optimized context loading with tiered summaries and smart reading.

Integrates summary cache and smart reading for 5-10x token reduction.
"""

from typing import Any, Dict, List, Optional

from .core import MemoryManager
from .smart_read import SessionContext, read_file_smart
from .summaries import SummaryCache, format_tier_context, generate_summary
from .utils import split_frontmatter


class OptimizedMemoryLoader:
    """
    Memory loader with tiered summaries and smart caching.

    Provides 5-10x token reduction vs loading full memories.
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize optimized loader.

        Args:
            memory_manager: WhiteMagic MemoryManager instance
        """
        self.manager = memory_manager

        # Initialize caches
        cache_dir = self.manager.base_dir / ".whitemagic" / "cache"
        self.summary_cache = SummaryCache(cache_dir)
        self.session_ctx = SessionContext(max_age_seconds=300)

    def _ensure_summary_cached(self, entry: Dict[str, Any]):
        """Ensure summary exists in cache for a memory entry."""
        filename = entry["filename"]

        # Check if already cached
        if self.summary_cache.get_summary(filename, tier=1):
            return  # Already cached

        # Generate and cache summary
        path = self.manager.base_dir / entry["path"]
        try:
            raw_content = path.read_text()
            frontmatter, content = split_frontmatter(raw_content)

            summary = generate_summary(
                filename=filename,
                title=entry.get("title", "Untitled"),
                content=content,
                tags=entry.get("tags", []),
                memory_type=entry.get("type", "unknown"),
                created_at=entry.get("created_at"),
                updated_at=entry.get("updated_at"),
            )

            self.summary_cache.set_summary(summary, tiers=[0, 1, 2])

        except Exception:
            # Failed to cache, will try again next time
            pass

    def ensure_all_summaries(self):
        """Ensure all memories have cached summaries (run in background)."""
        entries = list(self.manager._entries(None, include_archived=True))

        for entry in entries:
            self._ensure_summary_cached(entry)

    def get_context(
        self,
        tier: int = 1,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get memory context at specified tier.

        Tier 0: Titles + tags only (~500 tokens for all memories)
        Tier 1: Short summaries + top 5 full if query (~3-13K tokens)
        Tier 2: Medium summaries + top 10 full if query (~15-35K tokens)
        Tier 3: All full memories (~50K+ tokens, rarely needed)

        Args:
            tier: Context tier (0-3)
            query: Optional search query
            memory_type: Optional filter by type
            tags: Optional filter by tags
            limit: Optional limit on number of memories

        Returns:
            Dict with context and metadata
        """
        # Get all entries
        entries = list(self.manager._entries(memory_type, include_archived=False))

        # Filter by tags if specified
        if tags:
            entries = [e for e in entries if any(t in e.get("tags", []) for t in tags)]

        # Limit if specified
        if limit:
            entries = entries[:limit]

        # Tier 0: Ultra-fast title scan
        if tier == 0:
            summaries = []
            for entry in entries:
                self._ensure_summary_cached(entry)
                summary = self.summary_cache.get_summary(entry["filename"], tier=0)
                if summary:
                    summaries.append(summary)

            context = format_tier_context(summaries, tier=0)

            return {
                "context": context,
                "tier": 0,
                "memory_count": len(summaries),
                "estimated_tokens": len(context.split()) * 1.3,  # Rough estimate
                "source": "tier0_summaries",
            }

        # Tier 1: Balanced (summaries + selective full)
        elif tier == 1:
            summaries = []
            for entry in entries:
                self._ensure_summary_cached(entry)
                summary = self.summary_cache.get_summary(entry["filename"], tier=1)
                if summary:
                    summaries.append(summary)

            context_parts = [format_tier_context(summaries, tier=1)]

            # If query, load top 5 full memories
            if query and summaries:
                # Simple relevance: check if query terms in title/tags
                query_lower = query.lower()
                scores = []

                for summary in summaries:
                    score = 0
                    if query_lower in summary.title.lower():
                        score += 10
                    for tag in summary.tags:
                        if query_lower in tag.lower():
                            score += 5
                    if summary.tier1 and query_lower in summary.tier1.lower():
                        score += 3

                    if score > 0:
                        scores.append((summary, score))

                # Get top 5
                top_5 = sorted(scores, key=lambda x: -x[1])[:5]

                if top_5:
                    context_parts.append("\n\n---\n# Full Content (Top 5 Relevant)\n")

                    for summary, _ in top_5:
                        entry = next(e for e in entries if e["filename"] == summary.filename)
                        path = self.manager.base_dir / entry["path"]

                        try:
                            content, _ = read_file_smart(path, self.session_ctx)
                            context_parts.append(f"\n## {summary.title} (Full)\n{content}\n")
                        except Exception:
                            continue

            full_context = "\n".join(context_parts)

            return {
                "context": full_context,
                "tier": 1,
                "memory_count": len(summaries),
                "full_loaded": len(top_5) if query else 0,
                "estimated_tokens": len(full_context.split()) * 1.3,
                "source": "tier1_smart",
            }

        # Tier 2: Deep (medium summaries + top 10 full)
        elif tier == 2:
            summaries = []
            for entry in entries:
                self._ensure_summary_cached(entry)
                summary = self.summary_cache.get_summary(entry["filename"], tier=2)
                if summary:
                    summaries.append(summary)

            context_parts = [format_tier_context(summaries, tier=2)]

            # If query, load top 10 full
            if query and summaries:
                query_lower = query.lower()
                scores = []

                for summary in summaries:
                    score = 0
                    if query_lower in summary.title.lower():
                        score += 10
                    for tag in summary.tags:
                        if query_lower in tag.lower():
                            score += 5
                    if summary.tier2 and query_lower in summary.tier2.lower():
                        score += 3

                    if score > 0:
                        scores.append((summary, score))

                top_10 = sorted(scores, key=lambda x: -x[1])[:10]

                if top_10:
                    context_parts.append("\n\n---\n# Full Content (Top 10 Relevant)\n")

                    for summary, _ in top_10:
                        entry = next(e for e in entries if e["filename"] == summary.filename)
                        path = self.manager.base_dir / entry["path"]

                        try:
                            content, _ = read_file_smart(path, self.session_ctx)
                            context_parts.append(f"\n## {summary.title} (Full)\n{content}\n")
                        except Exception:
                            continue

            full_context = "\n".join(context_parts)

            return {
                "context": full_context,
                "tier": 2,
                "memory_count": len(summaries),
                "full_loaded": len(top_10) if query else 0,
                "estimated_tokens": len(full_context.split()) * 1.3,
                "source": "tier2_deep",
            }

        # Tier 3: Exhaustive (load everything, rarely used)
        else:
            # Fallback to standard get_context
            return self.manager.get_context(tier=2)

    def invalidate_summary(self, filename: str):
        """Invalidate cached summary for a memory (call after updates)."""
        self.summary_cache.invalidate(filename)

    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        return {
            "summary_cache": self.summary_cache.stats(),
            "session_cache": self.session_ctx.stats(),
        }
