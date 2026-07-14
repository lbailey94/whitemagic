# ruff: noqa: BLE001
"""Critique Protocol — Structured peer review for experiments (v24.3.0).

Inspired by Hyperspace AGI's peer critique stage, this module provides
a structured critique protocol where nodes review each other's experiments
with 1-10 scoring and written feedback.

The critique protocol:
1. Selects experiments ready for critique (result stage, not yet critiqued)
2. Assigns critics (avoiding self-review, preferring diverse nodes)
3. Critics score on 4 dimensions: methodology, novelty, significance, reproducibility
4. Aggregate score triggers breakthrough promotion or revision

Integration points:
    - ResearchDAG: record_critique() called with protocol results
    - PulseVerifier: Tier 2 peer review uses critique scores
    - ExperimentSync: critiques shared via mesh for cross-node review
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.evolution.research_dag import (
    ExperimentStage,
    ResearchDomain,
    get_research_dag,
)

logger = logging.getLogger(__name__)


@dataclass
class CritiqueScore:
    """A single dimension score in a critique."""

    dimension: str  # methodology, novelty, significance, reproducibility
    score: int  # 1-10
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "notes": self.notes,
        }


@dataclass
class Critique:
    """A structured peer critique of an experiment."""

    experiment_id: str
    critic_agent_id: str
    scores: list[CritiqueScore] = field(default_factory=list)
    aggregate_score: float = 0.0
    recommendation: str = ""  # accept, revise, reject
    written_review: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "critic_agent_id": self.critic_agent_id,
            "scores": [s.to_dict() for s in self.scores],
            "aggregate_score": round(self.aggregate_score, 2),
            "recommendation": self.recommendation,
            "written_review": self.written_review,
            "timestamp": self.timestamp,
        }


# Scoring dimensions
CRITIQUE_DIMENSIONS = ["methodology", "novelty", "significance", "reproducibility"]

# Recommendation thresholds
ACCEPT_THRESHOLD = 7.0
REVISE_THRESHOLD = 4.0


class CritiqueProtocol:
    """Structured peer critique protocol for experiment review.

    Manages critique assignment, scoring, and aggregation.
    Critiques are recorded in the ResearchDAG via record_critique().
    """

    _instance: CritiqueProtocol | None = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._dag = get_research_dag()
        self._critiques: dict[str, list[Critique]] = {}
        self._critiques_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        self._total_critiques = 0
        self._accepted = 0
        self._revisions_requested = 0
        self._rejected = 0
        self._breakthroughs_promoted = 0

    @classmethod
    def get_instance(cls) -> CritiqueProtocol:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def critique_experiment(
        self,
        experiment_id: str,
        critic_agent_id: str,
        scores: dict[str, int],
        written_review: str = "",
    ) -> Critique | None:
        """Submit a structured critique for an experiment.

        Args:
            experiment_id: The experiment being critiqued.
            critic_agent_id: ID of the critiquing agent/node.
            scores: Dict of dimension -> score (1-10).
            written_review: Optional written feedback.

        Returns:
            Critique object, or None if experiment not found.
        """
        exp = self._dag._load(experiment_id)
        if exp is None:
            return None

        # Build critique scores
        critique_scores: list[CritiqueScore] = []
        for dim in CRITIQUE_DIMENSIONS:
            score_val = scores.get(dim, 5)
            critique_scores.append(CritiqueScore(
                dimension=dim,
                score=max(1, min(10, score_val)),
            ))

        # Calculate aggregate
        aggregate = sum(s.score for s in critique_scores) / len(critique_scores)

        # Determine recommendation
        if aggregate >= ACCEPT_THRESHOLD:
            recommendation = "accept"
        elif aggregate >= REVISE_THRESHOLD:
            recommendation = "revise"
        else:
            recommendation = "reject"

        critique = Critique(
            experiment_id=experiment_id,
            critic_agent_id=critic_agent_id,
            scores=critique_scores,
            aggregate_score=aggregate,
            recommendation=recommendation,
            written_review=written_review,
        )

        # Record in DAG (uses aggregate score as the 1-10 score)
        self._dag.record_critique(
            experiment_id=experiment_id,
            critic_agent_id=critic_agent_id,
            score=int(round(aggregate)),
            notes=written_review or f"Aggregate: {aggregate:.1f} ({recommendation})",
        )

        # Store locally
        with self._critiques_lock:
            if experiment_id not in self._critiques:
                self._critiques[experiment_id] = []
            self._critiques[experiment_id].append(critique)

        # Update stats
        with self._stats_lock:
            self._total_critiques += 1
            if recommendation == "accept":
                self._accepted += 1
                # Check if this promoted to breakthrough
                updated = self._dag._load(experiment_id)
                if updated and updated.stage == ExperimentStage.BREAKTHROUGH:
                    self._breakthroughs_promoted += 1
            elif recommendation == "revise":
                self._revisions_requested += 1
            else:
                self._rejected += 1

        logger.info(
            "Critique submitted [%s] by %s: aggregate=%.1f recommendation=%s",
            experiment_id[:8], critic_agent_id, aggregate, recommendation,
        )

        return critique

    def auto_critique(
        self,
        experiment_id: str,
        critic_agent_id: str = "auto_critic",
    ) -> Critique | None:
        """Automatically critique an experiment using heuristics.

        Scores are derived from experiment metadata:
        - Methodology: based on parameters richness and trial completion
        - Novelty: based on hypothesis uniqueness
        - Significance: based on fitness score
        - Reproducibility: based on parameter documentation
        """
        exp = self._dag._load(experiment_id)
        if exp is None:
            return None

        # Heuristic scoring
        methodology = 5
        if exp.parameters:
            methodology = min(10, 5 + len(exp.parameters))
        if exp.stage == ExperimentStage.TRIAL:
            methodology += 1

        novelty = 5
        if exp.inspiration_ids:
            novelty = 7  # Building on prior work shows novelty awareness
        if not exp.parent_id:
            novelty = 8  # Original hypothesis

        significance = int(round(exp.fitness_score * 10))
        significance = max(1, min(10, significance))

        reproducibility = 5
        if exp.parameters and len(exp.parameters) >= 3:
            reproducibility = 7
        if exp.metadata.get("outcome"):
            reproducibility += 1

        scores = {
            "methodology": min(10, methodology),
            "novelty": min(10, novelty),
            "significance": min(10, significance),
            "reproducibility": min(10, reproducibility),
        }

        review = (
            f"Auto-critique: methodology={scores['methodology']} "
            f"novelty={scores['novelty']} "
            f"significance={scores['significance']} "
            f"reproducibility={scores['reproducibility']}"
        )

        return self.critique_experiment(
            experiment_id=experiment_id,
            critic_agent_id=critic_agent_id,
            scores=scores,
            written_review=review,
        )

    def get_critiques(self, experiment_id: str) -> list[Critique]:
        """Get all critiques for an experiment."""
        with self._critiques_lock:
            return list(self._critiques.get(experiment_id, []))

    def get_pending_critiques(
        self,
        domain: ResearchDomain | None = None,
        limit: int = 10,
    ) -> list[str]:
        """Get experiment IDs that have results but no critiques yet."""
        experiments = self._dag.get_experiments(
            domain=domain,
            stage=ExperimentStage.RESULT,
            limit=limit * 2,
        )
        with self._critiques_lock:
            return [
                e.experiment_id for e in experiments
                if e.experiment_id not in self._critiques
                or not self._critiques[e.experiment_id]
            ][:limit]

    def get_status(self) -> dict[str, Any]:
        """Get critique protocol status."""
        with self._stats_lock:
            stats = {
                "total_critiques": self._total_critiques,
                "accepted": self._accepted,
                "revisions_requested": self._revisions_requested,
                "rejected": self._rejected,
                "breakthroughs_promoted": self._breakthroughs_promoted,
            }

        with self._critiques_lock:
            experiments_critiqued = len(self._critiques)

        return {
            **stats,
            "experiments_critiqued": experiments_critiqued,
            "dimensions": CRITIQUE_DIMENSIONS,
            "accept_threshold": ACCEPT_THRESHOLD,
            "revise_threshold": REVISE_THRESHOLD,
        }


def get_critique_protocol() -> CritiqueProtocol:
    """Get the singleton CritiqueProtocol instance."""
    return CritiqueProtocol.get_instance()
