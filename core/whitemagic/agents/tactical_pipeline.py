"""
Yin-Yang Tactical Pipeline — Cyclical Campaign Refinement System

Transforms vague objectives into measurable victories through 7-phase cycles:
1. SCOUT (Yin) — Explore terrain, gather intelligence
2. DISCOVER (Yin) — Find patterns, identify gaps
3. CLARIFY (Yin) — Convert vague → specific, add metrics
4. PLAN (Yin) — Generate strategies, simulate, rank by consensus
5. EXECUTE (Yang) — Deploy parallel armies with top strategy
6. VERIFY (Yang) — Check victory conditions, measure results
7. SCOUT (Yin) — Re-scan with new knowledge, repeat cycle

Each cycle refines objectives until victory conditions are met.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from whitemagic.config.paths import PIPELINE_DIR


class PipelinePhase(Enum):
    """7 phases of the Yin-Yang tactical cycle"""
    SCOUT = "scout"              # YIN: Explore, gather intelligence
    DISCOVER = "discover"        # YIN: Find patterns, identify gaps
    CLARIFY = "clarify"          # YIN: Vague → specific + measurable
    PLAN = "plan"                # YIN: Strategy generation + simulation
    EXECUTE = "execute"          # YANG: Parallel deployment
    VERIFY = "verify"            # YANG: Victory condition checks
    REFLECT = "reflect"          # YIN: Learn from cycle, prepare next


class YinYang(Enum):
    """Phase polarity"""
    YIN = "yin"      # Receptive, analytical, planning
    YANG = "yang"    # Active, execution, manifestation


PHASE_POLARITY = {
    PipelinePhase.SCOUT: YinYang.YIN,
    PipelinePhase.DISCOVER: YinYang.YIN,
    PipelinePhase.CLARIFY: YinYang.YIN,
    PipelinePhase.PLAN: YinYang.YIN,
    PipelinePhase.EXECUTE: YinYang.YANG,
    PipelinePhase.VERIFY: YinYang.YANG,
    PipelinePhase.REFLECT: YinYang.YIN,
}


@dataclass
class ObjectiveRefinement:
    """Tracks transformation from vague → specific"""
    original: str
    refined: str
    metrics: list[str]
    baseline: dict[str, Any] | None = None
    target: dict[str, Any] | None = None
    verification_method: str | None = None
    confidence: float = 0.0


@dataclass
class StrategySimulation:
    """Results from simulating a strategy"""
    strategy_name: str
    predicted_success_rate: float
    predicted_duration: float
    predicted_clone_count: int
    risks: list[str]
    dependencies: list[str]
    consensus_votes: int = 0
    rank: int = 0


@dataclass
class CycleMetrics:
    """Metrics for one complete cycle"""
    cycle_number: int
    start_time: float
    end_time: float | None = None
    phase_durations: dict[str, float] = field(default_factory=dict)
    findings_count: int = 0
    objectives_refined: int = 0
    strategies_generated: int = 0
    clones_deployed: int = 0
    victory_conditions_met: int = 0
    victory_conditions_total: int = 0
    improvements_from_last_cycle: list[str] = field(default_factory=list)


@dataclass
class PipelineState:
    """Complete state of the tactical pipeline"""
    campaign_codename: str
    current_phase: PipelinePhase
    current_cycle: int
    total_cycles: int = 0

    # Accumulated knowledge across cycles
    scout_findings: list[dict[str, Any]] = field(default_factory=list)
    discovered_patterns: list[dict[str, Any]] = field(default_factory=list)
    refined_objectives: list[ObjectiveRefinement] = field(default_factory=list)
    strategy_simulations: list[StrategySimulation] = field(default_factory=list)
    execution_results: list[dict[str, Any]] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)

    # Cycle history
    cycle_metrics: list[CycleMetrics] = field(default_factory=list)

    # Victory tracking
    victory_achieved: bool = False
    victory_cycle: int | None = None
    stagnation_count: int = 0  # Cycles without progress

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'campaign_codename': self.campaign_codename,
            'current_phase': self.current_phase.value,
            'current_cycle': self.current_cycle,
            'total_cycles': self.total_cycles,
            'scout_findings': self.scout_findings,
            'discovered_patterns': self.discovered_patterns,
            'refined_objectives': [asdict(obj) for obj in self.refined_objectives],
            'strategy_simulations': [asdict(sim) for sim in self.strategy_simulations],
            'execution_results': self.execution_results,
            'verification_results': self.verification_results,
            'cycle_metrics': [asdict(m) for m in self.cycle_metrics],
            'victory_achieved': self.victory_achieved,
            'victory_cycle': self.victory_cycle,
            'stagnation_count': self.stagnation_count,
        }


class TacticalPipeline:
    """
    Yin-Yang Tactical Pipeline for cyclical campaign refinement.

    Transforms vague objectives into victories through iterative cycles:
    - Each cycle refines objectives, strategies, and execution
    - Yin phases (scout/discover/clarify/plan) gather intelligence
    - Yang phases (execute/verify) manifest and measure
    - Reflect phase learns from results and prepares next cycle
    """

    def __init__(self, campaign_codename: str, state_dir: Path | None = None):
        self.campaign_codename = campaign_codename
        self.state_dir = state_dir or PIPELINE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state = self._load_or_create_state()
        self.current_cycle_metrics: CycleMetrics | None = None

    def _load_or_create_state(self) -> PipelineState:
        """Load existing state or create new"""
        state_file = self.state_dir / f"{self.campaign_codename}_pipeline.json"

        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
                # Reconstruct enums and dataclasses
                state = PipelineState(
                    campaign_codename=data['campaign_codename'],
                    current_phase=PipelinePhase(data['current_phase']),
                    current_cycle=data['current_cycle'],
                    total_cycles=data['total_cycles'],
                    scout_findings=data['scout_findings'],
                    discovered_patterns=data['discovered_patterns'],
                    refined_objectives=[ObjectiveRefinement(**obj) for obj in data['refined_objectives']],
                    strategy_simulations=[StrategySimulation(**sim) for sim in data['strategy_simulations']],
                    execution_results=data['execution_results'],
                    verification_results=data['verification_results'],
                    cycle_metrics=[CycleMetrics(**m) for m in data['cycle_metrics']],
                    victory_achieved=data['victory_achieved'],
                    victory_cycle=data.get('victory_cycle'),
                    stagnation_count=data.get('stagnation_count', 0),
                )
                return state
        else:
            return PipelineState(
                campaign_codename=self.campaign_codename,
                current_phase=PipelinePhase.SCOUT,
                current_cycle=1,
            )

    def save_state(self):
        """Persist pipeline state to disk"""
        state_file = self.state_dir / f"{self.campaign_codename}_pipeline.json"
        with open(state_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def start_cycle(self) -> CycleMetrics:
        """Begin a new cycle"""
        self.current_cycle_metrics = CycleMetrics(
            cycle_number=self.state.current_cycle,
            start_time=time.time(),
        )
        self.state.current_phase = PipelinePhase.SCOUT
        return self.current_cycle_metrics

    def advance_phase(self) -> PipelinePhase:
        """Move to next phase in the cycle"""
        phase_order = [
            PipelinePhase.SCOUT,
            PipelinePhase.DISCOVER,
            PipelinePhase.CLARIFY,
            PipelinePhase.PLAN,
            PipelinePhase.EXECUTE,
            PipelinePhase.VERIFY,
            PipelinePhase.REFLECT,
        ]

        current_idx = phase_order.index(self.state.current_phase)
        next_idx = (current_idx + 1) % len(phase_order)

        # If we've completed REFLECT, start new cycle
        if self.state.current_phase == PipelinePhase.REFLECT:
            self.end_cycle()
            self.state.current_cycle += 1
            self.state.total_cycles += 1
            self.start_cycle()

        self.state.current_phase = phase_order[next_idx]
        self.save_state()
        return self.state.current_phase

    def end_cycle(self):
        """Complete current cycle and save metrics"""
        if self.current_cycle_metrics:
            self.current_cycle_metrics.end_time = time.time()
            self.state.cycle_metrics.append(self.current_cycle_metrics)
            self.current_cycle_metrics = None

    def record_phase_duration(self, phase: PipelinePhase, duration: float):
        """Record how long a phase took"""
        if self.current_cycle_metrics:
            self.current_cycle_metrics.phase_durations[phase.value] = duration

    # ========== PHASE 1: SCOUT (YIN) ==========

    def scout(self, scout_fn) -> list[dict[str, Any]]:
        """
        Phase 1: Scout and explore terrain

        Args:
            scout_fn: Function that performs scouting (e.g., file scan, DB query)

        Returns:
            List of findings from scouting
        """
        start = time.time()
        findings = scout_fn()

        self.state.scout_findings.extend(findings)
        if self.current_cycle_metrics:
            self.current_cycle_metrics.findings_count += len(findings)

        self.record_phase_duration(PipelinePhase.SCOUT, time.time() - start)
        self.save_state()
        return cast(list[dict[str, Any]], findings)

    # ========== PHASE 2: DISCOVER (YIN) ==========

    def discover(self, discover_fn) -> list[dict[str, Any]]:
        """
        Phase 2: Discover patterns and identify gaps

        Args:
            discover_fn: Function that analyzes findings and discovers patterns

        Returns:
            List of discovered patterns
        """
        start = time.time()
        patterns = discover_fn(self.state.scout_findings)

        # Ensure correct type for return and state
        if not isinstance(patterns, list):
            patterns = [patterns] if patterns else []

        patterns_list = [dict(p) if isinstance(p, dict) else {"pattern": str(p)} for p in patterns]

        self.state.discovered_patterns.extend(patterns_list)

        self.record_phase_duration(PipelinePhase.DISCOVER, time.time() - start)
        self.save_state()
        return patterns_list

    # ========== PHASE 3: CLARIFY (YIN) ==========

    def clarify(self, clarify_fn) -> list[ObjectiveRefinement]:
        """
        Phase 3: Convert vague objectives → specific + measurable

        Args:
            clarify_fn: Function that takes patterns and generates refined objectives

        Returns:
            List of refined objectives with metrics
        """
        start = time.time()
        refinements = clarify_fn(self.state.discovered_patterns)

        if not isinstance(refinements, list):
            refinements = [refinements] if refinements else []

        ref_list = [r for r in refinements if isinstance(r, ObjectiveRefinement)]

        self.state.refined_objectives.extend(ref_list)
        if self.current_cycle_metrics:
            self.current_cycle_metrics.objectives_refined += len(ref_list)

        self.record_phase_duration(PipelinePhase.CLARIFY, time.time() - start)
        self.save_state()
        return ref_list

    # ========== PHASE 4: PLAN (YIN) ==========

    def plan(self, plan_fn) -> list[StrategySimulation]:
        """
        Phase 4: Generate strategies, simulate, rank by consensus

        Args:
            plan_fn: Function that generates and simulates strategies

        Returns:
            List of strategy simulations ranked by consensus
        """
        start = time.time()
        simulations = plan_fn(self.state.refined_objectives)

        # Rank strategies by consensus votes
        simulations.sort(key=lambda s: s.consensus_votes, reverse=True)
        for idx, sim in enumerate(simulations):
            sim.rank = idx + 1

        self.state.strategy_simulations = simulations  # Replace with latest
        if self.current_cycle_metrics:
            self.current_cycle_metrics.strategies_generated += len(simulations)

        self.record_phase_duration(PipelinePhase.PLAN, time.time() - start)
        self.save_state()
        return cast(list[StrategySimulation], simulations)

    # ========== PHASE 5: EXECUTE (YANG) ==========

    def execute(self, execute_fn) -> dict[str, Any]:
        """
        Phase 5: Deploy parallel armies with top-ranked strategy

        Args:
            execute_fn: Function that executes the top strategy

        Returns:
            Execution results
        """
        start = time.time()

        # Get top-ranked strategy
        if not self.state.strategy_simulations:
            raise ValueError("No strategies available for execution. Run plan() first.")

        top_strategy = self.state.strategy_simulations[0]
        results = execute_fn(top_strategy)

        self.state.execution_results.append(results)
        if self.current_cycle_metrics:
            self.current_cycle_metrics.clones_deployed += results.get('clones_deployed', 0)

        self.record_phase_duration(PipelinePhase.EXECUTE, time.time() - start)
        self.save_state()
        return cast(dict[str, Any], results)

    # ========== PHASE 6: VERIFY (YANG) ==========

    def verify(self, verify_fn) -> dict[str, Any]:
        """
        Phase 6: Check victory conditions and measure results

        Args:
            verify_fn: Function that verifies victory conditions

        Returns:
            Verification results with VCs met/total
        """
        start = time.time()

        verification = verify_fn(self.state.execution_results[-1] if self.state.execution_results else {})

        self.state.verification_results.append(verification)
        if self.current_cycle_metrics:
            self.current_cycle_metrics.victory_conditions_met = verification.get('vcs_met', 0)
            self.current_cycle_metrics.victory_conditions_total = verification.get('vcs_total', 0)

        # Check for victory
        if verification.get('vcs_met', 0) == verification.get('vcs_total', 0) and verification.get('vcs_total', 0) > 0:
            self.state.victory_achieved = True
            self.state.victory_cycle = self.state.current_cycle

        self.record_phase_duration(PipelinePhase.VERIFY, time.time() - start)
        self.save_state()
        return cast(dict[str, Any], verification)

    # ========== PHASE 7: REFLECT (YIN) ==========

    def reflect(self, reflect_fn) -> dict[str, Any]:
        """
        Phase 7: Learn from cycle, prepare for next iteration

        Args:
            reflect_fn: Function that analyzes cycle and generates insights

        Returns:
            Reflection insights and recommendations
        """
        start = time.time()

        # Gather all cycle data
        cycle_data = {
            'cycle_number': self.state.current_cycle,
            'scout_findings': self.state.scout_findings,
            'discovered_patterns': self.state.discovered_patterns,
            'refined_objectives': [asdict(obj) for obj in self.state.refined_objectives],
            'strategy_simulations': [asdict(sim) for sim in self.state.strategy_simulations],
            'execution_results': self.state.execution_results,
            'verification_results': self.state.verification_results,
            'metrics': asdict(self.current_cycle_metrics) if self.current_cycle_metrics else {},
        }

        insights = reflect_fn(cycle_data)

        # Check for stagnation
        if self.state.verification_results:
            last_vcs = self.state.verification_results[-1].get('vcs_met', 0)
            if len(self.state.verification_results) > 1:
                prev_vcs = self.state.verification_results[-2].get('vcs_met', 0)
                if last_vcs <= prev_vcs:
                    self.state.stagnation_count += 1
                else:
                    self.state.stagnation_count = 0

        if self.current_cycle_metrics:
            self.current_cycle_metrics.improvements_from_last_cycle = insights.get('improvements', [])

        self.record_phase_duration(PipelinePhase.REFLECT, time.time() - start)
        self.save_state()
        return cast(dict[str, Any], insights)

    # ========== UTILITY METHODS ==========

    def get_current_polarity(self) -> YinYang:
        """Get current phase polarity (Yin or Yang)"""
        return PHASE_POLARITY[self.state.current_phase]

    def get_cycle_summary(self) -> dict[str, Any]:
        """Get summary of current cycle"""
        return {
            'cycle_number': self.state.current_cycle,
            'current_phase': self.state.current_phase.value,
            'polarity': self.get_current_polarity().value,
            'findings': len(self.state.scout_findings),
            'patterns': len(self.state.discovered_patterns),
            'refined_objectives': len(self.state.refined_objectives),
            'strategies': len(self.state.strategy_simulations),
            'executions': len(self.state.execution_results),
            'verifications': len(self.state.verification_results),
            'victory_achieved': self.state.victory_achieved,
            'stagnation_count': self.state.stagnation_count,
        }

    def should_continue(self, max_cycles: int = 10, max_stagnation: int = 3) -> bool:
        """Determine if pipeline should continue cycling"""
        if self.state.victory_achieved:
            return False
        if self.state.current_cycle >= max_cycles:
            return False
        if self.state.stagnation_count >= max_stagnation:
            return False
        return True

    def get_progress_report(self) -> str:
        """Generate human-readable progress report"""
        lines = [
            f"=== Tactical Pipeline: {self.campaign_codename} ===",
            f"Cycle: {self.state.current_cycle}/{self.state.total_cycles}",
            f"Phase: {self.state.current_phase.value.upper()} ({self.get_current_polarity().value})",
            "",
            "Intelligence Gathered:",
            f"  Scout findings: {len(self.state.scout_findings)}",
            f"  Patterns discovered: {len(self.state.discovered_patterns)}",
            f"  Objectives refined: {len(self.state.refined_objectives)}",
            f"  Strategies simulated: {len(self.state.strategy_simulations)}",
            "",
            "Execution:",
            f"  Deployments: {len(self.state.execution_results)}",
            f"  Verifications: {len(self.state.verification_results)}",
        ]

        if self.state.verification_results:
            last_verify = self.state.verification_results[-1]
            vcs_met = last_verify.get('vcs_met', 0)
            vcs_total = last_verify.get('vcs_total', 0)
            lines.append(f"  Victory Conditions: {vcs_met}/{vcs_total} ({100*vcs_met/vcs_total if vcs_total > 0 else 0:.1f}%)")

        lines.extend([
            "",
            "Status:",
            f"  Victory: {'✅ ACHIEVED' if self.state.victory_achieved else '🔄 In Progress'}",
            f"  Stagnation: {self.state.stagnation_count} cycles",
        ])

        return "\n".join(lines)


def create_pipeline(campaign_codename: str) -> TacticalPipeline:
    """Factory function to create a new tactical pipeline"""
    return TacticalPipeline(campaign_codename)
