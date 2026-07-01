"""Resonance Models for WhiteMagic Memory Core
==============================================

Four resonance models for advanced memory analysis:

1. Memory Decay Model — Exponential decay with reinforcement
2. Pattern Resonance Detector — Same-frequency memory clustering
3. Constellation Merger — Auto-merge overlapping clusters
4. Garden Resonance Matrix — Inter-garden harmony calculation

Usage:
    from whitemagic.core.resonance.resonance_models import (
        MemoryDecayModel,
        PatternResonanceDetector,
        ConstellationMerger,
        GardenResonanceMatrix,
    )

    decay = MemoryDecayModel()
    result = decay.predict_retention(importance=0.8, age_days=30, access_count=5)

    detector = PatternResonanceDetector()
    clusters = detector.find_resonant_patterns(memories)

    merger = ConstellationMerger(overlap_threshold=0.3)
    merged = merger.merge_overlapping(constellations)

    matrix = GardenResonanceMatrix()
    harmony = matrix.calculate_inter_garden_harmony(gardens)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class DecayParams:
    """Parameters for the memory decay model."""

    base_decay_rate: float = 0.02  # Daily decay rate (2% per day)
    importance_protection: float = 0.5  # How much importance slows decay
    reinforcement_boost: float = 0.3  # How much each access reinforces
    reinforcement_decay: float = 0.9  # Diminishing returns on reinforcement
    minimum_retention: float = 0.05  # Floor retention score
    half_life_base: float = 30.0  # Base half-life in days


class MemoryDecayModel:
    """Exponential decay model with reinforcement for memory retention."""

    def __init__(self, params: DecayParams | None = None):
        self.params = params or DecayParams()

    def predict_retention(
        self,
        importance: float = 0.5,
        age_days: float = 0.0,
        access_count: int = 0,
        recall_count: int = 0,
        last_access_days_ago: float = 0.0,
        initial_retention: float = 1.0,
    ) -> dict[str, Any]:
        """Predict current retention score for a memory."""
        p = self.params

        # Effective decay rate (importance protects against decay)
        effective_decay = p.base_decay_rate * (
            1.0 - importance * p.importance_protection
        )

        # Base decay (exponential)
        base_retention = initial_retention * math.exp(-effective_decay * age_days)

        # Reinforcement from accesses (diminishing returns)
        reinforcement = 0.0
        if access_count > 0:
            # Each access adds reinforcement, but with diminishing returns
            for i in range(access_count):
                reinforcement += p.reinforcement_boost * (p.reinforcement_decay**i)
            # Reinforcement decays based on time since last access
            recency_factor = math.exp(-0.1 * last_access_days_ago)
            reinforcement *= recency_factor

        # Recall bonus (active recall is stronger than passive access)
        recall_bonus = recall_count * 0.05 * math.exp(-0.05 * last_access_days_ago)

        # Final retention
        retention = min(1.0, base_retention + reinforcement + recall_bonus)
        retention = max(p.minimum_retention, retention)

        # Half-life calculation
        half_life = (
            math.log(2) / effective_decay if effective_decay > 0 else float("inf")
        )

        # Time to decay below threshold
        if retention > 0.5:
            time_to_half = (
                (math.log(retention / 0.5)) / effective_decay
                if effective_decay > 0
                else float("inf")
            )
        else:
            time_to_half = 0.0

        return {
            "retention": round(retention, 6),
            "base_retention": round(base_retention, 6),
            "reinforcement": round(reinforcement, 6),
            "recall_bonus": round(recall_bonus, 6),
            "effective_decay_rate": round(effective_decay, 6),
            "half_life_days": round(half_life, 2),
            "time_to_50_percent_days": round(time_to_half, 2)
            if time_to_half != float("inf")
            else None,
            "status": "stable"
            if retention > 0.7
            else ("decaying" if retention > 0.3 else "critical"),
        }

    def predict_decay_curve(
        self,
        importance: float = 0.5,
        access_count: int = 0,
        days: int = 365,
        step: int = 7,
    ) -> dict[str, Any]:
        """Generate a decay curve over time."""
        curve = []
        for d in range(0, days + 1, step):
            point = self.predict_retention(
                importance=importance,
                age_days=d,
                access_count=access_count,
                last_access_days_ago=0,  # Assume recent access
            )
            curve.append({"day": d, "retention": point["retention"]})

        return {
            "curve": curve,
            "importance": importance,
            "access_count": access_count,
            "days": days,
            "step": step,
        }

    def calculate_reinforcement_schedule(
        self,
        importance: float = 0.5,
        target_retention: float = 0.8,
    ) -> dict[str, Any]:
        """Calculate optimal reinforcement schedule to maintain target retention."""
        p = self.params
        effective_decay = p.base_decay_rate * (
            1.0 - importance * p.importance_protection
        )

        # Time until retention drops below target
        if effective_decay > 0:
            time_to_drop = math.log(1.0 / target_retention) / effective_decay
        else:
            time_to_drop = float("inf")

        # Recommended review intervals (spaced repetition)
        intervals = []
        current_interval = max(1, int(time_to_drop * 0.8))
        for i in range(5):
            intervals.append(current_interval)
            # Each successful review extends the interval
            current_interval = int(current_interval * (1.0 + importance * 0.5))

        return {
            "time_to_drop_below_target_days": round(time_to_drop, 2)
            if time_to_drop != float("inf")
            else None,
            "recommended_intervals_days": intervals,
            "target_retention": target_retention,
            "importance": importance,
        }


@dataclass
class ResonantCluster:
    """A cluster of memories with resonant frequencies."""

    cluster_id: int
    member_ids: list[int | str]
    center_frequency: float
    frequency_spread: float
    coherence: float  # 0-1, how well frequencies align
    avg_importance: float
    avg_damping: float
    garden: str
    size: int


class PatternResonanceDetector:
    """Detects same-frequency memory clustering patterns."""

    def __init__(self, frequency_tolerance: float = 0.15):
        self.frequency_tolerance = frequency_tolerance

    def find_resonant_patterns(
        self,
        memories: list[dict[str, Any]],
        min_cluster_size: int = 2,
    ) -> dict[str, Any]:
        """Find clusters of memories with similar resonance frequencies."""
        # Extract resonance params
        resonant_mems = []
        for mem in memories:
            resonance = mem.get("resonance", {})
            if resonance.get("frequency"):
                resonant_mems.append(
                    {
                        "id": mem.get("id"),
                        "frequency": resonance["frequency"],
                        "damping": resonance.get("damping", 0.1),
                        "importance": mem.get("importance", 0.5),
                        "garden": resonance.get("garden", "core_garden"),
                    }
                )

        if not resonant_mems:
            return {
                "clusters": [],
                "total_clusters": 0,
                "memories_analyzed": len(memories),
            }

        # Sort by frequency for clustering
        resonant_mems.sort(key=lambda m: m["frequency"])

        # Greedy clustering by frequency proximity
        clusters = []
        current_cluster = [resonant_mems[0]]

        for mem in resonant_mems[1:]:
            center_freq = sum(m["frequency"] for m in current_cluster) / len(
                current_cluster
            )
            if abs(mem["frequency"] - center_freq) <= self.frequency_tolerance:
                current_cluster.append(mem)
            else:
                if len(current_cluster) >= min_cluster_size:
                    clusters.append(current_cluster)
                current_cluster = [mem]

        # Don't forget the last cluster
        if len(current_cluster) >= min_cluster_size:
            clusters.append(current_cluster)

        # Build cluster objects
        result_clusters = []
        for i, cluster in enumerate(clusters):
            freqs = [m["frequency"] for m in cluster]
            center_freq = sum(freqs) / len(freqs)
            spread = max(freqs) - min(freqs)

            # Coherence: how tightly clustered the frequencies are
            coherence = max(0.0, 1.0 - spread / (2 * self.frequency_tolerance))

            result_clusters.append(
                {
                    "cluster_id": i,
                    "member_ids": [m["id"] for m in cluster],
                    "center_frequency": round(center_freq, 4),
                    "frequency_spread": round(spread, 4),
                    "coherence": round(coherence, 4),
                    "avg_importance": round(
                        sum(m["importance"] for m in cluster) / len(cluster), 4
                    ),
                    "avg_damping": round(
                        sum(m["damping"] for m in cluster) / len(cluster), 4
                    ),
                    "garden": self._dominant_garden(cluster),
                    "size": len(cluster),
                }
            )

        # Sort by coherence (most coherent first)
        result_clusters.sort(key=lambda c: c["coherence"], reverse=True)

        return {
            "clusters": result_clusters,
            "total_clusters": len(result_clusters),
            "memories_analyzed": len(memories),
            "memories_in_clusters": sum(c["size"] for c in result_clusters),
            "frequency_tolerance": self.frequency_tolerance,
        }

    @staticmethod
    def _dominant_garden(cluster: list[dict]) -> str:
        """Find the most common garden in a cluster."""
        garden_counts: dict = {}
        for m in cluster:
            g = m.get("garden", "core_garden")
            garden_counts[g] = garden_counts.get(g, 0) + 1
        return max(garden_counts, key=garden_counts.get)  # type: ignore[arg-type]

    def find_cross_garden_resonance(
        self,
        memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Find resonant patterns that span multiple gardens."""
        result = self.find_resonant_patterns(memories)

        cross_garden = []
        for cluster in result["clusters"]:
            gardens = set()
            for mem_id in cluster["member_ids"]:
                mem = next((m for m in memories if m.get("id") == mem_id), None)
                if mem:
                    g = mem.get("resonance", {}).get("garden", "core_garden")
                    gardens.add(g)
            if len(gardens) > 1:
                cross_garden.append(
                    {
                        **cluster,
                        "gardens": list(gardens),
                        "garden_count": len(gardens),
                    }
                )

        return {
            "cross_garden_clusters": cross_garden,
            "total_cross_garden": len(cross_garden),
            "total_clusters": result["total_clusters"],
        }


