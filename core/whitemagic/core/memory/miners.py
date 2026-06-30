# ruff: noqa: BLE001, E402
from __future__ import annotations

"""Pattern Extraction Engine - Week 3 of v2.3.1.

Analyzes long-term memories to extract:
- Solutions (when X happens, do Y)
- Anti-patterns (avoid Z because...)
- Heuristics (if condition, then action)
- Optimizations (proven approaches)
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime


logger = logging.getLogger(__name__)

try:
    from whitemagic.core.resonance.gan_ying import EventType
    # Ensure EventType is used to satisfy linter
    _ = EventType
    RESONANCE_AVAILABLE = True
except ImportError:
    RESONANCE_AVAILABLE = False

try:
    import whitemagic_rs
    # Ensure whitemagic_rs is used to satisfy linter
    _rs_ref = whitemagic_rs  # noqa: F841
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


@dataclass
class Pattern:
    """Represents an extracted pattern."""

    pattern_type: str  # solution, anti_pattern, heuristic, optimization
    title: str
    description: str
    confidence: float
    frequency: int = 1
    examples: list[str] | None = None

    def __post_init__(self) -> None:
        if self.examples is None:
            self.examples = []


@dataclass
class PatternReport:
    """Report of pattern extraction results."""

    total_memories: int
    patterns_found: int
    solutions: list[Pattern]
    anti_patterns: list[Pattern]
    heuristics: list[Pattern]
    optimizations: list[Pattern]
    duration_seconds: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_memories": self.total_memories,
            "patterns_found": self.patterns_found,
            "solutions": [asdict(p) for p in self.solutions],
            "anti_patterns": [asdict(p) for p in self.anti_patterns],
            "heuristics": [asdict(p) for p in self.heuristics],
            "optimizations": [asdict(p) for p in self.optimizations],
            "duration_seconds": self.duration_seconds,
        }


# PatternEngine is canonical in pattern_engine.py — re-export to avoid drift
from whitemagic.core.memory.pattern_engine import PatternEngine, get_engine  # noqa: E402,F401

"""Cross-Memory Association Miner.
===============================
Discovers hidden semantic links between memories that haven't been
explicitly associated. Uses lightweight content analysis (keyword overlap,
title similarity, temporal proximity) to propose new associations.

Works alongside the Consolidation engine — consolidation clusters recent
memories, while the miner discovers deep cross-temporal connections
across the entire Data Sea.

No memory is ever deleted or modified — only new association links are
created. New links are bidirectional with initial strength proportional
to the semantic overlap score.

Usage:
    from whitemagic.core.memory.association_miner import get_association_miner
    miner = get_association_miner()
    report = miner.mine(sample_size=500)
