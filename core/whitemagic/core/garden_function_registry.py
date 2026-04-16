"""🌸 Garden Function Registry — Function-to-Garden Mapping.

Extends the file-level mapping with function-level granularity,
enabling precise navigation to specific functions within gardens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.core.intelligence.garden_gana_registry import (
    calculate_resonance,
    get_by_garden,
)


@dataclass
class FunctionGardenMapping:
    """Mapping of a function to its garden affinity."""

    function_name: str
    file_path: str
    primary_garden: str
    garden_from_file: str  # Garden inherited from parent file
    garden_from_content: str  # Garden from function content/analysis
    resonant_gardens: list[str] = field(default_factory=list)
    quadrant: str = ""
    element: str = ""
    gana: str = ""
    confidence: float = 0.0
    is_public: bool = True
    docstring: str = ""
    dependencies: list[str] = field(default_factory=list)  # Functions this calls


class GardenFunctionRegistry:
    """Registry for function-to-garden mappings."""

    def __init__(self, registry_path: Path | None = None):
        if registry_path is None:
            from whitemagic.config.paths import WM_ROOT
            self.registry_path = WM_ROOT / "garden_function_registry.json"
        else:
            self.registry_path = registry_path
        self._function_mappings: dict[str, FunctionGardenMapping] = {}  # key: "file_path:function_name"
        self._garden_functions: dict[str, list[str]] = {}  # garden -> list of function keys
        self._function_index: dict[str, list[str]] = {}  # function_name -> list of keys (for overloads)
        self._loaded = False

    def load(self) -> bool:
        """Load registry from disk."""
        if self._loaded:
            return True
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text())
                for key, mapping_data in data.get("function_mappings", {}).items():
                    self._function_mappings[key] = FunctionGardenMapping(**mapping_data)
                self._rebuild_indices()
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
            "function_mappings": {
                key: {
                    "function_name": m.function_name,
                    "file_path": m.file_path,
                    "primary_garden": m.primary_garden,
                    "garden_from_file": m.garden_from_file,
                    "garden_from_content": m.garden_from_content,
                    "resonant_gardens": m.resonant_gardens,
                    "quadrant": m.quadrant,
                    "element": m.element,
                    "gana": m.gana,
                    "confidence": m.confidence,
                    "is_public": m.is_public,
                    "docstring": m.docstring,
                    "dependencies": m.dependencies,
                }
                for key, m in self._function_mappings.items()
            },
            "garden_functions": self._garden_functions,
            "function_index": self._function_index,
            "stats": self.get_stats(),
        }
        self.registry_path.write_text(json.dumps(data, indent=2))

    def _rebuild_indices(self) -> None:
        """Rebuild indices from function mappings."""
        self._garden_functions = {}
        self._function_index = {}

        for key, mapping in self._function_mappings.items():
            # Garden index
            if mapping.primary_garden not in self._garden_functions:
                self._garden_functions[mapping.primary_garden] = []
            self._garden_functions[mapping.primary_garden].append(key)

            # Function name index
            if mapping.function_name not in self._function_index:
                self._function_index[mapping.function_name] = []
            self._function_index[mapping.function_name].append(key)

    def register_function(self, mapping: FunctionGardenMapping) -> None:
        """Register a function mapping."""
        key = f"{mapping.file_path}:{mapping.function_name}"
        self._function_mappings[key] = mapping

        if mapping.primary_garden not in self._garden_functions:
            self._garden_functions[mapping.primary_garden] = []
        self._garden_functions[mapping.primary_garden].append(key)

        if mapping.function_name not in self._function_index:
            self._function_index[mapping.function_name] = []
        self._function_index[mapping.function_name].append(key)

        self._loaded = True

    def get_function(self, function_name: str, file_path: str | None = None) -> FunctionGardenMapping | None:
        """Get a function by name, optionally filtered by file."""
        if function_name not in self._function_index:
            return None

        keys = self._function_index[function_name]
        if file_path:
            for key in keys:
                if key.startswith(f"{file_path}:"):
                    return self._function_mappings.get(key)

        # Return first match
        return self._function_mappings.get(keys[0])

    def get_garden_functions(self, garden: str) -> list[FunctionGardenMapping]:
        """Get all functions for a garden."""
        keys = self._garden_functions.get(garden, [])
        return [self._function_mappings[k] for k in keys if k in self._function_mappings]

    def search_functions(self, query: str, gardens: list[str] | None = None) -> list[FunctionGardenMapping]:
        """Search for functions by name."""
        results = []
        query_lower = query.lower()

        for func_name, keys in self._function_index.items():
            if query_lower in func_name.lower():
                for key in keys:
                    mapping = self._function_mappings.get(key)
                    if mapping:
                        if gardens is None or mapping.primary_garden in gardens:
                            results.append(mapping)

        return results

    def get_cross_garden_calls(self) -> dict[str, list[str]]:
        """Get cross-garden function call graph.

        Returns:
            Dict mapping "source_garden" -> ["target_garden:count", ...]
        """
        cross_calls: dict[str, dict[str, int]] = {}

        for key, mapping in self._function_mappings.items():
            source_garden = mapping.primary_garden

            for dep in mapping.dependencies:
                # Find the garden of the dependency
                dep_mapping = self.get_function(dep)
                if dep_mapping:
                    target_garden = dep_mapping.primary_garden
                    if source_garden != target_garden:
                        if source_garden not in cross_calls:
                            cross_calls[source_garden] = {}
                        cross_calls[source_garden][target_garden] = cross_calls[source_garden].get(target_garden, 0) + 1

        # Convert to sorted lists
        result = {}
        for source, targets in cross_calls.items():
            result[source] = [f"{t}:{c}" for t, c in sorted(targets.items(), key=lambda x: -x[1])]

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        stats: dict[str, Any] = {
            "total_functions": len(self._function_mappings),
            "unique_names": len(self._function_index),
            "gardens": {},
            "public_functions": 0,
            "private_functions": 0,
        }

        garden_stats: dict[str, int] = stats["gardens"] # type: ignore
        for garden, keys in self._garden_functions.items():
            garden_stats[garden] = len(keys)

        for mapping in self._function_mappings.values():
            if mapping.is_public:
                stats["public_functions"] = int(stats["public_functions"]) + 1
            else:
                stats["private_functions"] = int(stats["private_functions"]) + 1

        return stats


def analyze_function_for_garden(
    function_name: str,
    file_path: str,
    file_garden: str,
    docstring: str = "",
    source_code: str = "",
    dependencies: list[str] | None = None,
) -> FunctionGardenMapping:
    """Analyze a function and determine its garden affinity."""

    # Start with file's garden
    primary_garden = file_garden
    garden_from_file = file_garden
    garden_from_content = file_garden
    confidence = 0.7  # Inherited from file

    # Analyze docstring/source for more specific garden
    content = f"{function_name} {docstring} {source_code}"
    resonance = calculate_resonance(content[:500])

    if resonance:
        # Get top resonating garden
        top_garden = list(resonance.keys())[0]
        top_score = resonance[top_garden].get("score", 0)

        if top_score > 2.0:
            garden_from_content = top_garden
            # Only override if significantly different
            if top_score > 5.0:
                primary_garden = top_garden
                confidence = min(0.95, 0.5 + top_score / 20.0)

    # Get garden metadata
    garden_entry = get_by_garden(primary_garden)
    quadrant = garden_entry.quadrant.value if garden_entry else ""
    element = garden_entry.element.value if garden_entry else ""
    gana = garden_entry.gana if garden_entry else ""

    # Determine resonant gardens
    resonant = []
    if garden_from_file != primary_garden:
        resonant.append(garden_from_file)
    if garden_from_content != primary_garden and garden_from_content not in resonant:
        resonant.append(garden_from_content)

    return FunctionGardenMapping(
        function_name=function_name,
        file_path=file_path,
        primary_garden=primary_garden,
        garden_from_file=garden_from_file,
        garden_from_content=garden_from_content,
        resonant_gardens=resonant,
        quadrant=quadrant,
        element=element,
        gana=gana,
        confidence=confidence,
        is_public=not function_name.startswith("_"),
        docstring=docstring[:200] if docstring else "",
        dependencies=dependencies or [],
    )


# Singleton
_function_registry: GardenFunctionRegistry | None = None


def get_function_registry() -> GardenFunctionRegistry:
    """Get the global function registry instance."""
    global _function_registry
    if _function_registry is None:
        _function_registry = GardenFunctionRegistry()
        _function_registry.load()
    return _function_registry


def get_functions_in_garden(garden: str) -> list[FunctionGardenMapping]:
    """Convenience function to get functions in a garden."""
    return get_function_registry().get_garden_functions(garden)


def find_function(name: str, file_path: str | None = None) -> FunctionGardenMapping | None:
    """Convenience function to find a function by name."""
    return get_function_registry().get_function(name, file_path)


if __name__ == "__main__":
    print("=" * 60)
    print("GARDEN FUNCTION REGISTRY — Function-to-Garden Mapping")
    print("=" * 60)
    registry = get_function_registry()
    stats = registry.get_stats()
    print(f"Total functions: {stats['total_functions']}")
    print(f"Unique names: {stats['unique_names']}")
    print(f"Public: {stats['public_functions']}, Private: {stats['private_functions']}")
