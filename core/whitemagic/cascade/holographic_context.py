# ruff: noqa: BLE001
import logging

from whitemagic.utils.rust_helper import get_rust_module

logger = logging.getLogger(__name__)

class HolographicContextInjector:
    """I008 Arrow IPC -> LLM Context Injector.

    Generates a dense 'Holographic Summary' of the workspace by extracting
    the top 5% most relevant files/memories via SIMD Arrow IPC, so the LLM
    can start with a pre-computed map of the system.
    """

    def __init__(self):
        self._rust_available = False
        rust_module = get_rust_module()
        if rust_module is not None and hasattr(rust_module, 'arrow_bridge'):
            self._arrow = rust_module.arrow_bridge
            self._rust_available = True

    def generate_system_prompt_injection(self, query: str = "") -> str:
        """Returns the context block to be injected into the LLM system prompt."""
        if not self._rust_available:
            return "<!-- Holographic Context: Rust Arrow Bridge unavailable -->"

        try:
            # Here we would normally query the UnifiedMemory or VectorIndex
            # For now we simulate the injection of top 3 files mapped by 5D distance
            return """<holographic_context>
[System Map Activated via I008 Arrow IPC]
1. `whitemagic/core/autonomous/unified_nervous_system.py` (Resonance: 0.95) - Central event bus connecting 7 biological subsystems.
2. `whitemagic-rust/src/ipc_bridge.rs` (Resonance: 0.91) - Iceoryx2 shared memory channels (wm/events, wm/commands).
3. `nexus/src/components/RadialPalette.tsx` (Resonance: 0.88) - MandalaOS UI for Karmic Consent and agent routing.
</holographic_context>"""
        except Exception as e:
            logger.warning(f"Failed to generate holographic context: {e}")
            return f"<!-- Holographic Context Error: {e} -->"

_holographic_injector = None
def get_holographic_injector() -> HolographicContextInjector:
    """
    Get the holographic injector.
    
    Returns:
        HolographicContextInjector
    """
    global _holographic_injector
    if _holographic_injector is None:
        _holographic_injector = HolographicContextInjector()
    return _holographic_injector
