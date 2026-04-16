"""Dream cycle phase definitions (PSR-011)."""
from enum import Enum


class DreamPhase(Enum):
    TRIAGE = "triage"
    CONSOLIDATION = "consolidation"
    SERENDIPITY = "serendipity"
    GOVERNANCE = "governance"
    NARRATIVE = "narrative"
    KAIZEN = "kaizen"
    ORACLE = "oracle"
    DECAY = "decay"

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
}
