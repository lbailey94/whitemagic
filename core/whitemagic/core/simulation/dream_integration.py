"""DreamCycleIntegration — Offline Consolidation (P5.7).

Wires simulation completion to DreamCycle phases:
- CONSOLIDATION: cluster + promote simulation memories
- SERENDIPITY: surface cross-simulation connections
- KAIZEN: analyze patterns
- ORACLE: strategic insight
- PREDICTION: detect drift
- NARRATIVE: compress story

Cross-simulation association mining. Next-run recommendation generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _try_import_dream_cycle():
    """Lazy import DreamCycle to avoid circular dependencies."""
    try:
        from whitemagic.core.dreaming.dream_cycle import DreamCycle, DreamPhase
        return DreamCycle, DreamPhase
    except Exception:  # noqa: BLE001
        return None, None


@dataclass
class ConsolidationReport:
    """Report from dream-cycle consolidation of a simulation."""
    simulation_id: str
    phase: str  # consolidation, serendipity, kaizen, oracle, prediction, narrative
    memories_consolidated: int = 0
    associations_discovered: int = 0
    insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    narrative: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class DreamCycleIntegration:
    """Integrates simulation results with the DreamCycle for offline consolidation.

    When a simulation completes, this module:
    1. Triggers CONSOLIDATION phase — cluster and promote simulation memories
    2. Triggers SERENDIPITY phase — surface cross-simulation connections
    3. Triggers KAIZEN phase — analyze patterns across simulations
    4. Triggers ORACLE phase — generate strategic insights
    5. Triggers PREDICTION phase — detect drift from predictions
    6. Triggers NARRATIVE phase — compress simulation story
    7. Mines cross-simulation associations
    8. Generates recommendations for next run
    """

    PHASES = [
        "consolidation",
        "serendipity",
        "kaizen",
        "oracle",
        "prediction",
        "narrative",
    ]

    def __init__(self) -> None:
        self._reports: dict[str, list[ConsolidationReport]] = {}  # sim_id → reports
        self._cross_sim_associations: list[dict[str, Any]] = []
        self._recommendations: list[str] = []

    def consolidate_simulation(
        self,
        simulation_id: str,
        simulation_data: dict[str, Any],
        galaxy: str | None = None,
    ) -> list[ConsolidationReport]:
        """Run full dream-cycle consolidation for a completed simulation.

        Args:
            simulation_id: Unique ID for the simulation.
            simulation_data: Dict with simulation results (events, outcomes, etc.).
            galaxy: Galaxy where simulation memories are stored.

        Returns:
            List of ConsolidationReports, one per phase.
        """
        reports: list[ConsolidationReport] = []

        for phase in self.PHASES:
            report = self._run_phase(simulation_id, phase, simulation_data, galaxy)
            reports.append(report)

        # Cross-simulation association mining
        self._mine_cross_sim_associations(simulation_id, simulation_data)

        # Generate next-run recommendations
        self._generate_recommendations(simulation_id, reports)

        self._reports[simulation_id] = reports
        logger.info("Consolidated simulation %s through %d phases", simulation_id, len(reports))
        return reports

    def _run_phase(
        self,
        sim_id: str,
        phase: str,
        data: dict[str, Any],
        galaxy: str | None,
    ) -> ConsolidationReport:
        """Run a single dream-cycle phase for simulation consolidation.

        Delegates to the real DreamCycle when available, falling back to
        simulated phases for standalone operation.
        """
        report = ConsolidationReport(simulation_id=sim_id, phase=phase)

        # Try delegating to the real DreamCycle
        DreamCycle, DreamPhase = _try_import_dream_cycle()
        if DreamCycle is not None:
            try:
                real_result = self._delegate_to_dream_cycle(
                    phase, data, galaxy, DreamPhase
                )
                # Only use delegation result if it has actual content
                if real_result is not None and (
                    real_result.get("memories_consolidated", 0) > 0
                    or real_result.get("associations_discovered", 0) > 0
                    or real_result.get("insights")
                    or real_result.get("narrative")
                ):
                    report.memories_consolidated = real_result.get("memories_consolidated", 0)
                    report.associations_discovered = real_result.get("associations_discovered", 0)
                    if real_result.get("insights"):
                        report.insights.extend(real_result["insights"])
                    if real_result.get("narrative"):
                        report.narrative = real_result["narrative"]
                    return report
            except Exception as e:  # noqa: BLE001
                logger.debug("DreamCycle delegation failed for %s: %s", phase, e)

        # Fallback: simulated phases
        if phase == "consolidation":
            # Cluster and promote simulation memories
            report.memories_consolidated = data.get("events_count", 0)
            report.insights.append(f"Consolidated {report.memories_consolidated} simulation events")

        elif phase == "serendipity":
            # Surface cross-simulation connections
            report.associations_discovered = len(self._cross_sim_associations)
            if report.associations_discovered > 0:
                report.insights.append(
                    f"Discovered {report.associations_discovered} cross-simulation connections"
                )

        elif phase == "kaizen":
            # Analyze patterns
            outcome = data.get("outcome", "unknown")
            coherence = data.get("final_coherence", 0.5)
            report.insights.append(f"Outcome pattern: {outcome} (coherence={coherence:.2f})")
            if coherence > 0.8:
                report.insights.append("High coherence suggests stable configuration")
            elif coherence < 0.3:
                report.insights.append("Low coherence suggests unstable configuration")

        elif phase == "oracle":
            # Strategic insight
            best = data.get("best_trial")
            if best:
                report.insights.append(
                    f"Best trajectory: coherence={best.get('final_coherence', 0):.2f}"
                )
            report.insights.append("Consider varying initial conditions for broader exploration")

        elif phase == "prediction":
            # Detect drift from predictions
            predictions = data.get("predictions", [])
            resolved = [p for p in predictions if p.get("resolved")]
            if resolved:
                avg_brier = sum(p.get("brier_score", 0.5) for p in resolved) / len(resolved)
                report.insights.append(f"Average Brier score: {avg_brier:.3f}")
                if avg_brier > 0.2:
                    report.insights.append("High prediction error — calibration needed")

        elif phase == "narrative":
            # Compress story
            events = data.get("events_count", 0)
            ticks = data.get("ticks", 0)
            outcome = data.get("outcome", "unknown")
            report.narrative = (
                f"Simulation {sim_id} ran for {ticks} ticks with {events} events. "
                f"Final outcome: {outcome}. "
                f"Coherence stabilized at {data.get('final_coherence', 0.5):.2f}."
            )

        return report

    def _delegate_to_dream_cycle(
        self,
        phase: str,
        data: dict[str, Any],
        galaxy: str | None,
        DreamPhase: Any,
    ) -> dict[str, Any] | None:
        """Delegate a phase to the real DreamCycle implementation.

        Maps simulation phases to DreamPhase enum values and calls the
        corresponding dream cycle method.
        """
        from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

        try:
            dc = get_dream_cycle()

            phase_map = {
                "consolidation": DreamPhase.CONSOLIDATION,
                "serendipity": DreamPhase.SERENDIPITY,
                "kaizen": DreamPhase.KAIZEN,
                "oracle": DreamPhase.ORACLE,
                "prediction": DreamPhase.PREDICTION,
                "narrative": DreamPhase.NARRATIVE,
            }

            dp = phase_map.get(phase)
            if dp is None:
                return None

            # Call the corresponding dream phase method
            method_map = {
                DreamPhase.CONSOLIDATION: "_dream_consolidation",
                DreamPhase.SERENDIPITY: "_dream_serendipity",
                DreamPhase.KAIZEN: "_dream_kaizen",
                DreamPhase.ORACLE: "_dream_oracle",
                DreamPhase.PREDICTION: "_dream_prediction",
                DreamPhase.NARRATIVE: "_dream_narrative",
            }

            method_name = method_map.get(dp)
            if method_name and hasattr(dc, method_name):
                result = getattr(dc, method_name)()
                return {
                    "memories_consolidated": result.get("consolidated", 0) if isinstance(result, dict) else 0,
                    "associations_discovered": result.get("connections", 0) if isinstance(result, dict) else 0,
                    "insights": [result.get("insight", "")] if isinstance(result, dict) and result.get("insight") else [],
                    "narrative": result.get("narrative", "") if isinstance(result, dict) else "",
                }
        except Exception as e:  # noqa: BLE001
            logger.debug("DreamCycle delegation error: %s", e)

        return None

    def _mine_cross_sim_associations(
        self, sim_id: str, data: dict[str, Any]
    ) -> None:
        """Mine associations between this simulation and previous ones."""
        for prev_sim_id, prev_reports in self._reports.items():
            if prev_sim_id == sim_id:
                continue
            # Simple association: same outcome pattern
            prev_outcome = prev_reports[-1].narrative if prev_reports else ""
            curr_outcome = data.get("outcome", "")
            if prev_outcome and curr_outcome and curr_outcome in prev_outcome:
                self._cross_sim_associations.append({
                    "source": prev_sim_id,
                    "target": sim_id,
                    "strength": 0.7,
                    "type": "outcome_similarity",
                })

    def _generate_recommendations(
        self, sim_id: str, reports: list[ConsolidationReport]
    ) -> None:
        """Generate recommendations for the next simulation run."""
        # Collect all insights
        all_insights = []
        for r in reports:
            all_insights.extend(r.insights)

        # Generate recommendations from insights
        if any("unstable" in i.lower() for i in all_insights):
            self._recommendations.append(
                f"[{sim_id}] Increase dharma_strictness to stabilize interactions"
            )
        if any("calibration" in i.lower() for i in all_insights):
            self._recommendations.append(
                f"[{sim_id}] Adjust prediction calibration before next run"
            )
        if any("broader exploration" in i.lower() for i in all_insights):
            self._recommendations.append(
                f"[{sim_id}] Vary initial conditions more aggressively"
            )

    def get_reports(self, simulation_id: str) -> list[ConsolidationReport] | None:
        return self._reports.get(simulation_id)

    def get_recommendations(self) -> list[str]:
        return self._recommendations

    def get_cross_sim_associations(self) -> list[dict[str, Any]]:
        return self._cross_sim_associations

    def persist_consolidation(
        self,
        simulation_id: str,
        reports: list[ConsolidationReport] | None = None,
    ) -> dict[str, Any]:
        """Persist consolidation reports as memories in appropriate galaxies.

        Routes narrative and oracle insights to dreams galaxy,
        kaizen/pattern reports to research galaxy.

        Args:
            simulation_id: ID of the simulation.
            reports: Optional list of reports (defaults to stored reports).

        Returns:
            Summary dict with persisted counts per galaxy.
        """
        if reports is None:
            reports = self._reports.get(simulation_id, [])

        if not reports:
            return {"persisted": 0, "errors": []}

        persisted = 0
        errors: list[str] = []

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()

            for report in reports:
                try:
                    # Route by phase: dreams for narrative/oracle, research for kaizen/prediction
                    if report.phase in ("narrative", "oracle"):
                        galaxy = "dreams"
                    elif report.phase in ("kaizen", "prediction"):
                        galaxy = "research"
                    else:
                        galaxy = "codex"

                    content = (
                        f"Dream Cycle Phase: {report.phase}\n"
                        f"Simulation: {simulation_id}\n"
                        f"Memories consolidated: {report.memories_consolidated}\n"
                        f"Associations discovered: {report.associations_discovered}\n"
                        f"Insights: {'; '.join(report.insights)}\n"
                        f"Recommendations: {'; '.join(report.recommendations)}\n"
                        f"Narrative: {report.narrative}"
                    )
                    um.store(
                        content=content,
                        memory_type="long_term",
                        tags={"dream_cycle", report.phase, f"simulation:{simulation_id}"},
                        galaxy=galaxy,
                        importance=0.6,
                        title=f"Dream {report.phase}: {simulation_id}",
                        source_trust="inferred",
                        metadata={
                            "simulation_id": simulation_id,
                            "phase": report.phase,
                            "memories_consolidated": report.memories_consolidated,
                            "associations_discovered": report.associations_discovered,
                        },
                        auto_embed=False,
                        enable_surprise_gate=False,
                        enable_entity_extraction=False,
                        enable_holographic_index=False,
                    )
                    persisted += 1
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{report.phase}: {e}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"unified_memory: {e}")

        logger.info("Persisted %d/%d consolidation reports for %s", persisted, len(reports), simulation_id)
        return {"persisted": persisted, "considered": len(reports), "errors": errors}

    def stats(self) -> dict[str, Any]:
        return {
            "total_simulations_consolidated": len(self._reports),
            "total_reports": sum(len(reports) for reports in self._reports.values()),
            "cross_sim_associations": len(self._cross_sim_associations),
            "recommendations": len(self._recommendations),
        }


# Singleton
_integration: DreamCycleIntegration | None = None


def get_dream_integration() -> DreamCycleIntegration:
    global _integration
    if _integration is None:
        _integration = DreamCycleIntegration()
    return _integration
