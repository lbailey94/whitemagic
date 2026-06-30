"""Dream cycle phase definitions (PSR-011).

Re-exports from the canonical source in dream_cycle.py to avoid
duplicate enum drift. The 8-phase version was superseded by the
12-phase version in v17.0.
"""

from whitemagic.core.dreaming.dream_cycle import DreamPhase

PHASE_ORDER = list(DreamPhase)

PHASE_DESCRIPTIONS = {
    DreamPhase.TRIAGE: "Auto-tag and drift-correct memories",
    DreamPhase.CONSOLIDATION: "Detect constellations via HDBSCAN",
    DreamPhase.SERENDIPITY: "Bridge synthesis and insight creation",
    DreamPhase.GOVERNANCE: "Community health and echo chamber detection",
    DreamPhase.NARRATIVE: "Cluster and compress narrative threads",
    DreamPhase.KAIZEN: "Emergence insights and persisting learnings",
    DreamPhase.ORACLE: "Predictive suggestions for next session",
    DreamPhase.DECAY: "Mindful forgetting sweep",
    DreamPhase.CONSTELLATION: "Auto-merge related constellations",
    DreamPhase.PREDICTION: "Predictive drift detection",
    DreamPhase.ENRICHMENT: "Entity extraction & semantic enrichment",
    DreamPhase.HARMONIZE: "Wu Xing balance & harmony tuning",
}

__all__ = ["DreamPhase", "PHASE_ORDER", "PHASE_DESCRIPTIONS"]
