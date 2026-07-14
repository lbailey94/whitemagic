# ruff: noqa: BLE001
"""Research Adapters — Wire existing research systems into ResearchDAG (v24.3.0).

Each adapter wraps an existing WhiteMagic research mechanism and records its
outputs as experiments in the Research DAG, ensuring full provenance tracking.

Adapters:
    - RabbitHoleAdapter: Web research → experiment
    - ParallelReasoningAdapter: Multi-branch reasoning → experiment
    - AlchemicalLoopAdapter: 7-stage alchemical process → experiment
    - RecursiveLoopAdapter: 6-phase improvement cycle → experiment
    - KnowledgeGapAdapter: Gap detection + filling → experiment
    - SelfDirectedAdapter: Self-initiated attention → experiment

Design principle: wire, don't rebuild. Each adapter calls the existing
system's API and translates results into DAG experiments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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
class AdapterStats:
    """Statistics for a research adapter."""

    calls: int = 0
    experiments_created: int = 0
    breakthroughs: int = 0
    errors: int = 0
    last_hypothesis: str = ""
    last_fitness: float = 0.0


class BaseAdapter:
    """Base class for research adapters."""

    def __init__(
        self,
        dag: ResearchDAG | None = None,
        agent_id: str = "",
        domain: ResearchDomain = ResearchDomain.SYNTHESIS,
    ) -> None:
        self._dag = dag or get_research_dag()
        self._agent_id = agent_id or self.__class__.__name__
        self._domain = domain
        self._stats = AdapterStats()
        self._stats_lock = __import__("threading").RLock()

    def _record_experiment(
        self,
        hypothesis: str,
        parameters: dict[str, Any] | None = None,
        fitness_score: float = 0.0,
        outcome: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Experiment | None:
        """Submit hypothesis, run trial, and record result in one call."""
        try:
            exp = self._dag.submit_hypothesis(
                hypothesis=hypothesis,
                domain=self._domain,
                parameters=parameters or {},
                agent_id=self._agent_id,
                metadata=metadata or {},
            )
            self._dag.record_trial(exp.experiment_id, parameters=parameters)
            result_exp = self._dag.record_result(
                exp.experiment_id,
                fitness_score=fitness_score,
                outcome=outcome,
            )

            with self._stats_lock:
                self._stats.experiments_created += 1
                self._stats.last_hypothesis = hypothesis[:100]
                self._stats.last_fitness = fitness_score
                if result_exp and result_exp.stage == ExperimentStage.BREAKTHROUGH:
                    self._stats.breakthroughs += 1

            return result_exp
        except Exception as e:
            with self._stats_lock:
                self._stats.errors += 1
            logger.debug("Adapter experiment recording failed: %s", e, exc_info=True)
            return None

    def get_stats(self) -> dict[str, Any]:
        with self._stats_lock:
            return {
                "adapter": self.__class__.__name__,
                "calls": self._stats.calls,
                "experiments_created": self._stats.experiments_created,
                "breakthroughs": self._stats.breakthroughs,
                "errors": self._stats.errors,
                "last_hypothesis": self._stats.last_hypothesis,
                "last_fitness": round(self._stats.last_fitness, 4),
            }


class RabbitHoleAdapter(BaseAdapter):
    """Adapter for RabbitHoleExplorer web research → ResearchDAG.

    Records rabbit hole exploration sessions as experiments with
    fitness scored by novelty and content richness.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="rabbit_hole",
            domain=ResearchDomain.SYNTHESIS,
        )

    async def explore_and_record(
        self,
        topic: str,
        max_depth: int = 3,
        max_parallel_terms: int = 12,
    ) -> Experiment | None:
        """Run a rabbit hole exploration and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.gardens.browser.web_research import RabbitHoleExplorer

            explorer = RabbitHoleExplorer()
            report = await explorer.web_explore(
                topic=topic,
                max_depth=max_depth,
                max_parallel_terms=max_parallel_terms,
            )

            # Score fitness by novelty and content volume
            entries_count = len(report.entries) if hasattr(report, "entries") else 0
            connections_count = len(report.connections) if hasattr(report, "connections") else 0
            novelty = min(entries_count / 20.0, 1.0)
            connectivity = min(connections_count / 10.0, 1.0)
            fitness = (novelty * 0.6 + connectivity * 0.4)

            return self._record_experiment(
                hypothesis=f"Rabbit hole exploration: {topic}",
                parameters={
                    "topic": topic,
                    "max_depth": max_depth,
                    "max_parallel_terms": max_parallel_terms,
                },
                fitness_score=fitness,
                outcome={
                    "entries_discovered": entries_count,
                    "connections_found": connections_count,
                    "synthesis_length": len(report.synthesis) if hasattr(report, "synthesis") else 0,
                },
                metadata={
                    "source": "rabbit_hole",
                    "topic": topic,
                    "explored_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.debug("RabbitHole adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


class ParallelReasoningAdapter(BaseAdapter):
    """Adapter for ParallelReasoningTree → ResearchDAG.

    Records parallel reasoning explorations as experiments with
    fitness scored by convergence and insight quality.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="parallel_reasoning",
            domain=ResearchDomain.COGNITIVE,
        )

    def explore_and_record(
        self,
        topic: str,
        max_branches: int = 4,
        max_depth: int = 6,
    ) -> Experiment | None:
        """Run parallel reasoning and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.core.intelligence.parallel_reasoning import (
                ParallelReasoningTree,
            )

            tree = ParallelReasoningTree(topic=topic)
            result = tree.explore(
                max_branches=max_branches,
                max_depth=max_depth,
            )

            # Score by convergence and confidence
            convergence = len(result.convergence_points) if hasattr(result, "convergence_points") else 0
            confidence = result.confidence if hasattr(result, "confidence") else 0.5
            branches_explored = len(result.branches) if hasattr(result, "branches") else 0
            fitness = min(confidence * 0.5 + min(convergence / 5.0, 1.0) * 0.3 + min(branches_explored / max_branches, 1.0) * 0.2, 1.0)

            return self._record_experiment(
                hypothesis=f"Parallel reasoning: {topic}",
                parameters={
                    "topic": topic,
                    "max_branches": max_branches,
                    "max_depth": max_depth,
                },
                fitness_score=fitness,
                outcome={
                    "branches_explored": branches_explored,
                    "convergence_points": convergence,
                    "confidence": confidence,
                    "synthesis": result.synthesis[:500] if hasattr(result, "synthesis") and result.synthesis else "",
                },
                metadata={
                    "source": "parallel_reasoning",
                    "topic": topic,
                },
            )
        except Exception as e:
            logger.debug("ParallelReasoning adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


class AlchemicalLoopAdapter(BaseAdapter):
    """Adapter for AlchemicalLoop 7-stage process → ResearchDAG.

    Records alchemical loop completions as experiments with
    fitness scored by stage completion and output quality.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="alchemical_loop",
            domain=ResearchDomain.EVOLUTION,
        )

    def execute_and_record(
        self,
        task_description: str,
        stages: list[str] | None = None,
    ) -> Experiment | None:
        """Run alchemical loop and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

            loop = AlchemicalLoop()
            result = loop.execute(task_description)

            # Score by stage completion
            stages_completed = 0
            if hasattr(result, "stages_completed"):
                stages_completed = result.stages_completed
            elif hasattr(result, "stage_results"):
                stages_completed = sum(
                    1 for r in result.stage_results.values()
                    if r.get("status") == "success"
                )
            total_stages = len(stages or ["calcination", "dissolution", "separation",
                                          "conjunction", "fermentation", "distillation",
                                          "coagulation"])
            fitness = stages_completed / total_stages if total_stages > 0 else 0.0

            return self._record_experiment(
                hypothesis=f"Alchemical synthesis: {task_description}",
                parameters={
                    "task": task_description,
                    "stages": stages or [],
                },
                fitness_score=fitness,
                outcome={
                    "stages_completed": stages_completed,
                    "total_stages": total_stages,
                    "result_summary": str(result)[:500] if result else "",
                },
                metadata={
                    "source": "alchemical_loop",
                    "task": task_description,
                },
            )
        except Exception as e:
            logger.debug("AlchemicalLoop adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


class RecursiveLoopAdapter(BaseAdapter):
    """Adapter for RecursiveImprovementLoop 6-phase cycle → ResearchDAG.

    Records recursive improvement cycles as experiments with
    fitness scored by improvement magnitude and learning quality.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="recursive_loop",
            domain=ResearchDomain.EVOLUTION,
        )

    def cycle_and_record(self, focus_area: str = "") -> Experiment | None:
        """Run a recursive improvement cycle and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.core.evolution.recursive_loop import (
                RecursiveImprovementLoop,
            )

            loop = RecursiveImprovementLoop()
            result = loop.run_cycle(focus_area=focus_area)

            # Score by improvement magnitude
            hypotheses_generated = 0
            recommendations = 0
            if hasattr(result, "hypotheses"):
                hypotheses_generated = len(result.hypotheses)
            if hasattr(result, "recommendations"):
                recommendations = len(result.recommendations)
            fitness = min(
                (hypotheses_generated / 5.0) * 0.4 +
                (recommendations / 3.0) * 0.4 + 0.2,
                1.0,
            )

            return self._record_experiment(
                hypothesis=f"Recursive improvement: {focus_area or 'general'}",
                parameters={"focus_area": focus_area},
                fitness_score=fitness,
                outcome={
                    "hypotheses_generated": hypotheses_generated,
                    "recommendations": recommendations,
                    "phases_completed": 6,
                },
                metadata={
                    "source": "recursive_loop",
                    "focus_area": focus_area,
                },
            )
        except Exception as e:
            logger.debug("RecursiveLoop adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


class KnowledgeGapAdapter(BaseAdapter):
    """Adapter for KnowledgeGapActionLoop → ResearchDAG.

    Records knowledge gap detection and filling as experiments with
    fitness scored by gap fill success rate.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="knowledge_gap",
            domain=ResearchDomain.COGNITIVE,
        )

    def detect_and_record(self, max_gaps: int = 5) -> Experiment | None:
        """Run knowledge gap detection and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.core.consciousness.knowledge_gap_loop import (
                get_knowledge_gap_loop,
            )

            loop = get_knowledge_gap_loop()
            results = loop.run(max_gaps=max_gaps)

            gaps_found = len(results)
            gaps_filled = sum(1 for r in results if r.get("status") == "success")
            fitness = gaps_filled / max(gaps_found, 1) if gaps_found > 0 else 0.0

            return self._record_experiment(
                hypothesis=f"Knowledge gap detection ({gaps_found} gaps)",
                parameters={"max_gaps": max_gaps},
                fitness_score=fitness,
                outcome={
                    "gaps_found": gaps_found,
                    "gaps_filled": gaps_filled,
                    "success_rate": fitness,
                    "gap_types": [r.get("type", "unknown") for r in results],
                },
                metadata={
                    "source": "knowledge_gap",
                    "results": results[:3],
                },
            )
        except Exception as e:
            logger.debug("KnowledgeGap adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


class SelfDirectedAdapter(BaseAdapter):
    """Adapter for SelfDirectedAttention → ResearchDAG.

    Records self-directed attention turns as experiments with
    fitness scored by imperative novelty and intensity.
    """

    def __init__(self, dag: ResearchDAG | None = None) -> None:
        super().__init__(
            dag=dag,
            agent_id="self_directed",
            domain=ResearchDomain.CONSCIOUSNESS,
        )

    def observe_and_record(self) -> Experiment | None:
        """Run self-directed attention and record results in the DAG."""
        with self._stats_lock:
            self._stats.calls += 1

        try:
            from whitemagic.core.consciousness.self_initiation import (
                get_self_directed_attention,
            )

            sda = get_self_directed_attention()
            turns = sda.observe_and_generate()

            if not turns:
                return self._record_experiment(
                    hypothesis="Self-directed observation (no imperatives generated)",
                    fitness_score=0.1,
                    outcome={"turns_generated": 0},
                    metadata={"source": "self_directed"},
                )

            top = turns[0]
            avg_intensity = sum(t.intensity for t in turns) / len(turns)
            fitness = min(avg_intensity, 1.0)

            return self._record_experiment(
                hypothesis=f"Self-directed: {top.imperative[:80]}",
                parameters={
                    "top_imperative": top.imperative,
                    "action_type": getattr(top, "action_type", "unknown"),
                },
                fitness_score=fitness,
                outcome={
                    "turns_generated": len(turns),
                    "avg_intensity": avg_intensity,
                    "top_imperative": top.imperative,
                },
                metadata={
                    "source": "self_directed",
                    "all_imperatives": [t.imperative for t in turns[:5]],
                },
            )
        except Exception as e:
            logger.debug("SelfDirected adapter: %s", e, exc_info=True)
            with self._stats_lock:
                self._stats.errors += 1
            return None


# ── Registry ──────────────────────────────────────────────────────────

_ADAPTERS: dict[str, BaseAdapter] = {}


def get_adapter(name: str) -> BaseAdapter:
    """Get or create a named adapter instance."""
    if name not in _ADAPTERS:
        dag = get_research_dag()
        if name == "rabbit_hole":
            _ADAPTERS[name] = RabbitHoleAdapter(dag=dag)
        elif name == "parallel_reasoning":
            _ADAPTERS[name] = ParallelReasoningAdapter(dag=dag)
        elif name == "alchemical_loop":
            _ADAPTERS[name] = AlchemicalLoopAdapter(dag=dag)
        elif name == "recursive_loop":
            _ADAPTERS[name] = RecursiveLoopAdapter(dag=dag)
        elif name == "knowledge_gap":
            _ADAPTERS[name] = KnowledgeGapAdapter(dag=dag)
        elif name == "self_directed":
            _ADAPTERS[name] = SelfDirectedAdapter(dag=dag)
        else:
            raise ValueError(f"Unknown adapter: {name}")
    return _ADAPTERS[name]


def get_all_adapter_stats() -> dict[str, Any]:
    """Get stats from all registered adapters."""
    return {name: adapter.get_stats() for name, adapter in _ADAPTERS.items()}
