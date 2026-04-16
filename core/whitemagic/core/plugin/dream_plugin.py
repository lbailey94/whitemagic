# Copyright 2026 WhiteMagic Contributors
"""Dream Plugin — REM Synthesis & Cache Catharsis (E4).
Wraps the DreamSynthesizer for automated memory consolidation.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class DreamPlugin:
    name = "dream"
    version = "1.0.0"
    description = "Dream Synthesizer — Automated memory consolidation and cache catharsis during Yin phases"

    def __init__(self) -> None:
        self._synthesizer: Any | None = None
        self._running = False

    def start(self) -> None:
        from whitemagic.core.intelligence.dream_synthesis import get_dream_synthesizer
        self._synthesizer = get_dream_synthesizer()
        self._synthesizer.awaken()
        self._running = True
        logger.info("DreamPlugin started")

    def stop(self) -> None:
        if self._synthesizer:
            self._synthesizer.sleep()
        self._running = False
        logger.info("DreamPlugin stopped")

    def status(self) -> dict[str, Any]:
        if not self._synthesizer:
            return {"running": False}
        return {
            "name": self.name,
            "running": self._running,
            "rem_active": self._synthesizer.is_rem_active(),
            "consolidated_count": self._synthesizer.get_stats().get("consolidations", 0)
        }

def register():
    try:
        from whitemagic.core.plugin import get_registry
        get_registry().register(DreamPlugin())
    except (ImportError, ModuleNotFoundError):
        pass