@dataclass
class Constellation:
    """A constellation (cluster) of memories in 5D space."""

    constellation_id: int
    member_ids: list[int | str]
    center: tuple[float, float, float, float, float]  # (x, y, z, w, v)
    radius: float
    avg_importance: float
    garden: str


class ConstellationMerger:
    """Auto-merges overlapping constellations in 5D holographic space."""

    def __init__(self, overlap_threshold: float = 0.3):
        self.overlap_threshold = overlap_threshold

    @staticmethod
    def _distance_5d(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        """Calculate 5D Euclidean distance."""
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    def _calculate_overlap(
        self,
        c1: Constellation,
        c2: Constellation,
    ) -> float:
        """Calculate overlap ratio between two constellations."""
        dist = self._distance_5d(c1.center, c2.center)
        combined_radius = c1.radius + c2.radius

        if combined_radius == 0:
            return 0.0

        # Overlap ratio: how much the spheres overlap
        # 0 = no overlap, 1 = one inside the other
        if dist >= combined_radius:
            return 0.0

        # Simple overlap metric
        overlap = 1.0 - (dist / combined_radius)
        return overlap

    def merge_overlapping(
        self,
        constellations: list[Constellation],
    ) -> dict[str, Any]:
        """Merge constellations that overlap above the threshold."""
        n = len(constellations)
        if n <= 1:
            return {
                "merged": constellations,
                "total_before": n,
                "total_after": n,
                "merges": 0,
            }

        # Build overlap matrix
        merges = []
        merged = set()

        for i in range(n):
            if i in merged:
                continue
            for j in range(i + 1, n):
                if j in merged:
                    continue

                overlap = self._calculate_overlap(constellations[i], constellations[j])
                if overlap >= self.overlap_threshold:
                    merges.append(
                        {
                            "constellation_a": constellations[i].constellation_id,
                            "constellation_b": constellations[j].constellation_id,
                            "overlap": round(overlap, 4),
                        }
                    )
                    merged.add(j)

        # Create merged constellations
        result = []
        merge_map = {}  # merged_id -> primary_id

        for merge in merges:
            a_id = merge["constellation_a"]
            b_id = merge["constellation_b"]
            merge_map[b_id] = a_id

        # Build final list
        primary_ids = set()
        for c in constellations:
            if c.constellation_id not in merged:
                primary_ids.add(c.constellation_id)

        for c in constellations:
            if c.constellation_id in primary_ids:
                merged_with = [
                    m["constellation_b"]
                    for m in merges
                    if m["constellation_a"] == c.constellation_id
                ]

                if merged_with:
                    # Merge: combine members, recalculate center
                    all_members = list(c.member_ids)
                    all_centers = [c.center]
                    all_radii = [c.radius]
                    all_importance = [c.avg_importance]

                    for other_id in merged_with:
                        other = next(
                            (
                                oc
                                for oc in constellations
                                if oc.constellation_id == other_id
                            ),
                            None,
                        )
                        if other:
                            all_members.extend(other.member_ids)
                            all_centers.append(other.center)
                            all_radii.append(other.radius)
                            all_importance.append(other.avg_importance)

                    # New center (weighted by importance)
                    total_imp = sum(all_importance)
                    new_center = tuple(
                        sum(c[d] * imp for c, imp in zip(all_centers, all_importance))
                        / total_imp
                        for d in range(5)
                    )

                    # New radius (max of all)
                    new_radius = max(all_radii)

                    result.append(
                        Constellation(
                            constellation_id=c.constellation_id,
                            member_ids=all_members,
                            center=new_center,  # type: ignore[arg-type]
                            radius=new_radius,
                            avg_importance=sum(all_importance) / len(all_importance),
                            garden=c.garden,
                        )
                    )
                else:
                    result.append(c)

        return {
            "merged": result,
            "total_before": n,
            "total_after": len(result),
            "merges": len(merges),
            "merge_details": merges,
        }

    def find_constellation_networks(
        self,
        constellations: list[Constellation],
    ) -> dict[str, Any]:
        """Find networks of interconnected constellations."""
        n = len(constellations)
        if n == 0:
            return {"networks": [], "total_networks": 0}

        # Build adjacency
        adj: dict[str, set[str]] = {c.constellation_id: set() for c in constellations}  # type: ignore[misc]
        for i in range(n):
            for j in range(i + 1, n):
                overlap = self._calculate_overlap(constellations[i], constellations[j])
                if overlap > 0:
                    adj[constellations[i].constellation_id].add(
                        constellations[j].constellation_id
                    )  # type: ignore[index, arg-type]
                    adj[constellations[j].constellation_id].add(
                        constellations[i].constellation_id
                    )  # type: ignore[index, arg-type]

        # Find connected components
        visited = set()
        networks = []

        for c in constellations:
            if c.constellation_id in visited:
                continue

            # BFS
            component = []
            queue = [c.constellation_id]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for neighbor in adj[node]:  # type: ignore[index]
                    if neighbor not in visited:
                        queue.append(neighbor)  # type: ignore[arg-type]

            if len(component) > 1:
                networks.append(
                    {
                        "constellation_ids": component,
                        "size": len(component),
                        "total_connections": sum(len(adj[cid]) for cid in component)
                        // 2,  # type: ignore[misc, index]
                    }
                )

        return {
            "networks": networks,
            "total_networks": len(networks),
            "isolated_count": n - sum(net["size"] for net in networks),  # type: ignore[misc]
        }


class GardenResonanceMatrix:
    """Calculates inter-garden harmony and resonance patterns."""

    # Garden affinity matrix (how well gardens resonate with each other)
    # Based on Wu Xing elemental relationships
    GARDEN_AFFINITY = {
        ("knowledge_garden", "research_garden"): 0.9,  # Both analytical
        ("knowledge_garden", "wisdom_garden"): 0.7,  # Knowledge → Wisdom
        ("wisdom_garden", "core_garden"): 0.8,  # Wisdom is core
        ("emotion_garden", "dream_garden"): 0.85,  # Emotional/dreamy
        ("code_garden", "system_garden"): 0.75,  # Technical
        ("creative_garden", "emotion_garden"): 0.7,  # Creative/emotional
        ("creative_garden", "dream_garden"): 0.65,  # Creative/dreamy
        ("core_garden", "ephemeral_garden"): 0.3,  # Core vs fleeting
        ("knowledge_garden", "emotion_garden"): 0.4,  # Logic vs emotion
        ("code_garden", "wisdom_garden"): 0.5,  # Technical vs deep
    }

    def calculate_inter_garden_harmony(
        self,
        gardens: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate harmony between all garden pairs.

        Args:
            gardens: Dict of garden_name -> {
                "memory_count": int,
                "avg_frequency": float,
                "avg_damping": float,
                "avg_importance": float,
                "avg_vitality": float,
            }
        """
        garden_names = list(gardens.keys())
        n = len(garden_names)

        if n < 2:
            return {"matrix": [], "pairs": [], "overall_harmony": 1.0}

        # Build harmony matrix
        matrix = [[0.0] * n for _ in range(n)]
        pairs = []

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                    continue

                g1 = garden_names[i]
                g2 = garden_names[j]

                # Base affinity
                affinity = self.GARDEN_AFFINITY.get(
                    (g1, g2), self.GARDEN_AFFINITY.get((g2, g1), 0.5)
                )

                # Frequency resonance (closer frequencies = more harmony)
                freq1 = gardens[g1].get("avg_frequency", 1.0)
                freq2 = gardens[g2].get("avg_frequency", 1.0)
                freq_harmony = 1.0 - min(1.0, abs(freq1 - freq2) / 2.0)

                # Damping compatibility (similar damping = stable resonance)
                damp1 = gardens[g1].get("avg_damping", 0.1)
                damp2 = gardens[g2].get("avg_damping", 0.1)
                damp_harmony = 1.0 - min(1.0, abs(damp1 - damp2) / 0.5)

                # Combined harmony (weighted)
                harmony = affinity * 0.4 + freq_harmony * 0.3 + damp_harmony * 0.3

                matrix[i][j] = round(harmony, 4)

                if i < j:
                    # Only record each pair once
                    pairs.append(
                        {
                            "garden_a": g1,
                            "garden_b": g2,
                            "harmony": round(harmony, 4),
                            "affinity": affinity,
                            "frequency_harmony": round(freq_harmony, 4),
                            "damping_harmony": round(damp_harmony, 4),
                            "status": "harmonious"
                            if harmony > 0.7
                            else ("neutral" if harmony > 0.4 else "dissonant"),
                        }
                    )

        # Overall harmony
        all_harmonies = [p["harmony"] for p in pairs]
        overall = sum(all_harmonies) / len(all_harmonies) if all_harmonies else 1.0

        # Sort pairs by harmony
        pairs.sort(key=lambda p: p["harmony"], reverse=True)

        return {
            "matrix": matrix,
            "garden_names": garden_names,
            "pairs": pairs,
            "overall_harmony": round(overall, 4),
            "most_harmonious": pairs[0] if pairs else None,
            "most_dissonant": pairs[-1] if pairs else None,
            "harmonious_count": sum(1 for p in pairs if p["status"] == "harmonious"),
            "dissonant_count": sum(1 for p in pairs if p["status"] == "dissonant"),
        }

    def calculate_garden_resonance_score(
        self,
        garden_name: str,
        garden_data: dict[str, Any],
        all_gardens: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate how well a garden resonates with the entire system."""
        if garden_name not in all_gardens:
            return {"error": f"Garden {garden_name} not found"}

        # Resonance with each other garden
        resonances = []
        for other_name, other_data in all_gardens.items():
            if other_name == garden_name:
                continue

            harmony = self._pair_harmony(
                garden_data, other_data, garden_name, other_name
            )
            resonances.append(
                {
                    "garden": other_name,
                    "harmony": round(harmony, 4),
                }
            )

        avg_resonance = (
            sum(r["harmony"] for r in resonances) / len(resonances)
            if resonances
            else 0.0
        )  # type: ignore[misc]

        # Internal coherence (based on frequency spread)
        freq_spread = garden_data.get("frequency_spread", 0.0)
        internal_coherence = max(0.0, 1.0 - freq_spread / 2.0)

        # System integration score
        memory_weight = garden_data.get("memory_count", 0) / max(
            1, sum(g.get("memory_count", 0) for g in all_gardens.values())
        )
        integration = (
            avg_resonance * 0.6 + internal_coherence * 0.3 + memory_weight * 0.1
        )

        return {
            "garden": garden_name,
            "avg_resonance": round(avg_resonance, 4),
            "internal_coherence": round(internal_coherence, 4),
            "system_integration": round(integration, 4),
            "resonances": sorted(resonances, key=lambda r: r["harmony"], reverse=True),
            "status": "well_integrated"
            if integration > 0.7
            else ("moderate" if integration > 0.4 else "isolated"),
        }

    def _pair_harmony(
        self,
        g1: dict[str, Any],
        g2: dict[str, Any],
        name1: str,
        name2: str,
    ) -> float:
        """Calculate harmony between two gardens."""
        affinity = self.GARDEN_AFFINITY.get(
            (name1, name2), self.GARDEN_AFFINITY.get((name2, name1), 0.5)
        )

        freq1 = g1.get("avg_frequency", 1.0)
        freq2 = g2.get("avg_frequency", 1.0)
        freq_harmony = 1.0 - min(1.0, abs(freq1 - freq2) / 2.0)

        damp1 = g1.get("avg_damping", 0.1)
        damp2 = g2.get("avg_damping", 0.1)
        damp_harmony = 1.0 - min(1.0, abs(damp1 - damp2) / 0.5)

        return affinity * 0.4 + freq_harmony * 0.3 + damp_harmony * 0.3
