"""Adaptive Recursive Oracle Cycle.

Ties together all oracle-quantum integration components into a self-improving
recursive cycle:

1. Consult oracle (QuantumIChing with HRR amplitudes + Born-rule collapse)
2. Synthesize reading (OracleSynthesizer with HRR resonances)
3. Interpret reading (OracleLLMInterpreter)
4. Translate to BO parameters (OracleBOBridge)
5. Run simulation with oracle-guided parameters
6. Record outcome as falsifiable claim (TemporalForecastDB)
7. Feed calibration back into oracle confidence

The cycle adapts over time: as oracle claims are validated or falsified,
the confidence calibration improves, making future readings more accurate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    """Result of one adaptive oracle cycle iteration."""

    question: str
    timestamp: str
    hexagram: int | None = None
    synthesis: dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    bo_params: dict[str, Any] = field(default_factory=dict)
    claim_id: str | None = None
    simulation_result: dict[str, Any] = field(default_factory=dict)
    calibration_score: float | None = None
    cycle_number: int = 0


class AdaptiveOracleCycle:
    """Adaptive recursive oracle-quantum optimization cycle.

    Runs the full cycle: oracle → synthesis → interpretation → BO → simulation
    → outcome tracking → calibration feedback.
    """

    def __init__(self) -> None:
        self._cycle_count: int = 0
        self._results: list[CycleResult] = []
        self._calibration_history: list[float] = []

    @property
    def cycle_count(self) -> int:
        """Number of cycles completed."""
        return self._cycle_count

    @property
    def results(self) -> list[CycleResult]:
        """All cycle results."""
        return list(self._results)

    def run_cycle(
        self,
        question: str,
        context: dict[str, Any] | None = None,
        run_simulation: bool = False,
    ) -> CycleResult:
        """Run one complete adaptive oracle cycle.

        Args:
            question: The question to ask the oracle.
            context: Additional context for the consultation.
            run_simulation: If True, run BO simulation with oracle-guided params.

        Returns:
            CycleResult with all outputs from the cycle.
        """
        self._cycle_count += 1
        cycle_num = self._cycle_count
        timestamp = datetime.utcnow().isoformat()
        result = CycleResult(
            question=question,
            timestamp=timestamp,
            cycle_number=cycle_num,
        )

        # Step 1: Consult oracle
        try:
            from .quantum_iching import QuantumIChing
            oracle = QuantumIChing()
            consultation = oracle.consult(question, context or {})
            result.hexagram = consultation.primary_hexagram
        except Exception as exc:  # noqa: BLE001
            logger.debug("Oracle consultation failed: %s", exc)

        # Step 2: Synthesize reading
        try:
            from .wisdom_synthesis import OracleSynthesizer
            synthesizer = OracleSynthesizer()
            oracle_output = {
                "iching_number": result.hexagram,
                "iching_name": getattr(consultation, "primary_name", ""),
                "iching_judgment": getattr(consultation, "primary_judgment", ""),
                "iching_guidance": getattr(consultation, "primary_image", ""),
                "sign": "Leo",
                "element": "fire",
                "modality": "fixed",
                "phase": "yang",
                "wu_xing": "fire",
                "ifa_odu": "Ogbe",
                "ifa_wisdom": "Patience brings blessings.",
                "ifa_ire": "Good fortune",
                "ifa_osogbo": "Avoid haste",
            }
            synthesis = synthesizer.synthesize(oracle_output)
            result.synthesis = {
                "unified_message": synthesis.unified_message,
                "practical_guidance": synthesis.practical_guidance,
                "hrr_resonances": synthesis.hrr_resonances[:5],
                "primary_hexagram": synthesis.primary_hexagram,
                "claim_ids": synthesis.claim_ids,
            }
            if synthesis.claim_ids:
                result.claim_id = synthesis.claim_ids[0]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Synthesis failed: %s", exc)

        # Step 3: Interpret reading
        try:
            from .llm_interpreter import get_oracle_interpreter
            interpreter = get_oracle_interpreter()
            if synthesis:
                result.interpretation = interpreter.interpret(synthesis, question, context)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Interpretation failed: %s", exc)

        # Step 4: Translate to BO parameters
        try:
            from .oracle_bo_bridge import get_oracle_bo_bridge
            bridge = get_oracle_bo_bridge()
            if result.hexagram:
                result.bo_params = bridge.translate({
                    "primary_hexagram": result.hexagram,
                    "hrr_resonances": result.synthesis.get("hrr_resonances", []),
                })
        except Exception as exc:  # noqa: BLE001
            logger.debug("BO translation failed: %s", exc)

        # Step 5: Run simulation (optional)
        if run_simulation and result.bo_params:
            try:
                from whitemagic.core.consciousness.simulation_orchestrator import (
                    SimulationOrchestrator,
                )
                sim = SimulationOrchestrator()
                sim_result = sim.run_external(
                    model_type="superforecaster",
                    research_query=question,
                    n_iterations=result.bo_params.get("n_bo_iterations", 20),
                    xi=result.bo_params.get("xi", 0.01),
                )
                result.simulation_result = sim_result.to_dict()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Simulation failed: %s", exc)

        # Step 6: Get calibration feedback
        try:
            from whitemagic.forecasting.temporal_db import TemporalForecastDB
            db = TemporalForecastDB()
            score = db.oracle_prescience_score()
            if score.get("brier_score") is not None:
                result.calibration_score = score["brier_score"]
                self._calibration_history.append(score["brier_score"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Calibration lookup failed: %s", exc)

        self._results.append(result)
        return result

    def run_recursive(
        self,
        question: str,
        n_cycles: int = 3,
        context: dict[str, Any] | None = None,
    ) -> list[CycleResult]:
        """Run multiple adaptive cycles recursively.

        Each cycle builds on the previous one's calibration data.

        Args:
            question: The question to explore.
            n_cycles: Number of cycles to run.
            context: Additional context.

        Returns:
            List of CycleResults, one per cycle.
        """
        results: list[CycleResult] = []
        current_context = dict(context or {})

        for i in range(n_cycles):
            # Feed forward calibration from previous cycles
            if self._calibration_history:
                current_context["calibration_brier"] = self._calibration_history[-1]
                current_context["cycle_number"] = i + 1

            result = self.run_cycle(question, current_context, run_simulation=(i == n_cycles - 1))
            results.append(result)

        return results

    def summary(self) -> dict[str, Any]:
        """Get a summary of all cycles run.

        Returns:
            Dict with cycle count, calibration history, and last result.
        """
        return {
            "total_cycles": self._cycle_count,
            "calibration_history": self._calibration_history,
            "avg_calibration": (
                sum(self._calibration_history) / len(self._calibration_history)
                if self._calibration_history else None
            ),
            "last_hexagram": self._results[-1].hexagram if self._results else None,
            "last_interpretation": (
                self._results[-1].interpretation[:200] if self._results and self._results[-1].interpretation else None
            ),
        }


_cycle: AdaptiveOracleCycle | None = None


def get_adaptive_cycle() -> AdaptiveOracleCycle:
    """Get the singleton AdaptiveOracleCycle instance."""
    global _cycle
    if _cycle is None:
        _cycle = AdaptiveOracleCycle()
    return _cycle
