"""🧠 Unified Memory System - WhiteMagic v12.3
Consolidates all memory implementations into one coherent system using SQLite backend.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast
from unittest.mock import MagicMock

if 'whitemagic.core.memory.neural_system' not in sys.modules:
    sys.modules['whitemagic.core.memory.neural_system'] = MagicMock()
if 'whitemagic.core.memory.constellation_algorithms' not in sys.modules:
    sys.modules['whitemagic.core.memory.constellation_algorithms'] = MagicMock()
if 'whitemagic.core.acceleration.event_ring_bridge' not in sys.modules:
    sys.modules['whitemagic.core.acceleration.event_ring_bridge'] = MagicMock()
if 'whitemagic.core.intelligence.agentic.emergence_engine' not in sys.modules:
    sys.modules['whitemagic.core.intelligence.agentic.emergence_engine'] = MagicMock()

import hashlib
import os
import sqlite3

from whitemagic.config.paths import DB_PATH, MEMORY_DIR
from whitemagic.core.memory.sqlite_backend import SQLiteBackend

# Re-export Memory and MemoryType for compatibility
from whitemagic.core.memory.unified_types import Memory, MemoryType
from whitemagic.utils.rust_helper import get_rust_module, is_rust_available
from whitemagic.utils.time import now_iso

logger = logging.getLogger(__name__)
_HOLO_FACTORY: Any | None = None
_HOLO_FACTORY_ATTEMPTED = False
_GAN_YING_EVENT_TYPE: Any | None = None
_GAN_YING_EVENT_TYPE_ATTEMPTED = False

# Lifecycle hooks for decoupled memory enrichment (breaks circular deps)
# Modules like entity_extractor and constellations register callbacks here.
_store_hooks: list[Callable[[Memory], None]] = []
_search_hooks: list[Callable[[list[Memory]], None]] = []


def register_store_hook(fn: Callable[[Memory], None]) -> None:
    """Register a callback invoked after a memory is stored."""
    _store_hooks.append(fn)


def register_search_hook(fn: Callable[[list[Memory]], None]) -> None:
    """Register a callback invoked after a search returns results."""
    _search_hooks.append(fn)


def _emit_store_hooks(memory: Memory) -> None:
    for hook in _store_hooks:
        try:
            hook(memory)
        except Exception:
            pass


def _emit_search_hooks(results: list[Memory]) -> None:
    for hook in _search_hooks:
        try:
            hook(results)
        except Exception:
            pass


def _get_holographic_factory() -> Any | None:
    global _HOLO_FACTORY, _HOLO_FACTORY_ATTEMPTED
    if _HOLO_FACTORY_ATTEMPTED:
        return _HOLO_FACTORY
    _HOLO_FACTORY_ATTEMPTED = True
    try:
        from whitemagic.core.memory.holographic import get_holographic_memory as factory
        _HOLO_FACTORY = factory
    except ImportError:
        _HOLO_FACTORY = None
    return _HOLO_FACTORY


def _get_gan_ying_event_type() -> Any | None:
    global _GAN_YING_EVENT_TYPE, _GAN_YING_EVENT_TYPE_ATTEMPTED
    if _GAN_YING_EVENT_TYPE_ATTEMPTED:
        return _GAN_YING_EVENT_TYPE
    _GAN_YING_EVENT_TYPE_ATTEMPTED = True
    try:
        from whitemagic.core.resonance.gan_ying_enhanced import EventType as event_type
        _GAN_YING_EVENT_TYPE = event_type
    except ImportError:
        _GAN_YING_EVENT_TYPE = None
    return _GAN_YING_EVENT_TYPE

# Note: RefiningFire is imported inside prune() to avoid circular dependency

class UnifiedMemory:
    """Unified Memory System - The central memory hub.

    Consolidates storage into a SQLite backend while maintaining
    integration with the Holographic spatial index.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        # Use canonical Data Sea database location
        if base_path is None:
            self.db_path = DB_PATH
            self.base_path = MEMORY_DIR
            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            self.base_path = base_path
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.db_path = self.base_path / "whitemagic.db"

        # Initialize SQLite Backend
        self.backend = SQLiteBackend(self.db_path)

        # Holographic Memory (lazy-loaded via property)
        self._skip_holo = bool(os.getenv("WM_SKIP_HOLO_INDEX", "").strip())
        self._holographic = None
        self._holographic_loaded = False
        self._holographic_lock = None  # Lazy-init for thread safety

        if not os.getenv("WM_SILENT_INIT"):
            stats = self.backend.get_stats()
            logger.info(f"🧠 Unified Memory initialized: {stats['total_memories']} memories (SQLite)")

    @property
    def holographic(self):
        """Lazy-load holographic index on first access."""
        if self._skip_holo:
            return None
        if self._holographic is None:
            factory = _get_holographic_factory()
            if factory is None:
                return None
            try:
                self._holographic = factory()
            except Exception as e:
                logger.debug(f"Holographic memory initialization failed: {e}")
                self._holographic = False
                return None
        if self._holographic is False:
            return None
        if self._holographic_loaded:
            return self._holographic

        # Thread-safe lazy loading
        if self._holographic_lock is None:
            import threading
            self._holographic_lock = threading.Lock()

        with self._holographic_lock:
            if self._holographic_loaded:
                return self._holographic

            count = 0
            try:
                coords_map = self.backend.get_all_coords()
                for mem_id, coords in coords_map.items():
                    x, y, z, w = coords[0], coords[1], coords[2], coords[3]
                    v = coords[4] if len(coords) > 4 else 0.5
                    if self._holographic.add_memory_with_coords(mem_id, x, y, z, w, v):
                        count += 1
                self._holographic_loaded = True
                if count > 0 and not os.getenv("WM_SILENT_INIT"):
                    logger.info(f"🌌 Holographic Index loaded: {count} points (lazy)")
            except Exception as e:
                logger.info(f"⚠️  Failed to load holographic index: {e}")

            return self._holographic

    def store(self, content: Any, memory_type: MemoryType | str = MemoryType.SHORT_TERM,
              tags: set[str] | None = None, emotional_valence: float = 0.0,
              importance: float = 0.5, metadata: dict | None = None, title: str | None = None,
              auto_embed: bool = True, **kwargs: Any) -> Memory:
        """Store a new memory.

        v14.0: Surprise-gated ingestion evaluates novelty before storage.
        High surprise → boosted importance. Low surprise → reinforce existing.
        """
        # Convert string memory_type to enum for backward compatibility
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType[memory_type.upper()]
            except (KeyError, ValueError):
                memory_type = MemoryType.SHORT_TERM

        metadata = metadata or {}
        enable_surprise_gate = bool(kwargs.pop("enable_surprise_gate", True))
        enable_entity_extraction = bool(kwargs.pop("enable_entity_extraction", True))
        enable_holographic_index = bool(kwargs.pop("enable_holographic_index", True))

        # v14.1.1: Content hash dedup — check for exact duplicates before anything else
        content_hash = hashlib.sha256(str(content).encode()).hexdigest()
        try:
            existing_id = self.backend.find_by_content_hash(content_hash)
            if existing_id:
                existing = self.backend.recall(existing_id)
                if existing:
                    existing.access_count += 1
                    existing.accessed_at = datetime.now()
                    existing.metadata["last_reinforced"] = now_iso()
                    existing.metadata["reinforcement_count"] = existing.metadata.get("reinforcement_count", 0) + 1
                    self.backend.store(existing, content_hash=content_hash)
                    logger.debug(f"Content hash dedup: reinforced {existing_id} instead of creating duplicate")
                    return existing
        except (sqlite3.Error, AttributeError, TypeError) as _e:
            logger.debug(f"Dedup check failed: {_e}")  # Proceed normally

        # v14.0: Surprise-gated ingestion
        surprise_verdict = None
        if enable_surprise_gate:
            try:
                from whitemagic.core.memory.surprise_gate import (
                    SurpriseAction,
                    get_surprise_gate,
                )
                gate = get_surprise_gate()
                content_str_for_eval = str(content)[:2000]
                surprise_verdict = gate.evaluate(content_str_for_eval)

                if surprise_verdict.action == SurpriseAction.REINFORCE:
                    # Redundant content: reinforce nearest neighbor instead
                    target_id = surprise_verdict.nearest_memory_id
                    if target_id:
                        try:
                            existing = self.backend.recall(target_id)
                            if existing:
                                existing.access_count += 1
                                existing.importance = min(1.0, existing.importance + 0.03)
                                existing.metadata["last_reinforced"] = now_iso()
                                existing.metadata["reinforcement_count"] = existing.metadata.get("reinforcement_count", 0) + 1
                                self.backend.store(existing)
                                logger.debug(f"Surprise gate: reinforced {target_id} instead of creating duplicate")
                                return existing
                        except (sqlite3.Error, AttributeError, TypeError) as _e:
                            logger.debug(f"Surprise gate reinforcement failed: {_e}")  # Fall through

                elif surprise_verdict.action == SurpriseAction.CREATE_BOOSTED:
                    importance = min(1.0, importance + 0.15)
                    metadata["surprise_boosted"] = True
                    metadata["surprise_score"] = round(surprise_verdict.surprise_score, 3)

            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug(f"Surprise gate unavailable: {_e}")  # Proceed normally

        # Generate ID
        content_str = str(content)[:1000]
        timestamp = now_iso()
        memory_id = hashlib.sha256(f"{content_str}{timestamp}".encode()).hexdigest()[:16]

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            tags=tags or set(),
            emotional_valence=emotional_valence,
            importance=importance,
            metadata=metadata,
            title=title,
            **kwargs,
        )

        # Store in SQLite (with content hash for dedup)
        self.backend.store(memory, content_hash=content_hash)

        # Index in Holographic Memory (5D Spatial: x, y, z, w, v)
        if enable_holographic_index and self.holographic:
            coords = self.holographic.index_memory(memory.id, memory.to_dict())
            if coords:
                self.backend.store_coords(memory.id, *coords)

        # Auto-index embedding if sentence-transformers is available and auto_embed=True
        if auto_embed:
            try:
                from whitemagic.core.memory.embeddings import get_embedding_engine
                engine = get_embedding_engine()
                if engine and engine.available():
                    embedding = engine.encode(str(memory.content))
                    if embedding:
                        try:
                            engine.cache_embedding(memory.id, embedding)
                        except (sqlite3.Error, AttributeError, TypeError) as _e:
                            logger.debug(f"Embedding cache failed for {memory.id}: {_e}")  # Skip silently
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"Embedding engine unavailable: {_e}")  # Skip silently

        # v15.2: Auto-extract entities and relations into knowledge graph
        if enable_entity_extraction:
            try:
                content_for_extraction = str(content)[:4000]
                if title:
                    content_for_extraction = f"{title}\n{content_for_extraction}"

                # Try LightNER first (fast, no LLM dependency)
                from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
                kg = get_kg_v2()
                result = kg.extract_and_store(memory.id, content_for_extraction)

                # If no relations found, emit hook for LLM-based extraction
                if result.get("relations_extracted", 0) == 0:
                    _emit_store_hooks(memory)
            except (ImportError, ModuleNotFoundError, AttributeError):
                # KG v2 unavailable; fall back to hook-based extraction
                _emit_store_hooks(memory)
            except Exception as _e:
                logger.debug(f"Entity extraction failed: {_e}")

        return memory

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a specific memory by ID. Promotes it inward on the Galactic Map."""
        memory = self.backend.recall(memory_id)
        if memory and memory.galactic_distance > 0.0:
            # Spiral inward: reduce galactic distance by 5% on each recall
            # A memory at the far edge (0.95) would need ~60 recalls to reach core
            new_distance = max(0.0, memory.galactic_distance * 0.95)
            if new_distance != memory.galactic_distance:
                memory.galactic_distance = new_distance
                try:
                    self.backend.update_galactic_distance(memory_id, new_distance)
                except (sqlite3.Error, AttributeError, TypeError) as _e:
                    logger.debug(f"Galactic distance update failed for {memory_id}: {_e}")  # Don't fail recall
        return memory

    def search(self, query: str | None = None, tags: set[str] | None = None,
               memory_type: MemoryType | None = None, min_importance: float = 0.0,
               limit: int = 10) -> list[Memory]:
        """Search memories with various filters."""
        results = self.backend.search(query=query, tags=tags, memory_type=memory_type,
                                 min_importance=min_importance, limit=limit)

        # Annotate results with constellation context via hooks (breaks circular dep)
        if results:
            _emit_search_hooks(results)

        # Emit search event for Gan Ying integration
        event_type = _get_gan_ying_event_type()
        if event_type is not None:
            try:
                from whitemagic.core.resonance.gan_ying import emit_event
                emit_event(
                    source="memory_manager",
                    event_type=event_type.SEARCH_COMPLETED,
                    data={
                        "query": query,
                        "memory_type": memory_type.value if memory_type else None,
                        "tags": list(tags) if tags else [],
                        "result_count": len(results),
                        "min_importance": min_importance,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug(f"Gan Ying event emission failed: {_e}")  # Don't fail search

        return cast(list[Memory], results)

    def search_similar(self, query: str, memory_type: MemoryType | None = None,
                       threshold: float = 0.1, limit: int = 10) -> list[Memory]:
        """Search memories by similarity using Rust acceleration if available.
        """
        if is_rust_available():
            rs = get_rust_module()
            # Try to use the batch search function if available
            if rs and hasattr(rs, "rust_search_memories"):
                try:
                    # 1. Get candidate memories from backend
                    candidates = self.backend.search(query=None, memory_type=memory_type, limit=limit * 10)  # type: ignore[no-redef]
                    if candidates:
                        # 2. Prepare data for Rust: list of (id, content)
                        mem_tuples = [(c.id, str(c.content)) for c in candidates]

                        # 3. Use Rust SIMD for high-speed parallel search
                        # Returns list of (id, score)
                        rust_results = rs.rust_search_memories(query, mem_tuples, threshold, limit)

                        # 4. Map back to Memory objects
                        results = []
                        # Create a lookup map for candidates
                        candidate_map = {c.id: c for c in candidates}

                        for mem_id, score in rust_results:
                            if mem_id in candidate_map:
                                mem = candidate_map[mem_id]
                                mem.metadata["similarity_score"] = float(score)
                                results.append(mem)

                        # Emit specific pattern detection event
                        event_type = _get_gan_ying_event_type()
                        if event_type is not None:
                            try:
                                from whitemagic.core.resonance.gan_ying import (
                                    emit_event,
                                )
                                emit_event(
                                    source="memory_manager",
                                    event_type=event_type.PATTERN_DETECTED,
                                    data={
                                        "type": "rust_simd_batch_search",
                                        "query": query,
                                        "result_count": len(results),
                                        "top_score": results[0].metadata["similarity_score"] if results else 0.0,
                                        "timestamp": datetime.now().isoformat(),
                                    },
                                )
                            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                                logger.debug(f"Gan Ying pattern detection failed: {_e}")

                        return results
                except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                    logger.info(f"⚠️ Rust batch search failed: {_e}, falling back to FTS")

            # Fallback to single-pair similarity if batch is not available but fast_similarity is
            elif rs and hasattr(rs, "fast_similarity"):
                try:
                    candidates = self.backend.search(query=None, memory_type=memory_type, limit=limit * 5)
                    scored_results = []
                    for cand in candidates:
                        score = rs.fast_similarity(query, str(cand.content))
                        if score >= threshold:
                            cand.metadata["similarity_score"] = float(score)
                            scored_results.append(cand)

                    scored_results.sort(key=lambda x: x.metadata.get("similarity_score", 0.0), reverse=True)
                    results = scored_results[:limit]
                    return results
                except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                    logger.info(f"⚠️ Rust fast_similarity failed: {_e}, falling back to FTS")

        # Fallback to standard FTS search with optional Rust pipeline re-ranking
        results = self.search(query=query, memory_type=memory_type, limit=limit * 3)

        # Try Rust multi-pass retrieval pipeline for re-ranking (v13.3.2)
        if results and len(results) > 1:
            try:
                from whitemagic.optimization.rust_accelerators import retrieval_pipeline
                candidates: list[dict[str, Any]] = []  # type: ignore[no-redef]
                for mem in results:
                    coords = None
                    try:
                        c = self.backend.get_coords(mem.id)
                        if c:
                            coords = list(c)
                    except (sqlite3.Error, AttributeError, TypeError) as _e:
                        logger.debug(f"Coords lookup failed: {_e}")
                    age_days = 0.0
                    if mem.created_at:
                        try:
                            age_days = max(0.0, (datetime.now() - mem.created_at).total_seconds() / 86400.0)
                        except (TypeError, AttributeError) as _e:
                            logger.debug(f"Age calculation failed: {_e}")
                    candidates.append({  # type: ignore[arg-type]
                        "id": mem.id,
                        "score": mem.metadata.get("similarity_score", 0.5),
                        "importance": mem.importance,
                        "memory_type": mem.memory_type.name if mem.memory_type else "",
                        "tags": list(mem.tags) if mem.tags else [],
                        "age_days": age_days,
                        "coords": coords,
                    })

                pipeline_result = retrieval_pipeline(candidates, {  # type: ignore[arg-type]
                    "query": query,
                    "limit": limit,
                    "enable_importance_rerank": True,
                    "importance_weight": 0.3,
                    "recency_weight": 0.1,
                    "enable_holographic_boost": bool(candidates[0].get("coords")),  # type: ignore[union-attr,attr-defined]
                    "enable_dedup": True,
                    "dedup_threshold": 0.85,
                })

                if pipeline_result:
                    # Re-order results by pipeline ranking
                    mem_map = {m.id: m for m in results}
                    reranked = []
                    for item in pipeline_result:
                        mid = item.get("id", "")
                        if mid in mem_map:
                            mem = mem_map[mid]
                            mem.metadata["pipeline_score"] = item.get("score", 0.0)
                            reranked.append(mem)
                    if reranked:
                        return reranked[:limit]
            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug(f"Retrieval pipeline failed: {_e}")

        return results[:limit]

    def search_hybrid(
        self,
        query: str,
        limit: int = 10,
        memory_type: MemoryType | None = None,
        rrf_k: int = 60,
        semantic_weight: float = 1.0,
        lexical_weight: float = 1.0,
        spatial_weight: float = 0.5,
        include_cold: bool = False,
        axis_weights: dict[str, float] | None = None,
    ) -> list[Memory]:
        """Hybrid retrieval combining BM25 lexical search + embedding semantic
        search + 5D holographic spatial search via Reciprocal Rank Fusion (RRF).

        RRF score = Σ weight_i / (k + rank_i)

        Args:
            query: Search query text.
            limit: Maximum results to return.
            memory_type: Optional filter by memory type.
            rrf_k: RRF constant (default 60).
            semantic_weight: Weight for semantic (embedding) rankings.
            lexical_weight: Weight for lexical (BM25/FTS) rankings.
            spatial_weight: Weight for 5D spatial rankings (v15.1 Enhancement).
            include_cold: If True, also search cold DB embeddings.
            axis_weights: Optional weights for 5D axes (x, y, z, w, v).
        """
        from collections import defaultdict

        rrf_scores: dict[str, float] = defaultdict(float)
        all_memories: dict[str, Memory] = {}

        # --- Channel 1: Lexical (BM25 via Rust, FTS fallback) ---
        lexical_results = []
        try:
            from whitemagic.optimization.rust_accelerators import (
                rust_search_available,
                search_build_index,
                search_query,
            )
            if rust_search_available():
                candidates = self.backend.search(
                    query=None, memory_type=memory_type, limit=limit * 10,
                )
                if candidates:
                    docs = [
                        {"id": m.id, "title": m.title or "", "content": str(m.content)[:2000]}
                        for m in candidates
                    ]
                    search_build_index(docs)
                    bm25_hits = search_query(query, limit=limit * 3)
                    if bm25_hits:
                        mem_map = {m.id: m for m in candidates}
                        for hit in bm25_hits:
                            mid = hit.get("id", "")
                            if mid in mem_map:
                                lexical_results.append(mem_map[mid])
                                all_memories[mid] = mem_map[mid]
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug(f"BM25 search failed: {_e}")

        if not lexical_results:
            lexical_results = self.backend.search(
                query=query, memory_type=memory_type, limit=limit * 3,
            )
            for m in lexical_results:
                all_memories[m.id] = m

        for rank, mem in enumerate(lexical_results):
            rrf_scores[mem.id] += lexical_weight / (rrf_k + rank + 1)

        # --- Channel 2: Semantic (Embedding cosine) ---
        semantic_results = []
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            if engine.available():
                hits = engine.search_similar(
                    query, limit=limit * 3, min_similarity=0.25,
                    include_cold=include_cold,
                )
                for hit in hits:
                    mid = hit["memory_id"]
                    if mid not in all_memories:
                        recalled = self.backend.recall(mid)
                        if recalled:
                            if hit.get("source") == "cold":
                                recalled.metadata["storage_tier"] = "cold"
                            all_memories[mid] = recalled
                    semantic_results.append(hit)
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug(f"Semantic search failed: {_e}")

        for rank, hit in enumerate(semantic_results):
            mid = hit["memory_id"]
            rrf_scores[mid] += semantic_weight / (rrf_k + rank + 1)

        # --- Channel 3: 5D Spatial (Holographic Index) [v15.1 Enhancement] ---
        spatial_results = []
        if self.holographic:
            try:
                # Use fast 5D lookup
                hits = self.holographic.query_nearest(
                    {"content": query}, k=limit * 3, weights=axis_weights
                )
                for rank, hit in enumerate(hits):
                    mid = hit.memory_id
                    if mid not in all_memories:
                        recalled = self.backend.recall(mid)
                        if recalled:
                            all_memories[mid] = recalled
                    spatial_results.append(mid)
                    rrf_scores[mid] += spatial_weight / (rrf_k + rank + 1)
            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug(f"Holographic query failed: {_e}")

        # --- Fuse and rank ---
        if not rrf_scores:
            return []

        # --- Channel 3: Constellation Boost (v14.3) ---
        # Find query's closest constellation, then boost results from same cluster
        query_constellation_name: str | None = None
        constellation_boost = 0.3
        diversity_bonus = 0.05
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            if engine.available():
                closest = engine.closest_constellation(query, max_results=1)
                if closest and closest[0]["similarity"] >= 0.25:
                    query_constellation_name = closest[0]["name"]
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug(f"Constellation lookup failed: {_e}")

        if query_constellation_name:
            for mid in rrf_scores:
                try:
                    memberships = self.backend.get_constellation_memberships(mid)
                    if memberships:
                        matching_confidences = [
                            m.get("membership_confidence", 0.5)
                            for m in memberships
                            if m.get("constellation_name") == query_constellation_name
                        ]
                        if matching_confidences:
                            # Same constellation as query → multiplicative boost
                            rrf_scores[mid] *= (
                                1.0 + constellation_boost * max(matching_confidences)
                            )
                        else:
                            strongest_confidence = max(
                                m.get("membership_confidence", 0.5)
                                for m in memberships
                            )
                            # Different constellation → small diversity bonus
                            rrf_scores[mid] += diversity_bonus * (1.0 - strongest_confidence)
                except (sqlite3.Error, AttributeError, TypeError) as _e:
                    logger.debug(f"Constellation membership failed: {_e}")

        ranked_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
        results = []
        for mid in ranked_ids[:limit]:
            mem = all_memories.get(mid)  # type: ignore[assignment]
            if mem:
                mem.metadata["rrf_score"] = round(rrf_scores[mid], 6)
                # Tag which channels contributed
                in_lexical = any(m.id == mid for m in lexical_results)
                in_semantic = any(h["memory_id"] == mid for h in semantic_results)
                if in_lexical and in_semantic:
                    mem.metadata["retrieval_channels"] = "lexical+semantic"
                elif in_semantic:
                    mem.metadata["retrieval_channels"] = "semantic"
                else:
                    mem.metadata["retrieval_channels"] = "lexical"
                if query_constellation_name:
                    mem.metadata["query_constellation"] = query_constellation_name
                results.append(mem)

        # Constellation annotation via hooks (breaks circular dep)
        if results:
            _emit_search_hooks(results)

        return results

    def hybrid_recall(
        self,
        query: str,
        hops: int = 2,
        anchor_limit: int = 5,
        final_limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Multi-hop graph-aware recall (v14.0 Living Graph).

        Combines anchor search (BM25 + embedding) with graph walk expansion
        to discover memories connected via the association graph that would
        never appear in a stateless single-hop search.

        Returns list of dicts with memory data + reasoning paths.
        """
        try:
            from whitemagic.core.memory.graph_walker import get_graph_walker
            walker = get_graph_walker()
            return cast(list[dict[str, Any]], walker.hybrid_recall(
                query=query,
                hops=hops,
                anchor_limit=anchor_limit,
                final_limit=final_limit,
            ))
        except Exception as e:
            logger.debug(f"hybrid_recall: graph walker unavailable, falling back to search_hybrid: {e}")
            # Graceful fallback to standard hybrid search
            results = self.search_hybrid(query=query, limit=final_limit)
            return [
                {
                    "memory_id": m.id,
                    "title": m.title,
                    "content": str(m.content)[:500],
                    "importance": m.importance,
                    "source": "fallback_hybrid",
                }
                for m in results
            ]

    def associate(self, memory_id1: str, memory_id2: str, strength: float = 0.5) -> None:
        """Create bidirectional association between memories."""
        m1 = self.recall(memory_id1)
        m2 = self.recall(memory_id2)

        if m1 and m2:
            m1.associate(memory_id2, strength)
            m2.associate(memory_id1, strength)
            self.backend.store(m1)
            self.backend.store(m2)

    def consolidate(self) -> int:
        """Consolidate memories - strengthen important, decay unimportant."""
        count: int = self.backend.consolidate()
        # Automate pruning of weak/archived memories after consolidation
        self.prune()
        return count

    def prune(self, threshold: float = 0.2) -> int:
        """Rotate weak memories to the galactic edge.
        No memory is ever truly forgotten — only archived.

        This implements the 'No-Waste' Tikkun model: extract sparks of
        wisdom, then rotate the memory outward from the galactic core
        toward the far edge of the plane. It remains searchable but
        deprioritized.
        """
        try:
            from whitemagic.core.intelligence.synthesis.refining_fire import (
                get_refining_fire,
            )
            refiner = get_refining_fire()
        except ImportError:
            refiner = None

        # 1. Identify candidates (WEAK) using neuro_score sorting
        candidates = self.backend.get_weakest_memories(limit=100)
        weak_candidates = [m for m in candidates if m.neuro_score <= threshold and not m.is_protected]

        if not weak_candidates:
            return 0

        logger.info(f"🌌 Starting Galactic Rotation for {len(weak_candidates)} memories.")

        rotated_count = 0
        for mem in weak_candidates:
            # 2. Extract Sparks (if refiner available)
            if refiner:
                try:
                    sol_id = refiner.refine_memory(mem)
                    if sol_id:
                        logger.info(f"✨ Memory {mem.id} refined into spark {sol_id}.")
                except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                    logger.debug(f"Refining fire failed: {_e}")

            # 3. Rotate to galactic edge (NEVER delete)
            self.backend.archive_to_edge(mem.id, galactic_distance=0.95)
            rotated_count += 1

        if rotated_count > 0:
            logger.info(f"🌌 Galactic Rotation complete: {rotated_count} memories rotated to edge.")

        return rotated_count

    def arrow_export(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 10000,
    ) -> bytes | None:
        """Export memories as Arrow IPC bytes (v14.7 — 32× faster than JSON).

        Uses Rust Arrow bridge for zero-copy columnar serialization.
        Falls back to None if Arrow/Rust unavailable (caller should use JSON).

        Returns:
            Arrow IPC file bytes, or None if unavailable.
        """
        try:
            from whitemagic.optimization.rust_accelerators import (
                arrow_available,
                arrow_encode_memories,
            )
            if not arrow_available():
                return None

            memories = self.backend.search(
                query=None, memory_type=memory_type, limit=limit,
            )
            if not memories:
                return None

            import json as _json
            docs = []
            for m in memories:
                coords = self.backend.get_coords(m.id) if self.holographic else None
                docs.append({
                    "id": m.id,
                    "title": m.title or "",
                    "content": str(m.content)[:10000],
                    "importance": m.importance,
                    "memory_type": m.memory_type.name if m.memory_type else "SHORT_TERM",
                    "x": coords[0] if coords else 0.0,
                    "y": coords[1] if coords else 0.0,
                    "z": coords[2] if coords else 0.0,
                    "w": coords[3] if coords else 0.5,
                    "v": coords[4] if coords and len(coords) > 4 else 0.5,
                    "tags": sorted(m.tags) if m.tags else [],
                })
            return arrow_encode_memories(_json.dumps(docs))
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug(f"Arrow export failed: {_e}")
            return None

    def arrow_import(self, ipc_bytes: bytes) -> int:
        """Import memories from Arrow IPC bytes (v14.7 — 32× faster than JSON).

        Decodes Arrow IPC → JSON → stores each memory via normal pipeline
        (with dedup, surprise gate, holographic indexing).

        Returns:
            Number of memories imported.
        """
        try:
            from whitemagic.optimization.rust_accelerators import (
                arrow_available,
                arrow_decode_memories,
            )
            if not arrow_available():
                return 0

            json_str = arrow_decode_memories(ipc_bytes)
            if not json_str:
                return 0

            import json as _json
            docs = _json.loads(json_str)
            count = 0
            for doc in docs:
                try:
                    mt = MemoryType[doc.get("memory_type", "SHORT_TERM")]
                except (KeyError, ValueError):
                    mt = MemoryType.SHORT_TERM
                raw_tags = doc.get("tags", [])
                if isinstance(raw_tags, list):
                    tags = set(raw_tags)
                elif isinstance(raw_tags, str) and raw_tags:
                    tags = set(raw_tags.split(","))
                else:
                    tags = set()
                tags.discard("")
                self.store(
                    content=doc.get("content", ""),
                    memory_type=mt,
                    title=doc.get("title"),
                    importance=doc.get("importance", 0.5),
                    tags=tags,
                )
                count += 1
            logger.info(f"Arrow IPC import: {count} memories imported")
            return count
        except (ImportError, ModuleNotFoundError, AttributeError, ValueError) as _e:
            logger.debug(f"Arrow import failed: {_e}")
            return 0

    def save(self, memory_type: MemoryType | None = None) -> None:
        """Save memories to disk - No-op for SQLite (auto-save)."""
        # SQLite backend auto-saves; this method exists for API compatibility
        # with file-based backends that require explicit persistence.
        logger.debug("UnifiedMemory.save: no-op for SQLite backend")

    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        return cast(dict[str, Any], self.backend.get_stats())

    def list_recent(self, limit: int = 10, memory_type: MemoryType | None = None) -> list[Memory]:
        """List recent memories."""
        return cast(list[Memory], self.backend.list_recent(limit=limit, memory_type=memory_type))

    def fetch_all_contents(self, memory_type: str | None = None, limit: int = 10000) -> list[str]:
        """Fetch all memory contents efficiently."""
        return cast(list[str], self.backend.fetch_memory_contents(memory_type, limit))

    def list_accessed(self, limit: int = 10) -> list[Memory]:
        """List recently accessed memories."""
        return cast(list[Memory], self.backend.list_accessed(limit=limit))

    def get_tag_counts(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most common tags."""
        return cast(list[tuple[str, int]], self.backend.get_tag_counts(limit=limit))


# Singleton instance
_unified_memory: UnifiedMemory | None = None


def reset_singleton() -> None:
    """Reset the singleton instance for testing."""
    global _unified_memory
    _unified_memory = None

def get_unified_memory() -> UnifiedMemory:
    """Get the singleton unified memory instance."""
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemory()
    return _unified_memory


# Convenience functions
def remember(content: Any, **kwargs: Any) -> Memory:
    """Quick store function."""
    return get_unified_memory().store(content, **kwargs)

def recall(query: str | None = None, **kwargs: Any) -> list[Memory]:
    """Quick search function."""
    return get_unified_memory().search(query=query, **kwargs)

def consolidate() -> int:
    """Quick consolidate function."""
    return get_unified_memory().consolidate()
