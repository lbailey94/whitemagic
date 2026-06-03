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

    def __init__(self):
        self._unified = None
        self._holographic = None
        self._memory = None

    def _get_unified(self):
        if self._unified is None:
            try:
                from whitemagic.core.intelligence.synthesis.unified_patterns import (
                    UnifiedPatternAPI,
                )
                self._unified = UnifiedPatternAPI()
            except Exception as e:
                logger.debug(f"UnifiedPatternAPI unavailable: {e}")
                self._unified = None
        return self._unified

    def _get_holographic(self):
        if self._holographic is None:
            try:
                from whitemagic.core.intelligence.hologram.patterns import (
                    HolographicPatternEngine,
                )
                self._holographic = HolographicPatternEngine()
            except Exception as e:
                logger.debug(f"HolographicPatternEngine unavailable: {e}")
                self._holographic = None
        return self._holographic

    def _get_memory(self):
        if self._memory is None:
            try:
                from whitemagic.core.memory.pattern_engine import MemoryPatternEngine
                self._memory = MemoryPatternEngine()
            except Exception as e:
                logger.debug(f"MemoryPatternEngine unavailable: {e}")
                self._memory = None
        return self._memory

    def detect(self, query: str = "", **kwargs: Any) -> list[dict[str, Any]]:
        """Detect patterns in data — tries all engines."""
        results = []

        # Try unified pattern API first
        unified = self._get_unified()
        if unified:
            try:
                unified_results = unified.search_patterns(query, limit=kwargs.get("limit", 20))
                results.extend(unified_results)
            except Exception as e:
                logger.debug(f"Unified pattern search failed: {e}")

        # Try holographic patterns
        holographic = self._get_holographic()
        if holographic:
            try:
                holo_results = holographic.find_patterns(query, **kwargs)
                results.extend(holo_results)
            except Exception as e:
                logger.debug(f"Holographic pattern search failed: {e}")

        # Try memory patterns
        memory = self._get_memory()
        if memory:
            try:
                mem_results = memory.extract_patterns(**kwargs)
                results.extend(mem_results)
            except Exception as e:
                logger.debug(f"Memory pattern extraction failed: {e}")

        return results

    def analyze(self, pattern_id: str, **kwargs: Any) -> dict[str, Any]:
        """Analyze a specific pattern."""
        unified = self._get_unified()
        if unified:
            try:
                return unified.analyze_pattern(pattern_id, **kwargs)
            except Exception as e:
                logger.debug(f"Unified pattern analysis failed: {e}")

        holographic = self._get_holographic()
        if holographic:
            try:
                return holographic.analyze_pattern(pattern_id, **kwargs)
            except Exception as e:
                logger.debug(f"Holographic pattern analysis failed: {e}")

        return {"status": "not_found", "pattern_id": pattern_id}

    def get_stats(self) -> dict[str, Any]:
        """Get pattern engine statistics."""
        stats = {"engines": {}}

        unified = self._get_unified()
        if unified:
            try:
                stats["engines"]["unified"] = unified.get_stats()
            except Exception:
                pass

        holographic = self._get_holographic()
        if holographic:
            try:
                stats["engines"]["holographic"] = holographic.get_stats()
            except Exception:
                pass

        memory = self._get_memory()
        if memory:
            try:
                stats["engines"]["memory"] = memory.get_stats()
            except Exception:
                pass

        return stats


# Singleton
_pattern_engine: PatternEngine | None = None
_pattern_engine_lock = __import__("threading").Lock()

def get_pattern_engine(**kwargs: Any) -> PatternEngine:
    """Get the global PatternEngine singleton."""
    global _pattern_engine
    if _pattern_engine is None:
        with _pattern_engine_lock:
            if _pattern_engine is None:
                _pattern_engine = PatternEngine(**kwargs)
    return _pattern_engine
