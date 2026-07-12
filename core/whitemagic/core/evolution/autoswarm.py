# ruff: noqa: BLE001
"""Evolutionary Autoswarm — Distributed Evolutionary Compute (v24.3.0).

Inspired by Hyperspace's Autoswarms (LLM-driven distributed evolutionary compute),
this module wires WhiteMagic's existing evolutionary infrastructure into a
unified, continuous loop:

    WarRoom (campaign) → AgentSwarm (decompose) → ImmortalClones (execute)
        → PossibilityExplorer (Monte Carlo) → Research DAG (record)
        → Mesh (share) → Dream Cycle (serendipity) → WarRoom (next campaign)

The autoswarm runs as a background task within the ConsciousnessLoop,
generating hypotheses, testing them via Monte Carlo simulation, recording
results in the Research DAG, and sharing breakthroughs via the P2P mesh.

Integration points:
    - PossibilitySpaceExplorer: runs Monte Carlo trials on parameter spaces
    - ImmortalClone: persistent execution loops with victory conditions
    - AgentSwarm: task decomposition + tricameral consensus
    - WarRoom: campaign planning and multi-phase tactics
    - ResearchDAG: experiment lineage tracking
    - MeshClient: P2P experiment sharing
    - Dream Cycle: serendipity on experiment results
    - KnowledgeGapActionLoop: gaps → hypotheses
    - MetaGalaxy: cross-domain experiment visibility
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.evolution.research_dag import (
    Experiment,
    ExperimentStage,
    ResearchDAG,
    ResearchDomain,
    get_research_dag,
)

logger = logging.getLogger(__name__)


@dataclass
class CampaignConfig:
    """Configuration for an evolutionary campaign."""

    campaign_name: str
    domain: ResearchDomain = ResearchDomain.COGNITIVE
    hypothesis_space: str = "guna_balance"
    n_trials: int = 100
    max_iterations: int = 10
    agent_id: str = "autoswarm"
    share_results: bool = True
    dream_integration: bool = True
    breakthrough_threshold: float = 0.8
    use_superforecaster: bool = False
    n_bo_iterations: int = 20
    seed: int = 42
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignResult:
    """Result of an evolutionary campaign."""

    campaign_name: str
    domain: ResearchDomain
    experiments_run: int = 0
    breakthroughs: int = 0
    best_fitness: float = 0.0
    best_experiment_id: str | None = None
    best_parameters: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    shared_via_mesh: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_name": self.campaign_name,
            "domain": self.domain.value,
            "experiments_run": self.experiments_run,
            "breakthroughs": self.breakthroughs,
            "best_fitness": round(self.best_fitness, 4),
            "best_experiment_id": self.best_experiment_id,
            "best_parameters": self.best_parameters,
            "duration_seconds": round(self.duration_seconds, 2),
            "shared_via_mesh": self.shared_via_mesh,
            "error": self.error,
        }


@dataclass
class AutoswarmStats:
    """Runtime statistics for the autoswarm."""

    campaigns_run: int = 0
    total_experiments: int = 0
    total_breakthroughs: int = 0
    best_fitness_ever: float = 0.0
    last_campaign_time: float = 0.0
    mesh_shares: int = 0
    dream_inspirations: int = 0


class EvolutionaryAutoswarm:
    """Continuous evolutionary compute loop.

    Wires PossibilitySpaceExplorer + ImmortalClone + AgentSwarm + ResearchDAG
    into a unified system that generates hypotheses, tests them, records
    results, and shares breakthroughs.
    """

    _instance: EvolutionaryAutoswarm | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._dag = get_research_dag()
        self._stats = AutoswarmStats()
        self._stats_lock = threading.RLock()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._campaign_history: list[CampaignResult] = []
        self._history_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> EvolutionaryAutoswarm:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def run_campaign(self, config: CampaignConfig) -> CampaignResult:
        """Run a single evolutionary campaign.

        Steps:
        1. Generate hypotheses from knowledge gaps + possibility space
        2. Run Monte Carlo trials via PossibilityExplorer
        3. Record results in Research DAG
        4. Share breakthroughs via mesh
        5. Feed breakthroughs back as inspiration for future campaigns
        """
        start = time.time()
        result = CampaignResult(
            campaign_name=config.campaign_name,
            domain=config.domain,
        )

        try:
            # Step 1: Generate hypotheses
            if config.use_superforecaster:
                sf_hypotheses, sf_best_fitness, sf_meta = self._run_superforecaster_campaign(config)
                hypotheses = sf_hypotheses
                result.best_fitness = sf_best_fitness
                result.metadata = sf_meta
                logger.info(
                    "Autoswarm: campaign '%s' [superforecaster] generated %d hypotheses, sf_best=%.4f",
                    config.campaign_name, len(hypotheses), sf_best_fitness,
                )
            else:
                hypotheses = self._generate_hypotheses(config)
                logger.info(
                    "Autoswarm: campaign '%s' generated %d hypotheses",
                    config.campaign_name, len(hypotheses),
                )

            # Step 2: Run trials for each hypothesis
            for i, (hypothesis, params) in enumerate(hypotheses):
                if self._stop_event.is_set():
                    break

                # Submit hypothesis to DAG
                exp = self._dag.submit_hypothesis(
                    hypothesis=hypothesis,
                    domain=config.domain,
                    parameters=params,
                    agent_id=config.agent_id,
                    metadata={"campaign": config.campaign_name, **config.metadata},
                )

                # Mark as trial
                self._dag.record_trial(exp.experiment_id, parameters=params)

                # Run Monte Carlo trial
                fitness = self._evaluate_trial(config, params)

                # Record result
                result_exp = self._dag.record_result(
                    exp.experiment_id,
                    fitness_score=fitness,
                    outcome={"parameters": params, "campaign": config.campaign_name},
                )

                result.experiments_run += 1

                if result_exp and result_exp.stage == ExperimentStage.BREAKTHROUGH:
                    result.breakthroughs += 1

                if fitness > result.best_fitness:
                    result.best_fitness = fitness
                    result.best_experiment_id = exp.experiment_id
                    result.best_parameters = params

                if i >= config.max_iterations - 1:
                    break

            # Step 3: Share via mesh
            if config.share_results and result.best_experiment_id:
                result.shared_via_mesh = self._share_via_mesh(result, config)

            # Step 4: Dream integration
            if config.dream_integration and result.breakthroughs > 0:
                self._feed_to_dream(result)

            result.duration_seconds = time.time() - start

            with self._stats_lock:
                self._stats.campaigns_run += 1
                self._stats.total_experiments += result.experiments_run
                self._stats.total_breakthroughs += result.breakthroughs
                if result.best_fitness > self._stats.best_fitness_ever:
                    self._stats.best_fitness_ever = result.best_fitness
                self._stats.last_campaign_time = time.time()
                if result.shared_via_mesh:
                    self._stats.mesh_shares += 1

            with self._history_lock:
                self._campaign_history.append(result)
                if len(self._campaign_history) > 50:
                    self._campaign_history = self._campaign_history[-25:]

            logger.info(
                "Autoswarm: campaign '%s' complete: %d experiments, %d breakthroughs, best=%.4f",
                config.campaign_name, result.experiments_run,
                result.breakthroughs, result.best_fitness,
            )

        except Exception as e:
            result.error = str(e)
            result.duration_seconds = time.time() - start
            logger.error("Autoswarm campaign failed: %s", e, exc_info=True)

        return result

    def run_continuous(
        self,
        interval_seconds: float = 300.0,
        campaign_configs: list[CampaignConfig] | None = None,
    ) -> None:
        """Run continuous evolutionary campaigns in a background thread.

        Args:
            interval_seconds: Seconds between campaigns.
            campaign_configs: List of campaign configs to cycle through.
                              If None, uses default configs.
        """
        if self._running:
            logger.warning("Autoswarm already running")
            return

        configs = campaign_configs or self._default_campaigns()
        self._stop_event.clear()
        self._running = True

        def _loop() -> None:
            cycle = 0
            while not self._stop_event.is_set():
                config = configs[cycle % len(configs)]
                try:
                    self.run_campaign(config)
                except Exception as e:
                    logger.error("Autoswarm continuous error: %s", e, exc_info=True)
                cycle += 1
                self._stop_event.wait(interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True, name="autoswarm")
        self._thread.start()
        logger.info("Autoswarm continuous loop started (interval=%.0fs)", interval_seconds)

    def stop(self) -> None:
        """Stop the continuous loop."""
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Autoswarm stopped")

    def tick(self, config: CampaignConfig | None = None) -> CampaignResult | None:
        """Run a single campaign cycle (for consciousness loop integration).

        Unlike run_continuous(), this runs one campaign synchronously and
        returns the result. The consciousness loop calls this at its own
        cadence instead of starting a separate background thread.

        Args:
            config: Campaign config to use. If None, cycles through defaults.

        Returns:
            CampaignResult if campaign ran, None if skipped.
        """
        if config is None:
            configs = self._default_campaigns()
            idx = self._stats.campaigns_run % len(configs)
            config = configs[idx]
        try:
            return self.run_campaign(config)
        except Exception as e:
            logger.error("Autoswarm tick failed: %s", e, exc_info=True)
            return None

    def tick_mesh_sync(self) -> dict[str, Any]:
        """Sync pending mesh broadcasts and check for peer experiments.

        Called by the consciousness loop at a faster cadence than campaigns.
        """
        results: dict[str, Any] = {"synced": 0, "discovered": 0}
        try:
            from whitemagic.mesh.experiment_sync import get_experiment_sync
            sync = get_experiment_sync()
            sync_result = sync.sync_pending()
            results["synced"] = sync_result.get("synced", 0)
        except Exception as e:
            logger.debug("Mesh sync tick: %s", e, exc_info=True)
        return results

    def get_status(self) -> dict[str, Any]:
        """Get autoswarm status."""
        with self._stats_lock:
            stats = AutoswarmStats(
                campaigns_run=self._stats.campaigns_run,
                total_experiments=self._stats.total_experiments,
                total_breakthroughs=self._stats.total_breakthroughs,
                best_fitness_ever=self._stats.best_fitness_ever,
                last_campaign_time=self._stats.last_campaign_time,
                mesh_shares=self._stats.mesh_shares,
                dream_inspirations=self._stats.dream_inspirations,
            )

        with self._history_lock:
            recent = [r.to_dict() for r in self._campaign_history[-5:]]

        return {
            "running": self._running,
            "stats": {
                "campaigns_run": stats.campaigns_run,
                "total_experiments": stats.total_experiments,
                "total_breakthroughs": stats.total_breakthroughs,
                "best_fitness_ever": round(stats.best_fitness_ever, 4),
                "mesh_shares": stats.mesh_shares,
                "dream_inspirations": stats.dream_inspirations,
            },
            "recent_campaigns": recent,
        }

    def _generate_hypotheses(self, config: CampaignConfig) -> list[tuple[str, dict[str, float]]]:
        """Generate hypotheses from knowledge gaps + possibility space.

        Combines:
        - KnowledgeGapActionLoop outputs (gaps → hypotheses)
        - PossibilityExplorer parameter sampling
        - Previous breakthroughs as inspiration
        """
        hypotheses: list[tuple[str, dict[str, float]]] = []

        # Source 1: Previous breakthroughs as inspiration
        breakthroughs = self._dag.get_breakthroughs(domain=config.domain, limit=5)
        inspiration_ids: list[str] = []
        for bt in breakthroughs:
            hypothesis = f"Variation of breakthrough: {bt.hypothesis[:60]}"
            # Mutate the breakthrough's parameters slightly
            mutated = self._mutate_params(bt.parameters)
            hypotheses.append((hypothesis, mutated))
            inspiration_ids.append(bt.experiment_id)

        # Source 2: PossibilityExplorer sampling
        try:
            from whitemagic.core.consciousness.possibility_explorer import (
                get_possibility_explorer,
            )
            import random

            explorer = get_possibility_explorer()
            space = explorer.DEFAULT_SPACES.get(config.hypothesis_space, {})
            param_ranges = space.get("params", {})

            if param_ranges:
                for i in range(min(config.n_trials, config.max_iterations)):
                    params = {
                        name: random.uniform(lo, hi)
                        for name, (lo, hi) in param_ranges.items()
                    }
                    hypothesis = f"Monte Carlo trial {i} in {config.hypothesis_space}"
                    hypotheses.append((hypothesis, params))
        except Exception as e:
            logger.debug("PossibilityExplorer sampling: %s", e, exc_info=True)

        # Source 3: Knowledge gaps as hypotheses
        try:
            from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy
            mg = get_meta_galaxy()
            gaps = mg.get_knowledge_gaps()
            for gap in gaps[:3]:
                hypothesis = f"Address knowledge gap: {gap.get('description', str(gap))[:60]}"
                hypotheses.append((hypothesis, {}))
        except Exception as e:
            logger.debug("Knowledge gap hypotheses: %s", e, exc_info=True)

        # Limit to max_iterations
        return hypotheses[:config.max_iterations]

    def _evaluate_trial(
        self,
        config: CampaignConfig,
        params: dict[str, float],
    ) -> float:
        """Evaluate a trial by running it through the PossibilityExplorer fitness function.

        When use_superforecaster is enabled on the campaign config, uses the
        superforecaster pipeline (LHS→PCE→Sobol→BO) for batch evaluation instead
        of individual trial scoring.
        """
        try:
            from whitemagic.core.consciousness.possibility_explorer import (
                get_possibility_explorer,
            )
            explorer = get_possibility_explorer()
            space = explorer.DEFAULT_SPACES.get(config.hypothesis_space, {})
            fitness_name = space.get("fitness", "")
            fitness_fn = explorer._get_fitness_fn(fitness_name)
            return fitness_fn(params)
        except Exception as e:
            logger.debug("Trial evaluation: %s", e, exc_info=True)
            return 0.0

    def _run_superforecaster_campaign(
        self,
        config: CampaignConfig,
    ) -> tuple[list[tuple[str, dict[str, float]]], float, dict[str, Any]]:
        """Run a superforecaster-enhanced campaign.

        Returns (hypotheses_with_params, best_fitness, sf_metadata).
        Uses the full LHS→PCE→Sobol→BO pipeline to find optimal parameters,
        then generates hypotheses around the optimal region.
        """
        try:
            from whitemagic.core.consciousness.possibility_explorer import (
                get_possibility_explorer,
            )
            explorer = get_possibility_explorer()
            result = explorer.explore(
                config.hypothesis_space,
                n_trials=config.n_trials,
                use_superforecaster=True,
                n_bo_iterations=config.n_bo_iterations,
                seed=config.seed,
            )

            best_params = result.best_trial.parameters if result.best_trial else {}
            best_fitness = result.best_trial.fitness_score if result.best_trial else 0.0

            hypotheses: list[tuple[str, dict[str, float]]] = []
            if best_params:
                hypotheses.append((
                    f"Superforecaster optimal: {config.hypothesis_space}",
                    best_params,
                ))
                for i in range(min(4, config.max_iterations - 1)):
                    mutated = self._mutate_params(best_params)
                    hypotheses.append((
                        f"SF variation {i}: {config.hypothesis_space}",
                        mutated,
                    ))

            sf_meta = {
                "surrogate_r_squared": 0.0,
                "parameter_sensitivity": result.parameter_sensitivity,
                "avg_fitness": result.avg_fitness,
                "fitness_variance": result.fitness_variance,
                "backend": result.backend,
            }

            return hypotheses, best_fitness, sf_meta
        except Exception as e:
            logger.debug("Superforecaster campaign: %s", e, exc_info=True)
            return [], 0.0, {}

    def _mutate_params(self, params: dict[str, Any]) -> dict[str, float]:
        """Mutate parameters slightly for variation."""
        import random
        mutated: dict[str, float] = {}
        for k, v in params.items():
            if isinstance(v, (int, float)):
                mutation = random.gauss(0, 0.05)
                mutated[k] = max(0.0, v + mutation)
            else:
                mutated[k] = float(random.uniform(0, 1))
        return mutated

    def _share_via_mesh(self, result: CampaignResult, config: CampaignConfig) -> bool:
        """Share breakthrough results via the P2P mesh."""
        try:
            from whitemagic.mesh.client import get_mesh_client
            import json

            client = get_mesh_client()
            payload = json.dumps({
                "type": "experiment_result",
                "campaign": result.campaign_name,
                "domain": result.domain.value,
                "best_fitness": result.best_fitness,
                "best_experiment_id": result.best_experiment_id,
                "best_parameters": result.best_parameters,
                "breakthroughs": result.breakthroughs,
                "timestamp": datetime.now().isoformat(),
            })

            signal = client.broadcast_signal(
                signal_type="EXPERIMENT_RESULT",
                payload=payload,
            )

            with self._stats_lock:
                self._stats.mesh_shares += 1

            logger.info(
                "Autoswarm: shared experiment via mesh (success=%s)",
                signal.success,
            )
            return signal.success
        except Exception as e:
            logger.debug("Mesh share: %s", e, exc_info=True)
            return False

    def _feed_to_dream(self, result: CampaignResult) -> None:
        """Feed breakthrough results to the dream cycle for serendipity processing."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            um.store(
                title=f"[Autoswarm Dream Feed] {result.campaign_name}",
                content=(
                    f"Campaign: {result.campaign_name}\n"
                    f"Domain: {result.domain.value}\n"
                    f"Breakthroughs: {result.breakthroughs}\n"
                    f"Best fitness: {result.best_fitness:.4f}\n"
                    f"Best params: {result.best_parameters}\n"
                ),
                tags={"autoswarm", "dream_feed", "breakthrough", result.domain.value},
                importance=min(result.best_fitness, 1.0),
                galaxy="dreams",
                metadata={
                    "campaign": result.campaign_name,
                    "domain": result.domain.value,
                    "best_fitness": result.best_fitness,
                    "source": "autoswarm",
                },
            )
            with self._stats_lock:
                self._stats.dream_inspirations += 1
            logger.debug("Autoswarm: fed breakthrough to dream cycle")
        except Exception as e:
            logger.debug("Dream feed: %s", e, exc_info=True)

    def _default_campaigns(self) -> list[CampaignConfig]:
        """Default campaign configurations cycling through domains.

        The 5th campaign uses the superforecaster pipeline (LHS→PCE→Sobol→BO)
        for rigorous parameter optimization.
        """
        return [
            CampaignConfig(
                campaign_name="cognitive_optimization",
                domain=ResearchDomain.COGNITIVE,
                hypothesis_space="guna_balance",
                n_trials=50,
                max_iterations=10,
            ),
            CampaignConfig(
                campaign_name="coherence_tuning",
                domain=ResearchDomain.CONSCIOUSNESS,
                hypothesis_space="coherence_optimization",
                n_trials=50,
                max_iterations=10,
            ),
            CampaignConfig(
                campaign_name="emergence_exploration",
                domain=ResearchDomain.EVOLUTION,
                hypothesis_space="emergence_thresholds",
                n_trials=50,
                max_iterations=10,
            ),
            CampaignConfig(
                campaign_name="health_setpoints",
                domain=ResearchDomain.COGNITIVE,
                hypothesis_space="health_setpoints",
                n_trials=50,
                max_iterations=10,
            ),
            CampaignConfig(
                campaign_name="superforecaster_deep_optimization",
                domain=ResearchDomain.COGNITIVE,
                hypothesis_space="guna_balance",
                n_trials=100,
                max_iterations=5,
                use_superforecaster=True,
                n_bo_iterations=30,
            ),
        ]


def get_autoswarm() -> EvolutionaryAutoswarm:
    """Get the singleton EvolutionaryAutoswarm instance."""
    return EvolutionaryAutoswarm.get_instance()
