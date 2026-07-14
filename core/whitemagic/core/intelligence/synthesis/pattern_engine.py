# ruff: noqa: BLE001
"""Pattern Engine - Pattern detection and analysis (v2.0 — Wired to Real Engines).
==================================================================================
Delegates to real pattern engines:
- UnifiedPatternAPI from unified_patterns.py
- HolographicPatternEngine from hologram/patterns.py
- Memory pattern engine from memory/pattern_engine.py
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PatternEngine:
    """Pattern detection and analysis engine — wires to real implementations."""

    def __init__(self) -> None:
        self._unified = None
        self._holographic = None
        self._memory = None

    def _get_unified(self) -> Any:
        if self._unified is None:
            try:
                from whitemagic.core.intelligence.synthesis.unified_patterns import (
                    UnifiedPatternAPI,
                )

                self._unified = UnifiedPatternAPI()  # type: ignore[assignment]
            except Exception as e:
                logger.debug("UnifiedPatternAPI unavailable: %s", e, exc_info=True)
                self._unified = None
        return self._unified

    def _get_holographic(self) -> Any:
        if self._holographic is None:
            try:
                from whitemagic.core.intelligence.hologram.patterns import (
                    HolographicPatternEngine,
                )

                self._holographic = HolographicPatternEngine()  # type: ignore[assignment]
            except Exception as e:
                logger.debug(
                    "HolographicPatternEngine unavailable: %s", e, exc_info=True
                )
                self._holographic = None
        return self._holographic

    def _get_memory(self) -> Any:
        if self._memory is None:
            try:
                from whitemagic.core.memory.pattern_engine import MemoryPatternEngine

                self._memory = MemoryPatternEngine()
            except Exception as e:
                logger.debug("MemoryPatternEngine unavailable: %s", e, exc_info=True)
                self._memory = None
        return self._memory

    def detect(self, query: str = "", **kwargs: Any) -> list[dict[str, Any]]:
        """Detect patterns in data — tries all engines."""
        results = []

        unified = self._get_unified()
        if unified:
            try:
                unified_results = unified.search_patterns(
                    query, limit=kwargs.get("limit", 20)
                )
                results.extend(unified_results)
            except Exception as e:
                logger.debug("Unified pattern search failed: %s", e, exc_info=True)

        holographic = self._get_holographic()
        if holographic:
            try:
                holo_results = holographic.find_patterns(query, **kwargs)
                results.extend(holo_results)
            except Exception as e:
                logger.debug("Holographic pattern search failed: %s", e, exc_info=True)

        memory = self._get_memory()
        if memory:
            try:
                mem_results = memory.extract_patterns(**kwargs)
                results.extend(mem_results)
            except Exception as e:
                logger.debug("Memory pattern extraction failed: %s", e, exc_info=True)

        return results

    def analyze(self, pattern_id: str, **kwargs: Any) -> dict[str, Any]:
        """Analyze a specific pattern."""
        unified = self._get_unified()
        if unified:
            try:
                return unified.analyze_pattern(pattern_id, **kwargs)
            except Exception as e:
                logger.debug("Unified pattern analysis failed: %s", e, exc_info=True)

        holographic = self._get_holographic()
        if holographic:
            try:
                return holographic.analyze_pattern(pattern_id, **kwargs)
            except Exception as e:
                logger.debug(
                    "Holographic pattern analysis failed: %s", e, exc_info=True
                )

        return {"status": "not_found", "pattern_id": pattern_id}

    def get_stats(self) -> dict[str, Any]:
        """Get pattern engine statistics."""
        stats: dict[str, Any] = {"engines": {}}

        unified = self._get_unified()
        if unified:
            try:
                stats["engines"]["unified"] = unified.get_stats()
            except Exception as e:
                logger.debug("Unified pattern stats failed: %s", e, exc_info=True)

        holographic = self._get_holographic()
        if holographic:
            try:
                stats["engines"]["holographic"] = holographic.get_stats()
            except Exception as e:
                logger.debug("Holographic pattern stats failed: %s", e, exc_info=True)

        memory = self._get_memory()
        if memory:
            try:
                stats["engines"]["memory"] = memory.get_stats()
            except Exception as e:
                logger.debug("Memory pattern stats failed: %s", e, exc_info=True)

        return stats

    _enhanced_pattern_engine_instance: Any = None
    _sub_clustering_engine_instance: Any = None

    def _get_enhanced_pattern_engine(self):
        """Lazy accessor for the EnhancedPatternEngine."""
        if self._enhanced_pattern_engine_instance is None:
            from whitemagic.core.patterns.pattern_consciousness.pattern_engine_enhanced import (
                EnhancedPatternEngine,
            )

            self._enhanced_pattern_engine_instance = EnhancedPatternEngine()
        return self._enhanced_pattern_engine_instance

    def enhanced_extract_patterns(self, content: str) -> list[dict[str, Any]]:
        """Extract patterns from content using ML/Rust-enhanced engine."""
        return self._get_enhanced_pattern_engine().extract_patterns(content)

    def enhanced_scan_continuously(self) -> None:
        """Start continuous background pattern scanning."""
        self._get_enhanced_pattern_engine().scan_continuously()

    def enhanced_emit_to_gan_ying(self, pattern: dict[str, Any]) -> None:
        """Emit a discovered pattern to the Gan Ying Bus."""
        self._get_enhanced_pattern_engine().emit_to_gan_ying(pattern)

    def enhanced_synthesize_creative(self, patterns: list[dict[str, Any]]) -> str:
        """Creative synthesis of multiple patterns."""
        return self._get_enhanced_pattern_engine().synthesize_creative(patterns)

    def enhanced_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using PolyglotRouter."""
        return self._get_enhanced_pattern_engine().similarity(text1, text2)

    def _get_sub_clustering_engine(self):
        """Lazy accessor for the SubClusteringEngine."""
        if self._sub_clustering_engine_instance is None:
            from whitemagic.core.intelligence.synthesis.sub_clustering import (
                get_sub_clustering_engine,
            )

            self._sub_clustering_engine_instance = get_sub_clustering_engine()
        return self._sub_clustering_engine_instance

    def sub_find_large_clusters(self, threshold: int = 20) -> list[tuple[str, int]]:
        """Find clusters larger than threshold."""
        return self._get_sub_clustering_engine().find_large_clusters(threshold)

    def sub_subdivide_cluster(self, cluster_id: str) -> list[Any]:
        """Subdivide a single cluster into quadrants."""
        return self._get_sub_clustering_engine().subdivide_cluster(cluster_id)

    def sub_subdivide_large_clusters(
        self, threshold: int = 20, dry_run: bool = False
    ) -> dict[str, list[Any]]:
        """Subdivide all large clusters."""
        return self._get_sub_clustering_engine().subdivide_large_clusters(
            threshold, dry_run
        )

    def sub_get_cluster_stats(self) -> dict[str, Any]:
        """Get statistics about current clustering."""
        return self._get_sub_clustering_engine().get_cluster_stats()


# Singleton
_pattern_engine: PatternEngine | None = None
_pattern_engine_lock = __import__("threading").RLock()


def get_pattern_engine(**kwargs: Any) -> PatternEngine:
    """Get the global PatternEngine singleton."""
    global _pattern_engine
    if _pattern_engine is None:
        with _pattern_engine_lock:
            if _pattern_engine is None:
                _pattern_engine = PatternEngine(**kwargs)
    return _pattern_engine
