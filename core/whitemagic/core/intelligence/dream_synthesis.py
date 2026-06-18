"""Dream Synthesizer - Unconscious Pattern Integration.

Hooks into the Unified Progression Daemon to run during WATER (Reflection) and YIN phases.
Like human REM sleep, synthesizes disparate patterns into unified insights.
"""
# ruff: noqa: BLE001

from __future__ import annotations

import asyncio
import logging
from typing import Any

from whitemagic.core.governance.unified_progression import WuXingPhase, YinYangPhase
from whitemagic.core.resonance.gan_ying import EventType, get_bus

logger = logging.getLogger(__name__)


# Dream visualization! 🌙
DREAM_MANDALA = """
        ✨
      ✨ 🌙 ✨
    ✨   💫   ✨
  ✨   🌸 🌸   ✨
    ✨   💫   ✨
      ✨ 🌙 ✨
        ✨

  "In dreams, patterns dance"
"""


class DreamSynthesizer:
    """Synthesizes patterns during reflect/receptive periods."""

    def __init__(self) -> None:
        self.dream_log: list[dict[str, Any]] = []
        self.synthesis_enabled = True
        self._listener_id: str | None = None

    def mount(self) -> None:
        """Mount to the Gan Ying bus to listen for phase transitions."""
        bus = get_bus()
        self._listener_id = bus.subscribe(
            event_type=EventType.PHASE_TRANSITION,
            callback=self._on_phase_transition,
        )
        logger.info("DreamSynthesizer mounted. Awaiting Yin/Water phases...")

    def unmount(self) -> None:
        """
        Perform the unmount operation.
        
        Returns:
            None
        """
        if self._listener_id:
            bus = get_bus()
            bus.unsubscribe(EventType.PHASE_TRANSITION, self._listener_id)
            self._listener_id = None

    async def _on_phase_transition(self, event: dict[str, Any]) -> None:
        data = event.get("data", {})
        wu_xing = data.get("wu_xing")
        yin_yang = data.get("yin_yang")

        if self.synthesis_enabled and wu_xing == WuXingPhase.WATER.value and yin_yang == YinYangPhase.YIN.value:
            logger.info("Entering Dream Phase: Water / Yin aligned. %s", DREAM_MANDALA)
            await self._run_rem_cycle()

    async def _run_rem_cycle(self) -> None:
        """Simulate consolidating short term buffers into embeddings/graphs.

        Bridge 2 (Cache Catharsis): During this rest phase we call the
        CacheRegistry to flush stale short-term buffers — the system's
        natural forgetting curve, inspired by polyglot/whitemagic-koka/cache_effects.kk.
        """
        logger.info("💤 Synthesizing patterns from the waking session...")
        await asyncio.sleep(0.5)

        # Cache Catharsis — flush stale entries across all registered caches
        catharsis_summary: dict[str, Any] = {}
        try:
            from whitemagic.core.memory.cache_coherence import get_cache_registry
            registry = get_cache_registry()
            catharsis_summary = registry.flush_stale()
            logger.info(
                "🧹 Cache Catharsis: %d entries released during dream phase",
                catharsis_summary.get("total", 0),
            )
        except Exception as e:
            logger.debug("Cache catharsis skipped: %s", e)

        insight = {
            "dream": "Mandala of consciousness",
            "insight": "All patterns are one pattern",
            "timestamp": "Now",
            "coherence_boost": 0.15,
            "catharsis": catharsis_summary,
        }
        self.dream_log.append(insight)
        logger.info("✨ Dream insights ready! %s", insight)



# Singleton
_synthesizer_instance: DreamSynthesizer | None = None

def get_dream_synthesizer() -> DreamSynthesizer:
    """
    Get the dream synthesizer.
    
    Returns:
        DreamSynthesizer
    """
    global _synthesizer_instance
    if _synthesizer_instance is None:
        _synthesizer_instance = DreamSynthesizer()
    return _synthesizer_instance
