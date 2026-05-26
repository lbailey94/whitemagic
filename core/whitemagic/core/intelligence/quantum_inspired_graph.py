"""Quantum-Inspired Graph Engine — Grover-enhanced traversal and Superposition scoring.

This module implements Option A of the V21.1 optimization plan, using quantum-inspired
algorithms to accelerate graph operations.
"""

import math
import logging
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class QuantumNode:
    """A node representation with amplitude for superposition walks."""
    id: str
    amplitude: float = 0.0
    phase: float = 0.0  # radians
    metadata: Dict[str, Any] = field(default_factory=dict)

class QuantumGraphEngine:
    """Quantum-inspired graph traversal and optimization engine."""
    
    def __init__(self, walker_sigma: float = 2.0):
        self._sigma = walker_sigma
        self._stats = {"grover_walks": 0, "superposition_fusions": 0}

    def grover_amplification(
        self, 
        nodes: List[QuantumNode], 
        oracle: Callable[[QuantumNode], bool], 
        iterations: int = 1
    ) -> List[QuantumNode]:
        """Apply Grover-inspired amplitude amplification to a set of nodes."""
        n = len(nodes)
        if n == 0:
            return []
        
        # Initial state: extract amplitudes
        amplitudes = np.array([node.amplitude for node in nodes])
        
        # Normalize if zero
        if np.sum(np.abs(amplitudes)) == 0:
            amplitudes = np.full(n, 1.0 / math.sqrt(n))
        
        for _ in range(iterations):
            # 1. Oracle: Flip phase of matching nodes
            for i in range(n):
                if oracle(nodes[i]):
                    amplitudes[i] *= -1.0
            
            # 2. Diffusion (Inversion about the mean)
            mean = np.mean(amplitudes)
            amplitudes = 2 * mean - amplitudes
            
        # Update nodes
        for i in range(n):
            nodes[i].amplitude = amplitudes[i]
            
        self._stats["grover_walks"] += 1
        return nodes

    def interference_fusion(self, state_a: List[QuantumNode], state_b: List[QuantumNode]) -> List[QuantumNode]:
        """Fuse two memory states using constructive/destructive interference."""
        node_map: Dict[str, QuantumNode] = {}
        
        for node in state_a:
            node_map[node.id] = QuantumNode(
                id=node.id, 
                amplitude=node.amplitude, 
                phase=node.phase,
                metadata=node.metadata
            )
            
        for node in state_b:
            if node.id in node_map:
                # Interference: sum of complex amplitudes
                # A * exp(i*p1) + B * exp(i*p2)
                existing = node_map[node.id]
                
                # Real and imaginary components
                r1 = existing.amplitude * math.cos(existing.phase)
                i1 = existing.amplitude * math.sin(existing.phase)
                r2 = node.amplitude * math.cos(node.phase)
                i2 = node.amplitude * math.sin(node.phase)
                
                r_new = r1 + r2
                i_new = i1 + i2
                
                existing.amplitude = math.sqrt(r_new**2 + i_new**2)
                existing.phase = math.atan2(i_new, r_new)
            else:
                node_map[node.id] = QuantumNode(
                    id=node.id, 
                    amplitude=node.amplitude, 
                    phase=node.phase,
                    metadata=node.metadata
                )
        
        self._stats["superposition_fusions"] += 1
        return sorted(node_map.values(), key=lambda x: x.amplitude**2, reverse=True)

    def walk_superposition(
        self, 
        seed_nodes: List[QuantumNode], 
        get_neighbors_func: Callable[[str], List[Dict[str, Any]]],
        hops: int = 2
    ) -> List[QuantumNode]:
        """Perform a walk where the frontier is in a 'superposition' of states."""
        current_state = seed_nodes
        
        for _ in range(hops):
            next_state_map: Dict[str, QuantumNode] = {}
            
            for node in current_state:
                neighbors = get_neighbors_func(node.id)
                if not neighbors:
                    continue
                
                # Distribute amplitude among neighbors
                # Amplitude is shared proportionally to edge strength (sqrt of probability)
                total_strength = sum(n.get("strength", 0.1) for n in neighbors)
                if total_strength == 0:
                    continue
                
                for n in neighbors:
                    target_id = n["target_id"]
                    strength = n.get("strength", 0.1)
                    # Amplitude distribution (preserving norm)
                    dist_amp = node.amplitude * math.sqrt(strength / total_strength)
                    
                    if target_id in next_state_map:
                        next_state_map[target_id].amplitude += dist_amp
                    else:
                        next_state_map[target_id] = QuantumNode(id=target_id, amplitude=dist_amp)
            
            current_state = list(next_state_map.values())
            # Normalize state
            total_prob = sum(node_prob.amplitude**2 for node_prob in current_state)
            if total_prob > 0:
                norm = math.sqrt(total_prob)
                for node_obj in current_state:
                    node_obj.amplitude /= norm
                    
        return sorted(current_state, key=lambda x: x.amplitude**2, reverse=True)

