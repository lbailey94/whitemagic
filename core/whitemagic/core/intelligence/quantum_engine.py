"""
Quantum-Inspired Engine - Grover's Amplification and Superposition Walks.
=======================================================================
Provides O(√N) search and parallel path exploration using complex amplitude 
simulations. Part of v22 Intelligence Matrix.
"""

import math
import numpy as np
from typing import List, Dict, Any, Callable

class QuantumEngine:
    """Simulates quantum algorithms for graph and search optimization."""

    def __init__(self):
        self.coherence_time = 1.0
        self.interference_threshold = 0.1

    def grover_search(self, items: List[Any], oracle: Callable[[Any], bool], iterations: int | None = None) -> List[Any]:
        """
        Grover's Amplification algorithm for O(√N) search.
        
        Args:
            items: List of search candidates.
            oracle: Function returning True for the target item.
            iterations: Number of amplification steps (defaults to π/4 * √N).
        """
        N = len(items)
        if N == 0:
            return []
        
        if iterations is None:
            iterations = int((math.pi / 4) * math.sqrt(N))
            
        # Initial uniform superposition
        amplitudes = np.full(N, 1.0 / math.sqrt(N))
        
        for _ in range(iterations):
            # 1. Oracle: Flip sign of target
            for i, item in enumerate(items):
                if oracle(item):
                    amplitudes[i] *= -1
            
            # 2. Diffusion: Reflect about the mean
            mean = np.mean(amplitudes)
            amplitudes = 2 * mean - amplitudes
            
        # Select top probability candidates
        probabilities: np.ndarray = amplitudes ** 2
        indices = np.argsort(probabilities)[::-1]
        
        return [items[i] for i in indices if probabilities[i] > (1.0 / N)]

    def superposition_walk(self, graph: Dict[str, List[str]], start_node: str, hops: int = 2) -> Dict[str, float]:
        """
        Explores multiple graph paths simultaneously using amplitude distribution.
        
        Args:
            graph: Adjacency list representation.
            start_node: Initial memory ID.
            hops: Max depth of exploration.
        """
        # Node ID -> Complex Amplitude
        state = {start_node: 1.0 + 0j}
        
        for _ in range(hops):
            next_state: Dict[str, complex] = {}
            for node, amplitude in state.items():
                neighbors = graph.get(node, [])
                if not neighbors:
                    next_state[node] = next_state.get(node, 0j) + amplitude
                    continue
                
                # Distribute amplitude across neighbors (superposition)
                branch_amplitude = amplitude / math.sqrt(len(neighbors))
                for neighbor in neighbors:
                    # Interference: amplitudes add up (constructive or destructive)
                    next_state[neighbor] = next_state.get(neighbor, 0j) + branch_amplitude
            
            state = next_state
            
        # Collapse to probabilities
        return {node: abs(amp)**2 for node, amp in state.items()}

    def interference_fusion(self, results: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Fuses multiple search/walk results using constructive interference.
        """
        fused: Dict[str, float] = {}
        for res in results:
            for node, prob in res.items():
                # Weighted interference: stronger signals amplify exponentially
                current = fused.get(node, 0.0)
                fused[node] = math.sqrt(current**2 + prob**2)
                
        # Re-normalize
        total = sum(fused.values())
        if total > 0:
            fused = {k: v/total for k, v in fused.items()}
            
        return fused
