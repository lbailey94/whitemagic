"""🌸 Garden Directory — File-to-Garden Mapping Registry.

Maps every file in the WhiteMagic codebase to its primary garden,
enabling intuitive navigation and MCP discoverability.

Architecture:
- Virtual organization (files stay in place, metadata in registry)
- 28-fold mapping to gardens/ganas
- Keyword + path + import analysis for affinity scoring
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import GARDEN_REGISTRY_PATH
from whitemagic.core.intelligence.garden_gana_registry import (
    GARDEN_GANA_REGISTRY,
    calculate_resonance,
    get_by_garden,
)


@dataclass
class FileGardenMapping:
    """Mapping of a file to its garden affinity."""

    file_path: str
    primary_garden: str
    resonant_gardens: list[str] = field(default_factory=list)
    quadrant: str = ""
    element: str = ""
    gana: str = ""
    gana_tool: str = ""
    confidence: float = 0.0
    mapping_reason: str = ""
    file_type: str = ""
    loc_count: int = 0
    public_functions: list[str] = field(default_factory=list)


# Garden affinity keywords for automatic classification
GARDEN_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "wonder": {
        "keywords": ["curiosity", "explore", "discover", "begin", "start", "init", "wonder", "question", "seek"],
        "paths": ["wonder", "discovery", "curiosity", "search/", "query"],
    },
    "stillness": {
        "keywords": ["calm", "pause", "reflect", "stable", "remember", "still", "quiet", "meditat", "rest"],
        "paths": ["stillness", "memory/", "cache", "stable", "persist"],
    },
    "healing": {
        "keywords": ["heal", "fix", "repair", "restore", "health", "recover", "remedy", "cure", "wellness"],
        "paths": ["healing", "health", "repair", "fix", "recovery", "immune/"],
    },
    "sanctuary": {
        "keywords": ["safe", "home", "refuge", "protect", "secure", "shelter", "guard", "sanctuary", "lock"],
        "paths": ["sanctuary", "safe", "protect", "security/", "guard", "shelter/"],
    },
    "love": {
        "keywords": ["love", "care", "connect", "heart", "compassion", "affection", "embrace", "cherish"],
        "paths": ["love", "heart", "care", "compassion", "emotion"],
    },
    "courage": {
        "keywords": ["brave", "push", "accelerate", "challenge", "dare", "courage", "risk", "bold", "venture"],
        "paths": ["courage", "accelerat", "challenge", "risk", "venture", "bold"],
    },
    "wisdom": {
        "keywords": ["wisdom", "discern", "filter", "separate", "judge", "insight", "knowledge", "learn", "teach"],
        "paths": ["wisdom", "knowledge", "learn", "teach", "filter", "discern"],
    },
    "dharma": {
        "keywords": ["guide", "strategy", "govern", "ethics", "dharma", "rule", "law", "principle", "doctrine"],
        "paths": ["dharma", "govern", "strategy", "doctrine", "policy", "rule"],
    },
    "patience": {
        "keywords": ["wait", "patient", "endure", "persist", "time", "steady", "persevere", "tolerance"],
        "paths": ["patience", "endurance", "persist", "temporal/", "time"],
    },
    "connection": {
        "keywords": ["connect", "nurture", "relationship", "bond", "community", "link", "network", "bridge"],
        "paths": ["connection", "bridge/", "network", "link", "relation", "gan_ying"],
    },
    "mystery": {
        "keywords": ["mystery", "void", "empty", "optimize", "unknown", "hidden", "secret", "occult", "dream"],
        "paths": ["mystery", "dream/", "void", "hidden", "secret", "occult"],
    },
    "protection": {
        "keywords": ["protect", "shelter", "guard", "shield", "defend", "secure", "safety", "armor"],
        "paths": ["protection", "guard", "shield", "defend", "security/", "armor"],
    },
    "transformation": {
        "keywords": ["transform", "change", "transition", "evolve", "handoff", "convert", "morph", "shift"],
        "paths": ["transform", "evolution/", "change", "convert", "morph"],
    },
    "truth": {
        "keywords": ["truth", "boundary", "limit", "alert", "verify", "fact", "real", "honest", "authentic"],
        "paths": ["truth", "boundary", "verify", "validat", "alert", "audit"],
    },
    "awe": {
        "keywords": ["awe", "balance", "equilibrium", "stand", "marvel", "wonder", "amaz", "stun", "breath"],
        "paths": ["awe", "balance", "equilibrium", "marvel"],
    },
    "gratitude": {
        "keywords": ["thank", "grateful", "harvest", "gather", "abundance", "appreciate", "bless", "gift"],
        "paths": ["gratitude", "harvest", "gather", "abundance", "bless"],
    },
    "creation": {
        "keywords": ["create", "make", "build", "digest", "process", "generat", "construct", "forge"],
        "paths": ["creation", "build", "generat", "construct", "forge", "synthesis/"],
    },
    "presence": {
        "keywords": ["focus", "present", "attention", "detail", "here", "now", "mindful", "aware"],
        "paths": ["presence", "focus", "attention", "mindful", "aware"],
    },
    "play": {
        "keywords": ["play", "fun", "game", "capture", "explore", "toy", "experiment", "toy", "demo"],
        "paths": ["play", "game", "toy", "demo", "experiment"],
    },
    "practice": {
        "keywords": ["practice", "train", "discipline", "precise", "skill", "drill", "exercise", "repeat"],
        "paths": ["practice", "train", "discipline", "skill", "drill", "agent"],
    },
    "reverence": {
        "keywords": ["revere", "sacred", "honor", "respect", "renew", "worship", "holy", "divine", "grail"],
        "paths": ["reverence", "sacred", "honor", "grail", "divine", "grimoire/"],
    },
    "joy": {
        "keywords": ["joy", "happy", "celebrate", "abundant", "overflow", "delight", "bliss", "cheer"],
        "paths": ["joy", "celebrate", "delight", "bliss", "happy"],
    },
    "adventure": {
        "keywords": ["adventure", "journey", "travel", "move", "discover", "expedition", "quest", "roam"],
        "paths": ["adventure", "journey", "travel", "quest", "expedition"],
    },
    "beauty": {
        "keywords": ["beauty", "aesthetic", "fly", "expand", "soar", "grace", "elegant", "art", "style"],
        "paths": ["beauty", "aesthetic", "style", "art", "grace", "elegant"],
    },
    "humor": {
        "keywords": ["humor", "laugh", "flexible", "resilient", "bend", "joke", "wit", "comic", "fun"],
        "paths": ["humor", "laugh", "joke", "wit", "comic", "resilien"],
    },
    "voice": {
        "keywords": ["voice", "speak", "express", "illuminate", "shine", "say", "tell", "announce", "cli"],
        "paths": ["voice", "cli/", "speak", "express", "announce", "command"],
    },
    "sangha": {
        "keywords": ["community", "together", "sangha", "collective", "network", "group", "team", "collab"],
        "paths": ["sangha", "community", "collective", "team", "group", "collab"],
    },
    "grief": {
        "keywords": ["grief", "loss", "mourn", "remember", "honor", "sad", "sorrow", "farewell", "passing"],
        "paths": ["grief", "mourn", "loss", "sorrow", "farewell"],
    },
}

# Path-based garden hints (directory → garden mapping)
PATH_GARDEN_HINTS: dict[str, str] = {
    "whitemagic/core/memory/": "wisdom",
    "whitemagic/core/dreaming/": "mystery",
    "whitemagic/core/intelligence/": "wisdom",
    "whitemagic/core/immune/": "healing",
    "whitemagic/core/evolution/": "transformation",
    "whitemagic/core/resonance/": "connection",
    "whitemagic/core/governance/": "dharma",
    "whitemagic/core/consciousness/": "mystery",
    "whitemagic/core/ganas/": "sangha",
    "whitemagic/core/gardens/": "sangha",
    "whitemagic/gardens/": "sangha",
    "whitemagic/tools/": "voice",
    "whitemagic/cli/": "voice",
    "whitemagic/agents/": "practice",
    "whitemagic/grimoire/": "reverence",
    "whitemagic/dharma/": "dharma",
    "whitemagic/shelter/": "sanctuary",
    "whitemagic/oms/": "wisdom",
    "whitemagic/payments/": "abundance",
    "whitemagic/marketplace/": "connection",
    "whitemagic/search/": "wonder",
    "whitemagic/integration/": "connection",
    "whitemagic/intake/": "creation",
    "whitemagic/ecology/": "sangha",
    "whitemagic/alchemy/": "transformation",
    "whitemagic/acceleration/": "courage",
    "whitemagic/bridge/": "connection",
    "whitemagic/zodiac/": "mystery",
    "whitemagic/patterns/": "wisdom",
    "whitemagic/monitoring/": "truth",
    "whitemagic/automation/": "practice",
    "whitemagic/learning/": "wisdom",
    "whitemagic/scoring/": "truth",
    "whitemagic/storage/": "sanctuary",
    "whitemagic/streaming/": "connection",
    "whitemagic/temporal/": "patience",
    "whitemagic/boundaries/": "truth",
    "whitemagic/fusion/": "transformation",
    "whitemagic/engines/": "creation",
    "whitemagic/nurturing/": "love",
    "whitemagic/alignment/": "truth",
    "whitemagic/plugin/": "play",
    "whitemagic/personality/": "love",
    "whitemagic/identity/": "love",
    "whitemagic/user.py": "love",
    "whitemagic/governor.py": "dharma",
    "whitemagic/homeostasis.py": "healing",
    "whitemagic/embodiment.py": "creation",
    "whitemagic/nervous_system.py": "connection",
    "whitemagic/wuxing_scheduler.py": "patience",
    "whitemagic/continuity.py": "patience",
    "whitemagic/semantic_fs.py": "wisdom",
    "scripts/": "practice",
    "tests/": "truth",
    "eval/": "truth",
    "docs/": "voice",
    "examples/": "play",
    "whitemagic-rust/": "courage",
    "whitemagic-mojo/": "courage",
    "whitemagic-zig/": "courage",
    "whitemagic-go/": "adventure",
    "whitemagic-koka/": "play",
    "whitemagic-julia/": "play",
    "whitemagic-haskell/": "wisdom",
    "whitemagic-elixir/": "connection",
    "elixir/": "connection",
    "haskell/": "wisdom",
    "koka-clones/": "play",
    "mesh/": "connection",
    "nexus/": "beauty",
    "sdk/": "voice",
    "models/": "wisdom",
    "monte_carlo_output/": "play",
    "geneseed/": "creation",
    "mandalaos-": "mystery",
}


class GardenDirectory:
    """Registry for file-to-garden mappings."""

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or GARDEN_REGISTRY_PATH
        self._file_mappings: dict[str, FileGardenMapping] = {}
        self._garden_files: dict[str, list[str]] = {g: [] for g in GARDEN_KEYWORDS.keys()}
        self._loaded = False

    def load(self) -> bool:
        """Load registry from disk."""
        if self._loaded:
            return True
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text())
                for fp, mapping_data in data.get("file_mappings", {}).items():
                    self._file_mappings[fp] = FileGardenMapping(**mapping_data)
                self._rebuild_garden_index()
                self._loaded = True
                return True
            except Exception:
                pass
        return False

    def save(self) -> None:
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "file_mappings": {
                fp: {
                    "file_path": m.file_path,
                    "primary_garden": m.primary_garden,
                    "resonant_gardens": m.resonant_gardens,
                    "quadrant": m.quadrant,
                    "element": m.element,
                    "gana": m.gana,
                    "gana_tool": m.gana_tool,
                    "confidence": m.confidence,
                    "mapping_reason": m.mapping_reason,
                    "file_type": m.file_type,
                    "loc_count": m.loc_count,
                    "public_functions": m.public_functions,
                }
                for fp, m in self._file_mappings.items()
            },
            "garden_files": self._garden_files,
            "stats": self.get_stats(),
        }
        self.registry_path.write_text(json.dumps(data, indent=2))

    def _rebuild_garden_index(self) -> None:
        """Rebuild the garden→files index from file mappings."""
        self._garden_files = {g: [] for g in GARDEN_KEYWORDS.keys()}
        for fp, mapping in self._file_mappings.items():
            if mapping.primary_garden in self._garden_files:
                self._garden_files[mapping.primary_garden].append(fp)

    def register_file(self, mapping: FileGardenMapping) -> None:
        """Register a file mapping."""
        self._file_mappings[mapping.file_path] = mapping
        if mapping.primary_garden in self._garden_files:
            self._garden_files[mapping.primary_garden].append(mapping.file_path)
        self._loaded = True

    def get_file_mapping(self, file_path: str) -> FileGardenMapping | None:
        """Get mapping for a specific file."""
        return self._file_mappings.get(file_path)

    def get_garden_files(self, garden: str, file_type: str | None = None) -> list[str]:
        """Get all files for a garden, optionally filtered by type."""
        files = self._garden_files.get(garden, [])
        if file_type:
            files = [f for f in files if f.endswith(f".{file_type}")]
        return files

    def get_all_gardens(self) -> list[str]:
        """Get list of all garden names."""
        return list(GARDEN_KEYWORDS.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        stats: dict[str, Any] = {
            "total_files": len(self._file_mappings),
            "gardens": {},
            "file_types": {},
            "orphan_files": [],
        }
        for garden, files in self._garden_files.items():
            stats["gardens"][garden] = len(files)
        for fp in self._file_mappings:
            ext = Path(fp).suffix or "unknown"
            stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
        return stats

    def search_files(self, query: str, gardens: list[str] | None = None) -> list[FileGardenMapping]:
        """Search for files by name/path within gardens."""
        results = []
        query_lower = query.lower()
        search_gardens = gardens or list(GARDEN_KEYWORDS.keys())
        for garden in search_gardens:
            for fp in self._garden_files.get(garden, []):
                if query_lower in fp.lower():
                    mapping = self._file_mappings.get(fp)
                    if mapping:
                        results.append(mapping)
        return results


def analyze_file_for_garden(
    file_path: str,
    content: str | None = None,
    public_functions: list[str] | None = None,
) -> FileGardenMapping:
    """Analyze a file and determine its garden affinity.

    Uses multiple signals:
    1. Path-based hints (directory structure)
    2. Keyword resonance in content
    3. Function names
    4. Import patterns
    """
    path_lower = file_path.lower()

    # Start with path-based hint
    primary_garden = "mystery"  # default
    confidence = 0.0
    reason = "default"

    # Check path hints first (highest confidence for structural organization)
    for hint_path, garden in PATH_GARDEN_HINTS.items():
        if hint_path.lower() in path_lower:
            primary_garden = garden
            confidence = 0.8
            reason = f"path_hint:{hint_path}"
            break

    # Analyze content if available
    if content:
        content_lower = content.lower()

        # Calculate resonance scores for each garden
        garden_scores: dict[str, float] = {}

        for garden, data in GARDEN_KEYWORDS.items():
            score = 0.0

            # Keyword matches
            for kw in data.get("keywords", []):
                if kw in content_lower:
                    score += 1.0

            # Path matches
            for path_hint in data.get("paths", []):
                if path_hint in path_lower:
                    score += 2.0  # Path matches are stronger

            if score > 0:
                garden_scores[garden] = score

        # Use resonance calculation from registry
        resonance = calculate_resonance(content[:1000] if len(content) > 1000 else content)
        for garden, res_data in resonance.items():
            if garden in garden_scores:
                garden_scores[garden] += res_data.get("score", 0) * 0.5
            else:
                garden_scores[garden] = res_data.get("score", 0) * 0.5

        # Pick highest scoring garden
        if garden_scores:
            best_garden = max(garden_scores.keys(), key=lambda g: garden_scores[g])
            best_score = garden_scores[best_garden]

            # Only override path hint if content score is significantly higher
            if best_score > 3.0 or confidence < 0.5:
                primary_garden = best_garden
                confidence = min(0.95, best_score / 10.0)
                reason = f"content_analysis:score={best_score:.1f}"

    # Analyze function names if available
    if public_functions:
        func_text = " ".join(public_functions).lower()
        for garden, data in GARDEN_KEYWORDS.items():
            for kw in data.get("keywords", []):
                if kw in func_text:
                    if garden != primary_garden:
                        # Add as resonant garden
                        pass

    # Get garden metadata from registry
    garden_entry = get_by_garden(primary_garden)
    quadrant = garden_entry.quadrant.value if garden_entry else ""
    element = garden_entry.element.value if garden_entry else ""
    gana = garden_entry.gana if garden_entry else ""
    gana_tool = garden_entry.gana_tool if garden_entry else ""

    # Determine file type
    ext = Path(file_path).suffix
    file_type_map = {
        ".py": "python",
        ".rs": "rust",
        ".ex": "elixir",
        ".exs": "elixir",
        ".go": "go",
        ".mojo": "mojo",
        ".zig": "zig",
        ".hs": "haskell",
        ".kk": "koka",
        ".jl": "julia",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sh": "shell",
    }
    file_type = file_type_map.get(ext, ext.lstrip(".") if ext else "unknown")

    # Count LOC if content available
    loc_count = 0
    if content:
        loc_count = len([line for line in content.split("\n") if line.strip() and not line.strip().startswith("#")])

    return FileGardenMapping(
        file_path=file_path,
        primary_garden=primary_garden,
        resonant_gardens=[],
        quadrant=quadrant,
        element=element,
        gana=gana,
        gana_tool=gana_tool,
        confidence=confidence,
        mapping_reason=reason,
        file_type=file_type,
        loc_count=loc_count,
        public_functions=public_functions or [],
    )


# Singleton instance
_directory: GardenDirectory | None = None


def get_garden_directory() -> GardenDirectory:
    """Get the global garden directory instance."""
    global _directory
    if _directory is None:
        _directory = GardenDirectory()
        _directory.load()
    return _directory


def get_files_in_garden(garden: str, file_type: str | None = None) -> list[str]:
    """Convenience function to get files in a garden."""
    return get_garden_directory().get_garden_files(garden, file_type)


def get_file_garden(file_path: str) -> FileGardenMapping | None:
    """Convenience function to get a file's garden mapping."""
    return get_garden_directory().get_file_mapping(file_path)


if __name__ == "__main__":
    print("=" * 60)
    print("GARDEN DIRECTORY — File-to-Garden Mapping Registry")
    print("=" * 60)
    print(f"Total gardens: {len(GARDEN_KEYWORDS)}")
    print(f"Path hints: {len(PATH_GARDEN_HINTS)}")
    print()
    print("Garden → Gana → Element mapping:")
    for entry in GARDEN_GANA_REGISTRY[:7]:
        print(f"  {entry.garden:15} → {entry.gana:25} [{entry.element.value}]")
    print("  ...")
