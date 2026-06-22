"""Convergence Bridge — TemporalForecastDB → Rust Convergence Detector.

Exports predictions from the DB as ConvergenceSignal JSON, runs the Rust
convergence detector, and returns clusters of converging claims.
"""

from __future__ import annotations

import json
from typing import Any

from whitemagic.forecasting.temporal_db import TemporalForecastDB


def detect_converging_claims(
    db: TemporalForecastDB | None = None,
    threshold: float = 0.25,
    min_signals: int = 2,
) -> list[dict[str, Any]]:
    """Run convergence detection on all predictions in the DB.

    Args:
        db: TemporalForecastDB instance (default: new default instance).
        threshold: Jaccard similarity threshold for clustering.
        min_signals: Minimum cluster size to include.

    Returns:
        List of ConvergenceCluster dicts sorted by score descending.
    """
    db = db or TemporalForecastDB()
    rows = db.export_claims()

    signals: list[dict[str, Any]] = []
    for row in rows:
        signals.append(
            {
                "id": row["id"],
                "claim": row["claim"],
                "domain": row.get("category") or "general",
                "source_date": row["source_date"],
                "confidence": row.get("confidence") or 0.5,
                "source_ref": row.get("source_ref") or "",
            }
        )

    if len(signals) < min_signals:
        return []

    import whitemagic_rust  # late import so the module loads even if Rust unavailable

    result_json = whitemagic_rust.detect_convergence(
        json.dumps(signals), threshold, min_signals
    )
    return json.loads(result_json)


def convergence_score(
    db: TemporalForecastDB | None = None,
    threshold: float = 0.25,
) -> float:
    """Return the single strongest convergence score across all DB claims.

    Returns 0.0 if no clusters meet the threshold.
    """
    db = db or TemporalForecastDB()
    rows = db.export_claims()

    signals: list[dict[str, Any]] = []
    for row in rows:
        signals.append(
            {
                "id": row["id"],
                "claim": row["claim"],
                "domain": row.get("category") or "general",
                "source_date": row["source_date"],
                "confidence": row.get("confidence") or 0.5,
                "source_ref": row.get("source_ref") or "",
            }
        )

    if len(signals) < 2:
        return 0.0

    import whitemagic_rust

    return whitemagic_rust.convergence_score(json.dumps(signals), threshold)