"""


import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, cast

logger = logging.getLogger(__name__)


_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "but", "and", "or",
    "if", "while", "about", "up", "out", "off", "over", "this", "that",
    "these", "those", "it", "its", "my", "your", "his", "her", "our",
    "their", "what", "which", "who", "whom", "me", "him", "them", "we",
    "you", "they", "i", "he", "she", "us", "self", "none", "also", "any",
    "def", "class", "import", "return", "true", "false", "none",
})

_WORD_RE = re.compile(r"[a-z_][a-z0-9_]{2,}")


@dataclass
class ProposedLink:
    """A proposed association between two memories."""

    source_id: str
    target_id: str
    overlap_score: float  # 0.0-1.0 semantic overlap
    shared_keywords: set[str]
    reason: str  # Human-readable explanation

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "overlap_score": round(self.overlap_score, 3),
            "shared_keywords": sorted(self.shared_keywords)[:10],
            "reason": self.reason,
        }


@dataclass
class MiningReport:
    """Results from an association mining run."""

    memories_sampled: int = 0
    pairs_evaluated: int = 0
    links_proposed: int = 0
    links_created: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    top_proposals: list[ProposedLink] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memories_sampled": self.memories_sampled,
            "pairs_evaluated": self.pairs_evaluated,
            "links_proposed": self.links_proposed,
            "links_created": self.links_created,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
            "top_proposals": [p.to_dict() for p in self.top_proposals[:10]],
        }


class AssociationMiner:
    """Discovers hidden semantic connections between memories.

    Strategy:
    1. Sample a diverse set of memories (mix of zones, types, ages).
    2. Extract keyword fingerprints from each memory's title + content.
    3. Compare all pairs (or a smart subset) for keyword overlap.
    4. Propose links for pairs above a threshold that aren't already associated.
    5. Optionally persist new associations to the backend.
    """

    def __init__(
        self,
        min_overlap: float = 0.15,
        max_proposals_per_run: int = 50,
        persist: bool = True,
    ):
        self._min_overlap = min_overlap
        self._max_proposals = max_proposals_per_run
        self._persist = persist
        self._lock = threading.Lock()
        self._total_runs = 0
        self._total_links_created = 0

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 50) -> set[str]:
        """Extract meaningful keywords from text.

        Uses Rust PyO3 extraction when available (v13.3.2), falls back to
        Python regex. Zig SIMD keyword path was disabled (v13.3.1) due to
        ctypes marshaling overhead making it 15× slower than Python.
        """
        # Try Rust PyO3 keyword extraction (v13.3.2) — zero-copy strings
        if len(text) > 200:
            try:
                from whitemagic.optimization.rust_accelerators import (
                    keyword_extract as rust_kw,
                )
                result = rust_kw(text, max_keywords)
                if result is not None:
                    return cast(set[str], result)
            except (ImportError, AttributeError):
                pass

        # Python extraction (fastest path for keywords)
        text_lower = text.lower()
        words = _WORD_RE.findall(text_lower)
        keywords = {w for w in words if w not in _STOP_WORDS and len(w) > 2}

        # Frequency-based selection: keep most frequent keywords
        if len(keywords) > max_keywords:
            freq: defaultdict[str, int] = defaultdict(int)
            for w in words:
                if w in keywords:
                    freq[w] += 1
            sorted_kw = sorted(keywords, key=lambda k: freq[k], reverse=True)
            keywords = set(sorted_kw[:max_keywords])

        return keywords

    @staticmethod
    def _compute_overlap(kw_a: set[str], kw_b: set[str]) -> tuple[float, set[str]]:
        """Compute Jaccard-like overlap between two keyword sets."""
        if not kw_a or not kw_b:
            return 0.0, set()

        shared = kw_a & kw_b
        union_size = len(kw_a | kw_b)
        if union_size == 0:
            return 0.0, set()

        # Weighted Jaccard: penalize very small shared sets
        raw_jaccard = len(shared) / union_size
        # Boost if many shared keywords (absolute count matters)
        count_bonus = min(1.0, len(shared) / 5.0) * 0.3
        score = min(1.0, raw_jaccard + count_bonus)
        return score, shared

    def mine(self, sample_size: int = 200) -> MiningReport:
        """Run a single association mining pass.

        Args:
            sample_size: How many memories to sample for comparison.

        """
        start = time.perf_counter()
        report = MiningReport()

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Association mining: could not get memory system: %s", e, exc_info=True)
            return report

        # Sample diverse memories: mix of zones
        all_mems = []
        try:
            # Get a mix: some from core/inner_rim, some from mid/outer
            core_mems = um.backend.list_recent(limit=sample_size // 4)
            # Also get some random from deeper zones via SQL
            import sqlite3
            with um.backend.pool.connection() as conn:
                conn.row_factory = sqlite3.Row
                # Sample from different galactic zones
                rows = conn.execute(
                    """SELECT * FROM memories
                       WHERE galactic_distance < 0.40
                         AND memory_type != 'quarantined'
                       ORDER BY RANDOM() LIMIT ?""",
                    (sample_size // 4,),
                ).fetchall()
                inner_mems = um.backend._batch_hydrate(rows, conn)

                rows = conn.execute(
                    """SELECT * FROM memories
                       WHERE galactic_distance BETWEEN 0.40 AND 0.70
                         AND memory_type != 'quarantined'
                       ORDER BY RANDOM() LIMIT ?""",
                    (sample_size // 4,),
                ).fetchall()
                mid_mems = um.backend._batch_hydrate(rows, conn)

                rows = conn.execute(
                    """SELECT * FROM memories
                       WHERE galactic_distance > 0.70
                         AND memory_type != 'quarantined'
                       ORDER BY RANDOM() LIMIT ?""",
                    (sample_size // 4,),
                ).fetchall()
                outer_mems = um.backend._batch_hydrate(rows, conn)

            all_mems = core_mems + inner_mems + mid_mems + outer_mems
        except Exception as e:
            logger.warning("Association mining: sampling failed, using recent: %s", e, exc_info=True)
            all_mems = um.backend.list_recent(limit=sample_size)

        if len(all_mems) < 2:
            return report

        report.memories_sampled = len(all_mems)

        # Get existing associations to avoid duplicates
        existing_assoc: set[tuple[str, str]] = set()
        for mem in all_mems:
            for target_id in mem.associations:
                existing_assoc.add((mem.id, target_id))
                existing_assoc.add((target_id, mem.id))

        # Try Rust accelerated path first (bulk keyword + pairwise in one shot)
        proposals: list[ProposedLink] = []
        used_rust = False
        try:
            from whitemagic.optimization.rust_accelerators import (
                association_mine,
                rust_available,
            )
            if rust_available():
                texts = [(mem.id, f"{mem.title or ''} {str(mem.content)[:2000]}") for mem in all_mems]
                rust_result = association_mine(
                    texts,
                    max_keywords=50,
                    min_score=self._min_overlap,
                    max_results=self._max_proposals * 2,
                )
                report.pairs_evaluated = rust_result.get("pair_count", 0)
                for ov in rust_result.get("overlaps", []):
                    a_id, b_id = ov["source_id"], ov["target_id"]
                    if (a_id, b_id) in existing_assoc:
                        continue
                    shared = set(ov.get("shared_keywords", []))
                    if len(shared) >= 3:
                        top_kw = sorted(shared)[:5]
                        proposals.append(ProposedLink(
                            source_id=a_id,
                            target_id=b_id,
                            overlap_score=ov["overlap_score"],
                            shared_keywords=shared,
                            reason=f"Semantic overlap ({len(shared)} shared keywords: {', '.join(top_kw)})",
                        ))
                used_rust = True
                logger.debug("Association mining used Rust accelerator")
        except Exception as e:
            logger.debug("Rust association mining unavailable, using Python: %s", e, exc_info=True)

        # Python fallback path (with batch Rust keyword extraction)
        if not used_rust:
            fingerprints: dict[str, set[str]] = {}
            texts_for_batch = [(mem.id, f"{mem.title or ''} {str(mem.content)[:2000]}") for mem in all_mems]

            # Try batch Rust keyword extraction (single FFI call for all texts)
            batch_done = False
            try:
                from whitemagic.optimization.rust_accelerators import (
                    keyword_extract_batch as rust_kw_batch,
                )
                result = rust_kw_batch([t[1] for t in texts_for_batch], 50)
                if result is not None:
                    for (mid, _), kw_set in zip(texts_for_batch, result):
                        fingerprints[mid] = kw_set
                    batch_done = True
            except (ImportError, AttributeError):
                pass

            if not batch_done:
                for mid, text in texts_for_batch:
                    fingerprints[mid] = self._extract_keywords(text)

            mem_ids = [m.id for m in all_mems if len(fingerprints.get(m.id, set())) >= 3]

            for i in range(len(mem_ids)):
                if len(proposals) >= self._max_proposals * 2:
                    break
                for j in range(i + 1, len(mem_ids)):
                    a_id, b_id = mem_ids[i], mem_ids[j]
                    if a_id == b_id or (a_id, b_id) in existing_assoc:
                        continue

                    report.pairs_evaluated += 1
                    score, shared = self._compute_overlap(
                        fingerprints[a_id], fingerprints[b_id],
                    )

                    if score >= self._min_overlap and len(shared) >= 3:
                        top_kw = sorted(shared)[:5]
                        proposals.append(ProposedLink(
                            source_id=a_id,
                            target_id=b_id,
                            overlap_score=score,
                            shared_keywords=shared,
                            reason=f"Semantic overlap ({len(shared)} shared keywords: {', '.join(top_kw)})",
                        ))

        # Sort by score descending, take top N
        proposals.sort(key=lambda p: p.overlap_score, reverse=True)
        proposals = proposals[:self._max_proposals]
        report.links_proposed = len(proposals)
        report.top_proposals = proposals

        # Persist if enabled
        if self._persist and proposals:
            try:
                import sqlite3
                with um.backend.pool.connection() as conn:
                    with conn:
                        for p in proposals:
                            # Bidirectional links with overlap_score as strength
                            try:
                                _now = datetime.now().isoformat()
                                conn.execute(
                                    """INSERT OR IGNORE INTO associations
                                       (source_id, target_id, strength,
                                        direction, relation_type, edge_type,
                                        created_at, ingestion_time)
                                       VALUES (?, ?, ?, 'undirected', 'associated_with', 'semantic', ?, ?)""",
                                    (p.source_id, p.target_id, p.overlap_score, _now, _now),
                                )
                                conn.execute(
                                    """INSERT OR IGNORE INTO associations
                                       (source_id, target_id, strength,
                                        direction, relation_type, edge_type,
                                        created_at, ingestion_time)
                                       VALUES (?, ?, ?, 'undirected', 'associated_with', 'semantic', ?, ?)""",
                                    (p.target_id, p.source_id, p.overlap_score, _now, _now),
                                )
                                report.links_created += 1
                            except Exception as e:
                                logger.debug("Association link insert failed: %s", e)
            except Exception as e:
                logger.error("Association mining: persistence failed: %s", e, exc_info=True)

        # Gap A3 synthesis: Feed strong associations into the Knowledge Graph
        self._feed_knowledge_graph(proposals)

        elapsed = (time.perf_counter() - start) * 1000
        report.duration_ms = elapsed

        with self._lock:
            self._total_runs += 1
            self._total_links_created += report.links_created

        logger.info(
            "🔗 Association mining: %s sampled, "
            "%s pairs, %s proposed, "
            "%s created (%.0fms)",
         report.memories_sampled, report.pairs_evaluated, report.links_proposed,
         report.links_created, elapsed)
        return report

    def _feed_knowledge_graph(self, proposals: list[ProposedLink]) -> None:
        """Create Knowledge Graph edges from strong association discoveries.

        When the miner finds semantically linked memories via keyword overlap,
        those links represent real semantic relationships that the KG should
        know about. We create 'associated_with' relations with the shared
        keywords as context.
        """
        if not proposals:
            return
        try:
            from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()

            edges_created = 0
            for p in proposals:
                if p.overlap_score < 0.3:
                    # Only strong links
                    continue
                # Create a KG edge: source_id --[associated_with]--> target_id
                kg.add_relation(
                    source=p.source_id,
                    relation="associated_with",
                    target=p.target_id,
                    metadata={
                        "overlap_score": p.overlap_score,
                        "shared_keywords": sorted(p.shared_keywords)[:5],
                        "origin": "association_miner",
                    },
                )
                edges_created += 1

            if edges_created:
                logger.info("KG enrichment: %s association edges created", edges_created, exc_info=True)
        except Exception as e:
            logger.debug("KG enrichment skipped: %s", e, exc_info=True)

    def mine_semantic(
        self,
        min_similarity: float = 0.50,
        strong_threshold: float = 0.70,
        max_proposals: int = 100,
        persist: bool = True,
    ) -> MiningReport:
        """Run semantic association mining using embedding cosine similarity.

        This replaces the keyword Jaccard approach with true semantic
        understanding via sentence-transformer embeddings (384 dims).

        Args:
            min_similarity: Minimum cosine similarity for a weak association.
            strong_threshold: Cosine threshold for a strong association.
            max_proposals: Maximum proposals to generate.
            persist: Whether to write associations to the DB.

        Returns:
            MiningReport with semantic association results.

        """
        start = time.perf_counter()
        report = MiningReport()

        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Semantic mining: embedding engine unavailable: %s", e, exc_info=True)
            return report

        if not engine.available():
            logger.info("Semantic mining: embeddings not available, falling back to keyword mining")
            return self.mine(sample_size=200)

        # Find all pairs above similarity threshold
        pairs = engine.find_similar_pairs(
            min_similarity=min_similarity,
            max_pairs=max_proposals * 3,  # over-fetch, filter later
        )

        if not pairs:
            elapsed = (time.perf_counter() - start) * 1000
            report.duration_ms = elapsed
            logger.info("Semantic mining: no pairs above %s threshold ({elapsed:.0f}ms)", min_similarity, exc_info=True)
            return report

        report.pairs_evaluated = len(pairs)

        # Filter out existing associations
        existing_assoc: set[tuple[str, str]] = set()
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            with um.backend.pool.connection() as conn:
                # Get existing associations for candidate IDs
                candidate_ids = set()
                for pair_item in pairs:
                    candidate_ids.add(pair_item["source_id"])
                    candidate_ids.add(pair_item["target_id"])

                if candidate_ids:
                    placeholders = ",".join("?" * len(candidate_ids))
                    rows = conn.execute(
                        f"""SELECT source_id, target_id FROM associations
                            WHERE source_id IN ({placeholders})
                            OR target_id IN ({placeholders})""",
                        list(candidate_ids) + list(candidate_ids),
                    ).fetchall()
                    for row in rows:
                        existing_assoc.add((row[0], row[1]))
                        existing_assoc.add((row[1], row[0]))
        except Exception as e:
            logger.debug("Semantic mining: could not load existing associations: %s", e, exc_info=True)

        # Build proposals
        proposals: list[ProposedLink] = []
        for p in pairs:
            src, tgt, sim = p["source_id"], p["target_id"], p["similarity"]
            if (src, tgt) in existing_assoc:
                continue

            strength_label = "strong" if sim >= strong_threshold else "weak"
            proposals.append(ProposedLink(
                source_id=src,
                target_id=tgt,
                overlap_score=sim,
                shared_keywords=set(),  # semantic, not keyword-based
                reason=f"Semantic similarity ({strength_label}, cosine={sim:.3f})",
            ))

            if len(proposals) >= max_proposals:
                break

        report.links_proposed = len(proposals)
        report.top_proposals = proposals
        report.memories_sampled = len(
            {pair_item["source_id"] for pair_item in pairs}
            | {pair_item["target_id"] for pair_item in pairs}
        )

        # Persist
        if persist and proposals:
            try:
                with um.backend.pool.connection() as conn:
                    with conn:
                        for proposal in proposals:
                            try:
                                _now = datetime.now().isoformat()
                                conn.execute(
                                    """INSERT OR IGNORE INTO associations
                                       (source_id, target_id, strength,
                                        direction, relation_type, edge_type,
                                        created_at, ingestion_time)
                                       VALUES (?, ?, ?, 'undirected', 'associated_with', 'semantic', ?, ?)""",
                                    (
                                        proposal.source_id,
                                        proposal.target_id,
                                        proposal.overlap_score,
                                        _now,
                                        _now,
                                    ),
                                )
                                conn.execute(
                                    """INSERT OR IGNORE INTO associations
                                       (source_id, target_id, strength,
                                        direction, relation_type, edge_type,
                                        created_at, ingestion_time)
                                       VALUES (?, ?, ?, 'undirected', 'associated_with', 'semantic', ?, ?)""",
                                    (
                                        proposal.target_id,
                                        proposal.source_id,
                                        proposal.overlap_score,
                                        _now,
                                        _now,
                                    ),
                                )
                                report.links_created += 1
                            except Exception as e:
                                logger.debug("Semantic link insert failed: %s", e)
            except Exception as e:
                logger.error("Semantic mining: persistence failed: %s", e, exc_info=True)

        # Feed strong links to Knowledge Graph
        strong_proposals = [p for p in proposals if p.overlap_score >= strong_threshold]
        self._feed_knowledge_graph(strong_proposals)

        elapsed = (time.perf_counter() - start) * 1000
        report.duration_ms = elapsed

        with self._lock:
            self._total_runs += 1
            self._total_links_created += report.links_created

        logger.info(
            "\U0001f9e0 Semantic mining: %s memories, "
            "%s pairs evaluated, "
            "%s proposed (%s strong), "
            "%s created (%.0fms)",
         report.memories_sampled, report.pairs_evaluated, report.links_proposed, len(strong_proposals),
         report.links_created, elapsed)
        return report

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return {
            "total_runs": self._total_runs,
            "total_links_created": self._total_links_created,
            "min_overlap": self._min_overlap,
            "max_proposals_per_run": self._max_proposals,
            "persist": self._persist,
        }


_miner_instance: AssociationMiner | None = None
_miner_lock = threading.Lock()


def get_association_miner(
    min_overlap: float = 0.15,
    max_proposals: int = 50,
    persist: bool = True,
) -> AssociationMiner:
    """Get or create the global AssociationMiner singleton."""
    global _miner_instance
    with _miner_lock:
        if _miner_instance is None:
            _miner_instance = AssociationMiner(
                min_overlap=min_overlap,
                max_proposals_per_run=max_proposals,
                persist=persist,
            )
        return _miner_instance
"""Causal Edge Miner (v14.1).
============================
Discovers directed causal relationships between memories by combining
temporal ordering with semantic similarity. Unlike the AssociationMiner
which creates undirected `associated_with` edges, the CausalMiner creates
directed edges: `led_to`, `caused_by`, `preceded`, `followed_by`.

