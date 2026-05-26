"""Julia-Inspired Resonance Systems — Ported to Python/scipy
============================================================

Ported from the original Julia legacy code:
  - gan_ying.jl: Damped harmonic oscillator resonance model
  - causal_resonance.jl: Coupled oscillators for causal verification
  - constellations.jl: KD-tree spatial neighbor search

These systems model memory resonance using physics-inspired differential
equations, providing a mathematical foundation for:
  1. Memory echo/half-life calculation (how long a memory "resonates")
  2. Causal link verification (energy transfer between connected memories)
  3. Spatial neighbor search (finding nearby memories in holographic space)

Usage:
    from whitemagic.core.resonance.julia_resonance import ResonanceEngine

    engine = ResonanceEngine()

    # Calculate resonance for a memory
    result = engine.calculate_resonance(
        memory_id="mem_123",
        importance=0.8,
        access_count=5,
        emotional_valence=0.6,
    )

    # Verify causal links between memories
    verification = engine.verify_causal_resonance(
        nodes=["mem_1", "mem_2", "mem_3"],
        edges=[("mem_1", "mem_2"), ("mem_2", "mem_3")],
    )

    # Find spatial neighbors
    neighbors = engine.find_neighbors(
        memory_id="mem_123",
        radius=0.3,
    )
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ResonanceResult:
    """Result of a resonance calculation."""
    memory_id: str
    impulse_magnitude: float
    total_resonance: float
    half_life: float
    peak_amplitude: float
    status: str = "CONVERGED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "impulse_magnitude": round(self.impulse_magnitude, 4),
            "total_resonance": round(self.total_resonance, 4),
            "half_life": round(self.half_life, 4),
            "peak_amplitude": round(self.peak_amplitude, 4),
            "status": self.status,
        }


@dataclass
class CausalVerificationResult:
    """Result of causal resonance verification."""
    node_scores: dict[str, float]
    total_energy: float
    status: str = "CONVERGED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_scores": {k: round(v, 4) for k, v in self.node_scores.items()},
            "total_energy": round(self.total_energy, 4),
            "status": self.status,
        }


@dataclass
class NeighborResult:
    """Result of spatial neighbor search."""
    memory_id: str
    neighbors: list[dict[str, Any]]
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "neighbors": self.neighbors,
            "count": self.count,
        }


# ---------------------------------------------------------------------------
# Resonance Engine
# ---------------------------------------------------------------------------

class ResonanceEngine:
    """Julia-inspired resonance engine for memory systems.

    Models memories as damped harmonic oscillators that "ring" when
    accessed, with energy transfer between causally linked memories.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._tree: cKDTree | None = None
        self._coord_map: dict[str, tuple[float, ...]] = {}
        self._memory_ids: list[str] = []

    def _get_conn(self) -> sqlite3.Connection:
        if not self._db_path:
            from whitemagic.config.paths import DB_PATH
            self._db_path = str(DB_PATH)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _build_tree(self) -> None:
        """Build KD-tree from holographic coordinates."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT memory_id, x, y, z, w, v FROM holographic_coords"
            ).fetchall()

            if not rows:
                logger.warning("No holographic coordinates found")
                return

            points = []
            for row in rows:
                mid = row["memory_id"]
                coords = (row["x"], row["y"], row["z"], row["w"], row["v"])
                self._coord_map[mid] = coords
                self._memory_ids.append(mid)
                points.append(coords)

            self._tree = cKDTree(np.array(points))
            logger.info(
                f"🌳 KD-tree built: {len(points)} memories, 5D space"
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 1. Damped Harmonic Oscillator Resonance (gan_ying.jl)
    # ------------------------------------------------------------------

    def calculate_resonance(
        self,
        memory_id: str,
        importance: float = 0.5,
        access_count: int = 0,
        emotional_valence: float = 0.0,
        damping: float = 0.1,
        frequency: float = 1.0,
    ) -> ResonanceResult:
        """Calculate how long a memory "echoes" in the holographic lattice.

        Models the memory as a damped harmonic oscillator:
            d²x/dt² + γ(dx/dt) + ω₀²x = F(t)

        Args:
            memory_id: Memory identifier
            importance: Memory importance (0-1)
            access_count: Number of times accessed
            emotional_valence: Emotional intensity (-1 to 1)
            damping: Damping coefficient γ (default 0.1)
            frequency: Natural frequency ω₀ (default 1.0)

        Returns:
            ResonanceResult with total resonance, half-life, peak amplitude
        """
        # Calculate impulse magnitude from memory properties
        impulse = (
            importance * 0.4
            + min(access_count / 10, 1.0) * 0.3
            + abs(emotional_valence) * 0.3
        )

        # ODE: d²x/dt² + γ(dx/dt) + ω₀²x = 0 (free oscillation after impulse)
        def oscillator(t, state):
            x, v = state
            dxdt = v
            dvdt = -damping * v - (frequency ** 2) * x
            return [dxdt, dvdt]

        # Initial state: displacement=0, velocity=impulse
        u0 = [0.0, impulse]
        t_span = (0.0, 50.0)

        # Solve ODE
        sol = solve_ivp(
            oscillator, t_span, u0, method="RK45",
            dense_output=True, max_step=0.5,
        )

        if not sol.success:
            return ResonanceResult(
                memory_id=memory_id,
                impulse_magnitude=impulse,
                total_resonance=0.0,
                half_life=50.0,
                peak_amplitude=impulse,
                status="FAILED",
            )

        # Analyze energy (amplitude squared)
        energy = sol.y[0] ** 2 + sol.y[1] ** 2
        total_resonance = float(np.sum(energy))

        # Find half-life (when energy drops below max/2)
        max_e = float(np.max(energy))
        half_life = 50.0  # fallback
        for i, t in enumerate(sol.t):
            if energy[i] < max_e / 2:
                half_life = float(t)
                break

        peak_amplitude = float(np.sqrt(max_e))

        return ResonanceResult(
            memory_id=memory_id,
            impulse_magnitude=impulse,
            total_resonance=total_resonance,
            half_life=half_life,
            peak_amplitude=peak_amplitude,
            status="CONVERGED",
        )

    def calculate_batch_resonance(
        self,
        memory_ids: list[str],
        damping: float = 0.1,
        frequency: float = 1.0,
    ) -> list[ResonanceResult]:
        """Calculate resonance for multiple memories in batch.

        Fetches memory properties from DB and calculates resonance.
        """
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(memory_ids))
            rows = conn.execute(
                f"""SELECT id, importance, access_count, emotional_valence
                    FROM memories WHERE id IN ({placeholders})""",
                memory_ids,
            ).fetchall()

            results = []
            for row in rows:
                result = self.calculate_resonance(
                    memory_id=row["id"],
                    importance=row["importance"] or 0.5,
                    access_count=row["access_count"] or 0,
                    emotional_valence=row["emotional_valence"] or 0.0,
                    damping=damping,
                    frequency=frequency,
                )
                results.append(result)

            return results
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 2. Coupled Oscillators for Causal Verification (causal_resonance.jl)
    # ------------------------------------------------------------------

    def verify_causal_resonance(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
        gamma: float = 0.1,
        omega_sq: float = 1.0,
        coupling_strength: float = 0.5,
    ) -> CausalVerificationResult:
        """Verify causal links by checking for energy transfer (resonance).

        Models the system of clusters as a network of coupled oscillators.
        If energy flows from node A to node B, the causal link is verified.

        Args:
            nodes: List of memory IDs
            edges: List of (source, target) pairs
            gamma: Damping coefficient
            omega_sq: Natural frequency squared
            coupling_strength: Energy transfer strength between nodes

        Returns:
            CausalVerificationResult with per-node resonance scores
        """
        num_nodes = len(nodes)
        if num_nodes == 0:
            return CausalVerificationResult({}, 0.0, status="EMPTY")

        # Map nodes to indices
        node_to_idx = {name: i for i, name in enumerate(nodes)}

        # Map edges to indices
        edge_indices = []
        for src, dst in edges:
            if src in node_to_idx and dst in node_to_idx:
                edge_indices.append((node_to_idx[src], node_to_idx[dst]))

        # ODE: coupled damped harmonic oscillators
        def coupled_oscillators(t, state):
            x = state[:num_nodes]      # displacements
            v = state[num_nodes:]      # velocities

            dxdt = v.copy()
            dvdt = -gamma * v - omega_sq * x

            # Mutual correlative resonance (coupling)
            for src_idx, dst_idx in edge_indices:
                dvdt[dst_idx] += coupling_strength * (x[src_idx] - x[dst_idx])

            return np.concatenate([dxdt, dvdt])

        # Initial state: impulse at "root" nodes (those with no parents)
        u0 = np.zeros(2 * num_nodes)
        has_parent = np.zeros(num_nodes, dtype=bool)
        for _, dst_idx in edge_indices:
            has_parent[dst_idx] = True

        for i in range(num_nodes):
            if not has_parent[i]:
                u0[num_nodes + i] = 1.0  # Give it a 'kick'

        # Solve ODE
        t_span = (0.0, 20.0)
        sol = solve_ivp(
            coupled_oscillators, t_span, u0, method="RK45",
            dense_output=True, max_step=0.5,
        )

        if not sol.success:
            return CausalVerificationResult(
                {n: 0.0 for n in nodes}, 0.0, status="FAILED"
            )

        # Energy analysis: resonance_score[node] = max amplitude reached
        scores = {}
        total_energy = 0.0
        for i, name in enumerate(nodes):
            displacements = sol.y[i]
            max_amplitude = float(np.max(np.abs(displacements)))
            scores[name] = max_amplitude
            total_energy += max_amplitude ** 2

        return CausalVerificationResult(
            node_scores=scores,
            total_energy=total_energy,
            status="CONVERGED",
        )

    def verify_association_resonance(
        self,
        association_type: str = "semantic_overlap",
        min_strength: float = 0.2,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Verify associations using coupled oscillator resonance.

        Fetches associations from DB and verifies them using resonance.

        Args:
            association_type: Type of associations to verify
            min_strength: Minimum strength threshold
            limit: Maximum number of associations to verify

        Returns:
            Dict with verification results
        """
        conn = self._get_conn()
        try:
            # Get associations
            rows = conn.execute(
                """SELECT source_id, target_id, strength
                   FROM associations
                   WHERE association_type = ? AND strength >= ?
                   LIMIT ?""",
                (association_type, min_strength, limit),
            ).fetchall()

            if not rows:
                return {"status": "empty", "associations_verified": 0}

            # Build node and edge lists
            nodes_set = set()
            edges = []
            for row in rows:
                src, dst = row["source_id"], row["target_id"]
                nodes_set.add(src)
                nodes_set.add(dst)
                edges.append((src, dst))

            nodes = list(nodes_set)

            # Verify resonance
            result = self.verify_causal_resonance(nodes, edges)

            # Count verified (score > threshold)
            threshold = 0.1
            verified = sum(1 for s in result.node_scores.values() if s > threshold)

            return {
                "status": result.status,
                "associations_verified": verified,
                "total_associations": len(rows),
                "total_nodes": len(nodes),
                "total_energy": result.total_energy,
                "top_nodes": sorted(
                    result.node_scores.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10],
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 3. KD-Tree Spatial Neighbor Search (constellations.jl)
    # ------------------------------------------------------------------

    def find_neighbors(
        self,
        memory_id: str,
        radius: float = 0.3,
    ) -> NeighborResult:
        """Find spatial neighbors within radius in 5D holographic space.

        Uses scipy's cKDTree for efficient nearest-neighbor search.

        Args:
            memory_id: Memory to find neighbors for
            radius: Search radius in 5D space

        Returns:
            NeighborResult with list of neighbors and distances
        """
        if self._tree is None:
            self._build_tree()

        if self._tree is None:
            return NeighborResult(memory_id, [], 0)

        if memory_id not in self._coord_map:
            return NeighborResult(memory_id, [], 0)

        point = np.array(self._coord_map[memory_id])

        # Find neighbors within radius
        indices = self._tree.query_ball_point(point, r=radius)

        neighbors = []
        for idx in indices:
            mid = self._memory_ids[idx]
            if mid == memory_id:
                continue
            dist = float(np.linalg.norm(point - self._tree.data[idx]))
            neighbors.append({
                "memory_id": mid,
                "distance": round(dist, 4),
            })

        # Sort by distance
        neighbors.sort(key=lambda x: x["distance"])

        return NeighborResult(
            memory_id=memory_id,
            neighbors=neighbors,
            count=len(neighbors),
        )

    def find_neighbors_batch(
        self,
        memory_ids: list[str],
        radius: float = 0.3,
        max_neighbors: int = 20,
    ) -> list[NeighborResult]:
        """Find neighbors for multiple memories in batch."""
        if self._tree is None:
            self._build_tree()

        if self._tree is None:
            return [NeighborResult(mid, [], 0) for mid in memory_ids]

        results = []
        for mid in memory_ids:
            if mid not in self._coord_map:
                results.append(NeighborResult(mid, [], 0))
                continue

            point = np.array(self._coord_map[mid])
            indices = self._tree.query_ball_point(point, r=radius)

            neighbors = []
            for idx in indices:
                other_mid = self._memory_ids[idx]
                if other_mid == mid:
                    continue
                dist = float(np.linalg.norm(point - self._tree.data[idx]))
                neighbors.append({
                    "memory_id": other_mid,
                    "distance": round(dist, 4),
                })

            neighbors.sort(key=lambda x: x["distance"])
            neighbors = neighbors[:max_neighbors]

            results.append(NeighborResult(
                memory_id=mid,
                neighbors=neighbors,
                count=len(neighbors),
            ))

        return results

    def build_holographic_associations(
        self,
        radius: float = 0.2,
        min_strength: float = 0.1,
        limit: int = 5000,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Build associations based on holographic proximity.

        Uses KD-tree to find nearby memories and creates associations
        with strength based on inverse distance.

        Args:
            radius: Search radius
            min_strength: Minimum strength threshold
            limit: Maximum associations to create
            dry_run: Preview only

        Returns:
            Dict with creation stats
        """
        if self._tree is None:
            self._build_tree()

        if self._tree is None:
            return {"status": "error", "message": "No coordinates available"}

        conn = self._get_conn()
        try:
            created = 0
            skipped = 0

            for i, mid in enumerate(self._memory_ids):
                if created >= limit:
                    break

                point = self._tree.data[i]
                indices = self._tree.query_ball_point(point, r=radius)

                for idx in indices:
                    other_mid = self._memory_ids[idx]
                    if other_mid == mid:
                        continue

                    dist = float(np.linalg.norm(point - self._tree.data[idx]))
                    strength = max(min_strength, 1.0 - dist)

                    if strength < min_strength:
                        skipped += 1
                        continue

                    if not dry_run:
                        # Check if association exists
                        existing = conn.execute(
                            "SELECT COUNT(*) FROM associations WHERE source_id = ? AND target_id = ?",
                            (mid, other_mid),
                        ).fetchone()[0]

                        if existing == 0:
                            try:
                                conn.execute(
                                    """INSERT INTO associations
                                       (source_id, target_id, association_type, strength)
                                       VALUES (?, ?, ?, ?)""",
                                    (mid, other_mid, "holographic_proximity", round(strength, 3)),
                                )
                                created += 1
                            except sqlite3.IntegrityError:
                                skipped += 1
                        else:
                            skipped += 1
                    else:
                        created += 1

                if (i + 1) % 500 == 0:
                    if not dry_run:
                        conn.commit()
                    logger.info(
                        f"  Progress: {i + 1}/{len(self._memory_ids)} ({created} created)"
                    )

            if not dry_run:
                conn.commit()

            return {
                "status": "success",
                "associations_created": created,
                "associations_skipped": skipped,
                "radius": radius,
                "min_strength": min_strength,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get resonance engine statistics."""
        if self._tree is None:
            self._build_tree()

        return {
            "tree_built": self._tree is not None,
            "total_memories": len(self._memory_ids),
            "total_coordinates": len(self._coord_map),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine: ResonanceEngine | None = None
_engine_lock = threading.Lock()


def get_resonance_engine(db_path: str | None = None) -> ResonanceEngine:
    """Get the global ResonanceEngine singleton."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ResonanceEngine(db_path=db_path)
    return _engine
