"""Consolidation strategy definitions extracted from consolidation.py (PSR-011)."""
from enum import Enum


class ConsolidationStrategy(Enum):
    SIMILARITY = "similarity"
    TEMPORAL = "temporal"
    IMPORTANCE = "importance"
    CONSTELLATION = "constellation"
    NARRATIVE = "narrative"

STRATEGY_THRESHOLDS = {
    ConsolidationStrategy.SIMILARITY: 0.85,
    ConsolidationStrategy.TEMPORAL: 3600,
    ConsolidationStrategy.IMPORTANCE: 0.7,
    ConsolidationStrategy.CONSTELLATION: 0.6,
    ConsolidationStrategy.NARRATIVE: 0.75,
}
