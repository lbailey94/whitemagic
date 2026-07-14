"""Phase 6 — Retrieval and Search Query Planning.

Explicit staged retrieval pipeline with per-stage timing, candidate
provenance, bounded federated galaxy search, and configurable channel
weights.

Stages:
  1. candidate_acquisition — gather raw candidates from galaxy backends
  2. lexical_ranking — FTS5 BM25 scoring per galaxy
  3. semantic_ranking — embedding similarity (HNSW or brute-force)
  4. spatial_ranking — 5D holographic coordinate nearest-neighbour
  5. entity_boost — entity-graph retrieval boosting
  6. constellation_boost — constellation membership multiplicative boost
  7. reranking — second-pass multi-signal re-scoring
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class RetrievalStage(StrEnum):
    """Explicit stages in the retrieval pipeline."""

    CANDIDATE_ACQUISITION = "candidate_acquisition"
    LEXICAL_RANKING = "lexical_ranking"
    SEMANTIC_RANKING = "semantic_ranking"
    SPATIAL_RANKING = "spatial_ranking"
    ENTITY_BOOST = "entity_boost"
    CONSTELLATION_BOOST = "constellation_boost"
    RERANKING = "reranking"


@dataclass
class StageTiming:
    """Timing and candidate count for a single retrieval stage."""

    stage: RetrievalStage
    duration_ms: float = 0.0
    candidates_in: int = 0
    candidates_out: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class CandidateScore:
    """Per-candidate score with provenance across retrieval stages.

    Each stage contributes a subscore; the final RRF score is the
    weighted sum of all stage contributions.
    """

    memory_id: str
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    spatial_score: float = 0.0
    entity_score: float = 0.0
    constellation_score: float = 0.0
    rerank_adjustment: float = 0.0
    final_score: float = 0.0
    galaxy: str = ""
    channels: set[str] = field(default_factory=set)

    @property
    def provenance(self) -> str:
        """Which channels contributed to this candidate's score."""
        return "+".join(sorted(self.channels)) if self.channels else "none"


@dataclass
class QueryProfile:
    """Per-query or per-policy-profile retrieval configuration.

    Allows callers to customise channel weights, over-fetch ratios,
    and stage toggles without modifying global state.
    """

    lexical_weight: float = 1.0
    semantic_weight: float = 1.0
    spatial_weight: float = 0.5
    entity_boost_weight: float = 0.3
    constellation_boost: float = 0.3
    diversity_bonus: float = 0.05
    rerank: bool = True
    include_skills: bool = True
    include_cold: bool = False
    rrf_k: int = 60
    over_fetch_ratio: int = 3
    max_candidates: int = 500
    galaxy_concurrency: int = 4
    axis_weights: dict[str, float] | None = None
    min_similarity: float = 0.25
    constellation_threshold: float = 0.25


@dataclass
class LatencyBudget:
    """Latency budget for a query class (milliseconds)."""

    p50: float
    p95: float
    p99: float


# Predefined latency budgets for common query classes
LATENCY_BUDGETS: dict[str, LatencyBudget] = {
    "simple": LatencyBudget(p50=5.0, p95=15.0, p99=30.0),
    "complex": LatencyBudget(p50=20.0, p95=60.0, p99=120.0),
    "federated": LatencyBudget(p50=50.0, p95=150.0, p99=300.0),
    "degraded": LatencyBudget(p50=100.0, p95=300.0, p99=600.0),
}


@dataclass
class RetrievalResult:
    """Result of a planned retrieval operation.

    Contains the final ranked candidates plus per-stage telemetry
    for observability and latency budget validation.
    """

    candidates: list[CandidateScore] = field(default_factory=list)
    stage_timings: list[StageTiming] = field(default_factory=list)
    total_duration_ms: float = 0.0
    galaxies_searched: int = 0
    query_class: str = "simple"
    degraded_stages: list[str] = field(default_factory=list)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def within_budget(self) -> bool:
        budget = LATENCY_BUDGETS.get(self.query_class)
        if budget is None:
            return True
        return self.total_duration_ms <= budget.p99

    def stage_timing(self, stage: RetrievalStage) -> StageTiming | None:
        for st in self.stage_timings:
            if st.stage == stage:
                return st
        return None

    def to_telemetry_dict(self) -> dict[str, Any]:
        """Serialise to a telemetry-friendly dict."""
        return {
            "total_duration_ms": round(self.total_duration_ms, 2),
            "candidate_count": self.candidate_count,
            "galaxies_searched": self.galaxies_searched,
            "query_class": self.query_class,
            "within_budget": self.within_budget,
            "degraded_stages": self.degraded_stages,
            "stages": [
                {
                    "stage": st.stage.value,
                    "duration_ms": round(st.duration_ms, 2),
                    "candidates_in": st.candidates_in,
                    "candidates_out": st.candidates_out,
                    "ok": st.ok,
                    "error": st.error,
                }
                for st in self.stage_timings
            ],
        }


def classify_query(query: str, galaxy_count: int, profile: QueryProfile | None = None) -> str:
    """Classify a query into a latency budget class.

    Args:
        query: The search query string.
        galaxy_count: Number of galaxies being searched.
        profile: Optional query profile (affects classification).

    Returns:
        One of: "simple", "complex", "federated", "degraded".
    """
    if galaxy_count > 1:
        return "federated"
    query_len = len(query or "")
    if query_len > 200 or (profile and profile.include_cold):
        return "complex"
    return "simple"


def now_ms() -> float:
    """Current monotonic time in milliseconds."""
    return time.perf_counter() * 1000.0


def elapsed_ms(start: float) -> float:
    """Milliseconds since a start time from now_ms()."""
    return time.perf_counter() * 1000.0 - start
