"""Constellation-Based Joint Evaluation (Objective N).

Clusters similar improvement hypotheses into constellations and evaluates
them jointly rather than individually.

- Improvements in the same constellation share a covariance structure
- P(all succeed | cluster) instead of P(each succeeds independently)
- Contagion effect: if one succeeds, posterior for others shifts upward
- Cluster-level confidence: "this group has 80% joint success probability"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Constellation:
    """A cluster of similar improvement hypotheses."""

    id: str
    member_ids: list[str] = field(default_factory=list)
    centroid: float = 0.0  # Semantic centroid (1D projection)
    joint_success_prob: float = 0.0
    individual_probs: dict[str, float] = field(default_factory=dict)
    covariance: float = 0.0  # Average pairwise correlation
    metadata: dict[str, Any] = field(default_factory=dict)


class ConstellationEvaluator:
    """Clusters and jointly evaluates improvement hypotheses.

    Uses semantic similarity (1D projection) to cluster hypotheses,
    then computes joint success probabilities accounting for correlation.
    """

    def __init__(self, similarity_threshold: float = 0.15) -> None:
        self._similarity_threshold = similarity_threshold
        self._constellations: dict[str, Constellation] = {}

    def cluster(
        self,
        hypotheses: list[dict[str, Any]],
    ) -> list[Constellation]:
        """Cluster hypotheses by semantic similarity.

        Args:
            hypotheses: List of dicts with 'id' and 'semantic_coord' (0-1).

        Returns:
            List of Constellation objects.
        """
        if not hypotheses:
            return []

        # Simple 1D clustering: group by proximity
        sorted_hyps = sorted(hypotheses, key=lambda h: h.get("semantic_coord", 0.0))
        clusters: list[list[dict[str, Any]]] = []
        current_cluster: list[dict[str, Any]] = [sorted_hyps[0]]

        for h in sorted_hyps[1:]:
            prev_coord = current_cluster[-1].get("semantic_coord", 0.0)
            curr_coord = h.get("semantic_coord", 0.0)
            if abs(curr_coord - prev_coord) <= self._similarity_threshold:
                current_cluster.append(h)
            else:
                clusters.append(current_cluster)
                current_cluster = [h]
        clusters.append(current_cluster)

        result = []
        for i, cluster in enumerate(clusters):
            member_ids = [h["id"] for h in cluster]
            coords = [h.get("semantic_coord", 0.0) for h in cluster]
            centroid = sum(coords) / len(coords) if coords else 0.0

            const = Constellation(
                id=f"constellation_{i}",
                member_ids=member_ids,
                centroid=centroid,
            )
            self._constellations[const.id] = const
            result.append(const)

        return result

    def compute_joint_probability(
        self,
        constellation: Constellation,
        individual_probs: dict[str, float],
        correlation: float = 0.0,
    ) -> float:
        """Compute joint success probability for a constellation.

        P(all succeed | cluster) = product of individual probs adjusted
        for correlation. With positive correlation, joint prob is higher
        than independent product (contagion effect).

        Args:
            constellation: The constellation to evaluate.
            individual_probs: P(success) for each member.
            correlation: Average pairwise correlation (0=independent, 1=perfect).

        Returns:
            Joint probability P(all succeed).
        """
        probs = [individual_probs.get(mid, 0.5) for mid in constellation.member_ids]
        if not probs:
            return 0.0

        # Independent joint probability
        independent_joint = 1.0
        for p in probs:
            independent_joint *= max(p, 0.01)

        # Adjust for correlation: positive correlation increases joint prob
        # when individual probs are high, decreases when low
        avg_prob = sum(probs) / len(probs)
        if correlation > 0 and avg_prob > 0.5:
            # Positive correlation + high confidence → higher joint prob
            adjustment = 1.0 + correlation * (1.0 - independent_joint) * 0.5
        elif correlation > 0 and avg_prob <= 0.5:
            # Positive correlation + low confidence → lower joint prob
            adjustment = 1.0 - correlation * (1.0 - independent_joint) * 0.3
        else:
            adjustment = 1.0

        joint = min(1.0, independent_joint * adjustment)
        constellation.joint_success_prob = joint
        constellation.individual_probs = individual_probs
        constellation.covariance = correlation
        return joint

    def apply_contagion(
        self,
        constellation: Constellation,
        succeeded_id: str,
        boost: float = 0.1,
    ) -> dict[str, float]:
        """Apply contagion effect: one success boosts others in the cluster.

        Args:
            constellation: The constellation.
            succeeded_id: ID of the hypothesis that succeeded.
            boost: How much to boost other members' probability.

        Returns:
            Updated individual probabilities.
        """
        updated = dict(constellation.individual_probs)
        for mid in constellation.member_ids:
            if mid != succeeded_id:
                current = updated.get(mid, 0.5)
                updated[mid] = min(1.0, current + boost)
        constellation.individual_probs = updated
        return updated

    def get_constellation(self, const_id: str) -> Constellation | None:
        return self._constellations.get(const_id)

    def get_all_constellations(self) -> dict[str, Constellation]:
        return dict(self._constellations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_constellations": len(self._constellations),
            "total_members": sum(
                len(c.member_ids) for c in self._constellations.values()
            ),
            "avg_cluster_size": (
                sum(len(c.member_ids) for c in self._constellations.values())
                / max(len(self._constellations), 1)
            ),
        }
