"""Smart context preloading - predict and cache likely memories."""

from pathlib import Path
from typing import Dict, List, Optional, Set

# Role-based memory prediction map
ROLE_MEMORY_MAP: Dict[str, List[str]] = {
    "bug-fix": [
        "debugging",
        "common-issues",
        "error-patterns",
        "test-patterns",
        "troubleshooting",
    ],
    "feature": [
        "architecture",
        "api-design",
        "testing",
        "design-patterns",
        "best-practices",
    ],
    "audit": [
        "quality-checklist",
        "version-sync",
        "testing",
        "code-review",
        "security",
    ],
    "refactor": [
        "architecture",
        "design-patterns",
        "code-quality",
        "technical-debt",
        "testing",
    ],
    "documentation": [
        "writing-style",
        "documentation-patterns",
        "examples",
        "user-guides",
    ],
    "deployment": [
        "production",
        "deployment",
        "infrastructure",
        "monitoring",
        "rollback",
    ],
    "exploration": [
        "overview",
        "architecture",
        "getting-started",
        "roadmap",
    ],
}


class ContextPreloader:
    """Predictive memory preloading based on task type."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.short_term_dir = base_dir / "memory" / "short_term"
        self.long_term_dir = base_dir / "memory" / "long_term"
        self._cache: Dict[str, str] = {}
        self._preloaded: Set[str] = set()

    def get_predicted_tags(self, role: str) -> List[str]:
        """Get predicted tags for a given role.

        Args:
            role: Task role (e.g., "bug-fix", "feature")

        Returns:
            List of predicted relevant tags
        """
        # Normalize role
        role_key = role.lower().replace("_", "-").replace(" ", "-")

        # Get from map or return empty
        return ROLE_MEMORY_MAP.get(role_key, [])

    def preload_for_role(self, role: str, max_memories: int = 10) -> Dict[str, str]:
        """Preload likely memories for a role.

        Args:
            role: Task role
            max_memories: Maximum number of memories to preload

        Returns:
            Dict of {filename: content} for preloaded memories
        """
        predicted_tags = self.get_predicted_tags(role)

        if not predicted_tags:
            return {}

        # Find memories matching predicted tags
        candidates = []

        # Search short-term memories
        if self.short_term_dir.exists():
            for mem_file in self.short_term_dir.glob("*.md"):
                tags = self._extract_tags(mem_file)
                # Check if any predicted tag matches
                if any(tag in predicted_tags for tag in tags):
                    candidates.append(("short_term", mem_file))

        # Search long-term memories (prioritize these)
        if self.long_term_dir.exists():
            for mem_file in self.long_term_dir.glob("*.md"):
                tags = self._extract_tags(mem_file)
                if any(tag in predicted_tags for tag in tags):
                    # Long-term memories get priority
                    candidates.insert(0, ("long_term", mem_file))

        # Load top candidates
        preloaded = {}
        for mem_type, mem_file in candidates[:max_memories]:
            key = f"{mem_type}/{mem_file.name}"
            if key not in self._preloaded:
                try:
                    content = mem_file.read_text(encoding="utf-8")
                    self._cache[key] = content
                    self._preloaded.add(key)
                    preloaded[key] = content
                except Exception:
                    pass  # Skip problematic files

        return preloaded

    def get_from_cache(self, filename: str) -> Optional[str]:
        """Get memory from preload cache if available.

        Args:
            filename: Memory filename (e.g., "short_term/memory.md")

        Returns:
            Memory content if preloaded, None otherwise
        """
        return self._cache.get(filename)

    def clear_cache(self):
        """Clear preload cache."""
        self._cache.clear()
        self._preloaded.clear()

    def _extract_tags(self, mem_file: Path) -> Set[str]:
        """Extract tags from memory file.

        Args:
            mem_file: Path to memory file

        Returns:
            Set of tags found in the file
        """
        try:
            content = mem_file.read_text(encoding="utf-8")

            # Look for tags in first 500 chars (metadata section)
            header = content[:500].lower()

            tags = set()

            # Parse "Tags: tag1, tag2, tag3" format
            if "tags:" in header:
                tag_line = header.split("tags:")[1].split("\n")[0]
                raw_tags = tag_line.split(",")
                tags.update(tag.strip() for tag in raw_tags if tag.strip())

            # Parse #hashtag format
            for word in header.split():
                if word.startswith("#"):
                    tags.add(word[1:].strip(".,!?"))

            return tags
        except Exception:
            return set()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with cache size and preloaded count
        """
        total_size = sum(len(content) for content in self._cache.values())
        return {
            "memories_cached": len(self._cache),
            "total_size_bytes": total_size,
            "unique_memories": len(self._preloaded),
        }


# Global instance
_preloader: Optional[ContextPreloader] = None


def get_preloader(base_dir: Optional[Path] = None) -> ContextPreloader:
    """Get global preloader instance.

    Args:
        base_dir: Base directory (uses cwd if not provided)

    Returns:
        Global ContextPreloader instance
    """
    global _preloader

    if _preloader is None:
        if base_dir is None:
            base_dir = Path.cwd()
        _preloader = ContextPreloader(base_dir)

    return _preloader


def preload_for_role(role: str, max_memories: int = 10) -> Dict[str, str]:
    """Convenience function for preloading memories.

    Args:
        role: Task role (e.g., "bug-fix", "feature")
        max_memories: Maximum memories to preload

    Returns:
        Dict of preloaded memories
    """
    preloader = get_preloader()
    return preloader.preload_for_role(role, max_memories)


def get_predicted_tags(role: str) -> List[str]:
    """Get predicted tags for a role.

    Args:
        role: Task role

    Returns:
        List of predicted tags
    """
    preloader = get_preloader()
    return preloader.get_predicted_tags(role)
