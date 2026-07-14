"""Oracle → Bayesian Optimization Bridge.

Maps oracle guidance to Bayesian optimization parameters so that divination
results influence simulation behavior. When the I Ching advises perseverance,
BO gets more iterations. When it advises retreat, BO explores more cautiously.

The mapping is based on hexagram semantics and Wu Xing phase theory:
- Fire: bold, high-energy exploration
- Water: careful, precise sampling
- Wood: balanced growth
- Metal: structured, disciplined
- Earth: stable, grounded

HRR resonance amplification from Phase 1 increases iterations when the primary
hexagram has strong resonances with others.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OracleBOBridge:
    """Maps oracle synthesis output to Bayesian optimization parameters.

    The bridge translates symbolic divination output into numerical BO
    parameters (xi, n_iterations, exploration temperature) that control
    the superforecaster pipeline's exploration-exploitation balance.
    """

    # Hexagram → BO parameter mapping (based on hexagram semantics)
    HEXAGRAM_BO_MAP: dict[int, dict[str, Any]] = {
        1:  {"xi": 0.01, "n_bo_iterations": 25, "exploration": "high"},
        2:  {"xi": 0.1,  "n_bo_iterations": 15, "exploration": "low"},
        3:  {"xi": 0.05, "n_bo_iterations": 20, "exploration": "cautious"},
        4:  {"xi": 0.08, "n_bo_iterations": 18, "exploration": "deliberate"},
        5:  {"xi": 0.03, "n_bo_iterations": 22, "exploration": "patient"},
        6:  {"xi": 0.15, "n_bo_iterations": 15, "exploration": "conflict"},
        7:  {"xi": 0.04, "n_bo_iterations": 22, "exploration": "disciplined"},
        8:  {"xi": 0.06, "n_bo_iterations": 20, "exploration": "unifying"},
        11: {"xi": 0.02, "n_bo_iterations": 25, "exploration": "harmonious"},
        12: {"xi": 0.2,  "n_bo_iterations": 10, "exploration": "stagnant"},
        14: {"xi": 0.01, "n_bo_iterations": 28, "exploration": "bold"},
        15: {"xi": 0.07, "n_bo_iterations": 20, "exploration": "modest"},
        17: {"xi": 0.04, "n_bo_iterations": 22, "exploration": "adaptable"},
        20: {"xi": 0.03, "n_bo_iterations": 24, "exploration": "observant"},
        23: {"xi": 0.25, "n_bo_iterations": 8,  "exploration": "minimal"},
        24: {"xi": 0.05, "n_bo_iterations": 22, "exploration": "returning"},
        27: {"xi": 0.06, "n_bo_iterations": 20, "exploration": "nourishing"},
        29: {"xi": 0.12, "n_bo_iterations": 16, "exploration": "danger"},
        30: {"xi": 0.02, "n_bo_iterations": 26, "exploration": "brilliant"},
        32: {"xi": 0.02, "n_bo_iterations": 30, "exploration": "patient"},
        33: {"xi": 0.5,  "n_bo_iterations": 10, "exploration": "retreat"},
        34: {"xi": 0.03, "n_bo_iterations": 24, "exploration": "powerful"},
        35: {"xi": 0.01, "n_bo_iterations": 25, "exploration": "high"},
        40: {"xi": 0.08, "n_bo_iterations": 18, "exploration": "deliverance"},
        41: {"xi": 0.1,  "n_bo_iterations": 16, "exploration": "decreasing"},
        42: {"xi": 0.02, "n_bo_iterations": 28, "exploration": "increasing"},
        47: {"xi": 0.3,  "n_bo_iterations": 20, "exploration": "constrained"},
        50: {"xi": 0.01, "n_bo_iterations": 30, "exploration": "transformative"},
        51: {"xi": 0.04, "n_bo_iterations": 22, "exploration": "shocking"},
        52: {"xi": 0.09, "n_bo_iterations": 18, "exploration": "still"},
        55: {"xi": 0.05, "n_bo_iterations": 22, "exploration": "abundant"},
        63: {"xi": 0.04, "n_bo_iterations": 22, "exploration": "completed"},
        64: {"xi": 0.05, "n_bo_iterations": 20, "exploration": "near_completion"},
    }

    # Wu Xing → exploration temperature
    WUXING_TEMP: dict[str, float] = {
        "fire":  1.5,
        "water": 0.3,
        "wood":  1.0,
        "metal": 0.5,
        "earth": 0.7,
    }

    # Default parameters when oracle is unavailable
    DEFAULT_PARAMS: dict[str, Any] = {
        "xi": 0.01,
        "n_bo_iterations": 20,
        "exploration": "default",
        "temperature": 1.0,
    }

    def translate(self, oracle_output: dict[str, Any]) -> dict[str, Any]:
        """Convert oracle synthesis output to BO parameters.

        Args:
            oracle_output: Dict from OracleSynthesizer.synthesize() or
                ZodiacalProcession.consult_oracle(). Must contain at least
                a primary_hexagram or iching_number key.

        Returns:
            Dict with xi, n_bo_iterations, exploration, temperature.
        """
        params = dict(self.DEFAULT_PARAMS)

        # Extract hexagram number
        hexagram = oracle_output.get("primary_hexagram")
        if hexagram is None:
            hexagram = oracle_output.get("iching_number")
        if hexagram is not None and isinstance(hexagram, int) and hexagram in self.HEXAGRAM_BO_MAP:
            params.update(self.HEXAGRAM_BO_MAP[hexagram])

        # Wu Xing temperature modulation
        wuxing = oracle_output.get("wu_xing")
        if wuxing and wuxing in self.WUXING_TEMP:
            params["temperature"] = self.WUXING_TEMP[wuxing]

        # HRR resonance amplification (from Phase 1)
        resonances = oracle_output.get("hrr_resonances", [])
        if resonances:
            avg_sim = sum(r.get("similarity", 0) for r in resonances) / len(resonances)
            params["n_bo_iterations"] = int(params["n_bo_iterations"] * (1 + avg_sim))
            # Strong resonances → more confident exploration
            if avg_sim > 0.5:
                params["xi"] = max(0.001, params["xi"] * 0.8)

        return params

    def translate_from_synthesis(self, synthesis_result: Any) -> dict[str, Any]:
        """Translate a SynthesisResult into BO parameters.

        Args:
            synthesis_result: A SynthesisResult from OracleSynthesizer.synthesize().

        Returns:
            Dict with BO parameters.
        """
        oracle_output = synthesis_result.raw_layers if hasattr(synthesis_result, "raw_layers") else {}
        if hasattr(synthesis_result, "primary_hexagram") and synthesis_result.primary_hexagram:
            oracle_output = {**oracle_output, "primary_hexagram": synthesis_result.primary_hexagram}
        if hasattr(synthesis_result, "hrr_resonances"):
            oracle_output = {**oracle_output, "hrr_resonances": synthesis_result.hrr_resonances}
        return self.translate(oracle_output)


_bridge: OracleBOBridge | None = None


def get_oracle_bo_bridge() -> OracleBOBridge:
    """Get the singleton OracleBOBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = OracleBOBridge()
    return _bridge
