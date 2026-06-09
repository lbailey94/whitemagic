"""Bridge to the Rust-backed Sutra/Dharma kernel.

Tries to load the Rust acceleration layer; falls back to the Python
Dharma subsystem if the Rust extension is not compiled.
"""

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

# Try to load Rust Sutra Kernel
try:
    import whitemagic_rust
    _sutra_kernel = getattr(whitemagic_rust, "sutra_kernel", None)
    if _sutra_kernel is not None and hasattr(_sutra_kernel, "DharmaEngine"):
        _RustDharmaEngine: Any | None = getattr(_sutra_kernel, "DharmaEngine")
        RUST_SUTRA_AVAILABLE = True
    else:
        _RustDharmaEngine = None
        RUST_SUTRA_AVAILABLE = False
except ImportError:
    _RustDharmaEngine = None
    RUST_SUTRA_AVAILABLE = False


class SutraKernelBridge:
    """Bridge to the Rust-backed Sutra/Dharma kernel."""

    def __init__(self, maturity_level: int = 1, strict_mode: bool = True):
        self._rust_engine = (
            _RustDharmaEngine(maturity_level, strict_mode)
            if _RustDharmaEngine
            else None
        )

    def evaluate_action(
        self,
        action_type: str,
        intent_score: float = 1.0,
        karma_debt: float = 0.0,
    ) -> str:
        """Evaluate an action using the Rust Dharma Kernel or Python fallback."""
        if self._rust_engine:
            return cast(
                str,
                self._rust_engine.evaluate_action(
                    action_type, intent_score, karma_debt
                ),
            )

        # Hardened Fallback: Use Dharma System instead of passive string
        try:
            from whitemagic.dharma import evaluate_ethics

            score, _concerns = evaluate_ethics(
                {"tool": action_type, "description": "Sutra Fallback Evaluation"}
            )

            if score < 0.4:
                return "Panic: Ethical misalignment detected in fallback mode."
            if score < 0.7:
                return "Intervene: Cautionary threshold reached."
            return "Observe" if score > 0.9 else "Rajasic: Proceed with logging"
        except (ImportError, AttributeError):
            # Absolute last resort: Fail-Safe (Restrictive)
            return "Intervene: Safety system failure."


_sutra_kernel_instance: SutraKernelBridge | None = None


def get_sutra_kernel() -> SutraKernelBridge:
    """Get or create the singleton SutraKernelBridge instance."""
    global _sutra_kernel_instance
    if _sutra_kernel_instance is None:
        _sutra_kernel_instance = SutraKernelBridge()
    return _sutra_kernel_instance
