# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Quantum-Inspired Intelligence Subsystem (Consolidated v1.2).
============================================================
Unified gateway for quantum-inspired optimization, Grover's amplification,
and superposition-based graph traversal.

Consolidated from quantum_engine.py, quantum_inspired_graph.py, and quantum_graph_adapter.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, dict, list

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)

# --- CORE TYPES ---

@dataclass
class QuantumNode:
    """A node in a quantum-inspired superposition state."""
    id: str
    amplitude: float = 1.0
    phase: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class QuantumWalkConfig:
    """Configuration for quantum-enhanced walks."""
    use_grover: bool = True
    use_superposition: bool = True
    grover_iterations: int = 2
    superposition_hops: int = 2
    classical_fallback: bool = True

# --- QUANTUM INSPIRED ENGINE ---

class QuantumEngine:
    """Simulates quantum algorithms for graph and search optimization."""

    def __init__(self):
        self.coherence_time = 1.0
        self.interference_threshold = 0.1

    def grover_search(self, items: list[Any], oracle: Callable[[Any], bool], iterations: int | None = None) -> list[Any]:
        """Grover's Amplification algorithm for O(√N) search."""
        if np is None:
            logger.warning("QuantumEngine: numpy not available, Grover search falling back to linear.")
            return [i for i in items if oracle(i)]

        N = len(items)
        if N == 0: return []
        if iterations is None: iterations = int((math.pi / 4) * math.sqrt(N))

        amplitudes = np.full(N, 1.0 / math.sqrt(N))
        for _ in range(iterations):
            for i, item in enumerate(items):
                if oracle(item): amplitudes[i] *= -1
            mean = np.mean(amplitudes)
            amplitudes = 2 * mean - amplitudes

        probabilities = amplitudes ** 2
        indices = np.argsort(probabilities)[::-1]
        return [items[i] for i in indices if probabilities[i] > (1.0 / N)]

class QuantumGraphEngine:
    """Graph-specific quantum-inspired algorithms."""

    def __init__(self, walker_sigma: float = 1.0):
        self._walker_sigma = walker_sigma
        self._stats = {"grover_calls": 0, "superposition_fusions": 0}

    def grover_amplification(self, nodes: list[QuantumNode], oracle: Callable[[QuantumNode], bool], iterations: int = 1) -> list[QuantumNode]:
        """Amplify the amplitude of nodes matching the oracle condition."""
        if not nodes: return []
        N = len(nodes)
        avg_amp = sum(n.amplitude for n in nodes) / N
        for _ in range(iterations):
            for node in nodes:
                if oracle(node): node.amplitude *= -1
            avg_amp = sum(n.amplitude for n in nodes) / N
            for node in nodes:
                node.amplitude = 2 * avg_amp - node.amplitude
        self._stats["grover_calls"] += 1
        return nodes

    def interference_fusion(self, state_a: list[QuantumNode], state_b: list[QuantumNode]) -> list[QuantumNode]:
        """Fuse two memory states using constructive/destructive interference."""
        node_map: dict[str, QuantumNode] = {n.id: n for n in state_a}
        for node in state_b:
            if node.id in node_map:
                existing = node_map[node.id]
                r1, i1 = existing.amplitude * math.cos(existing.phase), existing.amplitude * math.sin(existing.phase)
                r2, i2 = node.amplitude * math.cos(node.phase), node.amplitude * math.sin(node.phase)
                r_new, i_new = r1 + r2, i1 + i2
                existing.amplitude, existing.phase = math.sqrt(r_new**2 + i_new**2), math.atan2(i_new, r_new)
            else:
                node_map[node.id] = node
        self._stats["superposition_fusions"] += 1
        return sorted(node_map.values(), key=lambda x: x.amplitude**2, reverse=True)

    def walk_superposition(self, seed_nodes: list[QuantumNode], get_neighbors_func: Callable[[str], list[dict[str, Any]]], hops: int = 2) -> list[QuantumNode]:
        """Perform a walk where the frontier is in a 'superposition' of states."""
        current_state = seed_nodes
        for _ in range(hops):
            next_state_map: dict[str, QuantumNode] = {}
            for node in current_state:
                neighbors = get_neighbors_func(node.id)
                if not neighbors: continue
                total_strength = sum(n.get("strength", 0.1) for n in neighbors)
                if total_strength == 0: continue
                for n in neighbors:
                    target_id = n["target_id"]
                    dist_amp = node.amplitude * math.sqrt(n.get("strength", 0.1) / total_strength)
                    if target_id in next_state_map: next_state_map[target_id].amplitude += dist_amp
                    else: next_state_map[target_id] = QuantumNode(id=target_id, amplitude=dist_amp)
            current_state = list(next_state_map.values())
            total_prob = sum(node_prob.amplitude**2 for node_prob in current_state)
            if total_prob > 0:
                norm = math.sqrt(total_prob)
                for node_obj in current_state: node_obj.amplitude /= norm
        return sorted(current_state, key=lambda x: x.amplitude**2, reverse=True)

# --- ADAPTER ---

class QuantumGraphAdapter:
    """Adapter that enhances classical graph walking with quantum-inspired algorithms."""

    def __init__(self, classical_walker: Any = None):
        self._classical = classical_walker
        self._quantum = QuantumGraphEngine(walker_sigma=2.0)
        self._config = QuantumWalkConfig()

    def quantum_enhanced_walk(self, seed_ids: list[str], hops: int = 2, top_k: int = 5, query_embedding: list[float] | None = None, oracle_func: Callable[[str], bool] | None = None, get_neighbors_func: Callable[[str], list[dict]] | None = None) -> Any:
        # Simplified bridge for consolidation
        if self._classical:
            return self._classical.walk(seed_ids=seed_ids, hops=hops, top_k=top_k, query_embedding=query_embedding)
        return None

# --- SINGLETONS ---
_quantum_engine: QuantumEngine | None = None

def get_quantum_engine() -> QuantumEngine:
    global _quantum_engine
    if _quantum_engine is None: _quantum_engine = QuantumEngine()
    return _quantum_engine
