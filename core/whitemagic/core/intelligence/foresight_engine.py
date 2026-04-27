"""Foresight Engine — Logos Layer (CyberBrain Layer 7).

Predictive engine for:
- Constellation drift: project where clusters will be in N days
- Memory decay: estimate which memories will fade based on distance + recency
- Association convergence: detect constellations moving toward collision/merger

This is the final layer of the 7-layer CyberBrain cognitive stack.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ForesightReport:
    """Results from a foresight analysis."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    horizon_days: int = 7
    constellation_projections: list[dict[str, Any]] = field(default_factory=list)
    decay_predictions: list[dict[str, Any]] = field(default_factory=list)
    convergence_warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "horizon_days": self.horizon_days,
            "constellation_projections": self.constellation_projections,
            "decay_predictions": self.decay_predictions,
            "convergence_warnings": self.convergence_warnings,
        }


class ForesightEngine:
    """Predictive engine for holographic memory space."""

    def __init__(self, horizon_days: int = 7) -> None:
        self.horizon_days = horizon_days

    def analyze(self) -> ForesightReport:
        """Run full foresight analysis."""
        report = ForesightReport(horizon_days=self.horizon_days)
        report.constellation_projections = self._project_constellations()
        report.decay_predictions = self._predict_decay()
        report.convergence_warnings = self._detect_convergence()
        return report

    def _project_constellations(self) -> list[dict[str, Any]]:
        """Project constellation centroids forward based on drift vectors."""
        try:
            from whitemagic.core.memory.constellations import get_constellation_detector
            detector = get_constellation_detector()
            drift_data = detector.get_drift_vectors(window_days=self.horizon_days)
        except Exception as exc:
            logger.debug(f"Constellation drift unavailable: {exc}")
            return []

        projections: list[dict[str, Any]] = []
        for item in drift_data:
            # Linear projection: current + (drift_vector * projection_factor)
            # Use drift over the window to estimate daily rate, then multiply
            dv = item.get("drift_vector", {})
            factor = self.horizon_days / max(item.get("samples", 1), 1)
            projected = {
                "x": item["current_centroid"]["x"] + dv.get("dx", 0) * factor,
                "y": item["current_centroid"]["y"] + dv.get("dy", 0) * factor,
                "z": item["current_centroid"]["z"] + dv.get("dz", 0) * factor,
                "w": item["current_centroid"]["w"] + dv.get("dw", 0) * factor,
                "v": item["current_centroid"]["v"] + dv.get("dv", 0) * factor,
            }
            projections.append({
                "name": item["name"],
                "current_centroid": item["current_centroid"],
                "projected_centroid": {k: round(v, 4) for k, v in projected.items()},
                "drift_magnitude": item.get("drift_magnitude", 0.0),
                "confidence": "low" if item.get("samples", 0) < 3 else "medium" if item.get("samples", 0) < 7 else "high",
            })
        return projections

    def _predict_decay(self) -> list[dict[str, Any]]:
        """Predict which memories are likely to decay based on galactic distance + recency."""
        try:
            import sqlite3
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            backend = um.backend
        except Exception as exc:
            logger.debug(f"Decay prediction unavailable: {exc}")
            return []

        predictions: list[dict[str, Any]] = []
        cutoff = (datetime.now() - timedelta(days=self.horizon_days)).isoformat()

        with backend.pool.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.id, m.title, m.importance, m.galactic_distance, m.created_at, m.memory_type,
                       hc.x, hc.y, hc.z, hc.w, hc.v
                FROM memories m
                LEFT JOIN holographic_coords hc ON m.id = hc.memory_id
                WHERE m.memory_type != 'quarantined'
                  AND (m.created_at < ? OR m.last_accessed < ?)
                ORDER BY m.galactic_distance DESC, m.importance ASC
                LIMIT 50
                """,
                (cutoff, cutoff),
            ).fetchall()

        for r in rows:
            # Decay score: higher distance + lower importance + older = more likely to decay
            distance = r["galactic_distance"] or 0.5
            importance = r["importance"] or 0.5
            decay_score = (distance * 0.5) + ((1.0 - importance) * 0.3)
            if decay_score > 0.6:
                predictions.append({
                    "memory_id": r["id"][:8],
                    "title": r["title"][:40] if r["title"] else "",
                    "memory_type": r["memory_type"],
                    "decay_score": round(decay_score, 3),
                    "galactic_distance": round(distance, 3),
                    "importance": round(importance, 3),
                    "risk": "high" if decay_score > 0.8 else "medium",
                })
        return predictions

    def _detect_convergence(self) -> list[dict[str, Any]]:
        """Detect constellation pairs that are moving toward each other."""
        projections = self._project_constellations()
        if len(projections) < 2:
            return []

        warnings: list[dict[str, Any]] = []
        # Simple O(n²) pairwise check — fine for small constellation counts
        for i, a in enumerate(projections):
            for b in projections[i + 1 :]:
                pa = a["projected_centroid"]
                pb = b["projected_centroid"]
                distance = math.sqrt(
                    (pa["x"] - pb["x"]) ** 2
                    + (pa["y"] - pb["y"]) ** 2
                    + (pa["z"] - pb["z"]) ** 2
                    + (pa["w"] - pb["w"]) ** 2
                    + (pa["v"] - pb["v"]) ** 2
                )
                # Convergence threshold: if projected distance < 0.3 in 5D space
                if distance < 0.3:
                    warnings.append({
                        "constellation_a": a["name"],
                        "constellation_b": b["name"],
                        "projected_distance": round(distance, 4),
                        "severity": "merge_imminent" if distance < 0.15 else "converging",
                        "confidence": min(a.get("confidence", "low"), b.get("confidence", "low")),
                    })
        return warnings


# Singleton
_foresight_engine: ForesightEngine | None = None


def get_foresight_engine(horizon_days: int = 7) -> ForesightEngine:
    """Get the global foresight engine."""
    global _foresight_engine
    if _foresight_engine is None:
        _foresight_engine = ForesightEngine(horizon_days=horizon_days)
    return _foresight_engine
