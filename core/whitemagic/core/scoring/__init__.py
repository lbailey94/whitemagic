"""Scoring modules — neuro-score and related algorithms."""

try:
    from .neuro_score import (
        NeuroScoreInput,
        NeuroScoreResult,
        batch_neuro_score,
        neuro_score,
    )
except ImportError:
    neuro_score = None  # type: ignore[assignment,misc]
    batch_neuro_score = None  # type: ignore[assignment,misc]
    NeuroScoreInput = None  # type: ignore[assignment,misc]
    NeuroScoreResult = None  # type: ignore[assignment,misc]

__all__ = ["neuro_score", "batch_neuro_score", "NeuroScoreInput", "NeuroScoreResult"]
