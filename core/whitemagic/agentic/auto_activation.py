# ruff: noqa: BLE001
"""
Auto-Activation Protocol — Full self-activation on session start.

Ensures all cognitive systems are initialized and wired when
a new session begins, rather than waiting for lazy loading.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AutoActivation:
    """Activates cognitive systems on session start."""

    def __init__(self) -> None:
        self.activated: dict[str, bool] = {}
        self.activation_log: list[str] = []

    def activate_all(self) -> dict[str, bool]:
        """Attempt to activate all cognitive subsystems."""
        activations = [
            ("consciousness", self._activate_consciousness),
            ("coherence", self._activate_coherence),
            ("gardens", self._activate_gardens),
            ("resonance", self._activate_resonance),
            ("memory", self._activate_memory),
            ("dharma", self._activate_dharma),
            ("citta_stream", self._activate_citta),
        ]
        for name, fn in activations:
            try:
                fn()
                self.activated[name] = True
                self.activation_log.append(f"OK: {name}")
            except Exception as e:
                self.activated[name] = False
                self.activation_log.append(f"FAIL: {name} — {e}")
                logger.debug("Activation failed for %s: %s", name, e)
        return self.activated

    def _activate_consciousness(self) -> None:
        from whitemagic.core.consciousness import CoherenceMetric  # noqa: F401

    def _activate_coherence(self) -> None:
        from whitemagic.core.consciousness.coherence import CoherenceMetric
        metric = CoherenceMetric()
        metric.measure()

    def _activate_gardens(self) -> None:
        from whitemagic.gardens import get_all_gardens
        get_all_gardens()

    def _activate_resonance(self) -> None:
        from whitemagic.core.resonance.gan_ying_bus import GanYingBus
        GanYingBus()

    def _activate_memory(self) -> None:
        from whitemagic.core.memory.unified import get_unified_memory
        get_unified_memory()

    def _activate_dharma(self) -> None:
        from whitemagic.core.dharma.engine import DharmaEngine  # noqa: F401

    def _activate_citta(self) -> None:
        from whitemagic.core.consciousness.citta_stream import get_continuity_context
        get_continuity_context()

    def status(self) -> dict[str, Any]:
        return {
            "activated": self.activated,
            "log": self.activation_log,
            "all_active": all(self.activated.values()) if self.activated else False,
        }


_activation: AutoActivation | None = None


def get_auto_activation() -> AutoActivation:
    global _activation
    if _activation is None:
        _activation = AutoActivation()
    return _activation
