"""
Memory summary generation and tiered loading system.

Implements 4-tier memory access:
- Tier 0: Titles + tags only (ultra-fast, ~500 tokens)
- Tier 1: Short summaries (3-5K tokens for all memories)
- Tier 2: Medium summaries (10-15K tokens)
- Tier 3: Full content (50K+ tokens, rarely needed)
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemorySummary:
    """Summary of a memory at different tiers."""

    filename: str
    title: str
    tags: List[str]
    memory_type: str
    tier0: str  # Just "title | tags"
    tier1: Optional[str] = None  # 1-2 sentence summary (50 tokens)
    tier2: Optional[str] = None  # 1 paragraph summary (200 tokens)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SummaryCache:
    """
    File-based cache for memory summaries.

    Stores summaries at different tiers to enable fast context loading.
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize summary cache.

        Args:
            cache_dir: Directory for summary cache files
        """
        self.cache_dir = Path(cache_dir) / "summaries"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Tier-specific subdirectories
        for tier in range(4):
            (self.cache_dir / f"tier{tier}").mkdir(exist_ok=True)

    def _get_cache_key(self, filename: str, content_hash: Optional[str] = None) -> str:
        """Generate cache key for a memory file."""
        if content_hash:
            return hashlib.sha256(f"{filename}:{content_hash}".encode()).hexdigest()[:16]
        return hashlib.sha256(filename.encode()).hexdigest()[:16]

    def _get_tier_path(self, tier: int) -> Path:
        """Get path for tier directory."""
        return self.cache_dir / f"tier{tier}"

    def get_summary(self, filename: str, tier: int = 1) -> Optional[MemorySummary]:
        """
        Get cached summary for a memory.

        Args:
            filename: Memory filename
            tier: Summary tier (0-2)

        Returns:
            MemorySummary or None if not cached
        """
        cache_key = self._get_cache_key(filename)
        cache_file = self._get_tier_path(tier) / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            return MemorySummary(**data)
        except Exception:
            return None

    def set_summary(self, summary: MemorySummary, tiers: List[int] = [0, 1, 2]):
        """
        Cache summary at specified tiers.

        Args:
            summary: MemorySummary to cache
            tiers: List of tiers to cache (default: all)
        """
        cache_key = self._get_cache_key(summary.filename)
        data = asdict(summary)

        for tier in tiers:
            cache_file = self._get_tier_path(tier) / f"{cache_key}.json"
            try:
                cache_file.write_text(json.dumps(data, indent=2))
            except Exception:
                pass

    def get_all_summaries(self, tier: int = 1) -> List[MemorySummary]:
        """
        Get all cached summaries at a specific tier.

        Args:
            tier: Summary tier (0-2)

        Returns:
            List of MemorySummary objects
        """
        summaries = []
        tier_dir = self._get_tier_path(tier)

        for cache_file in tier_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text())
                summaries.append(MemorySummary(**data))
            except Exception:
                continue

        return summaries

    def invalidate(self, filename: str):
        """Invalidate all cached summaries for a memory."""
        cache_key = self._get_cache_key(filename)

        for tier in range(4):
            cache_file = self._get_tier_path(tier) / f"{cache_key}.json"
            cache_file.unlink(missing_ok=True)

    def clear(self, tier: Optional[int] = None):
        """Clear cache for specific tier or all tiers."""
        if tier is not None:
            tier_dir = self._get_tier_path(tier)
            for cache_file in tier_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)
        else:
            for t in range(4):
                self.clear(tier=t)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {}

        for tier in range(4):
            tier_dir = self._get_tier_path(tier)
            files = list(tier_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)

            stats[f"tier{tier}"] = {
                "entries": len(files),
                "size_bytes": total_size,
                "size_kb": total_size / 1024,
            }

        return stats


def generate_tier0_summary(title: str, tags: List[str], memory_type: str) -> str:
    """
    Generate tier 0 summary (titles + tags only).

    Ultra-fast, minimal tokens (~20 per memory).

    Args:
        title: Memory title
        tags: List of tags
        memory_type: Memory type

    Returns:
        Tier 0 summary string
    """
    tags_str = ", ".join(tags) if tags else "no-tags"
    return f"[{memory_type}] {title} | {tags_str}"


def generate_tier1_summary(title: str, content: str, max_length: int = 100) -> str:
    """
    Generate tier 1 summary (1-2 sentences, ~50 tokens).

    Quick extraction from first paragraph or simple truncation.

    Args:
        title: Memory title
        content: Full memory content
        max_length: Maximum characters for summary

    Returns:
        Tier 1 summary string
    """
    # Try to extract first paragraph
    lines = content.strip().split("\n")
    first_paragraph = []

    for line in lines:
        line = line.strip()
        if not line:
            if first_paragraph:
                break
        elif not line.startswith("#"):  # Skip headers
            first_paragraph.append(line)

    if first_paragraph:
        summary = " ".join(first_paragraph)
    else:
        # Fallback: use first N characters
        summary = content.replace("\n", " ").strip()

    # Truncate to max_length
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit(" ", 1)[0] + "..."

    return summary


def generate_tier2_summary(title: str, content: str, max_length: int = 500) -> str:
    """
    Generate tier 2 summary (1 paragraph, ~200 tokens).

    More comprehensive summary including key points.

    Args:
        title: Memory title
        content: Full memory content
        max_length: Maximum characters for summary

    Returns:
        Tier 2 summary string
    """
    # Extract key sections (headers, first sentences, etc.)
    lines = content.strip().split("\n")
    key_points = []
    current_section = []

    for line in lines:
        line = line.strip()

        # Headers are important
        if line.startswith("#"):
            if current_section:
                key_points.append(" ".join(current_section))
                current_section = []
            key_points.append(line.replace("#", "").strip())

        # First sentence of each paragraph
        elif line and not current_section:
            current_section.append(line)

        # Empty line ends section
        elif not line and current_section:
            key_points.append(" ".join(current_section))
            current_section = []

    # Add final section
    if current_section:
        key_points.append(" ".join(current_section))

    summary = ". ".join(key_points[:5])  # Top 5 key points

    # Truncate to max_length
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit(".", 1)[0] + "..."

    return summary


def generate_summary(
    filename: str,
    title: str,
    content: str,
    tags: List[str],
    memory_type: str,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> MemorySummary:
    """
    Generate complete multi-tier summary for a memory.

    Args:
        filename: Memory filename
        title: Memory title
        content: Full memory content
        tags: List of tags
        memory_type: Memory type
        created_at: Creation timestamp
        updated_at: Update timestamp

    Returns:
        MemorySummary with all tiers generated
    """
    return MemorySummary(
        filename=filename,
        title=title,
        tags=tags,
        memory_type=memory_type,
        tier0=generate_tier0_summary(title, tags, memory_type),
        tier1=generate_tier1_summary(title, content),
        tier2=generate_tier2_summary(title, content),
        created_at=created_at,
        updated_at=updated_at,
    )


def format_tier_context(summaries: List[MemorySummary], tier: int = 1) -> str:
    """
    Format summaries into context string for AI.

    Args:
        summaries: List of MemorySummary objects
        tier: Which tier to use (0-2)

    Returns:
        Formatted context string
    """
    if tier == 0:
        # Ultra-compact listing
        lines = [f"- {s.tier0}" for s in summaries]
        return f"# Memory Index ({len(summaries)} memories)\n\n" + "\n".join(lines)

    elif tier == 1:
        # Short summaries with basic metadata
        lines = []
        for s in summaries:
            lines.append(f"## {s.title}")
            lines.append(f"**Type**: {s.memory_type} | **Tags**: {', '.join(s.tags)}")
            lines.append(f"{s.tier1}\n")

        return f"# Memory Summaries ({len(summaries)} memories)\n\n" + "\n".join(lines)

    elif tier == 2:
        # Medium summaries with full metadata
        lines = []
        for s in summaries:
            lines.append(f"## {s.title}")
            lines.append(f"**Type**: {s.memory_type} | **File**: `{s.filename}`")
            lines.append(f"**Tags**: {', '.join(s.tags)}")
            if s.created_at:
                lines.append(f"**Created**: {s.created_at}")
            lines.append(f"\n{s.tier2}\n")

        return f"# Detailed Memory Summaries ({len(summaries)} memories)\n\n" + "\n".join(lines)

    else:
        return "# Invalid tier requested"
