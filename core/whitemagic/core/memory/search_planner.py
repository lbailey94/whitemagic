"""Phase 6 — Search Query Planner.

Orchestrates the retrieval pipeline as explicit stages with per-stage
timing, batched lookups, bounded federated galaxy search, and
configurable channel weights.

The planner replaces the inline search_hybrid logic with a structured
pipeline that is measurable, bounded, and free of avoidable N+1 work.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from whitemagic.core.memory.retrieval_plan import (
    CandidateScore,
    QueryProfile,
    RetrievalResult,
    RetrievalStage,
    StageTiming,
    classify_query,
    elapsed_ms,
    now_ms,
)

logger = logging.getLogger(__name__)


class SearchQueryPlanner:
    """Planned retrieval pipeline with explicit stages and telemetry.

    Stages:
      1. candidate_acquisition — lexical (FTS5) + semantic (HNSW) + spatial (5D)
      2. entity_boost — batched entity-graph retrieval boosting
      3. constellation_boost — batched constellation membership boosting
      4. reranking — second-pass multi-signal re-scoring

    The planner is stateless and thread-safe. Each call to ``execute()``
    produces a fresh ``RetrievalResult`` with per-stage telemetry.
    """

    def __init__(self, memory: Any) -> None:
        """Initialise with a UnifiedMemory instance.

        Args:
            memory: The UnifiedMemory instance providing backend access.
        """
        self._memory = memory

    def execute(
        self,
        query: str,
        limit: int = 10,
        memory_type: Any = None,
        profile: QueryProfile | None = None,
        galaxy: str | None = None,
    ) -> tuple[list[Any], RetrievalResult]:
        """Execute a planned retrieval operation.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            memory_type: Optional memory type filter.
            profile: Optional query profile for channel weights and toggles.
            galaxy: Optional galaxy restriction.

        Returns:
            Tuple of (ranked Memory list, RetrievalResult with telemetry).
        """
        profile = profile or QueryProfile()
        result = RetrievalResult()
        t_total = now_ms()

        # Determine galaxy count for query classification
        galaxy_backend = self._memory._galaxy_backend
        galaxy_count = 1 if galaxy else len(galaxy_backend.list_galaxies()) + 1
        result.galaxies_searched = galaxy_count
        result.query_class = classify_query(query, galaxy_count, profile)

        # ── Stage 1: Candidate acquisition (3 sub-channels) ──────────
        all_memories: dict[str, Any] = {}
        scores: dict[str, CandidateScore] = {}

        # 1a. Lexical (FTS5 BM25)
        t0 = now_ms()
        lexical_results: list[Any] = []
        try:
            lexical_results = galaxy_backend.search(
                query=query, memory_type=memory_type, limit=limit * profile.over_fetch_ratio,
                galaxy=galaxy,
            )
            for m in lexical_results:
                all_memories[m.id] = m
        except Exception as e:
            logger.debug("Planned lexical search failed: %s", e, exc_info=True)
        st_lexical = StageTiming(
            stage=RetrievalStage.LEXICAL_RANKING,
            duration_ms=elapsed_ms(t0),
            candidates_out=len(lexical_results),
        )
        result.stage_timings.append(st_lexical)

        # 1b. Semantic (embedding HNSW)
        t0 = now_ms()
        semantic_hits: list[dict[str, Any]] = []
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            engine = get_embedding_engine()
            if engine.available():
                semantic_hits = engine.search_similar(
                    query, limit=limit * profile.over_fetch_ratio,
                    min_similarity=profile.min_similarity,
                    include_cold=profile.include_cold,
                )
                for hit in semantic_hits:
                    mid = hit["memory_id"]
                    if mid not in all_memories:
                        recalled = galaxy_backend.recall(mid)
                        if recalled:
                            if hit.get("source") == "cold":
                                recalled.metadata["storage_tier"] = "cold"
                            all_memories[mid] = recalled
        except Exception as e:
            logger.debug("Planned semantic search failed: %s", e, exc_info=True)
            result.degraded_stages.append(RetrievalStage.SEMANTIC_RANKING.value)
        st_semantic = StageTiming(
            stage=RetrievalStage.SEMANTIC_RANKING,
            duration_ms=elapsed_ms(t0),
            candidates_out=len(semantic_hits),
            error=RetrievalStage.SEMANTIC_RANKING.value if result.degraded_stages and result.degraded_stages[-1] == RetrievalStage.SEMANTIC_RANKING.value else None,
        )
        result.stage_timings.append(st_semantic)

        # 1c. Spatial (5D holographic)
        t0 = now_ms()
        spatial_hits: list[Any] = []
        if self._memory.holographic:
            try:
                spatial_hits = self._memory.holographic.query_nearest(
                    {"content": query}, k=limit * profile.over_fetch_ratio,
                    weights=profile.axis_weights,
                )
                for hit in spatial_hits:
                    mid = hit.memory_id
                    if mid not in all_memories:
                        recalled = galaxy_backend.recall(mid)
                        if recalled:
                            all_memories[mid] = recalled
            except Exception as e:
                logger.debug("Planned spatial search failed: %s", e, exc_info=True)
                result.degraded_stages.append(RetrievalStage.SPATIAL_RANKING.value)
        st_spatial = StageTiming(
            stage=RetrievalStage.SPATIAL_RANKING,
            duration_ms=elapsed_ms(t0),
            candidates_out=len(spatial_hits),
            error=RetrievalStage.SPATIAL_RANKING.value if result.degraded_stages and result.degraded_stages[-1] == RetrievalStage.SPATIAL_RANKING.value else None,
        )
        result.stage_timings.append(st_spatial)

        # ── Build candidate scores from stage results ────────────────
        for rank, mem in enumerate(lexical_results):
            mid = mem.id
            cs = scores.setdefault(mid, CandidateScore(memory_id=mid, galaxy=getattr(mem, "galaxy", "")))
            cs.lexical_score = profile.lexical_weight / (profile.rrf_k + rank + 1)
            cs.channels.add("lexical")

        for rank, hit in enumerate(semantic_hits):
            mid = hit["memory_id"]
            cs = scores.setdefault(mid, CandidateScore(memory_id=mid))
            cs.semantic_score = profile.semantic_weight / (profile.rrf_k + rank + 1)
            cs.channels.add("semantic")

        for rank, hit in enumerate(spatial_hits):
            mid = hit.memory_id
            cs = scores.setdefault(mid, CandidateScore(memory_id=mid))
            cs.spatial_score = profile.spatial_weight / (profile.rrf_k + rank + 1)
            cs.channels.add("spatial")

        # Candidate explosion protection
        if len(scores) > profile.max_candidates:
            logger.warning(
                "Candidate explosion: %d candidates exceeds max %d — trimming by partial RRF",
                len(scores), profile.max_candidates,
            )
            # Compute partial final scores and trim
            for cs in scores.values():
                cs.final_score = cs.lexical_score + cs.semantic_score + cs.spatial_score
            sorted_ids = sorted(scores.keys(), key=lambda mid: scores[mid].final_score, reverse=True)
            kept = set(sorted_ids[:profile.max_candidates])
            scores = {mid: cs for mid, cs in scores.items() if mid in kept}
            all_memories = {mid: m for mid, m in all_memories.items() if mid in kept}

        # ── Stage 2: Entity boost (batched) ──────────────────────────
        t0 = now_ms()
        query_entities: list[str] = []
        if profile.entity_boost_weight > 0:
            try:
                from whitemagic.core.memory.entity_reranker import (
                    apply_entity_boosts,
                    extract_query_entities,
                )
                query_entities = extract_query_entities(query)
                if query_entities:
                    # Build RRF scores dict for entity boosting
                    rrf_dict = {mid: cs.lexical_score + cs.semantic_score + cs.spatial_score for mid, cs in scores.items()}
                    boosted = apply_entity_boosts(
                        rrf_dict, query_entities,
                        entity_weight=profile.entity_boost_weight,
                        backend=galaxy_backend,
                    )
                    # Apply boosts to candidate scores
                    for mid, boost_val in boosted.items():
                        cs = scores.get(mid)
                        if cs is None:
                            # New candidate from entity graph
                            cs = CandidateScore(memory_id=mid)
                            scores[mid] = cs
                            recalled = galaxy_backend.recall(mid)
                            if recalled:
                                all_memories[mid] = recalled
                        # Entity boost is the delta above the base RRF
                        base = rrf_dict.get(mid, 0.0)
                        cs.entity_score = boost_val - base
                        if cs.entity_score > 0 or mid not in rrf_dict:
                            cs.channels.add("entity")
            except Exception as e:
                logger.debug("Planned entity boost failed: %s", e, exc_info=True)
                result.degraded_stages.append(RetrievalStage.ENTITY_BOOST.value)
        st_entity = StageTiming(
            stage=RetrievalStage.ENTITY_BOOST,
            duration_ms=elapsed_ms(t0),
            candidates_in=len(scores),
            candidates_out=len(scores),
            error=RetrievalStage.ENTITY_BOOST.value if result.degraded_stages and result.degraded_stages[-1] == RetrievalStage.ENTITY_BOOST.value else None,
        )
        result.stage_timings.append(st_entity)

        # ── Stage 3: Constellation boost (batched) ───────────────────
        t0 = now_ms()
        query_constellation: str | None = None
        if profile.constellation_boost > 0 and scores:
            try:
                from whitemagic.core.memory.embeddings import get_embedding_engine
                engine = get_embedding_engine()
                if engine.available():
                    closest = engine.closest_constellation(query, max_results=1)
                    if closest and closest[0]["similarity"] >= profile.constellation_threshold:
                        query_constellation = closest[0]["name"]
            except Exception as e:
                logger.debug("Constellation lookup failed: %s", e, exc_info=True)

            if query_constellation:
                # Batch: collect all candidate IDs, do one lookup per galaxy backend
                candidate_ids = list(scores.keys())
                from whitemagic.core.memory.entity_reranker import batch_constellation_memberships
                batch_memberships = batch_constellation_memberships(candidate_ids, galaxy_backend)
                for mid, memberships in batch_memberships.items():
                    cs = scores.get(mid)
                    if not cs:
                        continue
                    matching = [m for m in memberships if m.get("constellation_name") == query_constellation]
                    if matching:
                        max_conf = max(m.get("membership_confidence", 0.5) for m in matching)
                        cs.constellation_score = profile.constellation_boost * max_conf
                        cs.channels.add("constellation")
                    else:
                        strongest = max((m.get("membership_confidence", 0.5) for m in memberships), default=0.0)
                        cs.constellation_score = profile.diversity_bonus * (1.0 - strongest)
        st_constellation = StageTiming(
            stage=RetrievalStage.CONSTELLATION_BOOST,
            duration_ms=elapsed_ms(t0),
            candidates_in=len(scores),
            candidates_out=len(scores),
        )
        result.stage_timings.append(st_constellation)

        # ── Compute final RRF scores ─────────────────────────────────
        for cs in scores.values():
            cs.final_score = (
                cs.lexical_score
                + cs.semantic_score
                + cs.spatial_score
                + cs.entity_score
                + cs.constellation_score
            )

        # Sort by final score
        ranked_ids = sorted(scores.keys(), key=lambda mid: scores[mid].final_score, reverse=True)

        # Over-fetch for reranking
        over_fetch = min(len(ranked_ids), limit * 2)
        results: list[Any] = []
        for mid in ranked_ids[:over_fetch]:
            mem = all_memories.get(mid)
            if mem:
                cs = scores[mid]
                mem.metadata["rrf_score"] = round(cs.final_score, 6)
                mem.metadata["retrieval_channels"] = "+".join(sorted(cs.channels))
                if query_constellation:
                    mem.metadata["query_constellation"] = query_constellation
                # Per-stage scores for debugging
                mem.metadata["stage_scores"] = {
                    "lexical": round(cs.lexical_score, 6),
                    "semantic": round(cs.semantic_score, 6),
                    "spatial": round(cs.spatial_score, 6),
                    "entity": round(cs.entity_score, 6),
                    "constellation": round(cs.constellation_score, 6),
                }
                results.append(mem)

        # ── Stage 4: Reranking ───────────────────────────────────────
        t0 = now_ms()
        if profile.rerank and len(results) > 1:
            try:
                from whitemagic.core.memory.entity_reranker import rerank_results
                results = rerank_results(results, query, query_entities)
            except Exception as e:
                logger.debug("Planned reranking failed: %s", e, exc_info=True)
                result.degraded_stages.append(RetrievalStage.RERANKING.value)
        st_rerank = StageTiming(
            stage=RetrievalStage.RERANKING,
            duration_ms=elapsed_ms(t0),
            candidates_in=len(results),
            candidates_out=len(results),
            error=RetrievalStage.RERANKING.value if result.degraded_stages and result.degraded_stages[-1] == RetrievalStage.RERANKING.value else None,
        )
        result.stage_timings.append(st_rerank)

        # Trim to final limit
        results = results[:limit]

        # ── Procedural skill matching (post-result injection) ────────
        if profile.include_skills:
            try:
                from whitemagic.core.memory.entity_reranker import match_procedural_skills
                skill_matches = match_procedural_skills(query)
                if skill_matches:
                    from whitemagic.core.memory.unified_types import Memory, MemoryType
                    for skill_info in skill_matches:
                        if results:
                            existing = results[0].metadata.get("procedural_skills", [])
                            existing.append(skill_info)
                            results[0].metadata["procedural_skills"] = existing
                        else:
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
            except Exception as e:
                logger.debug("Planned skill matching failed: %s", e, exc_info=True)

        # ── Finalise telemetry ───────────────────────────────────────
        result.total_duration_ms = elapsed_ms(t_total)
        result.candidates = [scores.get(mid) for mid in ranked_ids[:limit] if mid in scores]
        result.candidates = [cs for cs in result.candidates if cs is not None]

        # Emit search hooks
        if results:
            try:
                from whitemagic.core.memory.unified import _emit_search_hooks
                _emit_search_hooks(results)
            except Exception:
                logger.debug("Ignored error in search_planner.py:369")

        return results, result


# ── Federated galaxy search with bounded concurrency ────────────────


def federated_galaxy_search(
    galaxy_backend: Any,
    query: str,
    limit: int,
    memory_type: Any = None,
    galaxies: list[str] | None = None,
    over_fetch_ratio: int = 3,
    max_concurrency: int = 4,
    min_importance: float = 0.0,
    tags: set[str] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Search across multiple galaxies with bounded concurrency.

    Over-fetches per galaxy, merges deterministically by importance,
    then trims to the final limit.

    Args:
        galaxy_backend: The GalaxyAwareBackend instance.
        query: FTS5 search query.
        limit: Final result limit.
        memory_type: Optional memory type filter.
        galaxies: Optional list of galaxy names. If None, searches all.
        over_fetch_ratio: Multiplier for per-galaxy limit.
        max_concurrency: Maximum parallel galaxy searches.
        min_importance: Minimum importance threshold.
        tags: Optional tag filter.

    Returns:
        Tuple of (merged results, per-galaxy stats dict).
    """
    # Determine which galaxies to search
    if galaxies is None:
        # Discover all galaxy backends
        galaxy_backend._discover_galaxy_backends()
        galaxy_names = galaxy_backend.list_galaxies()
        # Also include default backend
        search_targets = [("default", galaxy_backend._get_default_backend())]
        for name in galaxy_names:
            search_targets.append((name, galaxy_backend._get_galaxy_backend(name)))
    else:
        search_targets = []
        for name in galaxies:
            if name == "default" or name == "universal":
                search_targets.append((name, galaxy_backend._get_default_backend()))
            else:
                search_targets.append((name, galaxy_backend._get_galaxy_backend(name)))

    per_galaxy_limit = limit * over_fetch_ratio
    all_results: list[Any] = []
    per_galaxy_stats: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    def _search_one(target: tuple[str, Any]) -> tuple[str, list[Any], str | None]:
        name, backend = target
        try:
            results = backend.search(
                query=query, tags=tags, memory_type=memory_type,
                limit=per_galaxy_limit, min_importance=min_importance,
            )
            return name, results, None
        except Exception as e:
            return name, [], str(e)

    with ThreadPoolExecutor(max_workers=min(len(search_targets), max_concurrency)) as executor:
        futures = {executor.submit(_search_one, t): t[0] for t in search_targets}
        for future in as_completed(futures):
            name, results, error = future.result()
            if error:
                errors[name] = error
                per_galaxy_stats[name] = {"count": 0, "error": error}
            else:
                per_galaxy_stats[name] = {"count": len(results)}
                for m in results:
                    if not getattr(m, "galaxy", None):
                        m.galaxy = name
                all_results.extend(results)

    # Deterministic merge: sort by importance (descending), then by id for tie-breaking
    all_results.sort(key=lambda m: (-getattr(m, "importance", 0.0), getattr(m, "id", "")))
    return all_results[:limit], {
        "galaxies_searched": len(per_galaxy_stats),
        "per_galaxy": per_galaxy_stats,
        "errors": errors if errors else None,
        "total_candidates": len(all_results),
    }
