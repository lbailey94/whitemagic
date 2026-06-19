# ruff: noqa: BLE001
"""Agent Swarm Protocols — Task Decomposition, Capability Routing, Consensus
===========================================================================
Enables multi-agent coordination within WhiteMagic:
  - Task decomposition: Break complex tasks into subtasks
  - Capability routing: Match subtasks to agents by declared capabilities
  - Consensus: Collect votes and resolve disagreements

Integrates with the existing agent registry (agent.register, agent.list).

Usage:
    from whitemagic.agents.swarm import get_swarm
    swarm = get_swarm()
    plan = swarm.decompose("Analyze codebase and generate report", context={})
    assignments = swarm.route(plan)
    result = swarm.execute(assignments)
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(StrEnum):
    """TaskStatus: task status.

    Enumeration.

    Members:
        PENDING
        ASSIGNED
        RUNNING
        COMPLETED
        FAILED"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConsensusStrategy(StrEnum):
    """ConsensusStrategy: consensus strategy.

    Enumeration.

    Members:
        MAJORITY
        UNANIMOUS
        FIRST_WINS
        WEIGHTED
        TRICAMERAL"""
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    FIRST_WINS = "first_wins"
    WEIGHTED = "weighted"
    TRICAMERAL = "tricameral"


@dataclass
class SubTask:
    """SubTask: sub task.

    Value object: equality and repr are field-based."""
    id: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    result: Any | None = None
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "id": self.id,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "priority": self.priority,
            "depends_on": self.depends_on,
        }


@dataclass
class SwarmPlan:
    """SwarmPlan: swarm plan.

    Value object: equality and repr are field-based."""
    id: str
    goal: str
    subtasks: list[SubTask] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        done = sum(1 for t in self.subtasks if t.status == TaskStatus.COMPLETED)
        return {
            "plan_id": self.id,
            "goal": self.goal,
            "subtask_count": len(self.subtasks),
            "completed": done,
            "progress": round(done / max(len(self.subtasks), 1), 2),
            "subtasks": [t.to_dict() for t in self.subtasks],
        }


@dataclass
class Vote:
    """Vote: vote.

    Value object: equality and repr are field-based."""
    agent_id: str
    value: Any
    confidence: float = 1.0
    timestamp: float = 0.0
    house: str | None = None  # For TRICAMERAL: "older_brothers" | "younger_brothers" | "firekeeper"


