# ruff: noqa: BLE001
"""Recursive Improvement Loop — WhiteMagic improving WhiteMagic.

Connects the existing intelligence systems into a closed loop:

  1. OBSERVE    KaizenEngine + PredictiveEngine + EmergenceEngine → proposals
  2. IMAGINE    MC-HLL simulates impact, SurpriseGate evaluates novelty
  3. PREDICT    TemporalForecastDB stores predictions with confidence
  4. ACT        ToolBandit recommends tools, Ollama agent executes
  5. CALIBRATE  MC engine scores predictions vs actual outcomes
  6. LEARN      AutodidacticLoop records outcomes, bandit updates posteriors

The loop emits Gan Ying events at each phase so downstream listeners
(dream cycle, insight pipeline, dashboard) can react.

Usage:
    from whitemagic.core.evolution.recursive_loop import get_improvement_loop
    loop = get_improvement_loop()
    cycle = loop.run_cycle()  # One full observe→imagine→predict cycle
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.evolution.autodidactic_loop import (
    AutodidacticLoop,
    PatternApplication,
    PatternOutcome,
)
from whitemagic.core.memory.probabilistic import CountMinSketch, HyperLogLog
from whitemagic.forecasting.mc_integration import MCForecastEnhancer
from whitemagic.tools.handlers.tool_bandit import get_tool_bandit

logger = logging.getLogger(__name__)


@dataclass
class ImprovementHypothesis:
    """A predicted improvement with confidence and simulated impact."""

    id: str
    source: str  # "kaizen", "predictive", "emergence", "dream"
    title: str
    description: str
    category: str  # quality, gap, performance, emergence, codebase_quality
    predicted_impact: float  # 0-1, from MC simulation
    confidence: float  # 0-1, from MC Brier skill score
    effort: str  # high, medium, low
    auto_fixable: bool = False
    fix_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    novelty_score: float = 0.0  # From surprise gate
    verification_query: str | None = None  # Kaizen check name for re-verification
    before_count: int | None = None  # Issue count before fix (for delta computation)
    information_gain: float = 0.0  # Objective P: Expected information gain (bits)
    garden: str | None = None  # Objective L: Garden classification
    guna: str | None = None  # Objective V: Guna classification
    galactic_zone: str | None = None  # Objective G: Galactic lifecycle zone
    debate_contention: float = 0.0  # Objective O: Bicameral debate contention score
    yield_type: str | None = None  # Objective Y: Yield curve type
    exploration_boost: float = 0.0  # Objective O/Q: Combined exploration boost


@dataclass
class ImprovementCycle:
    """Result of one complete improvement cycle."""

    cycle_id: str
    timestamp: str
    phase_results: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[ImprovementHypothesis] = field(default_factory=list)
    top_recommendations: list[dict[str, Any]] = field(default_factory=list)
    analytics: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "phases": list(self.phase_results.keys()),
            "hypothesis_count": len(self.hypotheses),
            "top_recommendations": self.top_recommendations,
            "analytics": self.analytics,
            "duration_ms": round(self.duration_ms, 1),
        }


class RecursiveImprovementLoop:
    """Orchestrates the observe→imagine→predict→act→calibrate→learn loop.

    Uses existing WhiteMagic systems:
    - KaizenEngine for codebase + memory analysis
    - PredictiveEngine for milestone/velocity/gap predictions
    - EmergenceEngine for novel pattern detection
    - MCForecastEnhancer for impact simulation + HLL/CMS tracking
    - ToolBandit for tool selection optimization
    - AutodidacticLoop for pattern confidence tracking
    - GanYingBus for event emission
    """

    def __init__(self) -> None:
        self._mc_enhancer = MCForecastEnhancer()
        self._bandit = get_tool_bandit()
        self._autodidactic = AutodidacticLoop()
        self._hll = HyperLogLog(precision=14)  # Track distinct improvements
        self._cms = CountMinSketch(width=4096, depth=5)  # Track improvement frequency
        self._cycle_count = 0
        self._last_cycle: ImprovementCycle | None = None
        # Objective D: Surprisal-driven exploration
        self._surprise_gate: Any = None
        self._surprisal_alpha = 0.6  # Weight for CMS novelty
        self._surprisal_beta = 0.4  # Weight for surprisal score
        # Objective P: Information-theoretic exploration
        self._exploration_weights: Any = None
        # Objective Q: Thermodynamic resource allocation
        self._thermo_state: Any = None
        # Objective J: Bayesian dream
        self._bayesian_dream: Any = None
        # Objective F: Holographic trajectory
        self._holographic_traj: Any = None
        # Objective G: Galactic hypothesis lifecycle
        self._galactic_hyp: Any = None
        # Objective H: HRR composition
        self._hrr_composer: Any = None
        # Objective N: Constellation evaluation
        self._constellation_eval: Any = None
        # Objective U: Dependency graph
        self._dependency_graph: Any = None
        # Objective K: Valence utility tracker
        self._valence_tracker: Any = None
        # Objective L: Garden router
        self._garden_router: Any = None
        # Objective R: Predictive coding model
        self._predictive_coding: Any = None
        # Objective T: Causal ledger
        self._causal_ledger: Any = None
        # Objective C: Counterfactual estimator
        self._counterfactual: Any = None
        # Objective V: Guna classifier
        self._guna_classifier: Any = None
        # Objective S: Polyglot MC orchestrator
        self._polyglot_mc: Any = None
        # Objective M: Actor supervisor
        self._actor_supervisor: Any = None
        # Objective I: Resonance transfer engine
        self._resonance_transfer: Any = None
        # Objective O: Bicameral debate
        self._bicameral_debate: Any = None
        # Objective Y: Yield portfolio
        self._yield_portfolio: Any = None
        # Objective Z: Meta-bandit
        self._meta_bandit: Any = None

    def run_cycle(self, max_hypotheses: int = 20) -> ImprovementCycle:
        """Run one complete improvement cycle.

        Args:
            max_hypotheses: Maximum hypotheses to generate per cycle

        Returns:
            ImprovementCycle with all phase results and recommendations.
        """
        cycle_start = time.perf_counter()
        cycle_id = str(uuid.uuid4())[:8]
        self._cycle_count += 1

        logger.info(
            "Recursive improvement cycle %d (%s) starting", self._cycle_count, cycle_id
        )

        cycle = ImprovementCycle(
            cycle_id=cycle_id,
            timestamp=datetime.now().isoformat(),
        )

        cycle.phase_results["verify"] = self._phase_verify(cycle)

        cycle.phase_results["observe"] = self._phase_observe(cycle)

        cycle.phase_results["imagine"] = self._phase_imagine(cycle, max_hypotheses)

        cycle.phase_results["predict"] = self._phase_predict(cycle)

        cycle.phase_results["recommend"] = self._phase_recommend(cycle)

        cycle.phase_results["learn"] = self._phase_learn(cycle)

        # Analytics
        cycle.analytics = self._build_analytics(cycle)
        cycle.duration_ms = (time.perf_counter() - cycle_start) * 1000

        # Emit Gan Ying event
        self._emit_cycle_event(cycle)

        self._last_cycle = cycle
        logger.info(
            "Improvement cycle %d complete: %d hypotheses, %.0fms",
            self._cycle_count,
            len(cycle.hypotheses),
            cycle.duration_ms,
        )

        return cycle

    def _get_surprise_gate(self) -> Any:
        """Lazy-load the SurpriseGate singleton (Objective D)."""
        if self._surprise_gate is None:
            try:
                from whitemagic.core.memory.surprise_gate import get_surprise_gate

                self._surprise_gate = get_surprise_gate()
            except (ImportError, AttributeError) as e:
                logger.debug("SurpriseGate unavailable: %s", e)
                self._surprise_gate = False  # Sentinel: unavailable
        return self._surprise_gate if self._surprise_gate is not False else None

    def _get_exploration_weights(self) -> Any:
        """Lazy-load and adapt exploration weights (Objective P)."""
        if self._exploration_weights is None:
            try:
                from whitemagic.core.evolution.info_theory import (
                    AdaptiveWeights,
                    system_uncertainty,
                )

                weights = AdaptiveWeights()
                # Adapt based on current cycle's confidence distribution
                if self._last_cycle and self._last_cycle.hypotheses:
                    confidences = [h.confidence for h in self._last_cycle.hypotheses]
                    uncertainty = system_uncertainty(confidences)
                    weights.adapt(uncertainty)
                self._exploration_weights = weights
            except (ImportError, AttributeError) as e:
                logger.debug("Info-theory weights unavailable: %s", e)
                self._exploration_weights = False
        return (
            self._exploration_weights
            if self._exploration_weights is not False
            else None
        )

    def _compute_surprisal_novelty(self, description: str, cms_novelty: float) -> float:
        """Blend CMS-based novelty with embedding-based surprisal (Objective D).

        novelty = alpha * cms_novelty + beta * surprisal_score

        Surprisal score is normalized from the SurpriseGate's surprise_score
        (which is -log2(max_similarity), typically 0-10) to 0-1 range.

        Args:
            description: Hypothesis description text to evaluate.
            cms_novelty: CMS-frequency-based novelty score (0-1).

        Returns:
            Blended novelty score in 0-1 range.
        """
        gate = self._get_surprise_gate()
        if gate is None:
            return cms_novelty

        try:
            verdict = gate.evaluate(description)
            # Normalize surprise score: typical range 0-10, clamp to 0-1
            surprisal = min(verdict.surprise_score / 10.0, 1.0)
            blended = (
                self._surprisal_alpha * cms_novelty + self._surprisal_beta * surprisal
            )
            return max(0.0, min(1.0, blended))
        except Exception as e:
            logger.debug("Surprisal evaluation failed: %s", e)
            return cms_novelty

    def _get_module(self, attr: str, module_path: str, class_name: str) -> Any:
        """Generic lazy-loading helper for evolution modules.

        Args:
            attr: Instance attribute name to cache the module.
            module_path: Dotted import path to the module.
            class_name: Class name to instantiate.

        Returns:
            Module instance or None if unavailable.
        """
        cached = getattr(self, attr, None)
        if cached is not None:
            return cached if cached is not False else None
        try:
            mod = __import__(module_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            instance = cls()
            setattr(self, attr, instance)
            return instance
        except (ImportError, AttributeError, Exception) as e:
            logger.debug("%s unavailable: %s", class_name, e)
            setattr(self, attr, False)  # Sentinel: unavailable
            return None

    def _get_thermo_state(self) -> Any:
        """Objective Q: Lazy-load ThermodynamicState."""
        return self._get_module(
            "_thermo_state",
            "whitemagic.core.evolution.thermodynamic",
            "ThermodynamicState",
        )

    def _get_garden_router(self) -> Any:
        """Objective L: Lazy-load GardenRouter."""
        return self._get_module(
            "_garden_router", "whitemagic.core.evolution.garden_router", "GardenRouter"
        )

    def _get_guna_classifier(self) -> Any:
        """Objective V: Lazy-load GunaClassifier."""
        return self._get_module(
            "_guna_classifier",
            "whitemagic.core.evolution.guna_classifier",
            "GunaClassifier",
        )

    def _get_valence_tracker(self) -> Any:
        """Objective K: Lazy-load ValenceUtilityTracker."""
        return self._get_module(
            "_valence_tracker",
            "whitemagic.core.evolution.valence_utility",
            "ValenceUtilityTracker",
        )

    def _get_bicameral_debate(self) -> Any:
        """Objective O: Lazy-load BicameralDebate."""
        return self._get_module(
            "_bicameral_debate",
            "whitemagic.core.evolution.bicameral_debate",
            "BicameralDebate",
        )

    def _get_causal_ledger(self) -> Any:
        """Objective T: Lazy-load CausalLedger."""
        return self._get_module(
            "_causal_ledger", "whitemagic.core.evolution.causal_ledger", "CausalLedger"
        )

    def _get_predictive_coding(self) -> Any:
        """Objective R: Lazy-load PredictiveCodingModel."""
        return self._get_module(
            "_predictive_coding",
            "whitemagic.core.evolution.predictive_coding",
            "PredictiveCodingModel",
        )

    def _get_yield_portfolio(self) -> Any:
        """Objective Y: Lazy-load YieldPortfolio."""
        return self._get_module(
            "_yield_portfolio",
            "whitemagic.core.evolution.yield_curve",
            "YieldPortfolio",
        )

    def _get_meta_bandit(self) -> Any:
        """Objective Z: Lazy-load MetaBandit."""
        return self._get_module(
            "_meta_bandit", "whitemagic.core.evolution.zen_meta", "MetaBandit"
        )

    def _get_actor_supervisor(self) -> Any:
        """Objective M: Lazy-load ActorSupervisor."""
        return self._get_module(
            "_actor_supervisor",
            "whitemagic.core.evolution.actor_outcome",
            "ActorSupervisor",
        )

    def _get_resonance_transfer(self) -> Any:
        """Objective I: Lazy-load ResonanceTransferEngine."""
        return self._get_module(
            "_resonance_transfer",
            "whitemagic.core.evolution.resonance_transfer",
            "ResonanceTransferEngine",
        )

    def _get_polyglot_mc(self) -> Any:
        """Objective S: Lazy-load PolyglotMCOrchestrator."""
        return self._get_module(
            "_polyglot_mc",
            "whitemagic.core.evolution.polyglot_mc",
            "PolyglotMCOrchestrator",
        )

    def _get_galactic_hyp(self) -> Any:
        """Objective G: Lazy-load GalacticHypothesisManager."""
        return self._get_module(
            "_galactic_hyp",
            "whitemagic.core.evolution.galactic_hypothesis",
            "GalacticHypothesisManager",
        )

    def _get_holographic_traj(self) -> Any:
        """Objective F: Lazy-load HolographicTrajectory."""
        return self._get_module(
            "_holographic_traj",
            "whitemagic.core.evolution.holographic_trajectory",
            "HolographicTrajectory",
        )

    def _get_dependency_graph(self) -> Any:
        """Objective U: Lazy-load DependencyGraph."""
        return self._get_module(
            "_dependency_graph",
            "whitemagic.core.evolution.dependency_graph",
            "DependencyGraph",
        )

    def _get_constellation_eval(self) -> Any:
        """Objective N: Lazy-load ConstellationEvaluator."""
        return self._get_module(
            "_constellation_eval",
            "whitemagic.core.evolution.constellation_eval",
            "ConstellationEvaluator",
        )

    def _classify_hypothesis(self, hyp: ImprovementHypothesis) -> None:
        """Classify a hypothesis through garden, guna, and galactic systems.

        Mutates the hypothesis in-place with classification results.
        """
        # Objective L: Garden routing
        router = self._get_garden_router()
        if router is not None:
            hyp.garden = router.classify(hyp.category, hyp.description)

        # Objective V: Guna classification
        clf = self._get_guna_classifier()
        if clf is not None:
            guna = clf.classify(hyp.category, hyp.description)
            hyp.guna = guna.value if hasattr(guna, "value") else str(guna)

        # Objective G: Galactic zone assignment
        galactic = self._get_galactic_hyp()
        if galactic is not None:
            try:
                zone = galactic.assign_zone(hyp.id, hyp.confidence, hyp.novelty_score)
                hyp.galactic_zone = zone.value if hasattr(zone, "value") else str(zone)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

    def _debate_hypothesis(self, hyp: ImprovementHypothesis) -> float:
        """Objective O: Run bicameral debate on a hypothesis.

        Returns exploration boost from contention (0-0.2).
        """
        debate = self._get_bicameral_debate()
        if debate is None:
            return 0.0
        try:
            risk = 1.0 - hyp.confidence
            result = debate.debate(
                hypothesis_id=hyp.id,
                predicted_impact=hyp.predicted_impact,
                feasibility=hyp.confidence,
                risk=risk,
                historical_failure_rate=0.3,
                opportunity_cost=0.2,
            )
            hyp.debate_contention = result.contention
            return debate.get_exploration_boost(hyp.id)
        except Exception:
            return 0.0

    def _get_thermodynamic_temperature(self) -> float:
        """Objective Q: Get current thermodynamic temperature for selection."""
        thermo = self._get_thermo_state()
        if thermo is None:
            return 1.0  # Default: no cooling
        try:
            return thermo.temperature
        except Exception:
            return 1.0

    def _phase_verify(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Phase 0: Auto-verify outcomes from the previous cycle.

        Closes the feedback loop by re-running kaizen checks on previous
        recommendations. If an auto-fixable issue (e.g. "untitled memories")
        was resolved between cycles, the outcome is recorded in the
        AutodidacticLoop, making learning_active transition to True.
        """
        results: dict[str, Any] = {"verified": 0, "outcomes": []}

        if self._last_cycle is None:
            results["skipped"] = "no previous cycle"
            return results

        try:
            verifications = self.auto_verify_cycle(self._last_cycle)
            results["verified"] = len(verifications)
            results["outcomes"] = verifications

            # Count successes for logging
            successes = sum(1 for v in verifications if v.get("success"))
            logger.info(
                "Verify phase: %d outcomes checked, %d succeeded",
                len(verifications),
                successes,
            )
        except Exception as e:
            results["error"] = str(e)
            logger.debug("Auto-verification failed: %s", e, exc_info=True)

        return results

    def _phase_observe(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Phase 1: Gather proposals from all intelligence engines."""
        results: dict[str, Any] = {"proposals": [], "errors": []}

        # KaizenEngine — codebase + memory analysis
        try:
            from whitemagic.core.intelligence.synthesis.kaizen_engine import (
                get_kaizen_engine,
            )

            engine = get_kaizen_engine()
            report = engine.analyze()
            for prop in report.proposals:
                # Extract verification query from proposal ID for automated outcome detection
                # e.g. "quality_untitled_5" → "untitled", "quality_untagged_3" → "untagged"
                parts = prop.id.split("_")
                verification_query = "_".join(parts[1:-1]) if len(parts) > 2 else None
                before_count = prop.metadata.get("count") if prop.metadata else None

                results["proposals"].append(
                    {
                        "source": "kaizen",
                        "id": prop.id,
                        "title": prop.title,
                        "description": prop.description,
                        "category": prop.category,
                        "impact": prop.impact,
                        "effort": prop.effort,
                        "auto_fixable": prop.auto_fixable,
                        "fix_action": prop.fix_action,
                        "metadata": prop.metadata,
                        "verification_query": verification_query,
                        "before_count": before_count,
                    }
                )
            results["kaizen_metrics"] = report.metrics
        except Exception as e:
            results["errors"].append(f"kaizen: {e}")
            logger.debug("KaizenEngine failed: %s", e, exc_info=True)

        # PredictiveEngine — milestone/velocity/gap predictions
        try:
            from whitemagic.core.intelligence.synthesis.predictive_engine import (
                get_predictive_engine,
            )

            engine = get_predictive_engine()
            report = engine.predict()
            for pred in report.predictions[:10]:
                results["proposals"].append(
                    {
                        "source": "predictive",
                        "id": pred.id,
                        "title": pred.title,
                        "description": pred.description,
                        "category": "prediction",
                        "impact": "high" if pred.impact_score > 0.7 else "medium",
                        "effort": "medium",
                        "auto_fixable": False,
                        "fix_action": None,
                        "metadata": {
                            "impact_score": pred.impact_score,
                            "time_horizon": pred.time_horizon,
                            "suggested_actions": pred.suggested_actions[:3],
                        },
                    }
                )
            results["predictive_metrics"] = {
                "patterns_analyzed": report.patterns_analyzed,
                "memories_scanned": report.memories_scanned,
            }
        except Exception as e:
            results["errors"].append(f"predictive: {e}")
            logger.debug("PredictiveEngine failed: %s", e, exc_info=True)

        # EmergenceEngine — novel pattern detection
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )

            engine = get_emergence_engine()
            insights = engine.scan_for_emergence()
            for insight in insights[:5]:
                results["proposals"].append(
                    {
                        "source": "emergence",
                        "id": insight.id,
                        "title": insight.title,
                        "description": insight.description,
                        "category": "emergence",
                        "impact": "high" if insight.confidence > 0.7 else "medium",
                        "effort": "medium",
                        "auto_fixable": False,
                        "fix_action": None,
                        "metadata": {
                            "confidence": insight.confidence,
                            "source_type": insight.source,
                        },
                    }
                )
        except Exception as e:
            results["errors"].append(f"emergence: {e}")
            logger.debug("EmergenceEngine failed: %s", e, exc_info=True)

        # InsightPipeline — strategic foresight from all cognitive engines
        try:
            from whitemagic.core.intelligence.insight_pipeline import InsightPipeline

            pipeline = InsightPipeline()
            briefing = pipeline.generate_briefing()
            for item in briefing.items:
                if item.priority in ("critical", "high"):
                    results["proposals"].append(
                        {
                            "source": "insight",
                            "id": item.id,
                            "title": item.title,
                            "description": item.description,
                            "category": item.category,
                            "impact": "high"
                            if item.priority == "critical"
                            else "medium",
                            "effort": "medium",
                            "auto_fixable": False,
                            "fix_action": None,
                            "metadata": {
                                "confidence": item.confidence,
                                "source_engine": item.source_engine,
                                "suggested_actions": item.suggested_actions[:3],
                                "priority": item.priority,
                            },
                        }
                    )
            results["insight_count"] = len(briefing.items)
        except Exception as e:
            results["errors"].append(f"insight: {e}")
            logger.debug("InsightPipeline failed: %s", e, exc_info=True)

        results["total_proposals"] = len(results["proposals"])
        logger.info("Observe phase: %d proposals gathered", results["total_proposals"])
        return results

    def _phase_imagine(
        self,
        cycle: ImprovementCycle,
        max_hypotheses: int,
    ) -> dict[str, Any]:
        """Phase 2: Convert proposals into testable hypotheses with MC simulation."""
        observe_data = cycle.phase_results.get("observe", {})
        proposals = observe_data.get("proposals", [])

        results: dict[str, Any] = {"hypotheses_created": 0, "mc_simulations": 0}
        hypotheses: list[ImprovementHypothesis] = []

        mc_claims = []
        for prop in proposals[:max_hypotheses]:
            # Estimate confidence from impact/effort
            impact_map = {"high": 0.8, "medium": 0.6, "low": 0.4}
            effort_map = {"high": 0.3, "medium": 0.5, "low": 0.7}
            base_confidence = impact_map.get(prop["impact"], 0.5)
            effort_factor = effort_map.get(prop["effort"], 0.5)
            confidence = base_confidence * effort_factor

            mc_claims.append(
                {
                    "id": prop["id"],
                    "claim": prop["title"],
                    "confidence": confidence,
                    "outcome": None,  # Unknown — this is a prediction
                    "category": prop["category"],
                    "status": "pending",
                }
            )

        if mc_claims:
            try:
                mc_result = self._mc_enhancer.run_calibrated(
                    mc_claims,
                    n_trials=5000,
                    deduplicate=False,
                )
                results["mc_simulations"] = mc_result.get("mc_result", {}).get(
                    "n_trials", 0
                )
                results["mc_analytics"] = mc_result.get("analytics", {})

                # Extract per-claim predicted impact from MC
                bss_mean = (
                    mc_result.get("mc_result", {})
                    .get("brier_skill_score", {})
                    .get("mean", 0.0)
                )

                for prop, claim in zip(proposals[:max_hypotheses], mc_claims):
                    # Track in HLL/CMS
                    self._hll.add(claim["id"])
                    self._cms.add(claim["id"])

                    # Novelty: how many times have we seen this improvement?
                    freq = self._cms.estimate(claim["id"])
                    cms_novelty = max(0.0, 1.0 - freq / 20.0)  # Novel if rarely seen
                    # Objective D: Blend CMS novelty with surprisal score
                    novelty = self._compute_surprisal_novelty(
                        prop["description"],
                        cms_novelty,
                    )

                    # Objective P: Compute information gain
                    ig = 0.0
                    try:
                        from whitemagic.core.evolution.info_theory import (
                            information_gain as compute_ig,
                        )

                        ig = compute_ig(claim["confidence"])
                    except (ImportError, Exception):
                        pass

                    hypotheses.append(
                        ImprovementHypothesis(
                            id=claim["id"],
                            source=prop["source"],
                            title=prop["title"],
                            description=prop["description"],
                            category=prop["category"],
                            predicted_impact=claim["confidence"],
                            confidence=max(0.0, min(1.0, bss_mean)),
                            effort=prop["effort"],
                            auto_fixable=prop["auto_fixable"],
                            fix_action=prop["fix_action"],
                            metadata=prop["metadata"],
                            novelty_score=novelty,
                            verification_query=prop.get("verification_query"),
                            before_count=prop.get("before_count"),
                            information_gain=ig,
                        )
                    )
            except Exception as e:
                results["mc_error"] = str(e)
                logger.debug("MC simulation failed: %s", e, exc_info=True)
                # Fall back: create hypotheses without MC
                for prop, claim in zip(proposals[:max_hypotheses], mc_claims):
                    hypotheses.append(
                        ImprovementHypothesis(
                            id=claim["id"],
                            source=prop["source"],
                            title=prop["title"],
                            description=prop["description"],
                            category=prop["category"],
                            predicted_impact=claim["confidence"],
                            confidence=claim["confidence"],
                            effort=prop["effort"],
                            auto_fixable=prop["auto_fixable"],
                            fix_action=prop["fix_action"],
                            metadata=prop["metadata"],
                            novelty_score=1.0,
                            verification_query=prop.get("verification_query"),
                            before_count=prop.get("before_count"),
                        )
                    )

        # Phase 4c: HRR-based analogical hypothesis generation
        # Use Holographic Reduced Representations to find novel analogies
        try:
            from whitemagic.core.memory.hrr import get_hrr_engine

            hrr = get_hrr_engine()

            # Bind current proposal descriptions with "improves" relation
            # to find analogical matches in the hypothesis space
            for prop in proposals[:3]:
                try:
                    from whitemagic.core.memory.embeddings import get_embedding_engine

                    emb_engine = get_embedding_engine()
                    prop_embedding = emb_engine.encode(prop["description"][:200])
                    if prop_embedding is None:
                        continue

                    # Project through HRR "improves" relation
                    projected = hrr.project(prop_embedding, "IMPROVES")

                    # Search for memories similar to the projected vector
                    # This finds past patterns that resonate with the
                    # "improvement" framing of the current proposal
                    try:
                        similar = emb_engine.search_similar(projected.tolist(), top_k=3)
                        analogical_sources = [
                            {
                                "id": s.get("id", ""),
                                "similarity": float(s.get("similarity", 0)),
                            }
                            for s in similar
                        ]
                    except Exception:
                        analogical_sources = []

                    hrr_hyp_id = f"hrr_{prop['source']}_{hash(prop['title']) % 100000}"

                    existing_ids = {h.id for h in hypotheses}
                    if hrr_hyp_id not in existing_ids:
                        hypotheses.append(
                            ImprovementHypothesis(
                                id=hrr_hyp_id,
                                source="hrr",
                                title=f"Analogical: {prop['title'][:60]}",
                                description=(
                                    f"HRR-projected hypothesis via IMPROVES relation. "
                                    f"Original: {prop['description'][:150]}. "
                                    f"This hypothesis was generated by binding the "
                                    f"proposal embedding with the improvement relation "
                                    f"vector, enabling analogical transfer from "
                                    f"historical improvement patterns."
                                ),
                                category=prop["category"],
                                predicted_impact={
                                    "high": 0.8,
                                    "medium": 0.5,
                                    "low": 0.3,
                                }.get(prop.get("impact"), 0.5)
                                if isinstance(prop.get("impact"), str)
                                else prop.get("impact", 0.5),
                                confidence=0.5,  # Base confidence for HRR-generated
                                effort=prop["effort"],
                                auto_fixable=False,
                                fix_action=None,
                                metadata={
                                    **prop.get("metadata", {}),
                                    "hrr_relation": "IMPROVES",
                                    "source_proposal": prop["source"],
                                    "analogical_sources": analogical_sources,
                                },
                                novelty_score=0.8,  # HRR analogies are inherently novel
                            )
                        )
                except Exception as e:
                    logger.debug(
                        "HRR hypothesis generation skipped for proposal: %s", e
                    )
        except Exception as e:
            logger.debug("HRR engine unavailable: %s", e, exc_info=True)

        cycle.hypotheses = hypotheses
        results["hypotheses_created"] = len(hypotheses)
        results["distinct_improvements"] = self._hll.estimate()

        # Objective L/V/G: Classify hypotheses through garden, guna, galactic
        for hyp in hypotheses:
            self._classify_hypothesis(hyp)

        # Objective O: Run bicameral debates on top hypotheses
        for hyp in hypotheses[:10]:
            boost = self._debate_hypothesis(hyp)
            hyp.exploration_boost = boost

        # Objective M: Create actor for each hypothesis
        supervisor = self._get_actor_supervisor()
        if supervisor is not None:
            for hyp in hypotheses:
                try:
                    supervisor.start_actor(hyp.id, prior=hyp.confidence)
                except Exception:
                    logger.debug("Swallowed exception", exc_info=True)

        # Objective F: Record holographic trajectory points
        traj = self._get_holographic_traj()
        if traj is not None:
            for hyp in hypotheses:
                try:
                    traj.add_point(
                        hypothesis_id=hyp.id,
                        timestamp=time.time(),
                        confidence=hyp.confidence,
                        novelty=hyp.novelty_score,
                        impact=hyp.predicted_impact,
                    )
                except Exception:
                    logger.debug("Swallowed exception", exc_info=True)

        logger.info("Imagine phase: %d hypotheses created", len(hypotheses))
        return results

    def _phase_predict(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Phase 3: Store predictions in TemporalForecastDB for later calibration.

        Also applies Brier calibration feedback: fetches the current calibration
        gap from TemporalForecastDB and adjusts hypothesis confidence values.
        If the system is overconfident (negative gap), confidence is reduced.
        """
        results: dict[str, Any] = {"predictions_stored": 0, "errors": []}

        # Apply Brier calibration to hypothesis confidence
        try:
            from whitemagic.core.intelligence.synthesis.predictive_engine import (
                get_predictive_engine,
            )

            engine = get_predictive_engine()
            cal = engine.get_calibration()
            if cal:
                results["calibration"] = cal
                for hyp in cycle.hypotheses:
                    hyp.confidence = engine.apply_calibration(hyp.confidence)
                logger.info(
                    "Calibration applied: brier=%.4f gap=%.4f",
                    cal.get("brier_score", 0),
                    cal.get("calibration_gap", 0),
                )
        except Exception as e:
            results["errors"].append(f"calibration: {e}")
            logger.debug("Calibration feedback failed: %s", e, exc_info=True)

        try:
            from whitemagic.forecasting.temporal_db import TemporalForecastDB

            db = TemporalForecastDB()

            for hyp in cycle.hypotheses:
                try:
                    db.add_prediction(
                        claim=hyp.title,
                        source_date=datetime.now().date().isoformat(),
                        confidence=hyp.predicted_impact,
                        category=f"self_improvement_{hyp.category}",
                        source_ref=f"recursive_loop:{hyp.id}",
                        notes=hyp.description[:200],
                    )
                    results["predictions_stored"] += 1
                except Exception as e:
                    results["errors"].append(f"{hyp.id}: {e}")
        except Exception as e:
            results["errors"].append(f"temporal_db: {e}")
            logger.debug("TemporalForecastDB unavailable: %s", e, exc_info=True)

        logger.info(
            "Predict phase: %d predictions stored", results["predictions_stored"]
        )

        # Phase 3b: Auto-generate prescience claims from PredictiveEngine
        try:
            from whitemagic.core.intelligence.synthesis.predictive_engine import (
                get_predictive_engine,
            )

            engine = get_predictive_engine()
            claim_results = engine.auto_prescience_claims(min_confidence=0.7)
            results["auto_prescience"] = claim_results
            if claim_results["stored_claims"] > 0:
                logger.info(
                    "Auto prescience: %d/%d predictions stored as claims",
                    claim_results["stored_claims"],
                    claim_results["total_predictions"],
                )
        except Exception as e:
            results["errors"].append(f"auto_prescience: {e}")
            logger.debug("Auto prescience claims failed: %s", e, exc_info=True)

        return results

    def _phase_recommend(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Phase 4: Rank hypotheses and recommend actions with tool suggestions.

        Objective Q: Uses thermodynamic temperature to control exploration.
        Objective O: Adds exploration boost from bicameral debate contention.
        Objective P: Incorporates information gain into scoring.
        Objective Z: Gets meta-bandit strategy recommendation.
        """
        results: dict[str, Any] = {"recommendations": []}

        # Objective Z: Get meta-strategy recommendation for this cycle
        meta_bandit = self._get_meta_bandit()
        if meta_bandit is not None:
            try:
                from whitemagic.core.evolution.zen_meta import MetaFeatures

                # Build meta-features from current cycle state
                confidences = [h.confidence for h in cycle.hypotheses] or [0.5]
                mf = MetaFeatures(
                    discovery_rate=min(1.0, len(cycle.hypotheses) / 20.0),
                    calibration_error=1.0 - sum(confidences) / len(confidences),
                )
                results["meta_strategy"] = meta_bandit.get_strategy_recommendations(mf)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Score: predicted_impact * confidence * novelty + exploration_boost + IG
        temperature = self._get_thermodynamic_temperature()
        scored = []
        for hyp in cycle.hypotheses:
            # Guard against non-float predicted_impact
            if not isinstance(hyp.predicted_impact, (int, float)):
                logger.debug(
                    "Skipping hypothesis %s: predicted_impact is %s",
                    hyp.id,
                    type(hyp.predicted_impact),
                )
                continue
            # Base score
            score = (
                hyp.predicted_impact * hyp.confidence * (0.5 + hyp.novelty_score * 0.5)
            )
            # Objective O: Add exploration boost from debate contention
            score += hyp.exploration_boost
            # Objective P: Add information gain (normalized)
            score += hyp.information_gain * 0.1
            # Objective Q: Thermodynamic temperature modulates exploration
            # High temperature → more weight on novelty (exploration)
            # Low temperature → more weight on predicted_impact (exploitation)
            if temperature < 1.0:
                score = (
                    score * (1 - (1 - temperature) * 0.3)
                    + hyp.predicted_impact * (1 - temperature) * 0.3
                )
            scored.append((hyp, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        for hyp, score in scored[:10]:
            # Recommend tools via bandit
            task_type = self._bandit.classify_task_type(hyp.title)
            recommended_tools = self._bandit.recommend_tools(
                task=hyp.title,
                k=3,
                task_type=task_type,
            )

            rec = {
                "rank": len(results["recommendations"]) + 1,
                "hypothesis_id": hyp.id,
                "title": hyp.title,
                "source": hyp.source,
                "category": hyp.category,
                "score": round(score, 4),
                "predicted_impact": round(hyp.predicted_impact, 3),
                "confidence": round(hyp.confidence, 3),
                "novelty": round(hyp.novelty_score, 3),
                "information_gain": round(hyp.information_gain, 4),
                "effort": hyp.effort,
                "auto_fixable": hyp.auto_fixable,
                "fix_action": hyp.fix_action,
                "recommended_tools": [
                    {"tool": t["tool"], "expected_success": t["expected_value"]}
                    for t in recommended_tools
                ],
                "task_type": task_type,
                "garden": hyp.garden,
                "guna": hyp.guna,
                "galactic_zone": hyp.galactic_zone,
                "debate_contention": round(hyp.debate_contention, 3),
                "exploration_boost": round(hyp.exploration_boost, 4),
            }
            results["recommendations"].append(rec)

        cycle.top_recommendations = results["recommendations"]
        logger.info(
            "Recommend phase: %d recommendations ranked",
            len(results["recommendations"]),
        )
        return results

    def _phase_learn(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Phase 5: Record hypotheses in AutodidacticLoop for outcome tracking."""
        results: dict[str, Any] = {"applications_recorded": 0}

        for hyp in cycle.hypotheses:
            try:
                app = PatternApplication(
                    application_id=str(uuid.uuid4()),
                    pattern_id=hyp.id,
                    pattern_type=hyp.category,
                    timestamp=time.time(),
                    initial_confidence=hyp.confidence,
                    context={
                        "source": hyp.source,
                        "title": hyp.title,
                        "cycle_id": cycle.cycle_id,
                        "predicted_impact": hyp.predicted_impact,
                        "novelty_score": hyp.novelty_score,
                    },
                )
                self._autodidactic.record_application(app)
                results["applications_recorded"] += 1
            except Exception as e:
                logger.debug("Failed to record application: %s", e, exc_info=True)

        try:
            results["learning_summary"] = self._autodidactic.get_learning_summary()
        except Exception:
            results["learning_summary"] = {}

        logger.info(
            "Learn phase: %d applications recorded", results["applications_recorded"]
        )
        return results

    def record_outcome(
        self,
        hypothesis_id: str,
        success: bool,
        performance_gain: float | None = None,
        quality_score: float | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Record the outcome of an implemented improvement.

        This closes the loop — the prediction from a previous cycle gets
        validated against reality, and all tracking structures update.

        Args:
            hypothesis_id: The ID from the ImprovementHypothesis
            success: Whether the improvement was successful
            performance_gain: e.g., 13.0 for 13x speedup
            quality_score: 0-1 quality assessment
            metrics: Additional outcome metrics
        """
        # Record in AutodidacticLoop
        outcome = PatternOutcome(
            application_id=str(uuid.uuid4()),
            pattern_id=hypothesis_id,
            success=success,
            performance_gain=performance_gain,
            quality_score=quality_score,
            user_feedback=None,
            measured_at=time.time(),
            metrics=metrics or {},
        )
        self._autodidactic.record_outcome(outcome)

        # Update tool bandit
        self._bandit.record_outcome(hypothesis_id, success=success)

        # Track in CMS
        self._cms.add(hypothesis_id)

        # Objective K: Record valence (RPE-based)
        valence = self._get_valence_tracker()
        if valence is not None:
            try:
                # Find the hypothesis to get prediction
                hyp = None
                if self._last_cycle:
                    for h in self._last_cycle.hypotheses:
                        if h.id == hypothesis_id:
                            hyp = h
                            break
                prediction = hyp.confidence if hyp else 0.5
                actual = 1.0 if success else 0.0
                category = hyp.category if hyp else "default"
                valence.record_outcome(hypothesis_id, prediction, actual, category)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Objective T: Record causal effect
        ledger = self._get_causal_ledger()
        if ledger is not None:
            try:
                from whitemagic.core.evolution.causal_ledger import EffectType

                magnitude = performance_gain or (1.0 if success else 0.0)
                ledger.record_effect(
                    improvement_id=hypothesis_id,
                    effect_type=EffectType.INTENDED,
                    effect_metric="primary",
                    effect_magnitude=magnitude,
                    effect_confidence=quality_score or 0.5,
                )
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Objective M: Send outcome to actor
        supervisor = self._get_actor_supervisor()
        if supervisor is not None:
            try:
                supervisor.send_outcome(
                    hypothesis_id, success=success, gain=performance_gain or 0.0
                )
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Objective L: Update garden calibration
        router = self._get_garden_router()
        if router is not None and self._last_cycle:
            try:
                hyp = next(
                    (h for h in self._last_cycle.hypotheses if h.id == hypothesis_id),
                    None,
                )
                if hyp and hyp.garden:
                    router.record_outcome(
                        hyp.garden, hyp.confidence, 1.0 if success else 0.0
                    )
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Objective V: Record guna outcome
        clf = self._get_guna_classifier()
        if clf is not None and self._last_cycle:
            try:
                from whitemagic.core.evolution.guna_classifier import Guna

                hyp = next(
                    (h for h in self._last_cycle.hypotheses if h.id == hypothesis_id),
                    None,
                )
                if hyp and hyp.guna:
                    guna = Guna(hyp.guna)
                    clf.record_outcome(guna, success)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Objective R: Update predictive coding layer 1 (operational)
        pc = self._get_predictive_coding()
        if pc is not None:
            try:
                pc.compute_error(1, 1.0 if success else 0.0)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

        # Emit Gan Ying event
        self._emit_outcome_event(hypothesis_id, success, performance_gain)

        logger.info(
            "Outcome recorded: %s success=%s gain=%s",
            hypothesis_id,
            success,
            performance_gain,
        )

    def verify_outcome(
        self,
        hypothesis_id: str,
        before_count: int,
        verification_query: str,
        threshold: float = 0.1,
    ) -> dict[str, Any]:
        """Automatically verify an improvement by re-running its kaizen check.

        Objective A — Automated Outcome Detection. After an auto-fixable
        improvement is applied, this method re-runs the relevant kaizen
        check, computes the delta, and auto-records the outcome.

        Args:
            hypothesis_id: The ID from the ImprovementHypothesis.
            before_count: Issue count before the fix (from hypothesis.before_count).
            verification_query: The kaizen check name (e.g. "untitled", "untagged").
            threshold: Minimum delta fraction to count as success (default 10%).

        Returns:
            Dict with verification results: success, delta, after_count, recorded.
        """
        result: dict[str, Any] = {
            "hypothesis_id": hypothesis_id,
            "verification_query": verification_query,
            "before_count": before_count,
            "after_count": None,
            "delta": 0.0,
            "success": False,
            "recorded": False,
        }

        if not verification_query or before_count is None or before_count <= 0:
            result["error"] = "Missing verification_query or before_count"
            return result

        # Re-run the relevant kaizen check to get after_count
        try:
            from whitemagic.core.intelligence.synthesis.kaizen_engine import (
                get_kaizen_engine,
            )

            engine = get_kaizen_engine()
            report = engine.analyze()

            # Find the matching proposal by verification_query
            after_count = before_count  # Default: no change
            for prop in report.proposals:
                parts = prop.id.split("_")
                prop_query = "_".join(parts[1:-1]) if len(parts) > 2 else None
                if prop_query == verification_query:
                    after_count = prop.metadata.get("count", before_count)
                    break

            if after_count == before_count:
                matching = [
                    p
                    for p in report.proposals
                    if "_".join(p.id.split("_")[1:-1]) == verification_query
                ]
                if not matching:
                    after_count = 0

            delta = (before_count - after_count) / before_count
            success = delta >= threshold

            result["after_count"] = after_count
            result["delta"] = round(delta, 4)
            result["success"] = success

            # Auto-record the outcome
            self.record_outcome(
                hypothesis_id=hypothesis_id,
                success=success,
                performance_gain=round(delta * 100, 2) if delta > 0 else None,
                metrics={
                    "verification_query": verification_query,
                    "before_count": before_count,
                    "after_count": after_count,
                    "delta": round(delta, 4),
                    "auto_verified": True,
                },
            )
            result["recorded"] = True

            logger.info(
                "Auto-verified %s: before=%d after=%d delta=%.2f success=%s",
                hypothesis_id,
                before_count,
                after_count,
                delta,
                success,
            )
        except Exception as e:
            result["error"] = str(e)
            logger.debug("Auto-verification failed: %s", e, exc_info=True)

        return result

    def auto_verify_cycle(
        self, cycle: ImprovementCycle | None = None
    ) -> list[dict[str, Any]]:
        """Auto-verify all auto-fixable hypotheses from a cycle.

        Args:
            cycle: The cycle to verify. If None, uses the last cycle.

        Returns:
            List of verification results for each auto-fixable hypothesis.
        """
        target_cycle = cycle or self._last_cycle
        if target_cycle is None:
            return []

        results = []
        for hyp in target_cycle.hypotheses:
            if hyp.auto_fixable and hyp.verification_query and hyp.before_count:
                result = self.verify_outcome(
                    hypothesis_id=hyp.id,
                    before_count=hyp.before_count,
                    verification_query=hyp.verification_query,
                )
                results.append(result)

        return results

    def _build_analytics(self, cycle: ImprovementCycle) -> dict[str, Any]:
        """Build analytics summary for the cycle."""
        observe = cycle.phase_results.get("observe", {})
        imagine = cycle.phase_results.get("imagine", {})
        learn = cycle.phase_results.get("learn", {})
        recommend = cycle.phase_results.get("recommend", {})

        # Gather stats from Phase 3-6 modules
        evolution_stats: dict[str, Any] = {}
        for name, getter in [
            ("garden", self._get_garden_router),
            ("guna", self._get_guna_classifier),
            ("valence", self._get_valence_tracker),
            ("causal_ledger", self._get_causal_ledger),
            ("predictive_coding", self._get_predictive_coding),
            ("actors", self._get_actor_supervisor),
            ("resonance_transfer", self._get_resonance_transfer),
            ("yield_portfolio", self._get_yield_portfolio),
            ("meta_bandit", self._get_meta_bandit),
            ("polyglot_mc", self._get_polyglot_mc),
        ]:
            mod = getter()
            if mod is not None:
                try:
                    evolution_stats[name] = mod.get_stats()
                except Exception:
                    logger.debug("Swallowed exception", exc_info=True)

        return {
            "cycle_number": self._cycle_count,
            "total_proposals": observe.get("total_proposals", 0),
            "hypotheses_created": imagine.get("hypotheses_created", 0),
            "distinct_improvements_seen": self._hll.estimate(),
            "mc_simulations": imagine.get("mc_simulations", 0),
            "mc_analytics": imagine.get("mc_analytics", {}),
            "predictions_stored": cycle.phase_results.get("predict", {}).get(
                "predictions_stored", 0
            ),
            "recommendations_count": len(cycle.top_recommendations),
            "learning_summary": learn.get("learning_summary", {}),
            "errors": observe.get("errors", []),
            "meta_strategy": recommend.get("meta_strategy"),
            "evolution_modules": evolution_stats,
            "garden_distribution": {h.garden: 1 for h in cycle.hypotheses if h.garden}
            if cycle.hypotheses
            else {},
            "guna_distribution": {h.guna: 1 for h in cycle.hypotheses if h.guna}
            if cycle.hypotheses
            else {},
            "galactic_zones": {
                h.galactic_zone: 1 for h in cycle.hypotheses if h.galactic_zone
            }
            if cycle.hypotheses
            else {},
            "avg_debate_contention": (
                sum(h.debate_contention for h in cycle.hypotheses)
                / len(cycle.hypotheses)
                if cycle.hypotheses
                else 0.0
            ),
            "avg_information_gain": (
                sum(h.information_gain for h in cycle.hypotheses)
                / len(cycle.hypotheses)
                if cycle.hypotheses
                else 0.0
            ),
        }

    def _emit_cycle_event(self, cycle: ImprovementCycle) -> None:
        """Emit Gan Ying event for cycle completion."""
        try:
            from whitemagic.core.resonance._consolidated import EventType, emit_event

            emit_event(
                source="recursive_improvement_loop",
                event_type=EventType.LEARNING_COMPLETED,
                data={
                    "cycle_id": cycle.cycle_id,
                    "cycle_number": self._cycle_count,
                    "hypotheses": len(cycle.hypotheses),
                    "recommendations": len(cycle.top_recommendations),
                    "duration_ms": round(cycle.duration_ms, 1),
                },
            )
        except Exception as e:
            logger.debug("Gan Ying emission failed: %s", e, exc_info=True)

    def _emit_outcome_event(
        self,
        hypothesis_id: str,
        success: bool,
        performance_gain: float | None,
    ) -> None:
        """Emit Gan Ying event for outcome recording."""
        try:
            from whitemagic.core.resonance._consolidated import EventType, emit_event

            event_type = (
                EventType.SOLUTION_FOUND if success else EventType.ANOMALY_DETECTED
            )
            emit_event(
                source="recursive_improvement_loop",
                event_type=event_type,
                data={
                    "hypothesis_id": hypothesis_id,
                    "success": success,
                    "performance_gain": performance_gain,
                },
            )
        except Exception as e:
            logger.debug("Gan Ying emission failed: %s", e, exc_info=True)

    def get_status(self) -> dict[str, Any]:
        """Get current loop status."""
        status = {
            "cycle_count": self._cycle_count,
            "distinct_improvements": self._hll.estimate(),
            "last_cycle": self._last_cycle.to_dict() if self._last_cycle else None,
            "bandit_summary": self._bandit.to_dict(),
        }

        evolution_status: dict[str, Any] = {}
        for name, getter in [
            ("garden", self._get_garden_router),
            ("guna", self._get_guna_classifier),
            ("valence", self._get_valence_tracker),
            ("causal_ledger", self._get_causal_ledger),
            ("predictive_coding", self._get_predictive_coding),
            ("actors", self._get_actor_supervisor),
            ("meta_bandit", self._get_meta_bandit),
            ("polyglot_mc", self._get_polyglot_mc),
        ]:
            mod = getter()
            if mod is not None:
                try:
                    evolution_status[name] = mod.get_stats()
                except Exception:
                    logger.debug("Swallowed exception", exc_info=True)
        if evolution_status:
            status["evolution_modules"] = evolution_status

        return status


_loop: RecursiveImprovementLoop | None = None


def get_improvement_loop() -> RecursiveImprovementLoop:
    """Get or create the global RecursiveImprovementLoop singleton."""
    global _loop
    if _loop is None:
        _loop = RecursiveImprovementLoop()
    return _loop


def reset_improvement_loop() -> None:
    """Reset the global loop (for testing)."""
    global _loop
    _loop = None
