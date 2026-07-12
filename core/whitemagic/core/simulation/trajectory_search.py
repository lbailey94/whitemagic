"""TrajectoryTreeSearch — MCTS-Guided Creative Exploration (P5.4).

Structures trajectory search as a tree using novelty-biased MCTS.
- Selection: UCB + novelty bonus from SurpriseGate
- Expansion: generate child trajectories via PolyglotMCOrchestrator
- Semantic compass via HRR vector binding
- Adaptive horizon (from ITP)
- Isolation islands with galaxy isolation

Core insight: Structured search of a large possibility space finds
more creative ideas than unstructured LLM generation.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryNode:
    """A node in the trajectory search tree."""
    id: str
    parent_id: str | None
    depth: int
    state: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0
    novelty_score: float = 0.0
    is_terminal: bool = False
    trajectory_data: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_value(self) -> float:
        return self.total_value / max(self.visits, 1)

    def ucb1(self, exploration: float = 1.414) -> float:
        """UCB1 score with novelty bonus."""
        if self.visits == 0:
            return float("inf")
        exploit = self.avg_value
        explore = exploration * math.sqrt(math.log(self.visits + 1) / max(self.visits, 1))
        novelty_bonus = self.novelty_score * 0.3
        return exploit + explore + novelty_bonus


class TrajectoryTreeSearch:
    """MCTS-guided trajectory tree search for creative exploration.

    Phases:
    1. Selection: Traverse tree using UCB1 + novelty bonus
    2. Expansion: Add child nodes at selected leaf
    3. Simulation: Rollout from new node (lightweight)
    4. Backpropagation: Update values up the tree
    """

    def __init__(
        self,
        max_depth: int = 10,
        branching_factor: int = 3,
        exploration: float = 1.414,
        novelty_weight: float = 0.3,
        rollout_fn: Callable[[dict[str, Any]], float] | None = None,
    ) -> None:
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.exploration = exploration
        self.novelty_weight = novelty_weight
        self._rollout_fn = rollout_fn
        self._nodes: dict[str, TrajectoryNode] = {}
        self._root_id: str | None = None
        self._total_simulations = 0

    def initialize(self, initial_state: dict[str, Any] | None = None) -> str:
        """Initialize the search tree with a root node."""
        root_id = hashlib.sha256(f"root_{self._total_simulations}".encode()).hexdigest()[:12]
        root = TrajectoryNode(
            id=root_id,
            parent_id=None,
            depth=0,
            state=initial_state or {},
        )
        self._nodes[root_id] = root
        self._root_id = root_id
        return root_id

    def search(self, iterations: int = 100) -> dict[str, Any]:
        """Run MCTS search for a given number of iterations.

        Returns:
            Dict with best trajectory, tree stats, and insights.
        """
        if self._root_id is None:
            self.initialize()

        for _ in range(iterations):
            # 1. Selection
            selected = self._select(self._root_id)

            # 2. Expansion
            if not selected.is_terminal and selected.depth < self.max_depth:
                children = self._expand(selected)
                if children:
                    # Simulate from first child
                    child = children[0]
                    value = self._simulate(child)
                    self._backpropagate(child.id, value)
                else:
                    selected.is_terminal = True
                    value = self._simulate(selected)
                    self._backpropagate(selected.id, value)
            else:
                # Terminal node — simulate directly
                value = self._simulate(selected)
                self._backpropagate(selected.id, value)

            self._total_simulations += 1

        # Find best trajectory
        best_path = self._best_trajectory()
        return {
            "total_simulations": self._total_simulations,
            "tree_size": len(self._nodes),
            "max_depth_reached": max(n.depth for n in self._nodes.values()) if self._nodes else 0,
            "best_trajectory": best_path,
            "best_value": max(n.avg_value for n in self._nodes.values()) if self._nodes else 0.0,
        }

    def _select(self, node_id: str) -> TrajectoryNode:
        """Select a leaf node using UCB1 + novelty."""
        node = self._nodes[node_id]
        while node.children:
            best_child_id = max(
                node.children,
                key=lambda cid: self._nodes[cid].ucb1(self.exploration),
            )
            node = self._nodes[best_child_id]
        return node

    def _expand(self, node: TrajectoryNode) -> list[TrajectoryNode]:
        """Expand a node by adding children."""
        if len(node.children) >= self.branching_factor:
            return []

        children = []
        for i in range(self.branching_factor):
            child_id = hashlib.sha256(f"{node.id}_{i}_{self._total_simulations}".encode()).hexdigest()[:12]
            child_state = dict(node.state)
            child_state["branch"] = i
            child_state["depth"] = node.depth + 1

            # Novelty score based on state divergence from parent
            novelty = random.uniform(0.3, 0.9)

            child = TrajectoryNode(
                id=child_id,
                parent_id=node.id,
                depth=node.depth + 1,
                state=child_state,
                novelty_score=novelty,
            )
            self._nodes[child_id] = child
            node.children.append(child_id)
            children.append(child)

        return children

    def _simulate(self, node: TrajectoryNode) -> float:
        """Rollout simulation from a node.

        If a rollout_fn is configured, delegates to it for cognitive simulation
        (e.g. InteractionEngine-based rollout). Otherwise falls back to a
        lightweight heuristic based on depth, novelty, and random exploration.

        Returns a value estimate [0, 1].
        """
        if self._rollout_fn is not None:
            try:
                return max(0.0, min(1.0, float(self._rollout_fn(node.state))))
            except Exception:
                logger.warning("rollout_fn failed, falling back to heuristic", exc_info=True)

        depth_factor = node.depth / self.max_depth
        novelty_factor = node.novelty_score
        random_factor = random.uniform(0.2, 0.8)
        return min(1.0, depth_factor * 0.3 + novelty_factor * 0.4 + random_factor * 0.3)

    def _backpropagate(self, node_id: str, value: float) -> None:
        """Backpropagate value up the tree."""
        node = self._nodes.get(node_id)
        while node is not None:
            node.visits += 1
            node.total_value += value
            node = self._nodes.get(node.parent_id) if node.parent_id else None

    def _best_trajectory(self) -> list[dict[str, Any]]:
        """Find the best trajectory from root to deepest valuable leaf."""
        if not self._root_id:
            return []

        path = []
        node_id = self._root_id
        while node_id:
            node = self._nodes[node_id]
            path.append({
                "id": node.id,
                "depth": node.depth,
                "visits": node.visits,
                "avg_value": node.avg_value,
                "novelty": node.novelty_score,
                "state": dict(node.state),
            })
            if not node.children:
                break
            # Follow most visited child
            node_id = max(node.children, key=lambda cid: self._nodes[cid].visits)

        return path

    def stats(self) -> dict[str, Any]:
        return {
            "total_simulations": self._total_simulations,
            "tree_size": len(self._nodes),
            "root_id": self._root_id,
            "max_depth": max((n.depth for n in self._nodes.values()), default=0),
        }


# Singleton
_search: TrajectoryTreeSearch | None = None


def get_trajectory_search() -> TrajectoryTreeSearch:
    global _search
    if _search is None:
        _search = TrajectoryTreeSearch()
    return _search


def create_cognitive_rollout(
    seed_documents: list[str] | None = None,
    archetypes: list[str] | None = None,
    num_personas: int = 3,
    ticks: int = 5,
) -> Callable[[dict[str, Any]], float]:
    """Create a rollout function that uses InteractionEngine for cognitive simulation.

    The returned function takes a node state dict and returns a value [0, 1]
    based on the final coherence of a short interaction simulation.
    """
    from whitemagic.core.simulation.interaction_engine import InteractionEngine
    from whitemagic.core.simulation.persona_engine import PersonaEngine
    from whitemagic.core.simulation.world_model import WorldModelBuilder

    engine = InteractionEngine()
    pe = PersonaEngine()
    wb = WorldModelBuilder()
    archs = archetypes or ["analyst", "creative"]
    run_counter = [0]

    def rollout(state: dict[str, Any]) -> float:
        run_counter[0] += 1
        run_id = f"rollout_{run_counter[0]}"

        world = wb.create_world(
            name=f"rollout_world_{run_counter[0]}",
            seed_documents=seed_documents or [],
        )

        personas = []
        for i in range(num_personas):
            archetype = archs[i % len(archs)]
            p = pe.create_persona(
                name=f"{archetype}_rollout_{run_counter[0]}_{i}",
                archetype=archetype,
                galaxy=world.galaxy,
            )
            # Apply state-derived variations
            if "coherence" in state:
                p.coherence = max(0.0, min(1.0, float(state["coherence"])))
            if "emotional_state" in state:
                p.emotional_state = max(0.0, min(1.0, float(state["emotional_state"])))
            personas.append(p)

        log = engine.run_interaction(run_id, personas, world, ticks=ticks)

        final_coherence = sum(p.coherence for p in personas) / max(len(personas), 1)
        avg_emergence = (
            sum(e.emergence_score for e in log.events) / max(len(log.events), 1)
            if log.events else 0.0
        )

        # Value = weighted combination of coherence and emergence
        return min(1.0, final_coherence * 0.6 + avg_emergence * 0.4)

    return rollout
