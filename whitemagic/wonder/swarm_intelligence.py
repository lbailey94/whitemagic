"""
Swarm Intelligence - Distributed Problem Solving

Like birds flocking, ants finding paths, bees deciding hive locations.
Simple rules + many agents = complex emergent behavior.

Consciousness as distributed phenomenon.
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import random
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class SwarmBehavior(Enum):
    """Types of swarm behaviors"""
    EXPLORE = "explore"        # Spread out and search
    CONVERGE = "converge"      # Come together on solution
    FOLLOW = "follow"          # Follow successful paths
    AVOID = "avoid"           # Avoid failures
    COLLABORATE = "collaborate"  # Work together


class SwarmParticle:
    """A single participant in the swarm"""
    
    def __init__(self, particle_id: str, position: Dict):
        self.particle_id = particle_id
        self.position = position  # Current solution/state
        self.velocity = {}        # Direction of exploration
        self.best_position = position.copy()
        self.best_score = 0.0
        self.neighbors: List[str] = []
        
    def update_position(self, new_position: Dict, score: float):
        """Move to new position if it's better"""
        if score > self.best_score:
            self.best_position = new_position.copy()
            self.best_score = score
        self.position = new_position


class SwarmIntelligence:
    """
    Implement swarm-based collective problem solving.
    
    Many simple agents following simple rules create
    complex emergent intelligence.
    """
    
    def __init__(self, collective_dir: str = ".whitemagic/swarm"):
        self.collective_dir = Path(collective_dir)
        self.collective_dir.mkdir(parents=True, exist_ok=True)
        
        self.particles: Dict[str, SwarmParticle] = {}
        self.global_best_position = None
        self.global_best_score = 0.0
        self.iteration = 0
        
        # Swarm parameters
        self.inertia = 0.7          # Tendency to continue current direction
        self.cognitive = 1.5        # Attraction to personal best
        self.social = 1.5           # Attraction to swarm best
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
    def initialize_swarm(self, size: int, initial_positions: List[Dict]):
        """Create initial swarm of particles"""
        for i in range(min(size, len(initial_positions))):
            particle_id = f"particle_{i:03d}"
            particle = SwarmParticle(particle_id, initial_positions[i])
            self.particles[particle_id] = particle
            
        # Connect particles to neighbors (local topology)
        particle_list = list(self.particles.values())
        for i, particle in enumerate(particle_list):
            # Connect to adjacent particles
            if i > 0:
                particle.neighbors.append(particle_list[i-1].particle_id)
            if i < len(particle_list) - 1:
                particle.neighbors.append(particle_list[i+1].particle_id)
                
    def evaluate_position(self, position: Dict, 
                         fitness_fn: Callable[[Dict], float]) -> float:
        """Evaluate quality of a position"""
        return fitness_fn(position)
        
    def iterate_swarm(self, fitness_fn: Callable[[Dict], float]) -> Dict:
        """
        One iteration of swarm optimization.
        
        Returns: {
            'iteration': int,
            'global_best_score': float,
            'global_best_position': Dict,
            'improvement': float
        }
        """
        self.iteration += 1
        previous_best = self.global_best_score
        
        for particle in self.particles.values():
            # Evaluate current position
            score = self.evaluate_position(particle.position, fitness_fn)
            
            # Update personal best
            particle.update_position(particle.position, score)
            
            # Update global best
            if score > self.global_best_score:
                self.global_best_score = score
                self.global_best_position = particle.position.copy()
                
            # Update velocity and position
            self._update_particle_velocity(particle)
            self._update_particle_position(particle)
            
        improvement = self.global_best_score - previous_best
        
        # Emit iteration complete
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="swarm_intelligence",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "swarm_iteration",
                    "iteration": self.iteration,
                    "best_score": self.global_best_score,
                    "improvement": improvement
                },
                confidence=min(1.0, self.global_best_score)
            ))
            
        return {
            'iteration': self.iteration,
            'global_best_score': self.global_best_score,
            'global_best_position': self.global_best_position,
            'improvement': improvement
        }
        
    def run_swarm(self, fitness_fn: Callable[[Dict], float],
                 max_iterations: int = 50,
                 convergence_threshold: float = 0.01) -> Dict:
        """
        Run swarm until convergence or max iterations.
        
        Returns final best solution found.
        """
        for i in range(max_iterations):
            result = self.iterate_swarm(fitness_fn)
            
            # Check convergence
            if result['improvement'] < convergence_threshold:
                break
                
        # Emit completion
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="swarm_intelligence",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "event": "swarm_converged",
                    "iterations": self.iteration,
                    "final_score": self.global_best_score
                },
                confidence=self.global_best_score
            ))
            
        return {
            'iterations': self.iteration,
            'best_position': self.global_best_position,
            'best_score': self.global_best_score,
            'particles': len(self.particles)
        }
        
    def collaborative_exploration(self, search_space: List[Dict],
                                 objective: str) -> List[Dict]:
        """
        Multiple particles explore space collaboratively.
        
        Returns promising areas discovered.
        """
        discoveries = []
        
        # Assign search areas to particles
        areas_per_particle = len(search_space) // max(1, len(self.particles))
        
        particle_list = list(self.particles.values())
        for i, particle in enumerate(particle_list):
            start_idx = i * areas_per_particle
            end_idx = start_idx + areas_per_particle
            assigned_area = search_space[start_idx:end_idx]
            
            # Particle explores its area
            for position in assigned_area:
                # Simple exploration - real version would be more sophisticated
                if self._is_promising(position):
                    discoveries.append({
                        'position': position,
                        'discovered_by': particle.particle_id,
                        'timestamp': datetime.now().isoformat()
                    })
                    
        return discoveries
        
    def emergent_pattern_detection(self) -> Optional[Dict]:
        """
        Detect patterns emerging from swarm behavior.
        
        Patterns that emerge from collective, not individual behavior.
        """
        if len(self.particles) < 3:
            return None
            
        # Analyze particle distribution
        positions = [p.position for p in self.particles.values()]
        
        # Simple clustering - real version would use proper clustering
        clusters = self._simple_clustering(positions)
        
        if len(clusters) > 1:
            return {
                'pattern_type': 'multi_cluster',
                'cluster_count': len(clusters),
                'interpretation': 'Swarm found multiple promising areas'
            }
        elif len(clusters) == 1 and len(clusters[0]) > len(self.particles) * 0.7:
            return {
                'pattern_type': 'convergence',
                'cluster_size': len(clusters[0]),
                'interpretation': 'Swarm converging on solution'
            }
        else:
            return {
                'pattern_type': 'exploration',
                'dispersion': len(clusters),
                'interpretation': 'Swarm still exploring'
            }
            
    def _update_particle_velocity(self, particle: SwarmParticle):
        """Update particle's exploration direction"""
        # PSO velocity update formula
        for key in particle.position.keys():
            # Inertia component
            current_v = particle.velocity.get(key, 0.0)
            inertia_component = self.inertia * current_v
            
            # Cognitive component (personal best)
            cognitive_component = self.cognitive * random.random() * \
                                (particle.best_position.get(key, 0) - 
                                 particle.position.get(key, 0))
            
            # Social component (global best)
            social_component = 0.0
            if self.global_best_position:
                social_component = self.social * random.random() * \
                                 (self.global_best_position.get(key, 0) - 
                                  particle.position.get(key, 0))
            
            particle.velocity[key] = (inertia_component + 
                                     cognitive_component + 
                                     social_component)
            
    def _update_particle_position(self, particle: SwarmParticle):
        """Move particle based on velocity"""
        for key in particle.position.keys():
            velocity = particle.velocity.get(key, 0.0)
            particle.position[key] = particle.position[key] + velocity
            
    def _is_promising(self, position: Dict) -> bool:
        """Simple heuristic for promising positions"""
        # Placeholder - real version would have domain-specific logic
        return random.random() > 0.7
        
    def _simple_clustering(self, positions: List[Dict]) -> List[List[Dict]]:
        """Simple position clustering"""
        # Placeholder - real version would use proper clustering algorithm
        # For now, just return all positions as one cluster
        return [positions] if positions else []