class AgentSwarm:
    """Multi-agent coordination with decomposition, routing, and consensus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._plans: dict[str, SwarmPlan] = {}
        self._votes: dict[str, list[Vote]] = {}  # topic_id -> votes
        self._max_plans = 100
        self._agent_houses: dict[str, str] = {}  # agent_id -> house assignment
        self._prune_threshold_seconds: float = 3600.0  # 1 hour default

    def decompose(self, goal: str, hints: list[str] | None = None) -> SwarmPlan:
        """Decompose a goal into subtasks.

        Uses heuristic keyword-based decomposition. For richer decomposition,
        feed the plan through an LLM via the pipeline system.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        subtasks = []

        # Heuristic decomposition based on common patterns
        keywords_to_caps = {
            "search": ["memory_search", "vector_search"],
            "analyze": ["analysis", "pattern_detection"],
            "report": ["reporting", "formatting"],
            "code": ["code_analysis", "file_ops"],
            "memory": ["memory_ops", "memory_search"],
            "test": ["testing", "validation"],
            "deploy": ["deployment", "infrastructure"],
            "monitor": ["monitoring", "metrics"],
            "ethic": ["dharma", "ethics"],
            "harmony": ["harmony", "balance"],
        }

        goal_lower = goal.lower()
        detected_caps = set()
        for kw, caps in keywords_to_caps.items():
            if kw in goal_lower:
                detected_caps.update(caps)

        # If hints provided, use those as subtask descriptions
        if hints:
            for i, hint in enumerate(hints):
                caps = []
                for kw, c in keywords_to_caps.items():
                    if kw in hint.lower():
                        caps.extend(c)
                subtasks.append(SubTask(
                    id=f"{plan_id}_t{i}",
                    description=hint,
                    required_capabilities=caps or ["general"],
                    priority=len(hints) - i,
                ))
        else:
            # Auto-generate subtasks from detected capabilities
            if not detected_caps:
                detected_caps = {"general"}

            for i, cap in enumerate(sorted(detected_caps)):
                subtasks.append(SubTask(
                    id=f"{plan_id}_t{i}",
                    description=f"{cap}: {goal}",
                    required_capabilities=[cap],
                    priority=i,
                ))

        plan = SwarmPlan(
            id=plan_id,
            goal=goal,
            subtasks=subtasks,
            created_at=time.time(),
        )

        with self._lock:
            self._plans[plan_id] = plan
            if len(self._plans) > self._max_plans:
                oldest = sorted(self._plans.values(), key=lambda p: p.created_at)
                for p in oldest[:
                    10]:
                    del self._plans[p.id]

        return plan

    def route(self, plan_id: str) -> dict[str, Any]:
        """Route subtasks to available agents based on capability matching.
        Uses the agent registry to find suitable agents.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return {"status": "error", "error": f"Plan {plan_id} not found"}

        # Get available agents
        agents: list[dict[str, Any]] = []
        try:
            from whitemagic.tools.handlers.agent_registry import handle_agent_list

            listed = handle_agent_list(only_active=True)
            raw_agents = listed.get("agents", [])
            if isinstance(raw_agents, list):
                for agent in raw_agents:
                    if isinstance(agent, dict):
                        agents.append(
                            {
                                "agent_id": str(agent.get("id", "")),
                                "capabilities": list(agent.get("capabilities", [])),
                            }
                        )
        except Exception as e:
            logger.debug("Agent listing failed: %s", e, exc_info=True)

        assignments = []
        for task in plan.subtasks:
            if task.status != TaskStatus.PENDING:
                continue

            best_agent = None
            best_score = 0

            for agent in agents:
                # Score = number of matching capabilities
                match = len(set(task.required_capabilities) & set(agent["capabilities"]))
                if match > best_score:
                    best_score = match
                    best_agent = agent["agent_id"]

            if best_agent:
                task.assigned_to = best_agent
                task.status = TaskStatus.ASSIGNED
                assignments.append({
                    "task_id": task.id,
                    "agent_id": best_agent,
                    "capabilities_matched": best_score,
                })
            else:
                assignments.append({
                    "task_id": task.id,
                    "agent_id": None,
                    "reason": "no matching agent found",
                })

        return {
            "status": "success",
            "plan_id": plan_id,
            "assignments": assignments,
            "agents_available": len(agents),
        }

    def complete_task(self, plan_id: str, task_id: str, result: Any = None,
                      success: bool = True) -> dict[str, Any]:
        """Mark a subtask as completed or failed."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return {"status": "error", "error": "Plan not found"}

            for task in plan.subtasks:
                if task.id == task_id:
                    task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                    task.result = result
                    break
            else:
                return {"status": "error", "error": "Task not found"}

            # Check if plan is complete
            all_done = all(t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) for t in plan.subtasks)
            if all_done:
                plan.completed_at = time.time()

            return {"status": "success", "plan": plan.to_dict()}

    def vote(self, topic_id: str, agent_id: str, value: Any,
             confidence: float = 1.0) -> dict[str, Any]:
        """Record a vote from an agent on a topic."""
        v = Vote(agent_id=agent_id, value=value, confidence=confidence, timestamp=time.time())
        with self._lock:
            if topic_id not in self._votes:
                self._votes[topic_id] = []
            self._votes[topic_id].append(v)
        return {"status": "success", "topic_id": topic_id, "votes_count": len(self._votes[topic_id])}

    def resolve(self, topic_id: str,
                strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY) -> dict[str, Any]:
        """Resolve a consensus vote using the specified strategy."""
        with self._lock:
            votes = self._votes.get(topic_id, [])

        if not votes:
            return {"status": "error", "error": "No votes found"}

        if strategy == ConsensusStrategy.FIRST_WINS:
            first_winner = votes[0]
            return {"status": "success", "result": first_winner.value,
                    "strategy": strategy.value, "votes": len(votes)}

        if strategy == ConsensusStrategy.UNANIMOUS:
            values = set(str(v.value) for v in votes)
            if len(values) == 1:
                return {"status": "success", "result": votes[0].value,
                        "strategy": strategy.value, "unanimous": True}
            return {"status": "no_consensus", "strategy": strategy.value,
                    "distinct_values": len(values)}

        if strategy == ConsensusStrategy.WEIGHTED:
            weighted: dict[str, float] = {}
            for v in votes:
                key = str(v.value)
                weighted[key] = weighted.get(key, 0) + v.confidence
            weighted_winner = max(weighted, key=lambda k: weighted[k])
            return {"status": "success", "result": weighted_winner,
                    "strategy": strategy.value, "weight": weighted[weighted_winner]}

        if strategy == ConsensusStrategy.TRICAMERAL:
            return self._resolve_tricameral(topic_id, votes)

        # MAJORITY (default)
        counts: dict[str, int] = {}
        for v in votes:
            key = str(v.value)
            counts[key] = counts.get(key, 0) + 1
        majority_winner = max(counts, key=lambda k: counts[k])
        return {"status": "success", "result": majority_winner,
                "strategy": strategy.value, "count": counts[majority_winner], "total": len(votes)}

    def _resolve_tricameral(self, topic_id: str, votes: list[Vote]) -> dict[str, Any]:
        """Tricameral consensus — Iroquois-inspired two-house review + Sutra Firekeeper.

        Older Brothers (Pragmatists): Review for security, profitability, viability.
        Younger Brothers (Ethicists): Audit for ethics, cost, long-term consequences.
        Firekeeper (Sutra Kernel): Executes only if both houses agree.

        Blends MandalaOS Dharma Engine (ethical audit) and Sutra Kernel (dharma gating).
        """
        # Auto-assign houses if not already set
        for v in votes:
            if not v.house:
                v.house = self._agent_houses.get(v.agent_id, "older_brothers")

        older_votes = [v for v in votes if v.house == "older_brothers"]
        younger_votes = [v for v in votes if v.house == "younger_brothers"]
        firekeeper_votes = [v for v in votes if v.house == "firekeeper"]

        if not older_votes or not younger_votes:
            return {
                "status": "error",
                "error": "TRICAMERAL requires at least one Older Brothers and one Younger Brothers vote",
                "older_count": len(older_votes),
                "younger_count": len(younger_votes),
            }

        # Phase 1: Older Brothers resolve by weighted majority
        older_weighted: dict[str, float] = {}
        for v in older_votes:
            key = str(v.value)
            older_weighted[key] = older_weighted.get(key, 0) + v.confidence
        older_winner = max(older_weighted, key=lambda k: older_weighted[k])
        older_score = older_weighted[older_winner]

        # Phase 2: Younger Brothers audit via Dharma Engine
        # Evaluate the winning proposal for ethical alignment
        dharma_ok = True
        dharma_score = 1.0
        dharma_reason = "No Dharma concerns."
        try:
            from whitemagic.dharma.rules import get_rules_engine
            engine = get_rules_engine()
            decision = engine.evaluate({
                "tool": "swarm_consensus",
                "description": f"Tricameral consensus on topic {topic_id}: value {older_winner}",
                "safety": "READ",
            })
            dharma_score = decision.score
            dharma_ok = decision.action.value != "block"
            dharma_reason = decision.explain
        except Exception as e:
            logger.debug("Dharma engine evaluation failed for tricameral: %s", e, exc_info=True)

        # Phase 3: Younger Brothers resolve their own weighted preference
        younger_weighted: dict[str, float] = {}
        for v in younger_votes:
            key = str(v.value)
            younger_weighted[key] = younger_weighted.get(key, 0) + v.confidence
        younger_winner = max(younger_weighted, key=lambda k: younger_weighted[k])
        younger_score = younger_weighted[younger_winner]

        # Phase 4: Firekeeper (Sutra Kernel) — both houses must agree on the same value
        # If they disagree, the Firekeeper blocks and requests reconciliation
        firekeeper_verdict = "proceed"
        firekeeper_reason = "Both houses agree."
        if older_winner != younger_winner:
            firekeeper_verdict = "block"
            firekeeper_reason = (
                f"House disagreement: Older Brothers chose '{older_winner}' "
                f"(score {older_score:.2f}), Younger Brothers chose '{younger_winner}' "
                f"(score {younger_score:.2f}). Reconciliation required."
            )
        elif not dharma_ok:
            firekeeper_verdict = "block"
            firekeeper_reason = f"Dharma audit failed: {dharma_reason}"
        else:
            # Optional: Sutra Kernel deep evaluation
            try:
                from whitemagic.core.bridge.sutra_bridge import get_sutra_kernel
                sutra = get_sutra_kernel()
                verdict = sutra.evaluate_action(
                    action_type="swarm_consensus",
                    intent_score=min(older_score, younger_score),
                    karma_debt=0.0,
                )
                if verdict.startswith("Panic") or verdict.startswith("Intervene"):
                    firekeeper_verdict = "block"
                    firekeeper_reason = f"Sutra Kernel intervention: {verdict}"
            except Exception as e:
                logger.debug("Sutra Kernel evaluation failed for tricameral: %s", e, exc_info=True)

        # Firekeeper override check
        if firekeeper_votes:
            fk_values = [str(v.value) for v in firekeeper_votes]
            if all(v == "block" for v in fk_values):
                firekeeper_verdict = "block"
                firekeeper_reason = "Firekeeper explicitly blocked."
            elif all(v == "proceed" for v in fk_values):
                firekeeper_verdict = "proceed"
                firekeeper_reason = "Firekeeper explicitly approved."

        result = {
            "status": "success" if firekeeper_verdict == "proceed" else "blocked",
            "result": older_winner if firekeeper_verdict == "proceed" else None,
            "strategy": "tricameral",
            "older_winner": older_winner,
            "older_score": older_score,
            "younger_winner": younger_winner,
            "younger_score": younger_score,
            "dharma_score": dharma_score,
            "dharma_reason": dharma_reason,
            "firekeeper_verdict": firekeeper_verdict,
            "firekeeper_reason": firekeeper_reason,
            "older_count": len(older_votes),
            "younger_count": len(younger_votes),
            "firekeeper_count": len(firekeeper_votes),
        }

        # Emit Gan Ying event for audit trail
        try:
            from whitemagic.tools.unified_api import _emit_gan_ying
            _emit_gan_ying("TRICAMERAL_CONSENSUS", {
                "topic_id": topic_id,
                "result": result["status"],
                "older_winner": older_winner,
                "younger_winner": younger_winner,
                "firekeeper_verdict": firekeeper_verdict,
            })
        except Exception as e:
            logger.debug("Gan Ying emit failed for tricameral: %s", e, exc_info=True)

        return result

    def assign_house(self, agent_id: str, house: str) -> dict[str, Any]:
        """Assign an agent to a tricameral house.

        Houses:
          - older_brothers: pragmatic review (security, viability)
          - younger_brothers: ethical audit (dharma, cost, consequences)
          - firekeeper: final arbiter (optional override)
        """
        valid_houses = {"older_brothers", "younger_brothers", "firekeeper"}
        if house not in valid_houses:
            return {"status": "error", "error": f"Invalid house. Choose from {valid_houses}"}
        with self._lock:
            self._agent_houses[agent_id] = house
        return {"status": "success", "agent_id": agent_id, "house": house}

    def prune_stale(self, max_age_seconds: float | None = None) -> dict[str, Any]:
        """Proof-of-Utility pruning — archive plans and votes older than threshold.

        Emits Gan Ying events so the Karma Ledger records why something was pruned.
        """
        threshold = max_age_seconds or self._prune_threshold_seconds
        now = time.time()
        pruned_plans = 0
        pruned_votes = 0
        archived_plan_ids: list[str] = []

        with self._lock:
            # Prune stale plans
            stale_plans = [
                pid for pid, plan in self._plans.items()
                if plan.completed_at and (now - plan.completed_at) > threshold
            ]
            for pid in stale_plans:
                del self._plans[pid]
                pruned_plans += 1
                archived_plan_ids.append(pid)

            # Prune stale vote topics
            stale_topics = [
                tid for tid, vote_list in self._votes.items()
                if vote_list and (now - max(v.timestamp for v in vote_list)) > threshold
            ]
            for tid in stale_topics:
                del self._votes[tid]
                pruned_votes += 1

        # Emit Gan Ying events for audit trail
        if pruned_plans or pruned_votes:
            try:
                from whitemagic.tools.unified_api import _emit_gan_ying
                _emit_gan_ying("RITUAL_OF_PRUNING", {
                    "pruned_plans": pruned_plans,
                    "pruned_vote_topics": pruned_votes,
                    "archived_plan_ids": archived_plan_ids,
                    "threshold_seconds": threshold,
                    "reason": "Proof-of-Utility: entities exceeded max_age without contributing",
                })
            except Exception as e:
                logger.debug("Gan Ying emit failed for pruning: %s", e, exc_info=True)

        return {
            "status": "success",
            "pruned_plans": pruned_plans,
            "pruned_vote_topics": pruned_votes,
            "threshold_seconds": threshold,
        }

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        """
        Get the plan.

        Args:
            plan_id: Parameter description.

        Returns:
            dict[str, Any] | None
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            return plan.to_dict() if plan else None

    def list_plans(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        List the plans.

        Args:
            limit: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        with self._lock:
            plans = sorted(self._plans.values(), key=lambda p: p.created_at, reverse=True)
            return [p.to_dict() for p in plans[:limit]]

    def status(self) -> dict[str, Any]:
        """
        Perform the status operation.

        Returns:
            dict[str, Any]
        """
        with self._lock:
            active = sum(1 for p in self._plans.values() if not p.completed_at)
            return {
                "total_plans": len(self._plans),
                "active_plans": active,
                "total_votes": sum(len(v) for v in self._votes.values()),
                "vote_topics": len(self._votes),
            }


# Singleton
_swarm: AgentSwarm | None = None
_swarm_lock = threading.Lock()

def get_swarm() -> AgentSwarm:
    """
    Get the swarm.

    Returns:
        AgentSwarm
    """
    global _swarm
    if _swarm is None:
        with _swarm_lock:
            if _swarm is None:
                _swarm = AgentSwarm()
    return _swarm
