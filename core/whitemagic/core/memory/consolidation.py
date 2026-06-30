# ruff: noqa: BLE001
"""Cross-Session Memory Consolidation — Hippocampal Replay.
=========================================================
Inspired by how biological hippocampal replay strengthens memories
during sleep: the brain re-activates recent experiences, clusters
related traces, and extracts meta-patterns that become long-term
semantic knowledge.

This module runs on the Temporal Scheduler's SLOW lane and:
  1. Loads recent memories from the current session window.
  2. Clusters them by semantic similarity (tag overlap + association overlap).
  3. Identifies high-value clusters (frequent access, strong emotions, patterns).
  4. Synthesizes "strategy memories" — compressed meta-insights from clusters.
  5. Promotes strategy memories to LONG_TERM storage.
  6. Emits MEMORY_CONSOLIDATED and INSIGHT_CRYSTALLIZED events.

The consolidation cycle is gentle: it never deletes, only promotes and
annotates. It works alongside Mindful Forgetting — one archives the
weak, the other strengthens the strong.

Usage:
    from whitemagic.core.memory.consolidation import get_consolidator
    consolidator = get_consolidator()
    report = consolidator.consolidate()
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ── Reconsolidation constants (fused from reconsolidation.py) ──
DEFAULT_LABILE_WINDOW = 300  # 5 minutes
MAX_LABILE = 20


@dataclass
class LabileMemory:
    """A memory in labile (modifiable) state after retrieval.

    When a memory is recalled, it enters a brief labile state where it can
    be updated with new context before being re-stored. This mirrors the
    neuroscience finding that recalled memories are temporarily destabilized
    and can be modified during reconsolidation.
    """

    memory_id: str
    original_content: str
    original_tags: list[str]
    retrieved_at: float = 0.0
    query_context: str = ""
    updates: list[dict[str, Any]] = field(default_factory=list)
    reconsolidated: bool = False

    def __post_init__(self) -> None:
        if self.retrieved_at == 0.0:
            self.retrieved_at = time.time()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.retrieved_at) > DEFAULT_LABILE_WINDOW

    @property
    def age_seconds(self) -> float:
        return time.time() - self.retrieved_at


@dataclass
class MemoryCluster:
    """A cluster of related memories for consolidation."""

    cluster_id: str
    memory_ids: list[str]
    shared_tags: set[str]
    avg_importance: float
    total_access_count: int
    avg_emotional_valence: float
    theme: str

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "cluster_id": self.cluster_id,
            "memory_ids": self.memory_ids,
            "shared_tags": list(self.shared_tags),
            "avg_importance": self.avg_importance,
            "total_access_count": self.total_access_count,
            "avg_emotional_valence": self.avg_emotional_valence,
            "theme": self.theme,
            "size": len(self.memory_ids),
        }


@dataclass
class ConsolidationReport:
    """Report from a consolidation run."""

    memories_analyzed: int = 0
    clusters_found: int = 0
    duration_ms: int = 0
    strategies_synthesized: int = 0
    promotions: int = 0
    clusters: list[MemoryCluster] | None = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "memories_analyzed": self.memories_analyzed,
            "clusters_found": self.clusters_found,
            "duration_ms": self.duration_ms,
            "strategies_synthesized": self.strategies_synthesized,
            "promotions": self.promotions,
            "clusters": [c.to_dict() for c in (self.clusters or [])],
            "timestamp": self.timestamp,
        }


class MemoryConsolidator:
    """Hippocampal replay engine for cross-session memory consolidation.

    Clusters recent memories, identifies patterns, synthesizes strategy
    memories, and promotes high-value clusters to long-term storage.
    """

    def __init__(
        self,
        min_cluster_size: int = 3,
        tag_overlap_threshold: float = 0.3,
        importance_boost: float = 0.15,
        max_memories: int = 2000,
        labile_window: float = DEFAULT_LABILE_WINDOW,
    ) -> None:
        self._min_cluster_size = min_cluster_size
        self._tag_overlap_threshold = tag_overlap_threshold
        self._importance_boost = importance_boost
        self._max_memories = max_memories
        self._lock = threading.Lock()
        self._total_consolidations = 0
        self._total_strategies = 0
        self._total_promotions = 0
        # Reconsolidation state (fused from ReconsolidationEngine)
        self._labile_window = labile_window
        self._labile: dict[str, LabileMemory] = {}
        self._reconsolidation_stats = {
            "total_marked": 0,
            "total_updated": 0,
            "total_reconsolidated": 0,
            "total_expired": 0,
        }

    def consolidate(self, memories: Any = None) -> ConsolidationReport:
        """Run a full consolidation cycle.

        1. Load recent memories (or use provided list)
        2. Rust pre-pass: content-based consolidation (PyO3 accelerated)
        3. Cluster by tag/association similarity
        4. Synthesize strategy memories from strong clusters
        5. Promote high-value memories to LONG_TERM
        """
        start = time.perf_counter()
        report = ConsolidationReport()

        if memories is None:
            memories = self._load_recent()
        if not memories:
            report.duration_ms = int((time.perf_counter() - start) * 1000)
            with self._lock:
                self._total_consolidations += 1
            return report

        report.memories_analyzed = len(memories)

        rust_clusters = self._rust_content_consolidation(memories)
        if rust_clusters:
            report.details = {"rust_consolidation": rust_clusters}

        clusters = self._cluster_by_tags(memories)
        report.clusters_found = len(clusters)
        report.clusters = clusters

        strategies = self._synthesize_strategies(clusters, memories)
        report.strategies_synthesized = len(strategies)

        self._bicameral_enrich(clusters, strategies)

        promotions = self._promote_high_value(memories)
        report.promotions = promotions

        report.duration_ms = int((time.perf_counter() - start) * 1000)

        with self._lock:
            self._total_consolidations += 1
            self._total_strategies += len(strategies)
            self._total_promotions += promotions

        self._galactic_promote(strategies)

        self._feed_knowledge_graph(clusters, strategies)

        reconsolidation_results = self.reconsolidate_all()
        if reconsolidation_results:
            logger.debug("Reconsolidated %d labile memories during consolidation", len(reconsolidation_results))

        self._update_harmony(report)

        # Emit events
        self._emit_events(report, strategies)

        logger.info(
            "Consolidation #%s: "
            "%s analyzed, "
            "%s clusters, "
            "%s strategies, "
            "%s promotions, "
            "%sms",
         self._total_consolidations, report.memories_analyzed, report.clusters_found, report.strategies_synthesized, report.promotions, report.duration_ms)

        return report

    def _load_recent(self) -> list[Any]:
        """Load recent memories from UnifiedMemory."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            return um.list_recent(limit=self._max_memories)
        except Exception as e:
            logger.debug("Consolidation: could not load memories: %s", e, exc_info=True)
            return []

    def _rust_content_consolidation(self, memories: list[Any]) -> dict[str, Any] | None:
        """Rust PyO3 content-based consolidation pre-pass.

        Uses whitemagic_rs.consolidate_memories_from_content to find
        content-similar memory clusters at native speed. Returns a dict
        with cluster info, or None if Rust is unavailable.
        """
        try:
            import whitemagic_rs

            # Build (id, content) tuples for Rust
            mem_tuples = [
                (m.id, str(m.content)[:500])
                for m in memories
                if hasattr(m, "content") and m.content
            ]
            if len(mem_tuples) < 3:
                return None

            result = whitemagic_rs.consolidate_memories_from_content(
                mem_tuples,
                top_n=min(20, len(mem_tuples) // 3),
                similarity_threshold=0.3,
            )

            if result and len(result) >= 5:
                total, consolidated, n_clusters, similarity, top_ids, cluster_details = result[:6]
                return {
                    "total_memories": total,
                    "consolidated_count": consolidated,
                    "clusters_found": n_clusters,
                    "avg_similarity": round(similarity, 4),
                    "top_memory_ids": top_ids if isinstance(top_ids, list) else [],
                    "accelerated": True,
                    "engine": "rust_consolidate",
                }
        except Exception as e:
            logger.debug("Rust content consolidation skipped: %s", e, exc_info=True)
        return None

    def _find_near_duplicates_minhash(self, memories: list[Any]) -> list[dict[str, Any]]:
        """Use Rust MinHash LSH to quickly find near-duplicate memory pairs."""
        try:
            from whitemagic.optimization.rust_accelerators import (
                minhash_find_duplicates,
                rust_v131_available,
            )
            if not rust_v131_available() or len(memories) < 10:
                return []

            # Build keyword sets from tags + title words
            keyword_sets = []
            for mem in memories:
                kws = set(mem.tags) if mem.tags else set()
                if mem.title:
                    kws |= {w.lower() for w in mem.title.split() if len(w) > 2}
                keyword_sets.append(sorted(kws))

            candidates = minhash_find_duplicates(keyword_sets, threshold=0.4, max_results=200)
            if candidates:
                logger.debug("MinHash found %s near-duplicate candidates", len(candidates))
            return candidates or []
        except Exception as e:
            logger.debug("MinHash near-duplicate detection skipped: %s", e, exc_info=True)
            return []

    def resolve_entities(self, similarity_threshold: float = 0.92, batch_limit: int = 500) -> dict[str, Any]:
        """Entity resolution: embedding-based dedup (v14.0 Living Graph).

        Finds near-duplicate memories via cosine similarity above threshold
        and merges them:
        1. Keep the canonical memory (highest importance + most accessed)
        2. Merge tags from duplicate into canonical
        3. Reinforce canonical (bump importance, access_count)
        4. Push duplicate to FAR_EDGE (never delete)

        Args:
            similarity_threshold: Cosine similarity threshold for dedup (default 0.92).
            batch_limit: Max memories to evaluate per run.

        Returns:
            Dict with resolution stats.
        """
        start = time.perf_counter()
        result: dict[str, Any] = {
            "status": "success",
            "pairs_evaluated": 0,
            "duplicates_found": 0,
            "duplicates_resolved": 0,
        }

        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            if not engine.available():
                result["status"] = "skipped"
                result["reason"] = "embeddings unavailable"
                return result
        except Exception as e:
            result["status"] = "skipped"
            result["reason"] = str(e)
            return result

        # Find similar pairs above threshold
        try:
            pairs = engine.find_similar_pairs(
                min_similarity=similarity_threshold,
                max_pairs=batch_limit,
            )
        except Exception as e:
            result["status"] = "error"
            result["reason"] = str(e)
            return result

        if not pairs:
            result["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            return result

        result["pairs_evaluated"] = len(pairs)

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except Exception as e:
            result["status"] = "error"
            result["reason"] = str(e)
            return result

        resolved_ids: set[str] = set()  # Already-resolved duplicates

        for pair in pairs:
            src_id = pair["source_id"]
            tgt_id = pair["target_id"]
            similarity = pair.get("similarity", 0.0)

            if src_id in resolved_ids or tgt_id in resolved_ids:
                continue

            # Load both memories
            try:
                mem_a = um.backend.recall(src_id)
                mem_b = um.backend.recall(tgt_id)
                if not mem_a or not mem_b:
                    continue
            except Exception as e:
                logger.debug("Memory recall failed during dedup check: %s", e)
                continue

            result["duplicates_found"] += 1

            # Determine canonical (higher importance, more accessed)
            score_a = (mem_a.importance or 0.5) * 10 + (mem_a.access_count or 0)
            score_b = (mem_b.importance or 0.5) * 10 + (mem_b.access_count or 0)
            canonical, duplicate = (mem_a, mem_b) if score_a >= score_b else (mem_b, mem_a)

            # Merge tags from duplicate into canonical
            if duplicate.tags:
                canonical.tags = canonical.tags | duplicate.tags

            # Reinforce canonical
            canonical.importance = min(1.0, (canonical.importance or 0.5) + 0.03)
            canonical.access_count += 1
            canonical.metadata["entity_resolution"] = {
                "merged_from": duplicate.id,
                "similarity": round(similarity, 4),
                "resolved_at": datetime.now().isoformat(),
            }

            try:
                um.backend.store(canonical)
                # Push duplicate to FAR_EDGE (never delete)
                um.backend.archive_to_edge(duplicate.id, galactic_distance=0.95)
                resolved_ids.add(duplicate.id)
                result["duplicates_resolved"] += 1
            except Exception as e:
                logger.warning("Duplicate resolution failed for %s: %s", duplicate.id, e, exc_info=True)

        result["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)

        if result["duplicates_resolved"] > 0:
            logger.info(
                "🔗 Entity resolution: %s duplicates found, "
                "%s resolved (%.0fms)",
             result['duplicates_found'], result['duplicates_resolved'], result['duration_ms'])
        return result

    def _cluster_by_tags(self, memories: list[Any]) -> list[MemoryCluster]:
        """Cluster memories by tag overlap using greedy agglomeration."""
        # Pre-pass: use MinHash to identify near-duplicates (Rust accelerated)
        minhash_candidates = self._find_near_duplicates_minhash(memories)
        if minhash_candidates:
            logger.info("MinHash pre-filter: %s near-duplicate pairs detected", len(minhash_candidates))

        # Build tag-to-memory index
        tag_index: dict[str, list] = defaultdict(list)
        for mem in memories:
            for tag in mem.tags:
                tag_index[tag].append(mem)

        # Find clusters: groups of memories sharing >= threshold fraction of tags
        visited: set[str] = set()
        clusters: list[MemoryCluster] = []

        # Sort tags by frequency (most common first = largest potential clusters)
        sorted_tags = sorted(tag_index.items(), key=lambda x: len(x[1]), reverse=True)

        for tag, tag_memories in sorted_tags:
            # Filter to unvisited memories
            unvisited = [m for m in tag_memories if m.id not in visited]
            if len(unvisited) < self._min_cluster_size:
                continue

            # Find the shared tag set for this group
            all_tag_sets = [m.tags for m in unvisited]
            shared = set.intersection(*all_tag_sets) if all_tag_sets else set()

            # Accept if there's meaningful overlap
            if not shared:
                shared = {tag}

            # Build the cluster
            mem_ids = [m.id for m in unvisited]
            avg_imp = sum((m.importance or 0.5) for m in unvisited) / len(unvisited)
            total_access = sum((m.access_count or 0) for m in unvisited)
            avg_valence = sum((m.emotional_valence or 0.0) for m in unvisited) / len(unvisited)

            cluster_id = hashlib.md5(
                "|".join(sorted(mem_ids)[:5]).encode(),
            ).hexdigest()[:12]

            cluster = MemoryCluster(
                cluster_id=cluster_id,
                memory_ids=mem_ids,
                shared_tags=shared,
                avg_importance=avg_imp,
                total_access_count=total_access,
                avg_emotional_valence=avg_valence,
                theme=tag,  # dominant tag as theme
            )
            clusters.append(cluster)

            # Mark as visited
            for mid in mem_ids:
                visited.add(mid)

        return clusters

    def _synthesize_strategies(self, clusters: list[MemoryCluster], memories: list[Any]) -> list[dict[str, Any]]:
        """Create strategy memories from strong clusters.

        A strategy memory is a compressed meta-insight that captures
        the essence of a cluster: "These N memories about [theme] with
        tags [X, Y, Z] have been accessed M times and have average
        importance P. Key insight: [theme] is a recurring pattern."
        """
        strategies = []
        mem_map = {m.id: m for m in memories}

        for cluster in clusters:
            # Only synthesize from significant clusters
            if (cluster.avg_importance < 0.4 or
                    cluster.total_access_count < 3 or
                    len(cluster.memory_ids) < self._min_cluster_size):
                continue

            # Build strategy content
            sample_titles = []
            for mid in cluster.memory_ids[:
                5]:
                mem = mem_map.get(mid)
                if mem and mem.title:
                    sample_titles.append(mem.title)

            strategy_content = {
                "type": "consolidated_strategy",
                "theme": cluster.theme,
                "cluster_size": len(cluster.memory_ids),
                "shared_tags": sorted(cluster.shared_tags),
                "avg_importance": round(cluster.avg_importance, 3),
                "total_access_count": cluster.total_access_count,
                "sample_titles": sample_titles,
                "insight": (
                    f"Recurring pattern '{cluster.theme}' detected across "
                    f"{len(cluster.memory_ids)} memories (avg importance: "
                    f"{cluster.avg_importance:.2f}, accessed {cluster.total_access_count} times). "
                    f"Tags: {', '.join(sorted(cluster.shared_tags))}."
                ),
            }

            # Store via UnifiedMemory
            try:
                from whitemagic.core.memory.unified import get_unified_memory
                from whitemagic.core.memory.unified_types import MemoryType
                um = get_unified_memory()
                um.store(
                    content=str(strategy_content),
                    memory_type=MemoryType.LONG_TERM,
                    title=f"Strategy: {cluster.theme} (consolidated)",
                    subsystem="consolidation",
                    tags=cluster.shared_tags | {"strategy", "consolidated"},
                    importance=min(1.0, (cluster.avg_importance or 0.5) + self._importance_boost),
                )
                strategies.append(strategy_content)
            except Exception as e:
                logger.debug("Could not persist strategy: %s", e, exc_info=True)

        return strategies

    def _bicameral_enrich(
        self, clusters: list[MemoryCluster], strategies: list[dict[str, Any]],
    ) -> None:
        """Use the Bicameral Reasoner's dual-hemisphere heuristics to find
        creative cross-cluster connections.

        Left hemisphere: identifies logical overlap between clusters
        (shared tags, causal chains, temporal sequences).

        Right hemisphere: detects unexpected creative connections
        (tag pairs that rarely co-occur, emotional resonance bridges,
        thematic contrasts that suggest deeper patterns).

        Results are stored as "creative_link" strategy memories.
        """
        if len(clusters) < 2:
            return

        try:
            from whitemagic.core.intelligence.bicameral import (
                get_bicameral_reasoner,
            )
            get_bicameral_reasoner()
        except (ImportError, AttributeError):
            return

        logical_links = []
        for i, c1 in enumerate(clusters):
            for c2 in clusters[i + 1:
                ]:
                shared = c1.shared_tags & c2.shared_tags
                if shared:
                    logical_links.append({
                        "type": "logical_bridge",
                        "cluster_a": c1.theme,
                        "cluster_b": c2.theme,
                        "shared_tags": sorted(shared),
                        "combined_access": c1.total_access_count + c2.total_access_count,
                    })

        creative_links = []
        for i, c1 in enumerate(clusters):
            for c2 in clusters[i + 1:
                ]:
                # Skip if already logically linked
                if c1.shared_tags & c2.shared_tags:
                    continue
                # Creative link: high emotional valence in both + no tag overlap
                if (c1.avg_emotional_valence > 0.5 and c2.avg_emotional_valence > 0.5):
                    creative_links.append({
                        "type": "creative_bridge",
                        "cluster_a": c1.theme,
                        "cluster_b": c2.theme,
                        "resonance": "emotional_affinity",
                        "valence_a": round(c1.avg_emotional_valence, 2),
                        "valence_b": round(c2.avg_emotional_valence, 2),
                    })
                # Creative link: high importance contrast (one very important, one not)
                elif abs(c1.avg_importance - c2.avg_importance) > 0.3:
                    creative_links.append({
                        "type": "creative_bridge",
                        "cluster_a": c1.theme,
                        "cluster_b": c2.theme,
                        "resonance": "importance_contrast",
                        "insight": (
                            f"'{c1.theme}' (imp={c1.avg_importance:.2f}) and "
                            f"'{c2.theme}' (imp={c2.avg_importance:.2f}) may reveal "
                            "hidden dependencies through their importance differential."
                        ),
                    })

        # Record bicameral stats on the reasoner
        all_links = logical_links[:5] + creative_links[:5]
        if all_links:
            logger.info(
                "Bicameral enrichment: %s logical, "
                "%s creative cross-cluster links",
             len(logical_links), len(creative_links))
            for link in all_links:
                strategies.append(link)

    def _promote_high_value(self, memories: list[Any]) -> int:
        """Promote frequently-accessed, high-importance short-term memories
        to LONG_TERM.
        """
        promotions = 0
        try:
            from whitemagic.core.memory.unified_types import MemoryType
        except ImportError:
            return 0

        for mem in memories:
            if mem.memory_type != MemoryType.SHORT_TERM:
                continue
            # Promotion criteria: high importance + accessed multiple times
            if (mem.importance or 0.5) >= 0.6 and (mem.access_count or 0) >= 3:
                try:
                    mem.memory_type = MemoryType.LONG_TERM
                    mem.importance = min(1.0, (mem.importance or 0.5) + 0.05)
                    promotions += 1
                except Exception as e:
                    logger.debug("Memory promotion failed for %s: %s", mem.id, e)

        return promotions

    def _feed_knowledge_graph(self, clusters: list[MemoryCluster],
                              strategies: list[dict[str, Any]]) -> None:
        """Create KG relations linking source memories to strategy memories.

        For each strategy, create 'consolidated_into' edges from every source
        memory in the cluster to the strategy, plus 'shares_theme' edges
        between cluster members. This makes the consolidation chain queryable.
        """
        if not strategies:
            return
        try:
            from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            edges = 0

            for cluster, strategy in zip(clusters, strategies):
                theme = strategy.get("theme", "unknown")
                strategy_id = f"strategy:{theme}:{hashlib.md5(theme.encode()).hexdigest()[:8]}"

                # Source → Strategy edges
                for mid in cluster.memory_ids:
                    kg.add_relation(
                        source=mid,
                        relation="consolidated_into",
                        target=strategy_id,
                        metadata={
                            "theme": theme,
                            "cluster_size": len(cluster.memory_ids),
                            "origin": "memory_consolidator",
                        },
                    )
                    edges += 1

                # Intra-cluster 'shares_theme' edges (top pairs only to avoid N²)
                ids = cluster.memory_ids[:10]
                for i in range(len(ids)):
                    for j in range(i + 1, min(i + 3, len(ids))):
                        kg.add_relation(
                            source=ids[i],
                            relation="shares_theme",
                            target=ids[j],
                            metadata={"theme": theme, "origin": "memory_consolidator"},
                        )
                        edges += 1

            if edges:
                logger.info("KG enrichment: %s consolidation edges created", edges, exc_info=True)
        except Exception as e:
            logger.debug("KG enrichment skipped: %s", e, exc_info=True)

    def _galactic_promote(self, strategies: list[dict[str, Any]]) -> None:
        """Promote synthesized strategy memories to INNER_RIM galactic zone.

        Consolidated knowledge is high-value by definition — it should
        live close to the galactic core, not drift outward with bulk
        ingested content.
        """
        if not strategies:
            return
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()

            # Find recently-created strategy memories and pull them inward
            recent = um.search("strategy consolidated", limit=len(strategies) + 5)
            promoted = 0
            for mem in recent:
                if "strategy" in (mem.tags or set()) and "consolidated" in (mem.tags or set()):
                    current_dist = getattr(mem, "galactic_distance", None)
                    # Only promote if not already in INNER_RIM or CORE
                    if current_dist is None or current_dist > 0.15:
                        um.backend.update_galactic_distance(mem.id, 0.12)
                        promoted += 1
            if promoted:
                logger.info("Galactic promotion: %s strategy memories → INNER_RIM", promoted, exc_info=True)
        except Exception as e:
            logger.debug("Galactic promotion skipped: %s", e, exc_info=True)

    def _update_harmony(self, report: ConsolidationReport) -> None:
        """Feed consolidation results into the Harmony Vector energy dimension."""
        try:
            from whitemagic.harmony.vector import get_harmony_vector
            hv = get_harmony_vector()
            hv.record_call(
                tool_name="_memory_consolidation",
                duration_s=report.duration_ms / 1000.0,
                success=True,
                declared_safety="READ",
                actual_writes=report.strategies_synthesized + report.promotions,
            )
        except Exception as e:
            logger.debug("Karma ledger append failed after consolidation: %s", e)

    def _emit_events(self, report: ConsolidationReport, strategies: list[dict[str, Any]]) -> None:
        """Emit consolidation and insight events."""
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import (
                EventType,
                ResonanceEvent,
                get_bus,
            )
            bus = get_bus()

            bus.emit(ResonanceEvent(
                event_type=EventType.MEMORY_CONSOLIDATED,
                source="memory_consolidator",
                data={
                    "analyzed": report.memories_analyzed,
                    "clusters": report.clusters_found,
                    "strategies": report.strategies_synthesized,
                    "promotions": report.promotions,
                },
            ))

            if strategies:
                bus.emit(ResonanceEvent(
                    event_type=EventType.INSIGHT_CRYSTALLIZED,
                    source="memory_consolidator",
                    data={
                        "strategy_count": len(strategies),
                        "themes": [s["theme"] for s in strategies[:5]],
                    },
                ))
        except Exception as e:
            logger.debug("Event emission failed during consolidation: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        with self._lock:
            return {
                "total_consolidations": self._total_consolidations,
                "total_strategies": self._total_strategies,
                "total_promotions": self._total_promotions,
                "config": {
                    "min_cluster_size": self._min_cluster_size,
                    "tag_overlap_threshold": self._tag_overlap_threshold,
                    "importance_boost": self._importance_boost,
                    "max_memories": self._max_memories,
                },
                "reconsolidation": self.get_reconsolidation_status(),
            }

    def mark_labile(
        self,
        memory_id: str,
        content: str,
        tags: list[str],
        query: str = "",
    ) -> LabileMemory:
        """Mark a memory as labile (modifiable) after retrieval.

        When a memory is recalled, it enters a brief labile state where it
        can be updated with new context before being re-stored.

        Args:
            memory_id: The memory's unique ID
            content: Current content of the memory
            tags: Current tags
            query: The query that triggered retrieval (provides context)

        Returns:
            The LabileMemory entry
        """
        self._expire_old()

        if memory_id in self._labile:
            existing = self._labile[memory_id]
            existing.retrieved_at = time.time()
            existing.query_context = query or existing.query_context
            return existing

        if len(self._labile) >= MAX_LABILE:
            self._evict_oldest()

        labile = LabileMemory(
            memory_id=memory_id,
            original_content=content,
            original_tags=list(tags),
            query_context=query,
        )
        self._labile[memory_id] = labile
        self._reconsolidation_stats["total_marked"] += 1
        logger.debug("Memory %s entered labile state (query: %s)", memory_id, query[:50])
        return labile

    def update_labile(
        self,
        memory_id: str,
        new_context: str | None = None,
        new_tags: list[str] | None = None,
        annotation: str | None = None,
    ) -> bool:
        """Update a labile memory with new context.

        Args:
            memory_id: The memory to update
            new_context: Additional context to append
            new_tags: New tags to merge
            annotation: A note about why the update happened

        Returns:
            True if the memory was updated, False if not labile or expired
        """
        labile = self._labile.get(memory_id)
        if labile is None or labile.is_expired:
            return False

        update: dict[str, Any] = {"timestamp": time.time()}
        if new_context:
            update["context"] = new_context
        if new_tags:
            update["tags"] = new_tags
        if annotation:
            update["annotation"] = annotation

        labile.updates.append(update)
        self._reconsolidation_stats["total_updated"] += 1
        logger.debug("Labile memory %s updated (%s updates)", memory_id, len(labile.updates))
        return True

    def is_labile(self, memory_id: str) -> bool:
        """Check if a memory is currently in labile state."""
        labile = self._labile.get(memory_id)
        if labile is None:
            return False
        if labile.is_expired:
            del self._labile[memory_id]
            return False
        return True

    def reconsolidate(self, memory_id: str, memory_store: Any = None) -> dict[str, Any] | None:
        """Reconsolidate a single labile memory — apply updates and re-stabilize.

        Args:
            memory_id: The memory to reconsolidate
            memory_store: Optional memory store to persist changes

        Returns:
            Dict with reconsolidation details, or None if not labile
        """
        labile = self._labile.get(memory_id)
        if labile is None:
            return None

        if not labile.updates:
            del self._labile[memory_id]
            return {"memory_id": memory_id, "action": "no_changes", "expired": labile.is_expired}

        content_additions = []
        tag_additions: set[str] = set()
        annotations = []

        for update in labile.updates:
            if "context" in update:
                content_additions.append(update["context"])
            if "tags" in update:
                tag_additions.update(update["tags"])
            if "annotation" in update:
                annotations.append(update["annotation"])

        new_content = labile.original_content
        if content_additions:
            reconsolidation_note = "\n\n[Reconsolidated: " + "; ".join(content_additions) + "]"
            new_content += reconsolidation_note

        new_tags = list(set(labile.original_tags) | tag_additions | {"reconsolidated"})

        if memory_store is not None:
            try:
                memory_store.update_memory(
                    memory_id,
                    content=new_content,
                    tags=new_tags,
                )
                logger.info("Reconsolidated memory %s: +%s contexts, +%s tags", memory_id, len(content_additions), len(tag_additions))
            except Exception as e:
                logger.warning("Failed to persist reconsolidation for %s: %s", memory_id, e, exc_info=True)

        labile.reconsolidated = True
        del self._labile[memory_id]
        self._reconsolidation_stats["total_reconsolidated"] += 1

        return {
            "memory_id": memory_id,
            "action": "reconsolidated",
            "updates_applied": len(labile.updates),
            "content_additions": len(content_additions),
            "tag_additions": list(tag_additions),
            "annotations": annotations,
            "labile_duration_s": round(labile.age_seconds, 1),
        }

    def reconsolidate_all(self, memory_store: Any = None) -> list[dict[str, Any]]:
        """Reconsolidate all labile memories that have updates.

        Typically called at session end, during consolidation cycles, or
        periodically.

        Args:
            memory_store: Memory store to persist changes

        Returns:
            List of reconsolidation reports
        """
        results = []
        ids = list(self._labile.keys())
        for memory_id in ids:
            result = self.reconsolidate(memory_id, memory_store)
            if result:
                results.append(result)
        return results

    def get_labile_ids(self) -> list[str]:
        """Get IDs of all currently labile memories."""
        self._expire_old()
        return list(self._labile.keys())

    def get_reconsolidation_status(self) -> dict[str, Any]:
        """Get reconsolidation engine status."""
        self._expire_old()
        return {
            "labile_count": len(self._labile),
            "labile_window_s": self._labile_window,
            "max_labile": MAX_LABILE,
            **self._reconsolidation_stats,
            "labile_memories": [
                {
                    "memory_id": lm.memory_id,
                    "age_s": round(lm.age_seconds, 1),
                    "updates": len(lm.updates),
                    "query": lm.query_context[:50],
                }
                for lm in self._labile.values()
            ],
        }

    def get_status(self) -> dict[str, Any]:
        """Backward-compat alias for get_reconsolidation_status."""
        return self.get_reconsolidation_status()

    def _expire_old(self) -> None:
        """Remove expired labile entries."""
        expired = [mid for mid, lm in self._labile.items() if lm.is_expired]
        for mid in expired:
            del self._labile[mid]
            self._reconsolidation_stats["total_expired"] += 1

    def _evict_oldest(self) -> None:
        """Evict the oldest labile memory to make room."""
        if not self._labile:
            return
        oldest_id = min(self._labile, key=lambda k: self._labile[k].retrieved_at)
        del self._labile[oldest_id]
        self._reconsolidation_stats["total_expired"] += 1


_consolidator: MemoryConsolidator | None = None
_consolidator_lock = threading.Lock()


def get_consolidator() -> MemoryConsolidator:
    """Get the global Memory Consolidator."""
    global _consolidator
    if _consolidator is None:
        with _consolidator_lock:
            if _consolidator is None:
                _consolidator = MemoryConsolidator()
    return _consolidator


class ConsolidationDaemon:
    """Background thread that auto-schedules memory consolidation.

    Runs consolidation on a configurable interval (default: every 30 minutes).
    Starts automatically when first accessed via get_consolidation_daemon().
    Can be started/stopped manually. Graceful degradation: if consolidation
    fails, it logs and continues to the next cycle.
    """

    def __init__(
        self,
        interval_seconds: int = 1800,
        consolidator: MemoryConsolidator | None = None,
    ) -> None:
        self._interval = interval_seconds
        self._consolidator = consolidator
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_report: ConsolidationReport | None = None
        self._last_run_ts: str = ""
        self._total_runs = 0
        self._total_errors = 0
        self._started = False

    @property
    def consolidator(self) -> MemoryConsolidator:
        if self._consolidator is None:
            self._consolidator = get_consolidator()
        return self._consolidator

    def start(self) -> None:
        """Start the daemon background thread."""
        if self._started:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="wm-consolidation")
        self._thread.start()
        self._started = True
        logger.info("ConsolidationDaemon started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Stop the daemon."""
        if not self._started:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._started = False
        logger.info("ConsolidationDaemon stopped")

    def _run_loop(self) -> None:
        """Main daemon loop."""
        while not self._stop_event.is_set():
            try:
                report = self.consolidator.consolidate()
                self._last_report = report
                self._last_run_ts = datetime.now().isoformat()
                self._total_runs += 1
                if report.clusters_found > 0:
                    logger.info(
                        "ConsolidationDaemon: %d clusters, %d strategies, %d promotions",
                        report.clusters_found, report.strategies_synthesized, report.promotions,
                    )
            except Exception as e:
                self._total_errors += 1
                logger.debug("ConsolidationDaemon cycle error: %s", e, exc_info=True)

            # Wait for interval or stop signal
            self._stop_event.wait(timeout=self._interval)

    def get_status(self) -> dict[str, Any]:
        """Get daemon status."""
        return {
            "running": self._started,
            "interval_seconds": self._interval,
            "total_runs": self._total_runs,
            "total_errors": self._total_errors,
            "last_run": self._last_run_ts,
            "last_report": self._last_report.to_dict() if self._last_report else None,
        }

    def run_once(self) -> ConsolidationReport:
        """Run a single consolidation cycle without starting the daemon."""
        report = self.consolidator.consolidate()
        self._last_report = report
        self._last_run_ts = datetime.now().isoformat()
        self._total_runs += 1
        return report


_consolidation_daemon: ConsolidationDaemon | None = None
_consolidation_daemon_lock = threading.Lock()


def get_consolidation_daemon() -> ConsolidationDaemon:
    """Get the global ConsolidationDaemon (auto-starts on first access)."""
    global _consolidation_daemon
    if _consolidation_daemon is None:
        with _consolidation_daemon_lock:
            if _consolidation_daemon is None:
                _consolidation_daemon = ConsolidationDaemon()
    return _consolidation_daemon
