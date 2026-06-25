"""Holographic Improvement Trajectory (Objective F).

Places each improvement hypothesis in 5D holographic space and tracks
velocity vectors over cycles to detect convergence and drift.

5D coordinates:
  x: temporal (cycle timestamp)
  y: semantic (hash of description projected to 1D)
  z: emotional valence (from associated memories)
  w: relational density (connections to other improvements)
  v: importance (predicted impact)

Convergence: multiple improvements heading toward the same region
Drift: importance (v) decreasing over cycles → deprioritize
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HolographicPosition:
    """5D position of an improvement hypothesis."""
    x: float = 0.0  # temporal
    y: float = 0.0  # semantic
    z: float = 0.0  # emotional valence
    w: float = 0.0  # relational density
    v: float = 0.0  # importance (predicted impact)

    def distance_to(self, other: HolographicPosition) -> float:
        """Euclidean distance in 5D space."""
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
            + (self.w - other.w) ** 2
            + (self.v - other.v) ** 2
        )

    def to_tuple(self) -> tuple[float, float, float, float, float]:
        return (self.x, self.y, self.z, self.w, self.v)


@dataclass
class VelocityVector:
    """Velocity of a hypothesis in 5D space."""
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    dw: float = 0.0
    dv: float = 0.0  # Importance velocity — negative = drifting

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.dx**2 + self.dy**2 + self.dz**2 + self.dw**2 + self.dv**2)

    @property
    def is_drifting(self) -> bool:
        """True if importance is decreasing."""
        return self.dv < 0.0


@dataclass
class TrajectoryPoint:
    """A single point in a hypothesis trajectory."""
    cycle: int
    timestamp: float
    position: HolographicPosition


@dataclass
class HypothesisTrajectory:
    """Full trajectory of a hypothesis across cycles."""
    hypothesis_id: str
    points: list[TrajectoryPoint] = field(default_factory=list)

    def add_point(self, cycle: int, position: HolographicPosition, timestamp: float | None = None) -> None:
        ts = timestamp or time.time()
        self.points.append(TrajectoryPoint(cycle=cycle, timestamp=ts, position=position))

    @property
    def latest(self) -> TrajectoryPoint | None:
        return self.points[-1] if self.points else None

    def velocity(self) -> VelocityVector | None:
        """Compute velocity from the last two trajectory points."""
        if len(self.points) < 2:
            return None
        p1 = self.points[-2].position
        p2 = self.points[-1].position
        dt = self.points[-1].timestamp - self.points[-2].timestamp
        if dt <= 0:
            dt = 1.0
        return VelocityVector(
            dx=(p2.x - p1.x) / dt,
            dy=(p2.y - p1.y) / dt,
            dz=(p2.z - p1.z) / dt,
            dw=(p2.w - p1.w) / dt,
            dv=(p2.v - p1.v) / dt,
        )


def semantic_hash_1d(text: str) -> float:
    """Project text to a 1D semantic coordinate in [0, 1).

    Uses a deterministic hash-based projection. Not as good as real
    embeddings but sufficient for spatial clustering.
    """
    h = hashlib.md5(text.encode()).hexdigest()
    # Take first 8 hex chars, convert to int, normalize to [0, 1)
    return int(h[:8], 16) / 0xFFFFFFFF


def compute_position(
    description: str,
    predicted_impact: float,
    cycle: int,
    emotional_valence: float = 0.0,
    relational_density: float = 0.0,
    timestamp: float | None = None,
) -> HolographicPosition:
    """Compute the 5D holographic position for a hypothesis.

    Args:
        description: Hypothesis description text.
        predicted_impact: Predicted impact (0-1) → v coordinate.
        cycle: Cycle number → x coordinate (temporal).
        emotional_valence: Emotional valence (-1 to 1) → z coordinate.
        relational_density: Number of related improvements → w coordinate.
        timestamp: Optional explicit timestamp.

    Returns:
        HolographicPosition with 5D coordinates.
    """
    return HolographicPosition(
        x=float(cycle),
        y=semantic_hash_1d(description),
        z=max(-1.0, min(1.0, emotional_valence)),
        w=float(relational_density),
        v=max(0.0, min(1.0, predicted_impact)),
    )


class TrajectoryTracker:
    """Tracks holographic trajectories for all hypotheses."""

    def __init__(self) -> None:
        self._trajectories: dict[str, HypothesisTrajectory] = {}

    def record(
        self,
        hypothesis_id: str,
        description: str,
        predicted_impact: float,
        cycle: int,
        emotional_valence: float = 0.0,
        relational_density: float = 0.0,
    ) -> HolographicPosition:
        """Record a new position for a hypothesis.

        Returns the computed position.
        """
        pos = compute_position(
            description=description,
            predicted_impact=predicted_impact,
            cycle=cycle,
            emotional_valence=emotional_valence,
            relational_density=relational_density,
        )

        if hypothesis_id not in self._trajectories:
            self._trajectories[hypothesis_id] = HypothesisTrajectory(hypothesis_id=hypothesis_id)
        self._trajectories[hypothesis_id].add_point(cycle, pos)

        return pos

    def get_trajectory(self, hypothesis_id: str) -> HypothesisTrajectory | None:
        return self._trajectories.get(hypothesis_id)

    def get_velocity(self, hypothesis_id: str) -> VelocityVector | None:
        traj = self._trajectories.get(hypothesis_id)
        if traj is None:
            return None
        return traj.velocity()

    def detect_drifting(self) -> list[str]:
        """Find hypotheses whose importance is decreasing over time."""
        drifting = []
        for hid, traj in self._trajectories.items():
            vel = traj.velocity()
            if vel is not None and vel.is_drifting:
                drifting.append(hid)
        return drifting

    def detect_convergence(self, threshold: float = 0.3) -> list[list[str]]:
        """Detect groups of hypotheses converging on the same region.

        Groups hypotheses whose latest positions are within `threshold`
        distance of each other AND have similar velocity directions.

        Args:
            threshold: Maximum distance to be considered converging.

        Returns:
            List of convergence groups (each is a list of hypothesis IDs).
        """
        active = [(hid, traj) for hid, traj in self._trajectories.items() if traj.latest is not None]
        if len(active) < 2:
            return []

        # Cluster by spatial proximity
        groups: list[list[str]] = []
        assigned: set[str] = set()

        for i, (hid_a, traj_a) in enumerate(active):
            if hid_a in assigned:
                continue
            group = [hid_a]
            assigned.add(hid_a)
            pos_a = traj_a.latest.position  # type: ignore[union-attr]

            for j, (hid_b, traj_b) in enumerate(active):
                if hid_b in assigned:
                    continue
                pos_b = traj_b.latest.position  # type: ignore[union-attr]
                dist = pos_a.distance_to(pos_b)
                if dist < threshold:
                    # Check velocity alignment
                    vel_a = traj_a.velocity()
                    vel_b = traj_b.velocity()
                    if vel_a is not None and vel_b is not None:
                        # Dot product of velocity vectors (normalized)
                        dot = (
                            vel_a.dx * vel_b.dx + vel_a.dy * vel_b.dy
                            + vel_a.dz * vel_b.dz + vel_a.dw * vel_b.dw
                            + vel_a.dv * vel_b.dv
                        )
                        if dot > 0:  # Moving in similar direction
                            group.append(hid_b)
                            assigned.add(hid_b)
                    else:
                        group.append(hid_b)
                        assigned.add(hid_b)

            if len(group) > 1:
                groups.append(group)

        return groups

    def get_all_trajectories(self) -> dict[str, HypothesisTrajectory]:
        return dict(self._trajectories)

    def get_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        total = len(self._trajectories)
        with_velocity = sum(1 for t in self._trajectories.values() if len(t.points) >= 2)
        drifting = len(self.detect_drifting())
        converging = len(self.detect_convergence())
        return {
            "total_tracked": total,
            "with_velocity": with_velocity,
            "drifting_count": drifting,
            "convergence_groups": converging,
        }
