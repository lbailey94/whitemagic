# ruff: noqa: BLE001
"""🧠 Unified Memory System - WhiteMagic v12.3
Consolidates all memory implementations into one coherent system using SQLite backend.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import hashlib
import os
import sqlite3
import threading

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
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass


def _emit_search_hooks(results: list[Memory]) -> None:
    for hook in _search_hooks:
        try:
            hook(results)
        except Exception as e:
            logger.debug("Operation failed: %s", e)
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

    def __init__(self, base_path: Path | None = None, user_id: str = "local") -> None:
        # Use canonical Data Sea database location
        if base_path is None:
            from whitemagic.config.paths import DB_PATH as _db_path, MEMORY_DIR as _mem_dir
            self._db_path = _db_path
            self.base_path = _mem_dir
            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            self.base_path = base_path
            self.base_path.mkdir(parents=True, exist_ok=True)
            self._db_path = self.base_path / "whitemagic.db"

        self._user_id = user_id

        # v24: Use GalaxyAwareBackend for per-galaxy SQLite routing
        # This isolates corruption risk and reduces lock contention
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend
        self._galaxy_backend = GalaxyAwareBackend(self._db_path, user_id=user_id)
        # Phase 2: .backend now resolves to the GalaxyAwareBackend façade.
        # GalaxyAwareBackend proxies all SQLiteBackend methods, with
        # galaxy-aware routing for store/recall/search/delete and
        # __getattr__ delegation to the default backend for other methods.
        self.backend = self._galaxy_backend

        # Holographic Memory (lazy-loaded via property)
        self._skip_holo = bool(os.getenv("WM_SKIP_HOLO_INDEX", "").strip())
        self._holographic = None
        self._holographic_loaded = False
        self._holographic_lock = None  # Lazy-init for thread safety

        if not os.getenv("WM_SILENT_INIT"):
            stats = self._galaxy_backend.get_stats()
            logger.info("🧠 Unified Memory initialized: %s memories (SQLite)", stats['total_memories'])

    @property
    def pool(self) -> Any:
        """Proxy to the galaxy-aware backend's connection pool.

        This provides a clean migration path for consumers that previously
        accessed ``.backend.pool`` directly. The pool routes to the default
        backend's connection pool.
        """
        return self._galaxy_backend.pool

    @property
    def db_path(self) -> Path:
        """Proxy to the galaxy-aware backend's database path."""
        return self._galaxy_backend.db_path

    @db_path.setter
    def db_path(self, value: Path) -> None:
        """Set the database path (used during init)."""
        self._db_path = value

    @property
    def holographic(self) -> Any:
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
                logger.debug("Holographic memory initialization failed: %s", e, exc_info=True)
                self._holographic = False  # type: ignore[assignment]
                return None
        if self._holographic is False:
            return None
        if self._holographic_loaded:
            return self._holographic

        # Thread-safe lazy loading
        if self._holographic_lock is None:
            import threading
            self._holographic_lock = threading.Lock()  # type: ignore[assignment]

        with self._holographic_lock:
            if self._holographic_loaded:
                return self._holographic

            count = 0
            try:
                coords_map = self._galaxy_backend.get_all_coords()
                for mem_id, coords in coords_map.items():
                    x, y, z, w = coords[0], coords[1], coords[2], coords[3]
                    v = coords[4] if len(coords) > 4 else 0.5
                    if self._holographic.add_memory_with_coords(mem_id, x, y, z, w, v):
                        count += 1
                self._holographic_loaded = True
                if count > 0 and not os.getenv("WM_SILENT_INIT"):
                    logger.info("🌌 Holographic Index loaded: %s points (lazy)", count, exc_info=True)
            except Exception as e:
                logger.info("⚠️  Failed to load holographic index: %s", e, exc_info=True)

            return self._holographic

    def _lww_resolve(self, local: Memory, remote: Memory) -> Memory:
        """CRDT Last-Writer-Wins merge for multi-agent memory coherence.

        Resolves conflicts between two Memory versions using:
        1. Higher version number wins
        2. If versions are equal, higher agent_id wins (deterministic tiebreak)

        Returns the winning Memory object.
        """
        if remote.version > local.version:
            return remote
        elif local.version > remote.version:
            return local
        # Versions are equal — tiebreak by agent_id (lexicographic)
        if remote.agent_id >= local.agent_id:
            return remote
        return local

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the galaxy-aware backend.

        This allows consumers to call backend methods directly on
        UnifiedMemory (e.g. ``um.decay_associations()`` instead of
        ``um.backend.decay_associations()``), providing a clean migration
        path away from ``.backend`` access.

        Core methods (store, recall, search, update_memory, etc.) are
        explicitly defined on UnifiedMemory and take precedence.
        """
        # Avoid recursion for internal attributes
        if name.startswith("_"):
            raise AttributeError(f"'UnifiedMemory' object has no attribute '{name}'")
        # Delegate to the galaxy-aware backend
        backend = self.__dict__.get("_galaxy_backend")
        if backend is not None:
            return getattr(backend, name)
        raise AttributeError(f"'UnifiedMemory' object has no attribute '{name}'")

    def store(self, content: Any, memory_type: MemoryType | str = MemoryType.SHORT_TERM,
              tags: set[str] | None = None, emotional_valence: float = 0.0,
              importance: float = 0.5, metadata: dict | None = None, title: str | None = None,
              auto_embed: bool = True, galaxy: str = "universal",
              subsystem: str | None = None, source_trust: str = "user",
              agent_id: str = "",
              memory_context: Any = None,
              **kwargs: Any) -> Memory:
        """Store a new memory.

        v14.0: Surprise-gated ingestion evaluates novelty before storage.
        High surprise → boosted importance. Low surprise → reinforce existing.
        v23.1: Galaxy parameter routes memory to cognitive galaxy (6D).
        v23.4: If galaxy is "universal" and subsystem is provided, auto-routes
               via GalaxyRouter.route(subsystem, metadata).
        v24: source_trust tags provenance (user/tool_output/web/inferred) to
             defend against Trojan Hippo memory poisoning attacks.
        """
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType[memory_type.upper()]
            except (KeyError, ValueError):
                memory_type = MemoryType.SHORT_TERM

        metadata = metadata or {}

        # Phase 2: Apply MemoryContext if provided (request-scoped namespace routing)
        if memory_context is not None:
            # MemoryContext overrides galaxy and agent_id for request-scoped operations
            ctx_galaxy = memory_context.galaxy
            if ctx_galaxy and ctx_galaxy != "default":
                galaxy = ctx_galaxy
            if memory_context.agent_id and memory_context.agent_id != "default":
                agent_id = memory_context.agent_id
            # Store the namespace in metadata for audit trail
            metadata.setdefault("_namespace", memory_context.namespace_key)
            metadata.setdefault("_user_id", memory_context.user_id)

        # v23.4: Auto-route galaxy via GalaxyRouter if subsystem is provided
        # and no explicit galaxy was given (galaxy defaults to "universal").
        if galaxy == "universal" and subsystem:
            try:
                from whitemagic.core.memory.galaxy_router import get_galaxy_router
                routed = get_galaxy_router().route(subsystem, metadata)
                if routed and routed != "universal":
                    galaxy = routed
            except Exception:
                pass  # Graceful degradation: fall back to universal

        enable_surprise_gate = bool(kwargs.pop("enable_surprise_gate", True))
        enable_entity_extraction = bool(kwargs.pop("enable_entity_extraction", True))
        enable_holographic_index = bool(kwargs.pop("enable_holographic_index", True))

        # v14.1.1: Content hash dedup — check for exact duplicates before anything else
        content_hash = hashlib.sha256(str(content).encode()).hexdigest()
        try:
            existing_id = self._galaxy_backend.find_by_content_hash(content_hash)
            if existing_id:
                existing = self._galaxy_backend.recall(existing_id)
                if existing:
                    existing.access_count += 1
                    existing.accessed_at = datetime.now()
                    existing.metadata["last_reinforced"] = now_iso()
                    existing.metadata["reinforcement_count"] = existing.metadata.get("reinforcement_count", 0) + 1
                    self._galaxy_backend.store(existing, content_hash=content_hash)
                    logger.debug("Content hash dedup: reinforced %s instead of creating duplicate", existing_id, exc_info=True)
                    return existing
        except (sqlite3.Error, AttributeError, TypeError) as _e:
            logger.debug("Dedup check failed: %s", _e)  # Proceed normally

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
                            existing = self._galaxy_backend.recall(target_id)
                            if existing:
                                existing.access_count += 1
                                existing.importance = min(1.0, existing.importance + 0.03)
                                existing.metadata["last_reinforced"] = now_iso()
                                existing.metadata["reinforcement_count"] = existing.metadata.get("reinforcement_count", 0) + 1
                                self._galaxy_backend.store(existing)
                                logger.debug("Surprise gate: reinforced %s instead of creating duplicate", target_id, exc_info=True)
                                return existing
                        except (sqlite3.Error, AttributeError, TypeError) as _e:
                            logger.debug("Surprise gate reinforcement failed: %s", _e)  # Fall through

                elif surprise_verdict.action == SurpriseAction.CREATE_BOOSTED:
                    importance = min(1.0, importance + 0.15)
                    metadata["surprise_boosted"] = True
                    metadata["surprise_score"] = round(surprise_verdict.surprise_score, 3)

            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug("Surprise gate unavailable: %s", _e)  # Proceed normally

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
            galaxy=galaxy,
            source_trust=source_trust,
            agent_id=agent_id,
            version=1,
            **kwargs,
        )

        self._galaxy_backend.store(memory, content_hash=content_hash)

        # Index in Holographic Memory (5D Spatial: x, y, z, w, v)
        if enable_holographic_index and self.holographic:
            coords = self.holographic.index_memory(memory.id, memory.to_dict())
            if coords:
                try:
                    self._galaxy_backend.store_coords(memory.id, *coords, galaxy=galaxy)
                except (TypeError, AttributeError):
                    # Older backends may not accept galaxy kwarg
                    self._galaxy_backend.store_coords(memory.id, *coords)

        # Compute and cache HRR vector for compositional memory operations
        # This binds the content embedding with a type role vector using HRR,
        # enabling typed retrieval via unbind(compressed, type_vector)
        try:
            from whitemagic.core.memory.hrr import get_hrr_engine
            from whitemagic.core.memory.embeddings import get_embedding_engine
            hrr_engine = get_hrr_engine()
            embed_engine = get_embedding_engine()
            if embed_engine and embed_engine.available():
                content_vec = embed_engine.encode(str(memory.content)[:2000])
                if content_vec is not None:
                    # Bind content with memory type as role vector for typed retrieval
                    if memory.memory_type:
                        type_rel = hrr_engine.get_relation_vector("OBJECT")
                        bound_vec = hrr_engine.bind(content_vec, type_rel)
                    else:
                        bound_vec = content_vec
                    try:
                        self._galaxy_backend.cache_hrr_vector(memory.id, bound_vec)
                    except (AttributeError, sqlite3.Error, TypeError):
                        pass  # Backend doesn't support HRR vector caching yet
        except (ImportError, ModuleNotFoundError, Exception) as _e:
            logger.debug("HRR vector computation skipped for %s: %s", memory.id, _e)

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
                            # Invalidate HRR pre-filter cache so new memory
                            # appears in pre-filter results on next query
                            try:
                                from whitemagic.core.intelligence.core_access import get_core_access
                                get_core_access().invalidate_hrr_cache()
                            except (ImportError, AttributeError):
                                pass
                        except (sqlite3.Error, AttributeError, TypeError) as _e:
                            logger.debug("Embedding cache failed for %s: %s", memory.id, _e)  # Skip silently
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug("Embedding engine unavailable: %s", _e)  # Skip silently

        # v15.2: Auto-extract entities and relations into knowledge graph
        if enable_entity_extraction:
            try:
                content_for_extraction = str(content)[:4000]
                if title:
                    content_for_extraction = f"{title}\n{content_for_extraction}"

                from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
                kg = get_kg_v2()
                result = kg.extract_and_store(memory.id, content_for_extraction)

                if result.get("relations_extracted", 0) == 0:
                    _emit_store_hooks(memory)
            except (ImportError, ModuleNotFoundError, AttributeError):
                # KG v2 unavailable; fall back to hook-based extraction
                _emit_store_hooks(memory)
            except Exception as _e:
                logger.debug("Entity extraction failed: %s", _e, exc_info=True)

        # Cache invalidation: write-invalidate protocol
        try:
            from whitemagic.core.memory.cache_registry import get_cache_registry
            reg = get_cache_registry()
            reg.invalidate_namespace(galaxy)
            # Spatial invalidation: flush cache entries near this memory's coords
            try:
                coords = self._galaxy_backend.get_coords(memory.id)
                if coords and len(coords) >= 4:
                    reg.invalidate_spatial(
                        (coords[0], coords[1], coords[2], coords[3]),
                        radius=0.3,
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Emit CACHE_INVALIDATE event for multi-agent coherence
        try:
            from whitemagic.core.resonance import emit_event, EventType
            emit_event(
                source="memory_store",
                event_type=EventType.CACHE_INVALIDATE,
                data={
                    "galaxy": galaxy,
                    "memory_id": memory.id,
                    "namespace": galaxy,
                    "operation": "store",
                },
            )
        except Exception:
            pass

        return memory

    def recall(self, memory_id: str, memory_context: Any = None) -> Memory | None:
        """Recall a specific memory by ID. Promotes it inward on the Galactic Map.

        Phase 2: If memory_context is provided, the recalled memory's namespace
        is validated against the context. A memory from a different user's
        namespace is not returned (returns None instead).
        """
        memory = self._galaxy_backend.recall(memory_id)
        if memory and memory.galactic_distance > 0.0:
            # Spiral inward: reduce galactic distance by 5% on each recall
            # A memory at the far edge (0.95) would need ~60 recalls to reach core
            new_distance = max(0.0, memory.galactic_distance * 0.95)
            if new_distance != memory.galactic_distance:
                memory.galactic_distance = new_distance
                try:
                    self._galaxy_backend.update_galactic_distance(memory_id, new_distance)
                except (sqlite3.Error, AttributeError, TypeError) as _e:
                    logger.debug("Galactic distance update failed for %s: %s", memory_id, _e)  # Don't fail recall

        # Phase 2: Namespace validation — don't return memories from other users
        if memory is not None and memory_context is not None:
            mem_user = memory.metadata.get("_user_id", "local")
            if mem_user != memory_context.user_id:
                logger.debug(
                    "Namespace isolation: memory %s belongs to user '%s', not '%s'",
                    memory_id, mem_user, memory_context.user_id,
                )
                return None

        return memory

    def update_memory(self, memory_id: str, updates: dict[str, Any],
                       agent_id: str = "", expected_version: int | None = None,
                       memory_context: Any = None) -> dict[str, Any]:
        """Update an existing memory with version increment and conflict resolution.

        Multi-agent cache coherence: uses optimistic concurrency control.
        If expected_version is provided and doesn't match the stored version,
        the update is rejected as a conflict.

        Args:
            memory_id: ID of the memory to update.
            updates: Dict of field -> new value to apply.
            agent_id: ID of the agent performing the update.
            expected_version: If set, update only succeeds when stored version matches.

        Returns:
            Dict with success status, conflict info, and updated memory.
        """
        existing = self._galaxy_backend.recall(memory_id)
        if not existing:
            return {"success": False, "error": "Memory not found", "memory_id": memory_id}

        # Phase 2: Namespace validation — don't allow updating other users' memories
        if memory_context is not None:
            mem_user = existing.metadata.get("_user_id", "local")
            if mem_user != memory_context.user_id:
                return {"success": False, "error": "namespace_violation",
                        "memory_id": memory_id,
                        "detail": f"Memory belongs to user '{mem_user}', not '{memory_context.user_id}'"}

        if expected_version is not None and existing.version != expected_version:
            return {
                "success": False,
                "error": "version_conflict",
                "memory_id": memory_id,
                "expected_version": expected_version,
                "actual_version": existing.version,
                "conflicting_agent": existing.agent_id,
            }

        for key, value in updates.items():
            if hasattr(existing, key) and key not in ("id", "created_at"):
                setattr(existing, key, value)

        existing.version += 1
        existing.agent_id = agent_id
        existing.last_modified = datetime.now()

        self._galaxy_backend.store(existing)

        # Cache invalidation
        try:
            from whitemagic.core.memory.cache_registry import get_cache_registry
            reg = get_cache_registry()
            reg.invalidate_namespace(existing.galaxy)
            # Spatial invalidation: flush cache entries near this memory's coords
            try:
                coords = self._galaxy_backend.get_coords(memory_id)
                if coords and len(coords) >= 4:
                    reg.invalidate_spatial(
                        (coords[0], coords[1], coords[2], coords[3]),
                        radius=0.3,
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Emit CACHE_INVALIDATE event
        try:
            from whitemagic.core.resonance import emit_event, EventType
            emit_event(
                source="memory_update",
                event_type=EventType.CACHE_INVALIDATE,
                data={
                    "galaxy": existing.galaxy,
                    "memory_id": memory_id,
                    "namespace": existing.galaxy,
                    "operation": "update",
                    "version": existing.version,
                    "agent_id": agent_id,
                },
            )
        except Exception:
            pass

        return {"success": True, "memory_id": memory_id, "version": existing.version, "memory": existing}

    def search(self, query: str | None = None, tags: set[str] | None = None,
               memory_type: MemoryType | None = None, min_importance: float = 0.0,
               limit: int = 10, galaxy: str | None = None,
               memory_context: Any = None) -> list[Memory]:
        """Search memories with various filters.

        Phase 2: If memory_context is provided, the galaxy from the context
        overrides the galaxy parameter, and results are filtered to only
        include memories from the same user namespace.
        """
        # Phase 2: Apply MemoryContext galaxy override
        if memory_context is not None and memory_context.galaxy != "default":
            galaxy = memory_context.galaxy

        results = self._galaxy_backend.search(query=query, tags=tags, memory_type=memory_type,
                                 min_importance=min_importance, limit=limit, galaxy=galaxy)

        # Phase 2: Filter results by user namespace if context is provided
        if memory_context is not None and results:
            ctx_user = memory_context.user_id
            results = [
                m for m in results
                if m.metadata.get("_user_id", "local") == ctx_user
            ]

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
                logger.debug("Gan Ying event emission failed: %s", _e)  # Don't fail search

        return cast(list[Memory], results)

    def search_similar(self, query: str, memory_type: MemoryType | None = None,
                       threshold: float = 0.1, limit: int = 10) -> list[Memory]:
        """Search memories by similarity using Rust acceleration if available.
        """
        if is_rust_available():
            rs = get_rust_module()
            if rs and hasattr(rs, "rust_search_memories"):
                try:
                    # 1. Get candidate memories from backend
                    candidates = self._galaxy_backend.search(query=None, memory_type=memory_type, limit=limit * 10)  # type: ignore[no-redef]
                    if candidates:
                        # 2. Prepare data for Rust: list of (id, content)
                        mem_tuples = [(c.id, str(c.content)) for c in candidates]

                        # 3. Use Rust SIMD for high-speed parallel search
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
                                logger.debug("Gan Ying pattern detection failed: %s", _e, exc_info=True)

                        return results
                except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                    logger.info("⚠️ Rust batch search failed: %s, falling back to FTS", _e, exc_info=True)

            # Fallback to single-pair similarity if batch is not available but fast_similarity is
            elif rs and hasattr(rs, "fast_similarity"):
                try:
                    candidates = self._galaxy_backend.search(query=None, memory_type=memory_type, limit=limit * 5)
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
                    logger.info("⚠️ Rust fast_similarity failed: %s, falling back to FTS", _e, exc_info=True)

        # Fallback to standard FTS search with optional Rust pipeline re-ranking
        results = self.search(query=query, memory_type=memory_type, limit=limit * 3)

        if results and len(results) > 1:
            try:
                from whitemagic.optimization.rust_accelerators import retrieval_pipeline
                candidates: list[dict[str, Any]] = []  # type: ignore[no-redef]
                for mem in results:
                    coords = None
                    try:
                        c = self._galaxy_backend.get_coords(mem.id)
                        if c:
                            coords = list(c)
                    except (sqlite3.Error, AttributeError, TypeError) as _e:
                        logger.debug("Coords lookup failed: %s", _e, exc_info=True)
                    age_days = 0.0
                    if mem.created_at:
                        try:
                            age_days = max(0.0, (datetime.now() - mem.created_at).total_seconds() / 86400.0)
                        except (TypeError, AttributeError) as _e:
                            logger.debug("Age calculation failed: %s", _e, exc_info=True)
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
                logger.debug("Retrieval pipeline failed: %s", _e, exc_info=True)

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
        entity_boost_weight: float = 0.3,
        rerank: bool = True,
        include_skills: bool = True,
        use_planner: bool = True,
        galaxy: str | None = None,
        profile: Any = None,
    ) -> list[Memory]:
        """Hybrid retrieval combining BM25 lexical search + embedding semantic
        search + 5D holographic spatial search via Reciprocal Rank Fusion (RRF).

        Phase 6: When ``use_planner=True`` (default), the search is executed
        through the ``SearchQueryPlanner`` pipeline with explicit stages,
        per-stage timing, batched lookups, and candidate explosion protection.
        Set ``use_planner=False`` to use the legacy inline path.

        v24.3 upgrades:
          - Entity-graph retrieval boosting (entity_boost_weight)
          - Second-pass reranking (rerank=True)
          - Procedural memory integration (include_skills=True)
          - Time-decay scoring (built into reranker)

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
            entity_boost_weight: Weight for entity-graph retrieval boosting (v24.3).
                Set to 0 to disable entity boosting.
            rerank: If True, apply second-pass multi-signal reranking (v24.3).
            include_skills: If True, match query against SkillForge triggers (v24.3).
            use_planner: If True (default), use the Phase 6 planned pipeline.
            galaxy: Optional galaxy restriction.
            profile: Optional QueryProfile for advanced configuration.
        """
        if use_planner:
            from whitemagic.core.memory.search_planner import SearchQueryPlanner
            from whitemagic.core.memory.retrieval_plan import QueryProfile as QP

            qp = profile or QP(
                lexical_weight=lexical_weight,
                semantic_weight=semantic_weight,
                spatial_weight=spatial_weight,
                entity_boost_weight=entity_boost_weight,
                rerank=rerank,
                include_skills=include_skills,
                include_cold=include_cold,
                rrf_k=rrf_k,
                axis_weights=axis_weights,
            )
            planner = SearchQueryPlanner(self)
            results, _telemetry = planner.execute(
                query=query, limit=limit, memory_type=memory_type,
                profile=qp, galaxy=galaxy,
            )
            return cast(list[Memory], results)

        return self._legacy_search_hybrid(
            query=query, limit=limit, memory_type=memory_type,
            rrf_k=rrf_k, semantic_weight=semantic_weight,
            lexical_weight=lexical_weight, spatial_weight=spatial_weight,
            include_cold=include_cold, axis_weights=axis_weights,
            entity_boost_weight=entity_boost_weight,
            rerank=rerank, include_skills=include_skills,
        )

    def _legacy_search_hybrid(
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
        entity_boost_weight: float = 0.3,
        rerank: bool = True,
        include_skills: bool = True,
    ) -> list[Memory]:
        """Legacy hybrid retrieval (pre-Phase 6 inline implementation).

        Kept as a selectable strategy until ranking parity and latency
        comparisons against the planned pipeline are complete.
        """
        rrf_scores: dict[str, float] = defaultdict(float)
        all_memories: dict[str, Memory] = {}

        lexical_results = []
        try:
            from whitemagic.optimization.rust_accelerators import (
                rust_search_available,
                search_build_index,
                search_query,
            )
            if rust_search_available():
                candidates = self._galaxy_backend.search(
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
            logger.debug("BM25 search failed: %s", _e, exc_info=True)

        if not lexical_results:
            lexical_results = self._galaxy_backend.search(
                query=query, memory_type=memory_type, limit=limit * 3,
            )
            for m in lexical_results:
                all_memories[m.id] = m

        for rank, mem in enumerate(lexical_results):
            rrf_scores[mem.id] += lexical_weight / (rrf_k + rank + 1)

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
                        recalled = self._galaxy_backend.recall(mid)
                        if recalled:
                            if hit.get("source") == "cold":
                                recalled.metadata["storage_tier"] = "cold"
                            all_memories[mid] = recalled
                    semantic_results.append(hit)
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug("Semantic search failed: %s", _e, exc_info=True)

        for rank, hit in enumerate(semantic_results):
            mid = hit["memory_id"]
            rrf_scores[mid] += semantic_weight / (rrf_k + rank + 1)

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
                        recalled = self._galaxy_backend.recall(mid)
                        if recalled:
                            all_memories[mid] = recalled
                    spatial_results.append(mid)
                    rrf_scores[mid] += spatial_weight / (rrf_k + rank + 1)
            except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                logger.debug("Holographic query failed: %s", _e, exc_info=True)

        # v24.3: Entity-graph retrieval boosting
        query_entities: list[str] = []
        if entity_boost_weight > 0:
            try:
                from whitemagic.core.memory.entity_reranker import (
                    apply_entity_boosts,
                    extract_query_entities,
                )

                query_entities = extract_query_entities(query)
                if query_entities:
                    rrf_scores = apply_entity_boosts(
                        rrf_scores,
                        query_entities,
                        entity_weight=entity_boost_weight,
                        backend=self._galaxy_backend,
                    )
            except (ImportError, ModuleNotFoundError, Exception) as _e:
                logger.debug("Entity boost failed: %s", _e, exc_info=True)

        if not rrf_scores:
            return []

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
            logger.debug("Constellation lookup failed: %s", _e, exc_info=True)

        if query_constellation_name:
            for mid in rrf_scores:
                try:
                    memberships = self._galaxy_backend.get_constellation_memberships(mid)
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
                    logger.debug("Constellation membership failed: %s", _e, exc_info=True)

        ranked_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
        results = []
        for mid in ranked_ids[:
            limit * 2]:  # Over-fetch for reranking
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

        # v24.3: Second-pass reranking with multi-signal scoring
        if rerank and len(results) > 1:
            try:
                from whitemagic.core.memory.entity_reranker import rerank_results

                results = rerank_results(results, query, query_entities)
            except (ImportError, ModuleNotFoundError, Exception) as _e:
                logger.debug("Reranking failed: %s", _e, exc_info=True)

        # Trim to final limit after reranking
        results = results[:limit]

        # v24.3: Procedural memory integration — inject matching skills
        if include_skills:
            try:
                from whitemagic.core.memory.entity_reranker import match_procedural_skills

                skill_matches = match_procedural_skills(query)
                if skill_matches:
                    for skill_info in skill_matches:
                        # Inject as metadata on first result, or as a standalone entry
                        if results:
                            existing_skills = results[0].metadata.get("procedural_skills", [])
                            existing_skills.append(skill_info)  # type: ignore[assignment]
                            results[0].metadata["procedural_skills"] = existing_skills
                        else:
                            # No regular results — create a synthetic skill result
                            skill_mem = Memory(
                                id=f"skill:{skill_info['skill_name']}",
                                content=f"Procedural skill: {skill_info['description']}",
                                memory_type=MemoryType.PROCEDURAL,
                                importance=0.8,
                                title=skill_info["skill_name"],
                            )
                            skill_mem.metadata["procedural_skill"] = skill_info
                            skill_mem.metadata["retrieval_channels"] = "procedural"
                            results.append(skill_mem)
            except (ImportError, ModuleNotFoundError, Exception) as _e:
                logger.debug("Skill matching failed: %s", _e, exc_info=True)

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

        Consolidated delegation chain (v23.1):
        1. CoreAccessLayer.hybrid_recall — vector + graph RRF (most powerful)
        2. GraphWalker.hybrid_recall — anchor search + multi-hop graph walk
        3. search_hybrid — 3-channel RRF (BM25 + embedding + 5D spatial)

        Returns list of dicts with memory data + reasoning paths.
        """
        # Check HybridRecallCache first
        try:
            from whitemagic.core.memory.hybrid_cache import get_hybrid_cache
            hcache = get_hybrid_cache()
            cached = hcache.get_query_result(query, limit=final_limit)
            if cached:
                logger.debug("hybrid_recall cache HIT for query: %s", query[:80])
                return cached
        except Exception:
            pass

        # 1. Try CoreAccessLayer (vector + graph RRF with Rust acceleration)
        try:
            from whitemagic.core.intelligence.core_access import get_core_access
            cal = get_core_access()
            results = cal.hybrid_recall(query=query, k=final_limit)
            if results:
                formatted = [
                    {
                        "memory_id": r.memory_id,
                        "title": r.title,
                        "content": r.content_preview,
                        "score": r.score,
                        "sources": r.sources,
                        "source": "core_access_rrf",
                    }
                    for r in results
                ]
                try:
                    from whitemagic.core.memory.hybrid_cache import get_hybrid_cache
                    get_hybrid_cache().put_query_result(query, formatted, limit=final_limit)
                except Exception:
                    pass
                return formatted
        except Exception as e:
            logger.debug("hybrid_recall: CoreAccessLayer unavailable: %s", e, exc_info=True)

        # 2. Try GraphWalker (anchor search + multi-hop graph walk)
        try:
            from whitemagic.core.memory.graph_walker import get_graph_walker
            walker = get_graph_walker()
            gw_results = cast(list[dict[str, Any]], walker.hybrid_recall(
                query=query,
                hops=hops,
                anchor_limit=anchor_limit,
                final_limit=final_limit,
            ))
            if gw_results:
                try:
                    from whitemagic.core.memory.hybrid_cache import get_hybrid_cache
                    get_hybrid_cache().put_query_result(query, gw_results, limit=final_limit)
                except Exception:
                    pass
            return gw_results
        except Exception as e:
            logger.debug("hybrid_recall: graph walker unavailable, falling back to search_hybrid: %s", e, exc_info=True)

        # 3. Fallback to standard 3-channel hybrid search
        results = self.search_hybrid(query=query, limit=final_limit)
        formatted = [
            {
                "memory_id": m.id,
                "title": m.title,
                "content": str(m.content)[:500],
                "importance": m.importance,
                "source": "fallback_hybrid",
            }
            for m in results
        ]
        if formatted:
            try:
                from whitemagic.core.memory.hybrid_cache import get_hybrid_cache
                get_hybrid_cache().put_query_result(query, formatted, limit=final_limit)
            except Exception:
                pass
        return formatted

    def associate(self, memory_id1: str, memory_id2: str, strength: float = 0.5) -> None:
        """Create bidirectional association between memories."""
        m1 = self.recall(memory_id1)
        m2 = self.recall(memory_id2)

        if m1 and m2:
            m1.associate(memory_id2, strength)
            m2.associate(memory_id1, strength)
            self._galaxy_backend.store(m1)
            self._galaxy_backend.store(m2)

    def consolidate(self) -> int:
        """Consolidate memories - strengthen important, decay unimportant."""
        count: int = self._galaxy_backend.consolidate()
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
        candidates = self._galaxy_backend.get_weakest_memories(limit=100)
        weak_candidates = [m for m in candidates if m.neuro_score <= threshold and not m.is_protected]

        if not weak_candidates:
            return 0

        logger.info("🌌 Starting Galactic Rotation for %s memories.", len(weak_candidates))

        rotated_count = 0
        for mem in weak_candidates:
            # 2. Extract Sparks (if refiner available)
            if refiner:
                try:
                    sol_id = refiner.refine_memory(mem)
                    if sol_id:
                        logger.info("✨ Memory %s refined into spark %s.", mem.id, sol_id, exc_info=True)
                except (ImportError, ModuleNotFoundError, AttributeError) as _e:
                    logger.debug("Refining fire failed: %s", _e, exc_info=True)

            # 3. Rotate to galactic edge (NEVER delete)
            self._galaxy_backend.archive_to_edge(mem.id, galactic_distance=0.95)
            rotated_count += 1

        if rotated_count > 0:
            logger.info("🌌 Galactic Rotation complete: %s memories rotated to edge.", rotated_count, exc_info=True)

        return rotated_count

    def arrow_export(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 10000,
        galaxy: str | None = None,
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

            memories = self._galaxy_backend.search(
                query=None, memory_type=memory_type, limit=limit, galaxy=galaxy,
            )
            if not memories:
                return None

            import json as _json
            docs = []
            for m in memories:
                coords = self._galaxy_backend.get_coords(m.id) if self.holographic else None
                galaxy_name = getattr(m, 'galaxy', 'universal')
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
                    "g": galaxy_name,  # 6th dimension: galaxy identity
                    "tags": sorted(m.tags) if m.tags else [],
                    "galaxy": galaxy_name,
                })
            return arrow_encode_memories(_json.dumps(docs))
        except (ImportError, ModuleNotFoundError, AttributeError) as _e:
            logger.debug("Arrow export failed: %s", _e, exc_info=True)
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
                # Use 6th dimension 'g' if present, fall back to 'galaxy' field
                galaxy = doc.get("g") or doc.get("galaxy", "universal")
                self.store(
                    content=doc.get("content", ""),
                    memory_type=mt,
                    title=doc.get("title"),
                    importance=doc.get("importance", 0.5),
                    tags=tags,
                    galaxy=galaxy,
                )
                count += 1
            logger.info("Arrow IPC import: %s memories imported", count, exc_info=True)
            return count
        except (ImportError, ModuleNotFoundError, AttributeError, ValueError) as _e:
            logger.debug("Arrow import failed: %s", _e, exc_info=True)
            return 0

    def json_export(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 10000,
        galaxy: str | None = None,
    ) -> str:
        """Export memories as JSON string with galaxy metadata header.

        Fallback for when Arrow/Rust is unavailable. Includes galaxy
        metadata (name, memory count, export timestamp) as a header
        object followed by the memory documents.

        Returns:
            JSON string with structure: {"galaxy_meta": {...}, "memories": [...]}
        """
        import json as _json
        from datetime import datetime

        memories = self._galaxy_backend.search(
            query=None, memory_type=memory_type, limit=limit, galaxy=galaxy,
        )

        galaxy_name = galaxy or "universal"
        docs = []
        for m in memories:
            coords = self._galaxy_backend.get_coords(m.id) if self.holographic else None
            mg = getattr(m, 'galaxy', 'universal')
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
                "g": mg,  # 6th dimension
                "tags": sorted(m.tags) if m.tags else [],
                "galaxy": mg,
            })

        return _json.dumps({
            "galaxy_meta": {
                "galaxy": galaxy_name,
                "memory_count": len(docs),
                "exported_at": datetime.now().isoformat(),
                "format": "json_v2",
                "dimensions": 6,
            },
            "memories": docs,
        })

    def json_import(self, json_str: str) -> int:
        """Import memories from JSON string with galaxy metadata.

        Fallback for when Arrow/Rust is unavailable. Accepts the
        format produced by json_export().

        Returns:
            Number of memories imported.
        """
        import json as _json

        data = _json.loads(json_str)
        # Support both wrapped format (json_export) and flat list (legacy)
        if isinstance(data, dict) and "memories" in data:
            docs = data["memories"]
        elif isinstance(data, list):
            docs = data
        else:
            docs = []

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
            galaxy = doc.get("g") or doc.get("galaxy", "universal")
            self.store(
                content=doc.get("content", ""),
                memory_type=mt,
                title=doc.get("title"),
                importance=doc.get("importance", 0.5),
                tags=tags,
                galaxy=galaxy,
            )
            count += 1
        return count

    def save(self, memory_type: MemoryType | None = None) -> None:
        """Save memories to disk - No-op for SQLite (auto-save)."""
        # SQLite backend auto-saves; this method exists for API compatibility
        # with file-based backends that require explicit persistence.
        logger.debug("UnifiedMemory.save: no-op for SQLite backend")

    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        return cast(dict[str, Any], self._galaxy_backend.get_stats())

    def list_recent(self, limit: int = 10, memory_type: MemoryType | None = None) -> list[Memory]:
        """List recent memories."""
        return cast(list[Memory], self._galaxy_backend.list_recent(limit=limit, memory_type=memory_type))

    def fetch_all_contents(self, memory_type: str | None = None, limit: int = 10000) -> list[str]:
        """Fetch all memory contents efficiently."""
        return cast(list[str], self._galaxy_backend.fetch_memory_contents(memory_type, limit))

    def list_accessed(self, limit: int = 10) -> list[Memory]:
        """List recently accessed memories."""
        return cast(list[Memory], self._galaxy_backend.list_accessed(limit=limit))

    def get_tag_counts(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most common tags."""
        return cast(list[tuple[str, int]], self._galaxy_backend.get_tag_counts(limit=limit))

    def galaxy_snapshot(self, galaxy: str | None = None) -> dict[str, Any]:
        """Create a full snapshot of a galaxy: memories, coords, associations, metadata.

        Unlike arrow_export/json_export which only export memories + coords,
        this includes associations and galaxy configuration, enabling
        trajectory branching for simulation.

        Returns:
            Dict with keys: galaxy_meta, memories, associations.
        """
        from datetime import datetime

        galaxy_name = galaxy or "universal"

        # Export memories with full metadata
        memories = self._galaxy_backend.search(
            query=None, limit=100000, galaxy=galaxy,
        )

        mem_docs = []
        for m in memories:
            coords = self._galaxy_backend.get_coords(m.id) if self.holographic else None
            mem_docs.append({
                "id": m.id,
                "title": m.title or "",
                "content": str(m.content)[:50000],
                "importance": m.importance,
                "memory_type": m.memory_type.name if m.memory_type else "SHORT_TERM",
                "tags": sorted(m.tags) if m.tags else [],
                "galaxy": getattr(m, 'galaxy', galaxy_name),
                "emotional_valence": getattr(m, 'emotional_valence', 0.0),
                "metadata": m.metadata if isinstance(m.metadata, dict) else {},
                "coords": {
                    "x": coords[0] if coords else 0.0,
                    "y": coords[1] if coords else 0.0,
                    "z": coords[2] if coords else 0.0,
                    "w": coords[3] if coords else 0.5,
                    "v": coords[4] if coords and len(coords) > 4 else 0.5,
                    "u": coords[5] if coords and len(coords) > 5 else 0.5,
                } if coords else None,
                "created_at": getattr(m, 'created_at', None),
            })

        # Export associations from the galaxy-specific backend
        associations = []
        try:
            galaxy_backend = self._galaxy_backend._get_backend_for_galaxy(galaxy_name)
            import sqlite3 as _sqlite3
            with galaxy_backend.pool.connection() as conn:
                conn.row_factory = _sqlite3.Row
                rows = conn.execute(
                    """SELECT source_id, target_id, strength
                       FROM associations
                       WHERE source_id IN (SELECT id FROM memories)
                       AND target_id IN (SELECT id FROM memories)"""
                ).fetchall()
                for row in rows:
                    associations.append({
                        "source_id": row["source_id"],
                        "target_id": row["target_id"],
                        "strength": row["strength"],
                    })
        except Exception:
            pass

        return {
            "galaxy_meta": {
                "galaxy": galaxy_name,
                "memory_count": len(mem_docs),
                "association_count": len(associations),
                "snapshot_at": datetime.now().isoformat(),
                "format": "snapshot_v1",
            },
            "memories": mem_docs,
            "associations": associations,
        }

    def galaxy_restore(
        self,
        snapshot: dict[str, Any],
        target_galaxy: str | None = None,
        merge: bool = False,
    ) -> dict[str, Any]:
        """Restore a galaxy from a snapshot.

        Args:
            snapshot: Snapshot dict from galaxy_snapshot().
            target_galaxy: Galaxy to restore into. If None, uses snapshot's galaxy.
            merge: If True, merge with existing memories (dedup by content hash).
                   If False, clears target galaxy first.

        Returns:
            Summary dict with restored counts.
        """
        galaxy_name = target_galaxy or snapshot.get("galaxy_meta", {}).get("galaxy", "universal")
        mem_docs = snapshot.get("memories", [])
        associations = snapshot.get("associations", [])

        restored_mems = 0
        restored_assocs = 0
        id_map: dict[str, str] = {}  # old_id → new_id

        import hashlib as _hashlib
        target_backend = self._galaxy_backend._get_backend_for_galaxy(galaxy_name)

        for doc in mem_docs:
            try:
                mt_name = doc.get("memory_type", "SHORT_TERM")
                try:
                    mt = MemoryType[mt_name]
                except (KeyError, ValueError):
                    mt = MemoryType.SHORT_TERM

                # Generate a fresh ID and store directly to the target galaxy backend,
                # bypassing um.store() to avoid cross-galaxy content-hash dedup.
                content_str = str(doc.get("content", ""))[:1000]
                timestamp = now_iso()
                new_id = _hashlib.sha256(f"{content_str}{timestamp}".encode()).hexdigest()[:16]

                mem = Memory(
                    id=new_id,
                    content=doc.get("content", ""),
                    memory_type=mt,
                    tags=set(doc.get("tags", [])),
                    emotional_valence=doc.get("emotional_valence", 0.0),
                    importance=doc.get("importance", 0.5),
                    metadata=doc.get("metadata", {}),
                    title=doc.get("title", ""),
                    galaxy=galaxy_name,
                    version=1,
                )
                content_hash = _hashlib.sha256(str(mem.content).encode()).hexdigest()
                target_backend.store(mem, content_hash=content_hash)
                id_map[doc["id"]] = new_id
                restored_mems += 1

                # Restore coords if provided
                coords = doc.get("coords")
                if coords and self.holographic:
                    try:
                        target_backend.store_coords(
                            new_id,
                            coords.get("x", 0.0),
                            coords.get("y", 0.0),
                            coords.get("z", 0.0),
                            coords.get("w", 0.5),
                            coords.get("v", 0.5),
                            coords.get("u", 0.5),
                        )
                    except Exception:
                        pass

            except Exception:
                pass

        # Restore associations to the galaxy-specific backend
        galaxy_backend = self._galaxy_backend._get_backend_for_galaxy(galaxy_name)
        for assoc in associations:
            try:
                src = id_map.get(assoc["source_id"], assoc["source_id"])
                tgt = id_map.get(assoc["target_id"], assoc["target_id"])
                strength = assoc.get("strength", 0.5)
                with galaxy_backend.pool.connection() as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO associations (source_id, target_id, strength)
                           VALUES (?, ?, ?)""",
                        (src, tgt, strength),
                    )
                restored_assocs += 1
            except Exception:
                pass

        return {
            "galaxy": galaxy_name,
            "memories_restored": restored_mems,
            "associations_restored": restored_assocs,
            "merge": merge,
        }


# Namespace-keyed singleton instances (Phase 2 §9)
_unified_memory_instances: dict[str, UnifiedMemory] = {}
_unified_memory_lock = threading.Lock()


def reset_singleton() -> None:
    """Reset all singleton instances for testing."""
    with _unified_memory_lock:
        for inst in _unified_memory_instances.values():
            try:
                inst.close()
            except Exception:
                pass
        _unified_memory_instances.clear()


def get_unified_memory(user_id: str = "local") -> UnifiedMemory:
    """Get the singleton unified memory instance for a given user namespace.

    Each user_id gets its own UnifiedMemory instance with a separate
    GalaxyAwareBackend, ensuring complete namespace isolation.
    """
    with _unified_memory_lock:
        if user_id not in _unified_memory_instances:
            _unified_memory_instances[user_id] = UnifiedMemory(user_id=user_id)
        return _unified_memory_instances[user_id]


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
