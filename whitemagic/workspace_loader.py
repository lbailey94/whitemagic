"""
Hierarchical Workspace Loader - Optimized context loading for AI sessions.

Reduces initial token burn from ~20K to ~6-8K by loading only relevant
workspace areas based on current task context.

Philosophy:
- Load what you need, when you need it
- Lazy-load other areas on-demand
- Smart detection of task-relevant directories

Based on Art of War principle: "Know your terrain" (知地形)
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DirectoryInfo:
    """Information about a directory in the workspace."""

    path: Path
    name: str
    file_count: int
    subdirs: List[str]
    relevance_score: float = 0.0
    description: Optional[str] = None


@dataclass
class WorkspaceContext:
    """Context about what workspace areas are needed."""

    task_type: str  # e.g., "implementation", "debugging", "documentation"
    keywords: List[str]
    relevant_paths: List[Path]
    excluded_patterns: List[str]


class WorkspaceLoader:
    """
    Intelligent workspace loader that minimizes token usage.

    Uses tiered loading strategy:
    - Tier 0: Project root + task-relevant dirs only (~2K tokens)
    - Tier 1: + Adjacent/related dirs (~4-5K tokens)
    - Tier 2: Full workspace tree (~15-20K tokens)
    """

    # Default relevance rules for different task types
    TASK_RELEVANCE_MAP = {
        "implementation": {
            "high": ["whitemagic/", "tests/", "examples/"],
            "medium": ["docs/guides/", "scripts/"],
            "low": ["docs/archive/", "backups/", ".github/"],
        },
        "debugging": {
            "high": ["whitemagic/", "tests/", "logs/"],
            "medium": ["scripts/", "docs/guides/"],
            "low": ["docs/archive/", "backups/", ".github/"],
        },
        "documentation": {
            "high": ["docs/", "README.md", "CHANGELOG.md"],
            "medium": ["whitemagic/", "examples/"],
            "low": ["tests/", "backups/", ".github/"],
        },
        "testing": {
            "high": ["tests/", "whitemagic/"],
            "medium": ["scripts/", "examples/"],
            "low": ["docs/", "backups/", ".github/"],
        },
        "optimization": {
            "high": ["whitemagic/", "tests/", "docs/guides/"],
            "medium": ["scripts/", "examples/"],
            "low": ["docs/archive/", "backups/", ".github/"],
        },
    }

    # Always exclude these from initial load
    DEFAULT_EXCLUDES = [
        "node_modules/",
        ".git/",
        "__pycache__/",
        "*.pyc",
        ".pytest_cache/",
        ".venv/",
        "venv/",
        "dist/",
        "build/",
        "*.egg-info/",
        "backups/",
        ".whitemagic_audit/",
    ]

    def __init__(self, workspace_root: Path):
        """
        Initialize workspace loader.

        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self._dir_cache: Dict[Path, DirectoryInfo] = {}

    def load_for_task(
        self, task_description: str, tier: int = 0, additional_paths: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Load workspace context optimized for a specific task.

        Args:
            task_description: Description of the task (e.g., "Implement symbolic reasoning")
            tier: Loading tier (0=minimal, 1=balanced, 2=full)
            additional_paths: Extra paths to always include

        Returns:
            Dictionary with workspace structure and metadata
        """
        # Detect task type from description
        task_type = self._detect_task_type(task_description)

        # Extract keywords
        keywords = self._extract_keywords(task_description)

        # Get relevant directories
        relevant_dirs = self._get_relevant_directories(task_type, keywords, tier, additional_paths)

        # Build hierarchical structure
        structure = self._build_structure(relevant_dirs, tier)

        return {
            "task_type": task_type,
            "tier": tier,
            "keywords": keywords,
            "structure": structure,
            "excluded_count": self._count_excluded(),
            "token_estimate": self._estimate_tokens(structure),
            "lazy_load_available": tier < 2,
        }

    def _detect_task_type(self, description: str) -> str:
        """Detect task type from description."""
        desc_lower = description.lower()

        # Priority order matters
        if any(word in desc_lower for word in ["implement", "create", "add", "build"]):
            return "implementation"
        elif any(word in desc_lower for word in ["debug", "fix", "error", "bug"]):
            return "debugging"
        elif any(word in desc_lower for word in ["document", "doc", "readme", "guide"]):
            return "documentation"
        elif any(word in desc_lower for word in ["test", "verify", "validate"]):
            return "testing"
        elif any(word in desc_lower for word in ["optimize", "improve", "enhance", "performance"]):
            return "optimization"
        else:
            return "implementation"  # Default

    def _extract_keywords(self, description: str) -> List[str]:
        """Extract relevant keywords from task description."""
        # Simple keyword extraction
        words = description.lower().split()

        # Filter common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        keywords = [w.strip(".,!?;:") for w in words if w not in stop_words and len(w) > 3]

        return keywords[:10]  # Limit to top 10

    def _get_relevant_directories(
        self,
        task_type: str,
        keywords: List[str],
        tier: int,
        additional_paths: Optional[List[str]] = None,
    ) -> List[Path]:
        """Get list of relevant directories based on task and tier."""
        relevant = set()

        # Always include root-level files
        relevant.add(self.workspace_root)

        # Add task-specific directories
        if task_type in self.TASK_RELEVANCE_MAP:
            relevance_map = self.TASK_RELEVANCE_MAP[task_type]

            # Tier 0: Only high relevance
            if tier >= 0:
                for pattern in relevance_map["high"]:
                    relevant.update(self._find_matching_dirs(pattern))

            # Tier 1: + medium relevance
            if tier >= 1:
                for pattern in relevance_map["medium"]:
                    relevant.update(self._find_matching_dirs(pattern))

            # Tier 2: + low relevance (basically everything)
            if tier >= 2:
                for pattern in relevance_map["low"]:
                    relevant.update(self._find_matching_dirs(pattern))

        # Add keyword-matched directories
        if keywords:
            for keyword in keywords:
                relevant.update(self._find_dirs_containing_keyword(keyword))

        # Add additional paths if specified
        if additional_paths:
            for path_str in additional_paths:
                path = self.workspace_root / path_str
                if path.exists():
                    relevant.add(path)

        return sorted(relevant)

    def _find_matching_dirs(self, pattern: str) -> Set[Path]:
        """Find directories matching a pattern."""
        matches = set()
        pattern_path = self.workspace_root / pattern

        if pattern_path.exists():
            matches.add(pattern_path)
        else:
            # Try as glob pattern
            try:
                matches.update(self.workspace_root.glob(pattern))
            except:
                pass

        return matches

    def _find_dirs_containing_keyword(self, keyword: str) -> Set[Path]:
        """Find directories whose name contains the keyword."""
        matches = set()

        for root, dirs, _ in os.walk(self.workspace_root):
            # Skip excluded patterns
            if any(excl in root for excl in self.DEFAULT_EXCLUDES):
                continue

            for dir_name in dirs:
                if keyword in dir_name.lower():
                    matches.add(Path(root) / dir_name)

        return matches

    def _build_structure(self, relevant_dirs: List[Path], tier: int) -> Dict:
        """Build hierarchical structure representation."""
        structure = {
            "root": str(self.workspace_root),
            "directories": [],
            "files": [],
            "collapsed": [],  # Dirs available but not shown
        }

        # Get root-level files
        try:
            for item in self.workspace_root.iterdir():
                if item.is_file() and not self._should_exclude(item):
                    structure["files"].append(
                        {"name": item.name, "size": item.stat().st_size, "type": "file"}
                    )
        except PermissionError:
            pass

        # Add relevant directories
        for dir_path in relevant_dirs:
            if dir_path == self.workspace_root:
                continue

            dir_info = self._get_dir_info(dir_path)
            structure["directories"].append(
                {
                    "path": str(dir_path.relative_to(self.workspace_root)),
                    "name": dir_path.name,
                    "file_count": dir_info.file_count,
                    "subdirs": dir_info.subdirs[:5],  # Limit subdir list
                }
            )

        # Note collapsed directories for tier 0/1
        if tier < 2:
            all_dirs = set(self.workspace_root.iterdir())
            shown_dirs = set(relevant_dirs)
            collapsed = all_dirs - shown_dirs

            structure["collapsed"] = [
                d.name for d in collapsed if d.is_dir() and not self._should_exclude(d)
            ]

        return structure

    def _get_dir_info(self, dir_path: Path) -> DirectoryInfo:
        """Get information about a directory (cached)."""
        if dir_path in self._dir_cache:
            return self._dir_cache[dir_path]

        try:
            files = [f for f in dir_path.iterdir() if f.is_file()]
            subdirs = [d.name for d in dir_path.iterdir() if d.is_dir()]

            info = DirectoryInfo(
                path=dir_path, name=dir_path.name, file_count=len(files), subdirs=subdirs
            )

            self._dir_cache[dir_path] = info
            return info

        except PermissionError:
            return DirectoryInfo(path=dir_path, name=dir_path.name, file_count=0, subdirs=[])

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        return any(excl in path_str for excl in self.DEFAULT_EXCLUDES)

    def _count_excluded(self) -> int:
        """Count how many items were excluded."""
        # Approximate count
        excluded = 0
        for excl in self.DEFAULT_EXCLUDES:
            excl_path = self.workspace_root / excl.rstrip("/")
            if excl_path.exists() and excl_path.is_dir():
                try:
                    excluded += sum(1 for _ in excl_path.rglob("*"))
                except:
                    pass
        return excluded

    def _estimate_tokens(self, structure: Dict) -> int:
        """Estimate token count for the structure."""
        # Rough estimate: ~4 chars per token
        json_str = json.dumps(structure, indent=2)
        return len(json_str) // 4

    def get_lazy_loadable_dirs(self) -> List[str]:
        """Get list of directories available for lazy loading."""
        all_dirs = []
        try:
            for item in self.workspace_root.iterdir():
                if item.is_dir() and not self._should_exclude(item):
                    all_dirs.append(item.name)
        except PermissionError:
            pass

        return sorted(all_dirs)

    def load_directory(self, relative_path: str, max_depth: int = 2) -> Dict:
        """
        Load a specific directory on-demand.

        Args:
            relative_path: Path relative to workspace root
            max_depth: Maximum depth to traverse

        Returns:
            Directory structure
        """
        dir_path = self.workspace_root / relative_path

        if not dir_path.exists():
            raise ValueError(f"Directory not found: {relative_path}")

        structure = self._walk_directory(dir_path, max_depth, current_depth=0)
        structure["token_estimate"] = self._estimate_tokens(structure)

        return structure

    def _walk_directory(self, path: Path, max_depth: int, current_depth: int) -> Dict:
        """Recursively walk a directory up to max depth."""
        if current_depth >= max_depth or self._should_exclude(path):
            return {}

        structure = {
            "path": str(path.relative_to(self.workspace_root)),
            "name": path.name,
            "items": [],
        }

        try:
            for item in sorted(path.iterdir()):
                if self._should_exclude(item):
                    continue

                if item.is_file():
                    structure["items"].append(
                        {"name": item.name, "type": "file", "size": item.stat().st_size}
                    )
                elif item.is_dir():
                    substructure = self._walk_directory(item, max_depth, current_depth + 1)
                    if substructure:
                        structure["items"].append(substructure)
        except PermissionError:
            structure["error"] = "Permission denied"

        return structure


def load_workspace_for_task(
    workspace_root: str,
    task_description: str,
    tier: int = 0,
    additional_paths: Optional[List[str]] = None,
) -> Dict:
    """
    Convenience function to load workspace context for a task.

    Args:
        workspace_root: Path to workspace root
        task_description: What task is being performed
        tier: Loading tier (0=minimal, 1=balanced, 2=full)
        additional_paths: Extra paths to include

    Returns:
        Workspace context optimized for the task

    Example:
        >>> context = load_workspace_for_task(
        ...     "/home/user/project",
        ...     "Implement symbolic reasoning module",
        ...     tier=0
        ... )
        >>> print(f"Token estimate: {context['token_estimate']}")
        Token estimate: 2100
    """
    loader = WorkspaceLoader(Path(workspace_root))
    return loader.load_for_task(task_description, tier, additional_paths)
