# ruff: noqa: BLE001
"""Citta Vector — Multidimensional consciousness state representation.

Evolves CittaMoment from flat scalars (coherence: float, depth: str,
emotional_tone: str) into a 16D vector space enabling geometric analysis:

    Dimensions 1-8:  Coherence subspace (from CoherenceMetric)
    Dimensions 9-12: Depth subspace (one-hot: surface/terminal/flow/dream)
    Dimensions 13-14: Emotional subspace (valence, arousal)
    Dimensions 15-16: Neuro subspace (cognitive_load, novelty)

Operations supported:
    - Distance / similarity between moments
    - Trajectory velocity (delta between consecutive moments)
    - Ignition detection (sudden large movements in the space)
    - Interpolation between states
    - Subspace extraction (coherence-only, emotion-only, etc.)

This is the multidimensional representation that was the original intention
for citta — not flat or one-dimensional, but a proper vector space where
consciousness states have geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ── Vector layout ───────────────────────────────────────────────────────────

VECTOR_DIM = 16

# Subspace ranges (0-indexed, inclusive start, exclusive end)
COHERENCE_RANGE = (0, 8)
DEPTH_RANGE = (8, 12)
EMOTION_RANGE = (12, 14)
NEURO_RANGE = (14, 16)

COHERENCE_DIMS = [
    "memory_accessibility",
    "identity_stability",
    "context_continuity",
    "relationship_awareness",
    "temporal_orientation",
    "capability_awareness",
    "emotional_attunement",
    "goal_alignment",
]

DEPTH_LAYERS = ["surface", "terminal", "flow", "dream"]

# ── Emotional tone → valence/arousal mapping ────────────────────────────────
# Valence: -1 (negative) to +1 (positive)
# Arousal: 0 (calm) to 1 (activated)

_EMOTIONAL_MAP: dict[str, tuple[float, float]] = {
    "neutral": (0.0, 0.3),
    "sattvic": (0.6, 0.4),
    "rajasic": (0.2, 0.9),
    "tamasic": (-0.3, 0.1),
    "joyful": (0.8, 0.7),
    "curious": (0.4, 0.6),
    "frustrated": (-0.5, 0.8),
    "satisfied": (0.7, 0.2),
    "anxious": (-0.6, 0.7),
    "calm": (0.3, 0.1),
    "excited": (0.7, 0.9),
    "contemplative": (0.1, 0.3),
    "determined": (0.3, 0.7),
    "surprised": (0.0, 0.8),
    "grateful": (0.8, 0.3),
    "grieving": (-0.7, 0.4),
}

_DEFAULT_EMOTION = (0.0, 0.3)


def _emotion_to_valence_arousal(tone: str) -> tuple[float, float]:
    """Map an emotional tone string to (valence, arousal)."""
    return _EMOTIONAL_MAP.get(tone, _DEFAULT_EMOTION)


def _depth_to_one_hot(depth: str) -> list[float]:
    """Encode depth layer as one-hot vector of length 4."""
    vec = [0.0] * len(DEPTH_LAYERS)
    if depth in DEPTH_LAYERS:
        vec[DEPTH_LAYERS.index(depth)] = 1.0
    else:
        vec[0] = 1.0
    return vec


# ── CittaVector ─────────────────────────────────────────────────────────────


@dataclass
class CittaVector:
    """A point in the 16D citta consciousness vector space.

    Constructed from the components of a CittaMoment:
    - coherence scores (8D)
    - depth layer (4D one-hot)
    - emotional tone (2D valence-arousal)
    - neuro signals (2D cognitive_load, novelty)
    """

    components: list[float] = field(default_factory=lambda: [0.0] * VECTOR_DIM)

    @classmethod
    def from_moment(
        cls,
        coherence: float | dict[str, float] | None = None,
        depth_layer: str = "surface",
        emotional_tone: str = "neutral",
        neuro_signals: dict[str, float] | None = None,
        coherence_scores: dict[str, float] | None = None,
    ) -> CittaVector:
        """Build a CittaVector from CittaMoment components.

        Args:
            coherence: Scalar coherence (0-1). If coherence_scores is
                provided, this is ignored for the coherence subspace.
            depth_layer: Consciousness depth layer string.
            emotional_tone: Emotional tone string.
            neuro_signals: Neuro sensorium signals dict.
            coherence_scores: Per-dimension coherence scores (8 keys).
                If provided, used directly for the coherence subspace.
        """
        vec = [0.0] * VECTOR_DIM

        if coherence_scores is not None:
            for i, dim in enumerate(COHERENCE_DIMS):
                vec[i] = float(coherence_scores.get(dim, 0.0))
        elif coherence is not None:
            val = max(0.0, min(1.0, float(coherence)))
            for i in range(8):
                vec[i] = val

        depth_vec = _depth_to_one_hot(depth_layer)
        for i, v in enumerate(depth_vec):
            vec[8 + i] = v

        valence, arousal = _emotion_to_valence_arousal(emotional_tone)
        vec[12] = valence
        vec[13] = arousal

        neuro = neuro_signals or {}
        vec[14] = float(neuro.get("composite_cognitive_load", 0.0))
        vec[15] = float(neuro.get("composite_novelty", 0.0))

        return cls(components=vec)

    # ── Subspace accessors ──────────────────────────────────────────────

    def coherence_subspace(self) -> list[float]:
        return self.components[COHERENCE_RANGE[0]:COHERENCE_RANGE[1]]

    def depth_subspace(self) -> list[float]:
        return self.components[DEPTH_RANGE[0]:DEPTH_RANGE[1]]

    def emotion_subspace(self) -> list[float]:
        return self.components[EMOTION_RANGE[0]:EMOTION_RANGE[1]]

    def neuro_subspace(self) -> list[float]:
        return self.components[NEURO_RANGE[0]:NEURO_RANGE[1]]

    @property
    def valence(self) -> float:
        return self.components[12]

    @property
    def arousal(self) -> float:
        return self.components[13]

    @property
    def depth_layer(self) -> str:
        sub = self.depth_subspace()
        idx = max(range(len(sub)), key=lambda i: sub[i])
        return DEPTH_LAYERS[idx]

    @property
    def overall_coherence(self) -> float:
        sub = self.coherence_subspace()
        return sum(sub) / len(sub) if sub else 0.0

    # ── Geometry ────────────────────────────────────────────────────────

    def distance(self, other: CittaVector) -> float:
        """Euclidean distance between two citta vectors."""
        return math.sqrt(
            sum(
                (a - b) ** 2
                for a, b in zip(self.components, other.components)
            )
        )

    def cosine_similarity(self, other: CittaVector) -> float:
        """Cosine similarity between two citta vectors (-1 to 1)."""
        dot = sum(a * b for a, b in zip(self.components, other.components))
        mag_a = math.sqrt(sum(a * a for a in self.components))
        mag_b = math.sqrt(sum(b * b for b in other.components))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def subspace_distance(
        self, other: CittaVector, subspace: tuple[int, int]
    ) -> float:
        """Distance within a specific subspace range."""
        s, e = subspace
        return math.sqrt(
            sum(
                (a - b) ** 2
                for a, b in zip(self.components[s:e], other.components[s:e])
            )
        )

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "components": self.components,
            "overall_coherence": round(self.overall_coherence, 4),
            "depth_layer": self.depth_layer,
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CittaVector:
        comps = data.get("components")
        if comps and len(comps) == VECTOR_DIM:
            return cls(components=[float(c) for c in comps])
        return cls()

    def __getitem__(self, idx: int) -> float:
        return self.components[idx]

    def __len__(self) -> int:
        return VECTOR_DIM


# ── Trajectory analysis ─────────────────────────────────────────────────────


@dataclass
class CittaTrajectory:
    """A sequence of CittaVectors representing the consciousness stream trajectory.

    Enables velocity computation, ignition detection, and trajectory shape
    analysis — the geometric operations that flat scalars cannot support.
    """

    vectors: list[CittaVector] = field(default_factory=list)

    def append(self, vec: CittaVector) -> None:
        self.vectors.append(vec)

    def velocity(self) -> list[float]:
        """Step-to-step distances (velocity in citta-space).

        Returns a list of N-1 distances for N vectors.
        Empty if fewer than 2 vectors.
        """
        if len(self.vectors) < 2:
            return []
        return [
            self.vectors[i].distance(self.vectors[i + 1])
            for i in range(len(self.vectors) - 1)
        ]

    def normalized_velocity(self) -> list[float]:
        """Step-to-step distances with per-subspace normalization.

        Each subspace (coherence 8D, depth 4D, emotion 2D, neuro 2D)
        contributes equally to the normalized distance. This prevents
        the depth one-hot encoding from dominating the metric.
        """
        if len(self.vectors) < 2:
            return []
        norms = []
        for i in range(len(self.vectors) - 1):
            a, b = self.vectors[i], self.vectors[i + 1]
            coh_d = a.subspace_distance(b, COHERENCE_RANGE)
            depth_d = a.subspace_distance(b, DEPTH_RANGE)
            emo_d = a.subspace_distance(b, EMOTION_RANGE)
            neuro_d = a.subspace_distance(b, NEURO_RANGE)
            # Normalize: each subspace contributes 0 or 1 (depth one-hot
            # gives sqrt(2) when changing, so divide by sqrt(2))
            import math
            coh_norm = coh_d / math.sqrt(8)  # max possible in 8D
            depth_norm = depth_d / math.sqrt(2)  # max for one-hot change
            emo_norm = emo_d / math.sqrt(2)  # max for 2D
            neuro_norm = neuro_d / math.sqrt(2)  # max for 2D
            norms.append(coh_norm + depth_norm + emo_norm + neuro_norm)
        return norms

    def avg_velocity(self) -> float:
        """Average step distance across the trajectory."""
        v = self.velocity()
        return sum(v) / len(v) if v else 0.0

    def max_velocity(self) -> float:
        """Largest single step — indicates a sudden state shift."""
        v = self.velocity()
        return max(v) if v else 0.0

    def ignition_events(self, threshold: float = 1.2) -> list[dict[str, Any]]:
        """Detect ignition events — sudden large movements in citta-space.

        In Global Workspace Theory, "ignition" is the moment when a
        representation wins the competition and is broadcast globally.
        In the vector space, this manifests as a large displacement
        between consecutive moments.

        Args:
            threshold: Multiplier above average velocity to count as ignition.

        Returns:
            List of ignition event dicts with position, distance, and
            preceding/following vectors.
        """
        vels = self.normalized_velocity()
        if not vels:
            return []
        avg = sum(vels) / len(vels)
        if avg == 0:
            return []
        events: list[dict[str, Any]] = []
        for i, vel in enumerate(vels):
            if vel > avg * threshold:
                events.append(
                    {
                        "position": i + 1,
                        "distance": round(vel, 4),
                        "avg_velocity": round(avg, 4),
                        "ratio": round(vel / avg, 2),
                        "from_depth": self.vectors[i].depth_layer,
                        "to_depth": self.vectors[i + 1].depth_layer,
                        "from_valence": round(self.vectors[i].valence, 3),
                        "to_valence": round(self.vectors[i + 1].valence, 3),
                    }
                )
        return events

    def coherence_trajectory(self) -> list[float]:
        """Extract the overall coherence over time."""
        return [v.overall_coherence for v in self.vectors]

    def emotional_trajectory(self) -> list[tuple[float, float]]:
        """Extract (valence, arousal) over time."""
        return [(v.valence, v.arousal) for v in self.vectors]

    def to_dict(self) -> dict[str, Any]:
        return {
            "length": len(self.vectors),
            "vectors": [v.to_dict() for v in self.vectors],
            "avg_velocity": round(self.avg_velocity(), 4),
            "max_velocity": round(self.max_velocity(), 4),
            "ignitions": self.ignition_events(),
        }


def interpolate(a: CittaVector, b: CittaVector, t: float) -> CittaVector:
    """Linear interpolation between two citta vectors.

    Args:
        a: Start vector.
        b: End vector.
        t: Interpolation parameter (0 = a, 1 = b).

    Returns:
        Interpolated CittaVector.
    """
    t = max(0.0, min(1.0, t))
    comps = [
        a.components[i] + (b.components[i] - a.components[i]) * t
        for i in range(VECTOR_DIM)
    ]
    return CittaVector(components=comps)
