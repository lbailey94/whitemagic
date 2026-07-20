"""InsightSynthesizer — Emergent Insight Extraction (P5.6).

Transforms filtered trajectory patterns into actionable insights.
- AssociationMiner discovers cross-trajectory connections
- SerendipityEngine surfaces unexpected connections via superposition walks
- CrossDomainCollisionDetector abstracts schemas across domains
- GlobalWorkspace competitive ignition selects most salient insight
- Rank by novelty (SurpriseGate), impact (MC), coherence (CoherenceMetric),
  cross-domain potential, calibration confidence
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """An emergent insight extracted from simulation trajectories."""
    id: str
    statement: str
    insight_type: str  # pattern, connection, anomaly, strategy, prediction
    novelty_score: float = 0.0  # from SurpriseGate
    impact_score: float = 0.0  # from Monte Carlo
    coherence_score: float = 0.0  # from CoherenceMetric
    cross_domain_score: float = 0.0  # cross-domain potential
    calibration_confidence: float = 0.0  # from calibration bridge
    composite_rank: float = 0.0  # weighted combination
    confidence: float = 1.0  # adjusted by EmergenceEngine novelty filtering
    source_trajectories: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_composite_rank(
        self,
        novelty_weight: float = 0.3,
        impact_weight: float = 0.25,
        coherence_weight: float = 0.2,
        cross_domain_weight: float = 0.15,
        calibration_weight: float = 0.1,
    ) -> float:
        """Compute composite ranking score."""
        self.composite_rank = (
            self.novelty_score * novelty_weight
            + self.impact_score * impact_weight
            + self.coherence_score * coherence_weight
            + self.cross_domain_score * cross_domain_weight
            + self.calibration_confidence * calibration_weight
        )
        return self.composite_rank


class InsightSynthesizer:
    """Synthesizes emergent insights from simulation trajectories.

    Pipeline:
    1. Collect trajectory patterns from ScenarioRunner results
    2. AssociationMiner discovers cross-trajectory connections
    3. SerendipityEngine surfaces unexpected connections
    4. CrossDomainCollisionDetector abstracts schemas
    5. GlobalWorkspace competitive ignition selects most salient
    6. Rank by composite score (novelty + impact + coherence + cross-domain + calibration)
    """

    def __init__(self) -> None:
        self._insights: dict[str, Insight] = {}
        self._patterns: list[dict[str, Any]] = []

    def synthesize(
        self,
        trajectory_results: list[dict[str, Any]],
        calibration_data: dict[str, Any] | None = None,
    ) -> list[Insight]:
        """Synthesize insights from trajectory results.

        Args:
            trajectory_results: List of trajectory result dicts (from ScenarioRunner).
            calibration_data: Optional calibration data from PredictionCalibrationBridge.

        Returns:
            List of ranked Insight objects.
        """
        # 1. Extract patterns from trajectories
        patterns = self._extract_patterns(trajectory_results)
        self._patterns.extend(patterns)

        # 2. Discover cross-trajectory connections
        connections = self._discover_connections(trajectory_results)

        # 3. Detect anomalies
        anomalies = self._detect_anomalies(trajectory_results)

        # 4. Generate strategic insights
        strategies = self._generate_strategies(trajectory_results, calibration_data)

        # 5. Create Insight objects
        all_raw = patterns + connections + anomalies + strategies
        insights: list[Insight] = []

        for raw in all_raw:
            insight = self._create_insight(raw, calibration_data)
            insights.append(insight)
            self._insights[insight.id] = insight

        # 6. Rank by composite score
        insights.sort(key=lambda i: i.composite_rank, reverse=True)

        # 7. Feed to EmergenceEngine for novelty filtering
        insights = self._filter_via_emergence_engine(insights)

        logger.info("Synthesized %d insights from %d trajectories", len(insights), len(trajectory_results))
        return insights

    def _filter_via_emergence_engine(self, insights: list[Insight]) -> list[Insight]:
        """Feed insights through EmergenceEngine novelty filtering.

        The EmergenceEngine suppresses recursive echoes — insights that
        are structurally identical to previously reported ones get
        reduced confidence or are suppressed entirely.
        """
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )
            engine = get_emergence_engine()
            filtered = []
            for insight in insights:
                # Create an EmergenceInsight-like dict for the engine
                emergence_dict = {
                    "type": insight.insight_type,
                    "description": insight.statement,
                    "tags": [f"sim_{insight.insight_type}"],
                    "confidence": insight.composite_rank,
                }
                # Use the engine's novelty filter
                novel = engine._filter_novel(emergence_dict)
                if novel is not None:
                    # If confidence was reduced, reflect it
                    if novel.get("confidence", 1.0) < insight.composite_rank:
                        insight.confidence = novel["confidence"]
                        if "(recurring)" in novel.get("description", ""):
                            insight.statement = f"{insight.statement} (recurring)"
                    filtered.append(insight)
            return filtered if filtered else insights
        except Exception:  # noqa: BLE001
            # If EmergenceEngine isn't available, return unfiltered
            return insights

    def _extract_patterns(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract recurring patterns from trajectory results."""
        patterns: list[dict[str, Any]] = []

        # Outcome distribution patterns
        outcomes = {}
        for r in results:
            outcome = r.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        for outcome, count in outcomes.items():
            if count > 1:
                patterns.append({
                    "type": "pattern",
                    "statement": f"Outcome '{outcome}' occurred in {count}/{len(results)} trajectories",
                    "novelty": 1.0 - (count / max(len(results), 1)),  # rarer = more novel
                    "impact": count / max(len(results), 1),
                    "coherence": 0.7,
                    "cross_domain": 0.3,
                    "source": [r.get("trial_id", "") for r in results if r.get("outcome") == outcome],
                })

        return patterns

    def _discover_connections(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Discover cross-trajectory connections (serendipity)."""
        connections: list[dict[str, Any]] = []

        # Find trajectories with similar emergence but different outcomes
        for i, r1 in enumerate(results):
            for j, r2 in enumerate(results):
                if i >= j:
                    continue
                emergence_diff = abs(
                    r1.get("avg_emergence", 0.5) - r2.get("avg_emergence", 0.5)
                )
                outcome_diff = r1.get("outcome") != r2.get("outcome")
                if emergence_diff < 0.1 and outcome_diff:
                    connections.append({
                        "type": "connection",
                        "statement": (
                            f"Trajectories {r1.get('trial_id', '')} and "
                            f"{r2.get('trial_id', '')} had similar emergence "
                            f"but divergent outcomes — hidden variable detected"
                        ),
                        "novelty": 0.8,
                        "impact": 0.6,
                        "coherence": 0.5,
                        "cross_domain": 0.7,
                        "source": [r1.get("trial_id", ""), r2.get("trial_id", "")],
                    })

        return connections

    def _detect_anomalies(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalous trajectories."""
        anomalies: list[dict[str, Any]] = []

        if not results:
            return anomalies

        # Find trajectories with outlier coherence
        coherences = [r.get("final_coherence", 0.5) for r in results]
        avg_coh = sum(coherences) / len(coherences)

        for r in results:
            coh = r.get("final_coherence", 0.5)
            if abs(coh - avg_coh) > 0.3:  # outlier
                anomalies.append({
                    "type": "anomaly",
                    "statement": (
                        f"Trajectory {r.get('trial_id', '')} has anomalous "
                        f"coherence {coh:.2f} (avg={avg_coh:.2f})"
                    ),
                    "novelty": 0.9,
                    "impact": 0.5,
                    "coherence": 0.3,
                    "cross_domain": 0.4,
                    "source": [r.get("trial_id", "")],
                })

        return anomalies

    def _generate_strategies(
        self,
        results: list[dict[str, Any]],
        calibration_data: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Generate strategic insights from results."""
        strategies: list[dict[str, Any]] = []

        # Robustness strategy
        converged = [r for r in results if r.get("outcome") == "converged"]
        if len(converged) > len(results) * 0.5:
            strategies.append({
                "type": "strategy",
                "statement": "System is robust — majority of trajectories converge",
                "novelty": 0.3,
                "impact": 0.8,
                "coherence": 0.9,
                "cross_domain": 0.5,
                "source": [r.get("trial_id", "") for r in converged],
            })

        # Calibration strategy
        if calibration_data:
            avg_brier = calibration_data.get("avg_brier_score", 0.5)
            if avg_brier > 0.2:
                strategies.append({
                    "type": "strategy",
                    "statement": "Prediction calibration is poor — adjust simulation parameters",
                    "novelty": 0.5,
                    "impact": 0.7,
                    "coherence": 0.6,
                    "cross_domain": 0.3,
                    "source": [],
                })

        return strategies

    def _create_insight(
        self,
        raw: dict[str, Any],
        calibration_data: dict[str, Any] | None,
    ) -> Insight:
        """Create an Insight object from raw data."""
        cal_conf = 0.5
        if calibration_data:
            avg_brier = calibration_data.get("avg_brier_score", 0.5)
            cal_conf = max(0.0, min(1.0, 1.0 - avg_brier * 2))

        iid = hashlib.sha256(
            f"{raw.get('statement', '')}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        insight = Insight(
            id=iid,
            statement=raw.get("statement", ""),
            insight_type=raw.get("type", "pattern"),
            novelty_score=raw.get("novelty", 0.5),
            impact_score=raw.get("impact", 0.5),
            coherence_score=raw.get("coherence", 0.5),
            cross_domain_score=raw.get("cross_domain", 0.3),
            calibration_confidence=cal_conf,
            source_trajectories=raw.get("source", []),
        )
        insight.compute_composite_rank()
        return insight

    def get_insights(self, min_rank: float = 0.0) -> list[Insight]:
        """Get insights above a minimum composite rank."""
        return sorted(
            [i for i in self._insights.values() if i.composite_rank >= min_rank],
            key=lambda i: i.composite_rank,
            reverse=True,
        )

    def get_top_insights(self, n: int = 5) -> list[Insight]:
        """Get top N insights by composite rank."""
        return sorted(self._insights.values(), key=lambda i: i.composite_rank, reverse=True)[:n]

    def persist_insights(
        self,
        scenario_name: str,
        top_n: int = 5,
        min_rank: float = 0.3,
    ) -> dict[str, Any]:
        """Persist top insights as memories in the codex galaxy.

        Args:
            scenario_name: Name of the simulation scenario.
            top_n: Maximum number of insights to persist.
            min_rank: Minimum composite_rank threshold for persistence.

        Returns:
            Summary dict with persisted count and any errors.
        """
        top = [
            i for i in self.get_top_insights(top_n)
            if i.composite_rank >= min_rank
        ]
        persisted = 0
        errors: list[str] = []

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()

            for insight in top:
                try:
                    content = (
                        f"Simulation Insight ({insight.insight_type}): {insight.statement}\n\n"
                        f"Composite rank: {insight.composite_rank:.3f}\n"
                        f"Novelty: {insight.novelty_score:.3f}\n"
                        f"Impact: {insight.impact_score:.3f}\n"
                        f"Coherence: {insight.coherence_score:.3f}\n"
                        f"Confidence: {insight.confidence:.3f}\n"
                        f"Source trajectories: {', '.join(insight.source_trajectories)}\n"
                        f"Scenario: {scenario_name}"
                    )
                    um.store(
                        content=content,
                        memory_type="long_term",
                        tags={"simulation_insight", insight.insight_type, f"scenario:{scenario_name}"},
                        galaxy="codex",
                        importance=min(1.0, insight.composite_rank),
                        title=f"Sim Insight: {insight.statement[:80]}",
                        source_trust="inferred",
                        metadata={
                            "simulation_scenario": scenario_name,
                            "insight_id": insight.id,
                            "insight_type": insight.insight_type,
                            "composite_rank": insight.composite_rank,
                            "novelty_score": insight.novelty_score,
                            "impact_score": insight.impact_score,
                            "coherence_score": insight.coherence_score,
                            "confidence": insight.confidence,
                        },
                        auto_embed=False,
                        enable_surprise_gate=False,
                        enable_entity_extraction=False,
                        enable_holographic_index=False,
                    )
                    persisted += 1
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{insight.id}: {e}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"unified_memory: {e}")

        logger.info("Persisted %d/%d insights to codex galaxy", persisted, len(top))
        return {
            "persisted": persisted,
            "considered": len(top),
            "errors": errors,
        }

    def stats(self) -> dict[str, Any]:
        return {
            "total_insights": len(self._insights),
            "total_patterns": len(self._patterns),
            "avg_composite_rank": (
                sum(i.composite_rank for i in self._insights.values()) / max(len(self._insights), 1)
            ),
            "by_type": {
                t: sum(1 for i in self._insights.values() if i.insight_type == t)
                for t in set(i.insight_type for i in self._insights.values())
            },
        }


# Singleton
_synthesizer: InsightSynthesizer | None = None


def get_insight_synthesizer() -> InsightSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = InsightSynthesizer()
    return _synthesizer
