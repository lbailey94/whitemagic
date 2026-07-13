# ruff: noqa: BLE001
"""Research DAG — Experiment Lineage Tracking (v24.3.0).

Inspired by Hyperspace's 5-stage research pipeline (Hypothesis → Training →
Paper Generation → Peer Critique → Discovery), this module extends
WhiteMagic's PhylogeneticTracker with experiment-specific lifecycle tracking.

Each experiment flows through stages:
    hypothesis → trial → result → critique → breakthrough
                ↑                                    │
                └────────── inspiration ─────────────┘

The DAG stores experiment nodes in a dedicated `research_experiments` table
and lineage edges in the existing `lineage_edges` table (via PhylogeneticTracker).

Integration points:
    - GalacticHypothesis: zone lifecycle for hypotheses (Core → Far Edge)
    - MetaGalaxy: cross-domain experiment visibility
    - KnowledgeGapActionLoop: gaps become hypotheses
    - Dream Cycle: serendipity on experiment results
    - P2P Mesh: share experiments via GossipSub
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentStage(str, Enum):
    """Lifecycle stages for an experiment."""

    HYPOTHESIS = "hypothesis"
    TRIAL = "trial"
    RESULT = "result"
    CRITIQUE = "critique"
    SYNTHESIS = "synthesis"
    BREAKTHROUGH = "breakthrough"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ResearchDomain(str, Enum):
    """Research domains mapped to WhiteMagic subsystems."""

    COGNITIVE = "cognitive"
    MEMORY = "memory"
    CONSCIOUSNESS = "consciousness"
    EVOLUTION = "evolution"
    SYNTHESIS = "synthesis"
    GOVERNANCE = "governance"
    INFERENCE = "inference"
    CUSTOM = "custom"


@dataclass
class Experiment:
    """A single experiment node in the research DAG."""

    experiment_id: str
    hypothesis: str
    domain: ResearchDomain
    stage: ExperimentStage = ExperimentStage.HYPOTHESIS
    parameters: dict[str, Any] = field(default_factory=dict)
    fitness_score: float = 0.0
    agent_id: str = ""
    parent_id: str | None = None
    inspiration_ids: list[str] = field(default_factory=list)
    critiques: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    galactic_zone: str = "core"

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "domain": self.domain.value,
            "stage": self.stage.value,
            "parameters": self.parameters,
            "fitness_score": self.fitness_score,
            "agent_id": self.agent_id,
            "parent_id": self.parent_id,
            "inspiration_ids": self.inspiration_ids,
            "critiques": self.critiques,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "galactic_zone": self.galactic_zone,
        }

    @classmethod
    def from_row(cls, row: Any) -> Experiment:
        import json

        return cls(
            experiment_id=row["experiment_id"],
            hypothesis=row["hypothesis"],
            domain=ResearchDomain(row["domain"]),
            stage=ExperimentStage(row["stage"]),
            parameters=json.loads(row["parameters"]) if row["parameters"] else {},
            fitness_score=row["fitness_score"],
            agent_id=row["agent_id"] or "",
            parent_id=row["parent_id"],
            inspiration_ids=json.loads(row["inspiration_ids"]) if row["inspiration_ids"] else [],
            critiques=json.loads(row["critiques"]) if row["critiques"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            galactic_zone=row["galactic_zone"] or "core",
        )


class ResearchDAG:
    """Directed Acyclic Graph tracking experiment lineage.

    Stores experiments in a SQLite table and records lineage edges
    via PhylogeneticTracker. Supports the full Hyperspace research
    pipeline: hypothesis → trial → result → critique → breakthrough.
    """

    _instance: ResearchDAG | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._initialized = False
        self._cache: dict[str, Experiment] = {}
        self._cache_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> ResearchDAG:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_table(self) -> None:
        if self._initialized:
            return
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            with um.pool.connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS research_experiments (
                        experiment_id TEXT PRIMARY KEY,
                        hypothesis TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        stage TEXT NOT NULL DEFAULT 'hypothesis',
                        parameters TEXT DEFAULT '{}',
                        fitness_score REAL DEFAULT 0.0,
                        agent_id TEXT DEFAULT '',
                        parent_id TEXT,
                        inspiration_ids TEXT DEFAULT '[]',
                        critiques TEXT DEFAULT '[]',
                        metadata TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        galactic_zone TEXT DEFAULT 'core'
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_domain
                    ON research_experiments(domain)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_stage
                    ON research_experiments(stage)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_parent
                    ON research_experiments(parent_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_fitness
                    ON research_experiments(fitness_score DESC)
                """)
                conn.commit()
            self._initialized = True
        except Exception as e:
            logger.debug("Research DAG table init: %s", e, exc_info=True)

    def _get_conn(self):
        from whitemagic.core.memory.unified import get_unified_memory
        um = get_unified_memory()
        return um.pool.connection()

    def submit_hypothesis(
        self,
        hypothesis: str,
        domain: ResearchDomain = ResearchDomain.COGNITIVE,
        parameters: dict[str, Any] | None = None,
        agent_id: str = "",
        inspiration_ids: list[str] | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Experiment:
        """Submit a new hypothesis to the research DAG.

        If inspiration_ids are provided, records lineage edges from
        each inspiration experiment to this new hypothesis.
        """
        self._ensure_table()

        exp_id = hashlib.sha256(
            f"{hypothesis}:{domain.value}:{time.time()}".encode()
        ).hexdigest()[:16]

        exp = Experiment(
            experiment_id=exp_id,
            hypothesis=hypothesis,
            domain=domain,
            stage=ExperimentStage.HYPOTHESIS,
            parameters=parameters or {},
            agent_id=agent_id,
            parent_id=parent_id,
            inspiration_ids=inspiration_ids or [],
            metadata=metadata or {},
        )

        self._persist(exp)

        # Record inspiration edges (breakthrough → hypothesis)
        if inspiration_ids:
            try:
                from whitemagic.core.memory.phylogenetics import get_phylogenetics
                pg = get_phylogenetics()
                for insp_id in inspiration_ids:
                    pg._record_edge(
                        source_id=insp_id,
                        source_galaxy="research",
                        target_id=exp_id,
                        target_galaxy="research",
                        edge_type="inspiration",
                        mechanism="breakthrough_to_hypothesis",
                        metadata={"domain": domain.value},
                    )
            except Exception as e:
                logger.debug("Inspiration edge recording: %s", e, exc_info=True)

        # Record parent edge if provided
        if parent_id:
            try:
                from whitemagic.core.memory.phylogenetics import get_phylogenetics
                pg = get_phylogenetics()
                pg._record_edge(
                    source_id=parent_id,
                    source_galaxy="research",
                    target_id=exp_id,
                    target_galaxy="research",
                    edge_type="derivative",
                    mechanism="parent_experiment",
                    metadata={"domain": domain.value},
                )
            except Exception as e:
                logger.debug("Parent edge recording: %s", e, exc_info=True)

        with self._cache_lock:
            self._cache[exp_id] = exp

        logger.info(
            "Research DAG: hypothesis submitted [%s] domain=%s: %s",
            exp_id[:8], domain.value, hypothesis[:80],
        )
        return exp

    def record_trial(
        self,
        experiment_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> Experiment | None:
        """Mark an experiment as entering the trial stage."""
        exp = self._load(experiment_id)
        if exp is None:
            return None
        if parameters:
            exp.parameters = {**exp.parameters, **parameters}
        exp.stage = ExperimentStage.TRIAL
        exp.updated_at = datetime.now().isoformat()
        self._persist(exp)
        return exp

    def record_result(
        self,
        experiment_id: str,
        fitness_score: float,
        outcome: dict[str, Any] | None = None,
    ) -> Experiment | None:
        """Record the result of an experiment trial.

        If fitness_score >= breakthrough threshold (default 0.8),
        automatically promotes to BREAKTHROUGH stage.
        """
        exp = self._load(experiment_id)
        if exp is None:
            return None

        exp.fitness_score = fitness_score
        exp.stage = ExperimentStage.RESULT
        exp.updated_at = datetime.now().isoformat()
        if outcome:
            exp.metadata = {**exp.metadata, "outcome": outcome}

        # Auto-promote breakthroughs
        if fitness_score >= 0.8:
            exp.stage = ExperimentStage.BREAKTHROUGH
            exp.galactic_zone = "core"
            self._record_breakthrough(exp)
        else:
            # Assign galactic zone based on fitness
            exp.galactic_zone = self._fitness_to_zone(fitness_score)

        self._persist(exp)

        # Record trial→result edge
        try:
            from whitemagic.core.memory.phylogenetics import get_phylogenetics
            pg = get_phylogenetics()
            pg._record_edge(
                source_id=experiment_id,
                source_galaxy="research",
                target_id=experiment_id,
                target_galaxy="research",
                edge_type="result",
                mechanism="trial_completed",
                metadata={"fitness_score": fitness_score},
            )
        except Exception as e:
            logger.debug("Result edge: %s", e, exc_info=True)

        logger.info(
            "Research DAG: result recorded [%s] fitness=%.4f stage=%s",
            experiment_id[:8], fitness_score, exp.stage.value,
        )
        return exp

    def record_critique(
        self,
        experiment_id: str,
        critic_agent_id: str,
        score: int,
        notes: str = "",
    ) -> Experiment | None:
        """Record a peer critique of an experiment.

        Score is 1-10 (Hyperspace convention). Scores >= 8 trigger
        breakthrough promotion.
        """
        exp = self._load(experiment_id)
        if exp is None:
            return None

        critique = {
            "critic_agent_id": critic_agent_id,
            "score": score,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        exp.critiques.append(critique)
        exp.updated_at = datetime.now().isoformat()

        # Peer critique can promote to breakthrough
        if score >= 8 and exp.stage != ExperimentStage.BREAKTHROUGH:
            exp.stage = ExperimentStage.BREAKTHROUGH
            exp.galactic_zone = "core"
            self._record_breakthrough(exp)

        # Update fitness score with critique-weighted average
        if exp.critiques:
            avg_score = sum(c["score"] for c in exp.critiques) / len(exp.critiques)
            exp.fitness_score = max(exp.fitness_score, avg_score / 10.0)

        self._persist(exp)

        logger.info(
            "Research DAG: critique recorded [%s] score=%d stage=%s",
            experiment_id[:8], score, exp.stage.value,
        )
        return exp

    def mark_failed(
        self,
        experiment_id: str,
        reason: str = "",
    ) -> Experiment | None:
        """Mark an experiment as failed."""
        exp = self._load(experiment_id)
        if exp is None:
            return None
        exp.stage = ExperimentStage.FAILED
        exp.galactic_zone = "far_edge"
        exp.updated_at = datetime.now().isoformat()
        if reason:
            exp.metadata = {**exp.metadata, "failure_reason": reason}
        self._persist(exp)
        return exp

    def get_lineage(self, experiment_id: str, max_depth: int = 10) -> dict[str, Any]:
        """Get the full lineage tree for an experiment.

        Returns ancestors (inspirations + parents) and descendants
        (experiments inspired by this one).
        """
        self._ensure_table()
        ancestors = self._walk_ancestors(experiment_id, max_depth)
        descendants = self._walk_descendants(experiment_id, max_depth)

        exp = self._load(experiment_id)
        return {
            "experiment_id": experiment_id,
            "hypothesis": exp.hypothesis if exp else "",
            "domain": exp.domain.value if exp else "",
            "stage": exp.stage.value if exp else "",
            "fitness_score": exp.fitness_score if exp else 0.0,
            "ancestors": ancestors,
            "descendants": descendants,
            "lineage_depth": len(ancestors),
            "progeny_count": len(descendants),
        }

    def get_breakthroughs(
        self,
        domain: ResearchDomain | None = None,
        limit: int = 20,
    ) -> list[Experiment]:
        """Get top breakthroughs, optionally filtered by domain."""
        self._ensure_table()
        try:
            with self._get_conn() as conn:
                conn.row_factory = __import__("sqlite3").Row
                if domain:
                    rows = conn.execute(
                        """SELECT * FROM research_experiments
                           WHERE stage = 'breakthrough' AND domain = ?
                           ORDER BY fitness_score DESC LIMIT ?""",
                        (domain.value, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT * FROM research_experiments
                           WHERE stage = 'breakthrough'
                           ORDER BY fitness_score DESC LIMIT ?""",
                        (limit,),
                    ).fetchall()
                return [Experiment.from_row(row) for row in rows]
        except Exception as e:
            logger.debug("Get breakthroughs: %s", e, exc_info=True)
            return []

    def get_experiments(
        self,
        domain: ResearchDomain | None = None,
        stage: ExperimentStage | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Experiment]:
        """Query experiments with optional filters."""
        self._ensure_table()
        try:
            with self._get_conn() as conn:
                conn.row_factory = __import__("sqlite3").Row
                query = "SELECT * FROM research_experiments WHERE 1=1"
                params: list[Any] = []
                if domain:
                    query += " AND domain = ?"
                    params.append(domain.value)
                if stage:
                    query += " AND stage = ?"
                    params.append(stage.value)
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                rows = conn.execute(query, params).fetchall()
                return [Experiment.from_row(row) for row in rows]
        except Exception as e:
            logger.debug("Get experiments: %s", e, exc_info=True)
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get research DAG statistics."""
        self._ensure_table()
        try:
            with self._get_conn() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM research_experiments"
                ).fetchone()[0]

                by_stage: dict[str, int] = {}
                for row in conn.execute(
                    "SELECT stage, COUNT(*) as cnt FROM research_experiments GROUP BY stage"
                ).fetchall():
                    by_stage[row[0]] = row[1]

                by_domain: dict[str, int] = {}
                for row in conn.execute(
                    "SELECT domain, COUNT(*) as cnt FROM research_experiments GROUP BY domain"
                ).fetchall():
                    by_domain[row[0]] = row[1]

                breakthroughs = by_stage.get("breakthrough", 0)
                avg_fitness = 0.0
                if total > 0:
                    result = conn.execute(
                        "SELECT AVG(fitness_score) FROM research_experiments WHERE stage != 'hypothesis'"
                    ).fetchone()
                    avg_fitness = result[0] if result and result[0] is not None else 0.0

                top_score = 0.0
                if breakthroughs > 0:
                    result = conn.execute(
                        "SELECT MAX(fitness_score) FROM research_experiments WHERE stage = 'breakthrough'"
                    ).fetchone()
                    top_score = result[0] if result and result[0] is not None else 0.0

                return {
                    "total_experiments": total,
                    "by_stage": by_stage,
                    "by_domain": by_domain,
                    "breakthroughs": breakthroughs,
                    "avg_fitness": round(avg_fitness, 4),
                    "top_fitness": round(top_score, 4),
                }
        except Exception as e:
            return {"error": str(e)}

    def get_domain_leaderboard(
        self,
        domain: ResearchDomain,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get the top experiments for a domain (leaderboard)."""
        self._ensure_table()
        try:
            with self._get_conn() as conn:
                conn.row_factory = __import__("sqlite3").Row
                rows = conn.execute(
                    """SELECT experiment_id, hypothesis, fitness_score, stage,
                              agent_id, created_at, galactic_zone
                       FROM research_experiments
                       WHERE domain = ? AND stage IN ('result', 'breakthrough')
                       ORDER BY fitness_score DESC LIMIT ?""",
                    (domain.value, limit),
                ).fetchall()
                return [
                    {
                        "rank": i + 1,
                        "experiment_id": row["experiment_id"],
                        "hypothesis": row["hypothesis"][:100],
                        "fitness_score": round(row["fitness_score"], 4),
                        "stage": row["stage"],
                        "agent_id": row["agent_id"],
                        "created_at": row["created_at"],
                        "galactic_zone": row["galactic_zone"],
                    }
                    for i, row in enumerate(rows)
                ]
        except Exception as e:
            logger.debug("Domain leaderboard: %s", e, exc_info=True)
            return []

    def _persist(self, exp: Experiment) -> None:
        """Persist an experiment to SQLite."""
        self._ensure_table()
        import json
        from whitemagic.utils.fast_json import dumps_str as _json_dumps

        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO research_experiments
                       (experiment_id, hypothesis, domain, stage, parameters,
                        fitness_score, agent_id, parent_id, inspiration_ids,
                        critiques, metadata, created_at, updated_at, galactic_zone)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        exp.experiment_id,
                        exp.hypothesis,
                        exp.domain.value,
                        exp.stage.value,
                        _json_dumps(exp.parameters, default=str),
                        exp.fitness_score,
                        exp.agent_id,
                        exp.parent_id,
                        json.dumps(exp.inspiration_ids),
                        json.dumps(exp.critiques),
                        _json_dumps(exp.metadata, default=str),
                        exp.created_at,
                        exp.updated_at,
                        exp.galactic_zone,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.debug("Experiment persist: %s", e, exc_info=True)

    def _load(self, experiment_id: str) -> Experiment | None:
        """Load an experiment from SQLite (with cache)."""
        with self._cache_lock:
            if experiment_id in self._cache:
                return self._cache[experiment_id]

        self._ensure_table()
        try:
            with self._get_conn() as conn:
                conn.row_factory = __import__("sqlite3").Row
                row = conn.execute(
                    "SELECT * FROM research_experiments WHERE experiment_id = ?",
                    (experiment_id,),
                ).fetchone()
                if row:
                    exp = Experiment.from_row(row)
                    with self._cache_lock:
                        self._cache[experiment_id] = exp
                    return exp
        except Exception as e:
            logger.debug("Experiment load: %s", e, exc_info=True)
        return None

    def _walk_ancestors(self, experiment_id: str, max_depth: int) -> list[dict[str, Any]]:
        """Walk upstream via lineage_edges to find inspiration/parent experiments."""
        try:
            from whitemagic.core.memory.phylogenetics import get_phylogenetics
            pg = get_phylogenetics()
            ancestors: list[dict[str, Any]] = []
            visited = {experiment_id}
            frontier = [experiment_id]

            for depth in range(max_depth):
                if not frontier:
                    break
                next_frontier: list[str] = []
                with self._get_conn() as conn:
                    conn.row_factory = __import__("sqlite3").Row
                    for eid in frontier:
                        rows = conn.execute(
                            """SELECT * FROM lineage_edges
                               WHERE target_id = ? AND target_galaxy = 'research'
                               ORDER BY created_at""",
                            (eid,),
                        ).fetchall()
                        for row in rows:
                            src = row["source_id"]
                            if src not in visited:
                                visited.add(src)
                                next_frontier.append(src)
                                # Load the ancestor experiment
                                anc = self._load(src)
                                ancestors.append({
                                    "experiment_id": src,
                                    "hypothesis": anc.hypothesis if anc else "",
                                    "domain": anc.domain.value if anc else "",
                                    "fitness_score": anc.fitness_score if anc else 0.0,
                                    "stage": anc.stage.value if anc else "",
                                    "edge_type": row["edge_type"],
                                    "depth": depth + 1,
                                })
                frontier = next_frontier
            return ancestors
        except Exception as e:
            logger.debug("Ancestor walk: %s", e, exc_info=True)
            return []

    def _walk_descendants(self, experiment_id: str, max_depth: int) -> list[dict[str, Any]]:
        """Walk downstream via lineage_edges to find inspired experiments."""
        try:
            descendants: list[dict[str, Any]] = []
            visited = {experiment_id}
            frontier = [experiment_id]

            for depth in range(max_depth):
                if not frontier:
                    break
                next_frontier: list[str] = []
                with self._get_conn() as conn:
                    conn.row_factory = __import__("sqlite3").Row
                    for eid in frontier:
                        rows = conn.execute(
                            """SELECT * FROM lineage_edges
                               WHERE source_id = ? AND source_galaxy = 'research'
                               ORDER BY created_at""",
                            (eid,),
                        ).fetchall()
                        for row in rows:
                            tgt = row["target_id"]
                            if tgt not in visited:
                                visited.add(tgt)
                                next_frontier.append(tgt)
                                desc = self._load(tgt)
                                descendants.append({
                                    "experiment_id": tgt,
                                    "hypothesis": desc.hypothesis if desc else "",
                                    "domain": desc.domain.value if desc else "",
                                    "fitness_score": desc.fitness_score if desc else 0.0,
                                    "stage": desc.stage.value if desc else "",
                                    "edge_type": row["edge_type"],
                                    "depth": depth + 1,
                                })
                frontier = next_frontier
            return descendants
        except Exception as e:
            logger.debug("Descendant walk: %s", e, exc_info=True)
            return []

    def _fitness_to_zone(self, fitness: float) -> str:
        """Map fitness score to galactic zone."""
        if fitness >= 0.8:
            return "core"
        elif fitness >= 0.6:
            return "inner_rim"
        elif fitness >= 0.4:
            return "mid_band"
        elif fitness >= 0.2:
            return "outer_rim"
        else:
            return "far_edge"

    def _record_breakthrough(self, exp: Experiment) -> None:
        """Record a breakthrough event in phylogenetics and persist to codex."""
        try:
            from whitemagic.core.memory.phylogenetics import get_phylogenetics
            pg = get_phylogenetics()
            pg._record_edge(
                source_id=exp.experiment_id,
                source_galaxy="research",
                target_id=exp.experiment_id,
                target_galaxy="research",
                edge_type="breakthrough",
                mechanism="fitness_threshold",
                metadata={
                    "fitness_score": exp.fitness_score,
                    "domain": exp.domain.value,
                },
            )
        except Exception as e:
            logger.debug("Breakthrough edge: %s", e, exc_info=True)

        # Persist breakthrough to codex galaxy
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            um.store(
                title=f"[Breakthrough] {exp.hypothesis[:80]}",
                content=f"Domain: {exp.domain.value}\nFitness: {exp.fitness_score:.4f}\nExperiment ID: {exp.experiment_id}",
                tags={"breakthrough", "research", exp.domain.value, "auto_generated"},
                importance=min(exp.fitness_score, 1.0),
                galaxy="codex",
                metadata={
                    "experiment_id": exp.experiment_id,
                    "domain": exp.domain.value,
                    "fitness_score": exp.fitness_score,
                    "source": "research_dag",
                },
            )
        except Exception as e:
            logger.debug("Breakthrough persist: %s", e, exc_info=True)

    def clear_cache(self) -> None:
        """Clear the in-memory experiment cache."""
        with self._cache_lock:
            self._cache.clear()

    def generate_synthesis(
        self,
        domain: ResearchDomain | None = None,
        min_experiments: int = 5,
        top_n: int = 10,
    ) -> dict[str, Any] | None:
        """Generate a synthesis (mini research paper) from accumulated experiments.

        When N+ experiments have results in a domain, this method:
        1. Gathers top experiments by fitness score
        2. Extracts common themes and patterns
        3. Generates a structured synthesis document
        4. Records the synthesis as a new experiment in the DAG
        5. Persists the synthesis to the codex galaxy

        Inspired by Hyperspace AGI's paper generation stage.

        Args:
            domain: Filter by domain. If None, uses all domains.
            min_experiments: Minimum experiments needed to trigger synthesis.
            top_n: Number of top experiments to include.

        Returns:
            Dict with synthesis data, or None if not enough experiments.
        """
        self._ensure_table()

        # Gather experiments with results
        experiments = self.get_experiments(
            domain=domain,
            stage=ExperimentStage.RESULT,
            limit=100,
        )
        breakthroughs = self.get_breakthroughs(domain=domain, limit=20)
        all_results = experiments + breakthroughs

        if len(all_results) < min_experiments:
            return None

        # Sort by fitness and take top N
        all_results.sort(key=lambda e: e.fitness_score, reverse=True)
        top_experiments = all_results[:top_n]

        # Extract themes
        hypotheses = [e.hypothesis for e in top_experiments]
        domains_represented = set(e.domain.value for e in top_experiments)
        avg_fitness = sum(e.fitness_score for e in top_experiments) / len(top_experiments)
        max_fitness = top_experiments[0].fitness_score
        breakthrough_count = sum(
            1 for e in top_experiments if e.stage == ExperimentStage.BREAKTHROUGH
        )

        # Group by agent source
        agents: dict[str, int] = {}
        for e in top_experiments:
            agent = e.agent_id or "unknown"
            agents[agent] = agents.get(agent, 0) + 1

        # Build synthesis document
        synthesis_title = f"Synthesis: {domain.value if domain else 'cross-domain'} — {len(top_experiments)} experiments"
        synthesis_body = self._format_synthesis(
            title=synthesis_title,
            experiments=top_experiments,
            avg_fitness=avg_fitness,
            max_fitness=max_fitness,
            breakthrough_count=breakthrough_count,
            domains_represented=domains_represented,
            agents=agents,
        )

        # Record synthesis as a new experiment
        synth_exp = self.submit_hypothesis(
            hypothesis=synthesis_title,
            domain=domain or ResearchDomain.SYNTHESIS,
            parameters={
                "source_experiments": [e.experiment_id for e in top_experiments],
                "min_experiments": min_experiments,
                "top_n": top_n,
            },
            agent_id="synthesis_engine",
            inspiration_ids=[e.experiment_id for e in top_experiments],
            metadata={
                "source": "synthesis_engine",
                "avg_fitness": avg_fitness,
                "max_fitness": max_fitness,
                "breakthrough_count": breakthrough_count,
                "experiments_synthesized": len(top_experiments),
            },
        )

        # Mark as synthesis stage
        synth_exp.stage = ExperimentStage.SYNTHESIS
        synth_exp.fitness_score = avg_fitness
        synth_exp.updated_at = datetime.now().isoformat()
        self._persist(synth_exp)

        # Persist to codex galaxy
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            um.store(
                title=synthesis_title,
                content=synthesis_body,
                tags={"synthesis", "research", "auto_generated"},
                importance=min(avg_fitness, 1.0),
                galaxy="codex",
                metadata={
                    "experiment_id": synth_exp.experiment_id,
                    "source_experiments": len(top_experiments),
                    "avg_fitness": avg_fitness,
                    "source": "research_dag_synthesis",
                },
            )
        except Exception as e:
            logger.debug("Synthesis persist: %s", e, exc_info=True)

        logger.info(
            "Research DAG: synthesis generated [%s] from %d experiments, avg_fitness=%.4f",
            synth_exp.experiment_id[:8], len(top_experiments), avg_fitness,
        )

        return {
            "synthesis_id": synth_exp.experiment_id,
            "title": synthesis_title,
            "experiments_synthesized": len(top_experiments),
            "avg_fitness": round(avg_fitness, 4),
            "max_fitness": round(max_fitness, 4),
            "breakthrough_count": breakthrough_count,
            "domains_represented": list(domains_represented),
            "agents": agents,
            "body": synthesis_body,
        }

    def _format_synthesis(
        self,
        title: str,
        experiments: list[Experiment],
        avg_fitness: float,
        max_fitness: float,
        breakthrough_count: int,
        domains_represented: set[str],
        agents: dict[str, int],
    ) -> str:
        """Format a synthesis document from experiment data."""
        lines = [f"# {title}", ""]
        lines.append(f"**Generated**: {datetime.now().isoformat()}")
        lines.append(f"**Experiments**: {len(experiments)}")
        lines.append(f"**Average Fitness**: {avg_fitness:.4f}")
        lines.append(f"**Max Fitness**: {max_fitness:.4f}")
        lines.append(f"**Breakthroughs**: {breakthrough_count}")
        lines.append(f"**Domains**: {', '.join(sorted(domains_represented))}")
        lines.append(f"**Agents**: {', '.join(f'{k}({v})' for k, v in sorted(agents.items(), key=lambda x: -x[1]))}")
        lines.append("")

        lines.append("## Top Experiments")
        lines.append("")
        for i, exp in enumerate(experiments):
            lines.append(f"### {i+1}. {exp.hypothesis[:100]}")
            lines.append(f"- **ID**: {exp.experiment_id[:16]}")
            lines.append(f"- **Fitness**: {exp.fitness_score:.4f}")
            lines.append(f"- **Stage**: {exp.stage.value}")
            lines.append(f"- **Domain**: {exp.domain.value}")
            lines.append(f"- **Agent**: {exp.agent_id}")
            if exp.parameters:
                lines.append(f"- **Parameters**: {exp.parameters}")
            lines.append("")

        lines.append("## Key Findings")
        lines.append("")
        if breakthrough_count > 0:
            lines.append(f"- {breakthrough_count} breakthrough(s) achieved fitness >= 0.8")
        lines.append(f"- Peak fitness of {max_fitness:.4f} demonstrates strong signal")
        lines.append(f"- Average fitness of {avg_fitness:.4f} across {len(experiments)} experiments")
        if len(domains_represented) > 1:
            lines.append(f"- Cross-domain synthesis spanning {len(domains_represented)} domains")
        lines.append("")

        return "\n".join(lines)


def get_research_dag() -> ResearchDAG:
    """Get the singleton ResearchDAG instance."""
    return ResearchDAG.get_instance()