Causal signals:
  1. **Temporal proximity**: Memories created close in time are more likely
     causally related than distant ones.
  2. **Semantic similarity**: Via embedding cosine (HNSW accelerated).
  3. **Tag overlap**: Shared tags reinforce causal hypotheses.
  4. **Title sequence**: "[GUIDE] X" → "[TUTORIAL] X" suggests progression.

Edges are always directed: source.created_at < target.created_at.
Strength = blend of semantic similarity × temporal proximity × tag overlap.

Usage:
    from whitemagic.core.memory.causal_miner import get_causal_miner
    miner = get_causal_miner()
    report = miner.mine(sample_size=200)
"""

import logging
import math
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CausalEdge:
    """A proposed directed causal edge between two memories."""

    source_id: str        # earlier memory
    target_id: str        # later memory
    relation: str         # led_to, caused_by, preceded, etc.
    strength: float       # composite causal strength 0.0–1.0
    semantic_sim: float   # embedding cosine similarity
    temporal_proximity: float  # 0.0=very far, 1.0=very close in time
    tag_overlap: float    # Jaccard of tag sets
    time_delta_hours: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "strength": round(self.strength, 4),
            "semantic_sim": round(self.semantic_sim, 4),
            "temporal_proximity": round(self.temporal_proximity, 4),
            "tag_overlap": round(self.tag_overlap, 4),
            "time_delta_hours": round(self.time_delta_hours, 2),
            "reason": self.reason,
        }


@dataclass
class CausalMiningReport:
    """Results from a causal mining run."""

    memories_sampled: int = 0
    pairs_evaluated: int = 0
    edges_proposed: int = 0
    edges_created: int = 0
    avg_strength: float = 0.0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    top_edges: list[CausalEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memories_sampled": self.memories_sampled,
            "pairs_evaluated": self.pairs_evaluated,
            "edges_proposed": self.edges_proposed,
            "edges_created": self.edges_created,
            "avg_strength": round(self.avg_strength, 4),
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
            "top_edges": [e.to_dict() for e in self.top_edges[:10]],
        }


# Temporal decay: memories more than this many hours apart get rapidly
# diminishing temporal proximity scores.
_MAX_CAUSAL_WINDOW_HOURS = 168.0  # 7 days


class CausalMiner:
    """Discovers directed causal edges between memories.

    Strategy:
    1. Find semantically similar memory pairs (HNSW or brute-force).
    2. For each pair, determine temporal order (earlier → later).
    3. Compute temporal proximity signal (exponential decay).
    4. Compute tag overlap signal (Jaccard).
    5. Blend signals into a composite causal strength.
    6. Classify relation type based on strength + context.
    7. Persist as directed associations.
    """

    def __init__(
        self,
        min_semantic_sim: float = 0.35,
        min_causal_strength: float = 0.20,
        max_edges_per_run: int = 100,
        persist: bool = True,
    ):
        self._min_semantic_sim = min_semantic_sim
        self._min_causal_strength = min_causal_strength
        self._max_edges = max_edges_per_run
        self._persist = persist
        self._lock = threading.Lock()
        self._total_runs: int = 0
        self._total_edges_created: int = 0

    @staticmethod
    def _temporal_proximity(dt_hours: float) -> float:
        """Exponential decay: close-in-time → high score."""
        if dt_hours <= 0:
            return 1.0
        # Half-life of 24 hours: after 24h proximity = 0.5, after 48h = 0.25
        return math.exp(-0.693 * dt_hours / 24.0)

    @staticmethod
    def _tag_jaccard(tags_a: set[str], tags_b: set[str]) -> float:
        """Jaccard similarity of tag sets."""
        if not tags_a and not tags_b:
            return 0.0
        union = tags_a | tags_b
        if not union:
            return 0.0
        return len(tags_a & tags_b) / len(union)

    @staticmethod
    def _classify_relation(strength: float, semantic_sim: float,
                           temporal_prox: float) -> str:
        """Classify the causal relationship type."""
        if strength >= 0.6 and temporal_prox >= 0.5:
            return "led_to"       # strong causal, close in time
        elif strength >= 0.4:
            return "influenced"   # moderate causal signal
        elif temporal_prox >= 0.7:
            return "preceded"     # close in time, weaker semantic
        else:
            return "related_to"   # distant but connected

    def _compute_causal_strength(
        self, semantic_sim: float, temporal_prox: float, tag_overlap: float,
    ) -> float:
        """Blend signals into composite causal strength.

        Weights:
          - semantic: 0.50 (primary signal)
          - temporal: 0.35 (causation requires proximity)
          - tags:     0.15 (reinforcing signal)
        """
        return (
            0.50 * semantic_sim
            + 0.35 * temporal_prox
            + 0.15 * tag_overlap
        )

    def mine(self, sample_size: int = 200) -> CausalMiningReport:
        """Run a causal edge mining pass.

        Args:
            sample_size: Max memories to include in the candidate pool.
        """
        start = time.perf_counter()
        report = CausalMiningReport()

        # Try embedding-based mining first, fall back to temporal-only
        use_embeddings = False
        pairs: list[dict] = []
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            # Try find_similar_pairs directly — works on pre-computed embeddings
            # even when the model isn't installed (available() may be False)
            pairs = engine.find_similar_pairs(
                min_similarity=self._min_semantic_sim,
                max_pairs=self._max_edges * 5,
            )
            if pairs:
                use_embeddings = True
        except Exception as e:
            logger.debug("find_similar_pairs failed: %s", e)

        # Hydrate memory metadata for temporal + tag signals
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Causal mining: memory system unavailable: %s", e, exc_info=True)
            return report

        # Temporal fallback: sample recent memories and pair by proximity + tags
        if not use_embeddings:
            pairs = self._temporal_fallback_pairs(um, sample_size)
            if not pairs:
                report.duration_ms = (time.perf_counter() - start) * 1000
                return report

        report.pairs_evaluated = len(pairs)

        # Collect all candidate IDs
        candidate_ids: set[str] = set()
        for p in pairs:
            candidate_ids.add(p["source_id"])
            candidate_ids.add(p["target_id"])

        # Batch hydrate: get created_at and tags for all candidates
        mem_meta: dict[str, dict[str, Any]] = {}
        try:
            for mid in candidate_ids:
                mem = um.backend.recall(mid)
                if mem:
                    mem_meta[mid] = {
                        "created_at": mem.created_at,
                        "tags": mem.tags or set(),
                        "title": mem.title or "",
                    }
        except Exception as e:
            logger.debug("Causal mining: hydration partially failed: %s", e, exc_info=True)

        report.memories_sampled = len(mem_meta)

        # Get existing directed associations to avoid duplicates
        existing_directed: set[tuple[str, str]] = set()
        try:
            with um.backend.pool.connection() as conn:
                rows = conn.execute(
                    """SELECT source_id, target_id FROM associations
                       WHERE direction = 'directed'""",
                ).fetchall()
                for row in rows:
                    existing_directed.add((row[0], row[1]))
        except Exception as e:
            logger.debug("Causal existing edges fetch failed: %s", e)

        # Score each pair
        edges: list[CausalEdge] = []
        total_strength = 0.0

        for p in pairs:
            src, tgt, sim = p["source_id"], p["target_id"], p["similarity"]

            # Need metadata for both
            if src not in mem_meta or tgt not in mem_meta:
                continue

            src_meta = mem_meta[src]
            tgt_meta = mem_meta[tgt]

            # Determine temporal order: earlier → later
            # Normalize timezone: strip tzinfo to avoid naive/aware comparison
            src_time = src_meta["created_at"]
            tgt_time = tgt_meta["created_at"]
            if hasattr(src_time, 'replace') and src_time.tzinfo is not None:
                src_time = src_time.replace(tzinfo=None)
            if hasattr(tgt_time, 'replace') and tgt_time.tzinfo is not None:
                tgt_time = tgt_time.replace(tzinfo=None)

            if src_time > tgt_time:
                # Swap so source is always earlier
                src, tgt = tgt, src
                src_meta, tgt_meta = tgt_meta, src_meta
                src_time, tgt_time = tgt_time, src_time

            # Skip if already directed-linked
            if (src, tgt) in existing_directed:
                continue

            # Compute signals
            dt_hours = (tgt_time - src_time).total_seconds() / 3600.0
            if dt_hours > _MAX_CAUSAL_WINDOW_HOURS:
                continue  # Too far apart for causal inference

            temporal_prox = self._temporal_proximity(dt_hours)
            tag_overlap = self._tag_jaccard(src_meta["tags"], tgt_meta["tags"])
            strength = self._compute_causal_strength(sim, temporal_prox, tag_overlap)

            if strength < self._min_causal_strength:
                continue

            relation = self._classify_relation(strength, sim, temporal_prox)

            edges.append(CausalEdge(
                source_id=src,
                target_id=tgt,
                relation=relation,
                strength=strength,
                semantic_sim=sim,
                temporal_proximity=temporal_prox,
                tag_overlap=tag_overlap,
                time_delta_hours=dt_hours,
                reason=(
                    f"{relation}: sem={sim:.2f}, time={dt_hours:.1f}h, "
                    f"tags={tag_overlap:.2f}"
                ),
            ))
            total_strength += strength

            if len(edges) >= self._max_edges:
                break

        # Sort by strength
        edges.sort(key=lambda e: e.strength, reverse=True)
        report.edges_proposed = len(edges)
        report.top_edges = edges
        if edges:
            report.avg_strength = total_strength / len(edges)

        # Persist directed edges
        if self._persist and edges:
            try:
                with um.backend.pool.connection() as conn:
                    with conn:
                        for edge in edges:
                            try:
                                _now = datetime.now().isoformat()
                                conn.execute(
                                    """INSERT OR IGNORE INTO associations
                                       (source_id, target_id, strength,
                                        direction, relation_type, edge_type,
                                        created_at, ingestion_time)
                                       VALUES (?, ?, ?, 'directed', ?, 'causal', ?, ?)""",
                                    (
                                        edge.source_id,
                                        edge.target_id,
                                        edge.strength,
                                        edge.relation,
                                        _now,
                                        _now,
                                    ),
                                )
                                report.edges_created += 1
                            except Exception as e:
                                logger.debug("Causal edge insert failed: %s", e)
            except Exception as e:
                logger.error("Causal mining: persistence failed: %s", e, exc_info=True)

        elapsed = (time.perf_counter() - start) * 1000
        report.duration_ms = elapsed

        with self._lock:
            self._total_runs += 1
            self._total_edges_created += report.edges_created

        logger.info(
            "⚡ Causal mining: %s sampled, "
            "%s pairs, %s proposed, "
            "%s created (%.0fms)",
         report.memories_sampled, report.pairs_evaluated, report.edges_proposed,
         report.edges_created, elapsed)
        return report

    def _temporal_fallback_pairs(
        self, um: Any, sample_size: int,
    ) -> list[dict[str, Any]]:
        """Generate candidate pairs from temporal proximity + tag overlap.

        When embeddings are unavailable, we sample recent LONG_TERM memories
        and pair them by creation-time proximity. This gives the causal miner
        something to work with even on a cold corpus.
        """
        pairs: list[dict[str, Any]] = []
        try:
            with um.backend.pool.connection() as conn:
                rows = conn.execute(
                    """SELECT id, title, created_at FROM memories
                       WHERE memory_type != 'quarantined'
                         AND created_at IS NOT NULL
                         AND LENGTH(content) > 100
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (sample_size,),
                ).fetchall()

            if len(rows) < 2:
                return []

            # Parse timestamps and pair adjacent memories
            parsed = []
            for row in rows:
                mid = row[0] if isinstance(row, tuple) else row["id"]
                title = row[1] if isinstance(row, tuple) else row["title"]
                ts_str = row[2] if isinstance(row, tuple) else row["created_at"]
                try:
                    ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
                parsed.append({"id": mid, "title": title, "ts": ts})

            # Sort by time (oldest first)
            parsed.sort(key=lambda m: m["ts"])

            # Pair each memory with the next N temporally-adjacent ones
            window = min(5, len(parsed))
            for i in range(len(parsed)):
                for j in range(i + 1, min(i + window, len(parsed))):
                    dt_hours = abs((parsed[j]["ts"] - parsed[i]["ts"]).total_seconds()) / 3600.0
                    if dt_hours > _MAX_CAUSAL_WINDOW_HOURS:
                        break
                    # Use temporal proximity as a stand-in for similarity
                    temporal_sim = self._temporal_proximity(dt_hours)
                    if temporal_sim >= 0.1:
                        # At least some proximity
                        pairs.append({
                            "source_id": parsed[i]["id"],
                            "target_id": parsed[j]["id"],
                            "similarity": temporal_sim,  # Stand-in for semantic sim
                        })

            logger.info(
                "Causal mining: temporal fallback generated %s pairs "
                "from %s memories",
             len(pairs), len(parsed))
        except Exception as e:
            logger.debug("Temporal fallback failed: %s", e, exc_info=True)

        return pairs[:self._max_edges * 5]

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return {
            "total_runs": self._total_runs,
            "total_edges_created": self._total_edges_created,
            "min_semantic_sim": self._min_semantic_sim,
            "min_causal_strength": self._min_causal_strength,
            "max_edges_per_run": self._max_edges,
        }


_miner_instance: CausalMiner | None = None  # type: ignore[no-redef]
_miner_lock = threading.Lock()


def get_causal_miner(
    min_semantic_sim: float = 0.35,
    min_causal_strength: float = 0.20,
    max_edges: int = 100,
    persist: bool = True,
) -> CausalMiner:
    """Get or create the global CausalMiner singleton."""
    global _miner_instance
    with _miner_lock:
        if _miner_instance is None:
            _miner_instance = CausalMiner(  # type: ignore[assignment]
                min_semantic_sim=min_semantic_sim,
                min_causal_strength=min_causal_strength,
                max_edges_per_run=max_edges,
                persist=persist,
            )
        return _miner_instance  # type: ignore[return-value]
