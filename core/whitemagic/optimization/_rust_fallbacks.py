"""Python fallback implementations for Rust accelerators.

This module contains pure-Python fallback implementations used when
the Rust extension (whitemagic_rs) is not available.
"""
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def rust_fallback_available() -> bool:
    """Check if Rust fallback implementations are available.

    Returns:
        True if fallback implementations are available (always True for this module)
    """
    return True


def _galactic_batch_score_python(
    memories: list[dict[str, Any]], quick: bool,
) -> list[dict[str, Any]]:
    """Pure-Python fallback for galactic batch scoring."""
    results = []
    for m in memories:
        if m.get("is_protected") or m.get("is_core_identity") or m.get("is_sacred") or m.get("is_pinned"):
            distance = 0.0
            retention = 1.0
        elif quick:
            s1 = m.get("importance", 0.5) * 1.0
            s2 = m.get("neuro_score", 0.5) * 0.9
            s3 = abs(m.get("emotional_valence", 0.0)) * 0.6
            s4 = min(1.0, m.get("recall_count", 0) / 20.0) * 0.5
            retention = (s1 + s2 + s3 + s4) / 3.0
            distance = round(1.0 - max(0.0, min(1.0, retention)), 4)
        else:
            weights = [0.35, 0.20, 0.10, 0.10, 0.10, 0.05, 0.10]
            values = [
                m.get("memory_type_weight", 0.5),
                m.get("richness", 0.3),
                m.get("activity", 0.0),
                m.get("recency", 0.5),
                m.get("importance", 0.5),
                m.get("emotion", 0.0),
                m.get("protection", 0.0),
            ]
            weighted_sum = sum(v * w for v, w in zip(values, weights))
            total_weight = sum(weights)
            retention = max(0.0, min(1.0, weighted_sum / total_weight))
            distance = round(1.0 - retention, 4)

        if distance < 0.15:
            zone = "core"
        elif distance < 0.40:
            zone = "inner_rim"
        elif distance < 0.65:
            zone = "mid_band"
        elif distance < 0.85:
            zone = "outer_rim"
        else:
            zone = "far_edge"

        results.append({
            "id": m.get("id", ""),
            "retention_score": round(retention, 4),
            "galactic_distance": distance,
            "zone": zone,
        })
    return results


def _association_mine_python(
    texts: list[tuple[str, str]],
    max_keywords: int,
    min_score: float,
    max_results: int,
) -> dict[str, Any]:
    """Pure-Python fallback for association mining."""
    import re
    from collections import defaultdict

    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "this", "that", "was", "are",
        "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "could", "should", "may", "might", "shall",
        "can", "not", "no", "nor", "so", "if", "then", "than", "too", "very",
        "just", "about", "up", "out", "into", "over", "after", "before",
    }
    word_re = re.compile(r"\w+")

    fingerprints = []
    for _, text in texts:
        words = word_re.findall(text.lower())
        kws = {w for w in words if w not in stop_words and len(w) > 2}
        if len(kws) > max_keywords:
            freq: dict[str, int] = defaultdict(int)
            for w in words:
                if w in kws:
                    freq[w] += 1
            sorted_kw = sorted(kws, key=lambda k: freq[k], reverse=True)
            kws = set(sorted_kw[:max_keywords])
        fingerprints.append(kws)

    overlaps = []
    n = len(fingerprints)
    for i in range(n):
        for j in range(i + 1, n):
            kw_a, kw_b = fingerprints[i], fingerprints[j]
            if not kw_a or not kw_b:
                continue
            shared = kw_a & kw_b
            union_size = len(kw_a | kw_b)
            if union_size == 0:
                continue
            raw_jaccard = len(shared) / union_size
            count_bonus = min(1.0, len(shared) / 5.0) * 0.3
            score = min(1.0, raw_jaccard + count_bonus)
            if score >= min_score:
                overlaps.append({
                    "source_id": texts[i][0],
                    "target_id": texts[j][0],
                    "overlap_score": round(score, 4),
                    "shared_count": len(shared),
                    "shared_keywords": sorted(shared)[:5],
                })

    overlaps.sort(key=lambda x: cast(float, x["overlap_score"]), reverse=True)
    overlaps = overlaps[:max_results]

    return {
        "memory_count": len(texts),
        "pair_count": len(overlaps),
        "overlaps": overlaps,
    }


class PythonSpatialIndex5D:
    """Pure-Python fallback for 5D spatial index using brute-force search."""

    def __init__(self) -> None:
        self._points: list[tuple[str, list[float]]] = []

    def add(self, memory_id: str, vector: list[float]) -> int:
        """
        Perform the add operation.
        
        Args:
            memory_id: Parameter description.
            vector: Parameter description.
        
        Returns:
            int
        """
        idx = len(self._points)
        self._points.append((memory_id, list(vector)))
        return idx

    def add_batch(self, items: list[tuple[str, list[float]]]) -> int:
        """
        Add batch.
        
        Args:
            items: Parameter description.
        
        Returns:
            int
        """
        for mid, vec in items:
            self._points.append((mid, list(vec)))
        return len(items)

    def query_nearest(self, vector: list[float], n: int) -> list[tuple[str, float]]:
        """
        Perform the query nearest operation.
        
        Args:
            vector: Parameter description.
            n: Parameter description.
        
        Returns:
            list[tuple[str, float]]
        """
        if not self._points:
            return []
        dists = []
        for mid, pt in self._points:
            d = sum((a - b) ** 2 for a, b in zip(vector, pt))
            dists.append((mid, d))
        dists.sort(key=lambda x: x[1])
        return dists[:n]

    def query_within_radius(self, vector: list[float], radius_sq: float) -> list[tuple[str, float]]:
        """
        Perform the query within radius operation.
        
        Args:
            vector: Parameter description.
            radius_sq: Parameter description.
        
        Returns:
            list[tuple[str, float]]
        """
        results = []
        for mid, pt in self._points:
            d = sum((a - b) ** 2 for a, b in zip(vector, pt))
            if d <= radius_sq:
                results.append((mid, d))
        return results

    def size(self) -> int:
        """
        Perform the size operation.
        
        Returns:
            int
        """
        return len(self._points)

    def get_snapshot(self) -> list[tuple[str, list[float]]]:
        """
        Get the snapshot.
        
        Returns:
            list[tuple[str, list[float]]]
        """
        return list(self._points)

    def clear(self) -> None:
        """
        Perform the clear operation.
        
        Returns:
            None
        """
        self._points.clear()
