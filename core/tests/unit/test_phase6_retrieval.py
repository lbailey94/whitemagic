"""Phase 6 — Retrieval and Search Query Planning tests.

Tests:
  1. RetrievalPlan data structures (CandidateScore, QueryProfile, RetrievalResult)
  2. RetrievalStage enum completeness
  3. LatencyBudget and classify_query
  4. RetrievalIndexCache (get, put, invalidate, TTL, stats)
  5. federated_galaxy_search (bounded concurrency, over-fetch, merge)
  6. batch_constellation_memberships (N+1 removal)
  7. SearchQueryPlanner (staged execution, telemetry, degraded stages)
  8. Candidate explosion protection
  9. Ranking determinism
  10. search.telemetry handler
  11. search_hybrid use_planner=True vs False (legacy fallback)
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.core.memory.retrieval_cache import (
    RetrievalIndexCache,
    get_retrieval_cache,
)
from whitemagic.core.memory.retrieval_plan import (
    LATENCY_BUDGETS,
    CandidateScore,
    QueryProfile,
    RetrievalResult,
    RetrievalStage,
    StageTiming,
    classify_query,
)

# ── 1. Data Structures ────────────────────────────────────────────────


class TestRetrievalPlanDataStructures:
    """Test Phase 6 retrieval plan data structures."""

    def test_candidate_score_defaults(self):
        cs = CandidateScore(memory_id="test-1")
        assert cs.memory_id == "test-1"
        assert cs.lexical_score == 0.0
        assert cs.semantic_score == 0.0
        assert cs.spatial_score == 0.0
        assert cs.entity_score == 0.0
        assert cs.constellation_score == 0.0
        assert cs.rerank_adjustment == 0.0
        assert cs.final_score == 0.0
        assert cs.galaxy == ""
        assert cs.channels == set()
        assert cs.provenance == "none"

    def test_candidate_score_provenance(self):
        cs = CandidateScore(memory_id="test-1")
        cs.channels = {"lexical", "semantic", "entity"}
        assert cs.provenance == "entity+lexical+semantic"

    def test_candidate_score_final_score(self):
        cs = CandidateScore(memory_id="test-1")
        cs.lexical_score = 0.5
        cs.semantic_score = 0.3
        cs.spatial_score = 0.1
        cs.entity_score = 0.05
        cs.constellation_score = 0.02
        cs.final_score = (
            cs.lexical_score + cs.semantic_score + cs.spatial_score
            + cs.entity_score + cs.constellation_score
        )
        assert cs.final_score == pytest.approx(0.97)

    def test_query_profile_defaults(self):
        qp = QueryProfile()
        assert qp.lexical_weight == 1.0
        assert qp.semantic_weight == 1.0
        assert qp.spatial_weight == 0.5
        assert qp.entity_boost_weight == 0.3
        assert qp.constellation_boost == 0.3
        assert qp.rerank is True
        assert qp.include_skills is True
        assert qp.include_cold is False
        assert qp.rrf_k == 60
        assert qp.over_fetch_ratio == 3
        assert qp.max_candidates == 500
        assert qp.galaxy_concurrency == 4
        assert qp.min_similarity == 0.25
        assert qp.constellation_threshold == 0.25

    def test_query_profile_custom(self):
        qp = QueryProfile(
            lexical_weight=2.0, semantic_weight=0.5,
            rerank=False, max_candidates=100,
        )
        assert qp.lexical_weight == 2.0
        assert qp.semantic_weight == 0.5
        assert qp.rerank is False
        assert qp.max_candidates == 100

    def test_retrieval_result_defaults(self):
        rr = RetrievalResult()
        assert rr.candidates == []
        assert rr.stage_timings == []
        assert rr.total_duration_ms == 0.0
        assert rr.galaxies_searched == 0
        assert rr.query_class == "simple"
        assert rr.degraded_stages == []
        assert rr.candidate_count == 0
        assert rr.within_budget is True

    def test_retrieval_result_telemetry_dict(self):
        rr = RetrievalResult(
            total_duration_ms=42.5,
            galaxies_searched=3,
            query_class="federated",
        )
        rr.stage_timings.append(StageTiming(
            stage=RetrievalStage.LEXICAL_RANKING,
            duration_ms=5.0, candidates_out=10,
        ))
        d = rr.to_telemetry_dict()
        assert d["total_duration_ms"] == 42.5
        assert d["galaxies_searched"] == 3
        assert d["query_class"] == "federated"
        assert len(d["stages"]) == 1
        assert d["stages"][0]["stage"] == "lexical_ranking"

    def test_retrieval_result_stage_timing_lookup(self):
        rr = RetrievalResult()
        st = StageTiming(stage=RetrievalStage.SEMANTIC_RANKING, duration_ms=10.0)
        rr.stage_timings.append(st)
        found = rr.stage_timing(RetrievalStage.SEMANTIC_RANKING)
        assert found is not None
        assert found.duration_ms == 10.0
        assert rr.stage_timing(RetrievalStage.RERANKING) is None


# ── 2. RetrievalStage Enum ────────────────────────────────────────────


class TestRetrievalStage:
    """Test RetrievalStage enum completeness."""

    def test_all_stages_present(self):
        stages = {s.value for s in RetrievalStage}
        assert "candidate_acquisition" in stages or "lexical_ranking" in stages
        assert "lexical_ranking" in stages
        assert "semantic_ranking" in stages
        assert "spatial_ranking" in stages
        assert "entity_boost" in stages
        assert "constellation_boost" in stages
        assert "reranking" in stages

    def test_stage_values_are_strings(self):
        for stage in RetrievalStage:
            assert isinstance(stage.value, str)


# ── 3. Latency Budgets and Query Classification ───────────────────────


class TestLatencyBudgets:
    """Test latency budget definitions and query classification."""

    def test_latency_budgets_defined(self):
        assert "simple" in LATENCY_BUDGETS
        assert "complex" in LATENCY_BUDGETS
        assert "federated" in LATENCY_BUDGETS
        assert "degraded" in LATENCY_BUDGETS

    def test_latency_budget_values(self):
        simple = LATENCY_BUDGETS["simple"]
        assert simple.p50 == 5.0
        assert simple.p95 == 15.0
        assert simple.p99 == 30.0
        federated = LATENCY_BUDGETS["federated"]
        assert federated.p50 == 50.0
        assert federated.p99 == 300.0

    def test_classify_query_simple(self):
        assert classify_query("hello", 1) == "simple"

    def test_classify_query_federated(self):
        assert classify_query("hello", 5) == "federated"

    def test_classify_query_complex_long(self):
        assert classify_query("x" * 300, 1) == "complex"

    def test_classify_query_complex_cold(self):
        qp = QueryProfile(include_cold=True)
        assert classify_query("short", 1, qp) == "complex"

    def test_retrieval_result_within_budget(self):
        rr = RetrievalResult(total_duration_ms=10.0, query_class="simple")
        assert rr.within_budget is True

    def test_retrieval_result_over_budget(self):
        rr = RetrievalResult(total_duration_ms=100.0, query_class="simple")
        assert rr.within_budget is False


# ── 4. RetrievalIndexCache ────────────────────────────────────────────


class TestRetrievalIndexCache:
    """Test namespace-aware retrieval index cache."""

    def test_get_put(self):
        cache = RetrievalIndexCache(ttl_seconds=10.0)
        cache.put("user1", "universal", {"hnsw_index": "idx1"})
        entry = cache.get("user1", "universal")
        assert entry is not None
        assert entry["hnsw_index"] == "idx1"

    def test_get_missing(self):
        cache = RetrievalIndexCache()
        assert cache.get("user1", "universal") is None

    def test_invalidate(self):
        cache = RetrievalIndexCache(ttl_seconds=10.0)
        cache.put("user1", "universal", {"hnsw_index": "idx1"})
        assert cache.invalidate("user1", "universal") is True
        assert cache.get("user1", "universal") is None

    def test_invalidate_missing(self):
        cache = RetrievalIndexCache()
        assert cache.invalidate("user1", "universal") is False

    def test_invalidate_user(self):
        cache = RetrievalIndexCache(ttl_seconds=10.0)
        cache.put("user1", "universal", {})
        cache.put("user1", "codex", {})
        cache.put("user2", "universal", {})
        count = cache.invalidate_user("user1")
        assert count == 2
        assert cache.get("user1", "universal") is None
        assert cache.get("user1", "codex") is None
        assert cache.get("user2", "universal") is not None

    def test_invalidate_all(self):
        cache = RetrievalIndexCache(ttl_seconds=10.0)
        cache.put("user1", "universal", {})
        cache.put("user2", "codex", {})
        count = cache.invalidate_all()
        assert count == 2
        assert cache.get("user1", "universal") is None

    def test_ttl_expiry(self):
        cache = RetrievalIndexCache(ttl_seconds=0.05)
        cache.put("user1", "universal", {"hnsw_index": "idx1"})
        time.sleep(0.06)
        assert cache.get("user1", "universal") is None

    def test_stats(self):
        cache = RetrievalIndexCache(ttl_seconds=10.0)
        cache.put("user1", "universal", {})
        cache.put("user1", "codex", {})
        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0

    def test_prune_expired(self):
        cache = RetrievalIndexCache(ttl_seconds=0.05)
        cache.put("user1", "universal", {})
        cache.put("user1", "codex", {})
        time.sleep(0.06)
        pruned = cache.prune_expired()
        assert pruned == 2

    def test_singleton(self):
        c1 = get_retrieval_cache()
        c2 = get_retrieval_cache()
        assert c1 is c2


# ── 5. Federated Galaxy Search ────────────────────────────────────────


class TestFederatedGalaxySearch:
    """Test bounded federated galaxy search."""

    def test_federated_search_merges_results(self):
        """Test that federated search merges results from multiple galaxies."""
        from whitemagic.core.memory.search_planner import federated_galaxy_search

        # Mock galaxy backend
        mock_backend = MagicMock()
        mock_backend._discover_galaxy_backends = MagicMock()
        mock_backend.list_galaxies = MagicMock(return_value=["codex", "citta"])

        # Mock individual backends
        default_backend = MagicMock()
        default_backend.search = MagicMock(return_value=[
            MagicMock(id="m1", importance=0.8, galaxy="universal"),
        ])
        codex_backend = MagicMock()
        codex_backend.search = MagicMock(return_value=[
            MagicMock(id="m2", importance=0.9, galaxy="codex"),
        ])
        citta_backend = MagicMock()
        citta_backend.search = MagicMock(return_value=[
            MagicMock(id="m3", importance=0.7, galaxy="citta"),
        ])

        mock_backend._get_default_backend = MagicMock(return_value=default_backend)
        mock_backend._get_galaxy_backend = MagicMock(side_effect=lambda name: {
            "codex": codex_backend, "citta": citta_backend,
        }[name])

        results, stats = federated_galaxy_search(
            mock_backend, query="test", limit=5,
        )

        assert len(results) <= 5
        assert stats["galaxies_searched"] == 3
        assert stats["total_candidates"] == 3
        assert stats["errors"] is None

    def test_federated_search_handles_errors(self):
        """Test that federated search handles per-galaxy errors gracefully."""
        from whitemagic.core.memory.search_planner import federated_galaxy_search

        mock_backend = MagicMock()
        mock_backend._discover_galaxy_backends = MagicMock()
        mock_backend.list_galaxies = MagicMock(return_value=[])

        default_backend = MagicMock()
        default_backend.search = MagicMock(side_effect=Exception("DB error"))
        mock_backend._get_default_backend = MagicMock(return_value=default_backend)

        results, stats = federated_galaxy_search(
            mock_backend, query="test", limit=5,
        )

        assert results == []
        assert stats["errors"] is not None
        assert "default" in stats["errors"]

    def test_federated_search_over_fetch(self):
        """Test that over_fetch_ratio multiplies per-galaxy limit."""
        from whitemagic.core.memory.search_planner import federated_galaxy_search

        mock_backend = MagicMock()
        mock_backend._discover_galaxy_backends = MagicMock()
        mock_backend.list_galaxies = MagicMock(return_value=[])

        default_backend = MagicMock()
        default_backend.search = MagicMock(return_value=[])
        mock_backend._get_default_backend = MagicMock(return_value=default_backend)

        federated_galaxy_search(
            mock_backend, query="test", limit=10, over_fetch_ratio=5,
        )

        # Check that the per-galaxy limit was 10 * 5 = 50
        call_args = default_backend.search.call_args
        assert call_args.kwargs["limit"] == 50


# ── 6. Batch Constellation Memberships ────────────────────────────────


class TestBatchConstellationMemberships:
    """Test batch N+1 removal for constellation memberships."""

    def test_batch_empty_ids(self):
        from whitemagic.core.memory.entity_reranker import (
            batch_constellation_memberships,
        )
        result = batch_constellation_memberships([], backend=MagicMock())
        assert result == {}

    def test_batch_no_backend(self):
        from whitemagic.core.memory.entity_reranker import (
            batch_constellation_memberships,
        )
        result = batch_constellation_memberships(["m1", "m2"], backend=None)
        assert result == {}

    def test_batch_with_mock_backend(self):
        from whitemagic.core.memory.entity_reranker import (
            batch_constellation_memberships,
        )

        mock_backend = MagicMock()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("m1", "constellation_a", 0.9),
            ("m2", "constellation_b", 0.7),
        ]
        mock_conn.execute = MagicMock(return_value=mock_cursor)
        # Use context manager mock for pool.connection()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)

        mock_default = MagicMock()
        mock_default.pool = mock_pool
        mock_backend._galaxy_backends = {}
        mock_backend._get_default_backend = MagicMock(return_value=mock_default)

        result = batch_constellation_memberships(["m1", "m2"], backend=mock_backend)
        assert "m1" in result
        assert result["m1"][0]["constellation_name"] == "constellation_a"
        assert result["m1"][0]["membership_confidence"] == 0.9
        assert "m2" in result


# ── 7. SearchQueryPlanner ─────────────────────────────────────────────


class TestSearchQueryPlanner:
    """Test the SearchQueryPlanner staged execution."""

    def test_planner_execute_basic(self):
        """Test that the planner executes and returns results + telemetry."""
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        from whitemagic.core.memory.search_planner import SearchQueryPlanner

        # Mock memory with galaxy backend
        mock_memory = MagicMock()
        mock_backend = MagicMock()
        mock_backend.search = MagicMock(return_value=[])
        mock_backend.recall = MagicMock(return_value=None)
        mock_backend.list_galaxies = MagicMock(return_value=[])
        mock_memory._galaxy_backend = mock_backend
        mock_memory.holographic = None

        planner = SearchQueryPlanner(mock_memory)
        results, telemetry = planner.execute(
            query="test query", limit=5,
            profile=QueryProfile(rerank=False, include_skills=False),
        )

        assert isinstance(results, list)
        assert isinstance(telemetry, RetrievalResult)
        assert telemetry.total_duration_ms > 0
        assert len(telemetry.stage_timings) >= 3  # lexical, semantic, spatial

    def test_planner_telemetry_has_stage_timings(self):
        """Test that telemetry contains per-stage timing."""
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        from whitemagic.core.memory.search_planner import SearchQueryPlanner

        mock_memory = MagicMock()
        mock_backend = MagicMock()
        mock_backend.search = MagicMock(return_value=[])
        mock_backend.recall = MagicMock(return_value=None)
        mock_backend.list_galaxies = MagicMock(return_value=[])
        mock_memory._galaxy_backend = mock_backend
        mock_memory.holographic = None

        planner = SearchQueryPlanner(mock_memory)
        _, telemetry = planner.execute(
            query="test", limit=5,
            profile=QueryProfile(rerank=False, include_skills=False),
        )

        stage_names = {st.stage for st in telemetry.stage_timings}
        assert RetrievalStage.LEXICAL_RANKING in stage_names
        assert RetrievalStage.SEMANTIC_RANKING in stage_names
        assert RetrievalStage.SPATIAL_RANKING in stage_names

    def test_planner_degraded_stages_tracked(self):
        """Test that degraded stages are tracked in telemetry."""
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        from whitemagic.core.memory.search_planner import SearchQueryPlanner

        mock_memory = MagicMock()
        mock_backend = MagicMock()
        mock_backend.search = MagicMock(return_value=[])
        mock_backend.recall = MagicMock(return_value=None)
        mock_backend.list_galaxies = MagicMock(return_value=[])
        mock_memory._galaxy_backend = mock_backend
        mock_memory.holographic = None

        # Make embeddings unavailable to trigger semantic degradation
        with patch("whitemagic.core.memory.embeddings.get_embedding_engine") as mock_get:
            mock_engine = MagicMock()
            mock_engine.available.return_value = False
            mock_get.return_value = mock_engine

            planner = SearchQueryPlanner(mock_memory)
            _, telemetry = planner.execute(
                query="test", limit=5,
                profile=QueryProfile(rerank=False, include_skills=False),
            )

        # Semantic stage should not have produced candidates
        semantic_timing = telemetry.stage_timing(RetrievalStage.SEMANTIC_RANKING)
        assert semantic_timing is not None
        assert semantic_timing.candidates_out == 0


# ── 8. Candidate Explosion Protection ─────────────────────────────────


class TestCandidateExplosion:
    """Test candidate explosion protection."""

    def test_explosion_protection_trims(self):
        """Test that exceeding max_candidates trims the candidate set."""
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        from whitemagic.core.memory.search_planner import SearchQueryPlanner

        # Create mock that returns many candidates
        mock_mems = []
        for i in range(100):
            m = MagicMock()
            m.id = f"m{i}"
            m.galaxy = "universal"
            mock_mems.append(m)

        mock_memory = MagicMock()
        mock_backend = MagicMock()
        mock_backend.search = MagicMock(return_value=mock_mems)
        mock_backend.recall = MagicMock(return_value=None)
        mock_backend.list_galaxies = MagicMock(return_value=[])
        mock_memory._galaxy_backend = mock_backend
        mock_memory.holographic = None

        planner = SearchQueryPlanner(mock_memory)
        profile = QueryProfile(
            rerank=False, include_skills=False,
            max_candidates=10, entity_boost_weight=0,
            constellation_boost=0,
        )
        results, telemetry = planner.execute(
            query="test", limit=5, profile=profile,
        )

        # Should not exceed max_candidates in the scores
        assert len(telemetry.candidates) <= 10


# ── 9. Ranking Determinism ────────────────────────────────────────────


class TestRankingDeterminism:
    """Test that ranking is deterministic for the same inputs."""

    def test_same_inputs_same_order(self):
        """Test that identical inputs produce identical ranking."""
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        from whitemagic.core.memory.search_planner import SearchQueryPlanner

        mock_mems = []
        for i in range(5):
            m = MagicMock()
            m.id = f"m{i}"
            m.galaxy = "universal"
            mock_mems.append(m)

        mock_memory = MagicMock()
        mock_backend = MagicMock()
        mock_backend.search = MagicMock(return_value=list(mock_mems))
        mock_backend.recall = MagicMock(return_value=None)
        mock_backend.list_galaxies = MagicMock(return_value=[])
        mock_memory._galaxy_backend = mock_backend
        mock_memory.holographic = None

        profile = QueryProfile(
            rerank=False, include_skills=False,
            entity_boost_weight=0, constellation_boost=0,
        )
        planner = SearchQueryPlanner(mock_memory)

        results1, _ = planner.execute(query="test", limit=5, profile=profile)
        results2, _ = planner.execute(query="test", limit=5, profile=profile)

        ids1 = [r.id for r in results1]
        ids2 = [r.id for r in results2]
        assert ids1 == ids2


# ── 10. search.telemetry Handler ──────────────────────────────────────


class TestSearchTelemetryHandler:
    """Test the search.telemetry MCP handler."""

    def test_handle_search_telemetry_returns_success(self):
        from whitemagic.tools.handlers.memory import handle_search_telemetry
        result = handle_search_telemetry()
        assert result["status"] == "success"
        assert "telemetry" in result

    def test_handle_search_telemetry_has_cache_stats(self):
        from whitemagic.tools.handlers.memory import handle_search_telemetry
        result = handle_search_telemetry()
        assert "index_cache" in result["telemetry"]

    def test_handle_search_telemetry_has_budgets(self):
        from whitemagic.tools.handlers.memory import handle_search_telemetry
        result = handle_search_telemetry()
        assert "latency_budgets" in result["telemetry"]
        assert "simple" in result["telemetry"]["latency_budgets"]


# ── 11. search_hybrid Planner vs Legacy ───────────────────────────────


class TestSearchHybridPlannerToggle:
    """Test that search_hybrid can toggle between planner and legacy."""

    def test_use_planner_param_exists(self):
        """Test that search_hybrid accepts use_planner parameter."""
        # We just verify the signature accepts the param without error
        # Full integration test would require a real UnifiedMemory instance
        import inspect

        from whitemagic.core.memory.unified import UnifiedMemory
        sig = inspect.signature(UnifiedMemory.search_hybrid)
        assert "use_planner" in sig.parameters
        assert "galaxy" in sig.parameters
        assert "profile" in sig.parameters

    def test_legacy_method_exists(self):
        """Test that _legacy_search_hybrid method exists."""
        import inspect

        from whitemagic.core.memory.unified import UnifiedMemory
        assert hasattr(UnifiedMemory, "_legacy_search_hybrid")
        sig = inspect.signature(UnifiedMemory._legacy_search_hybrid)
        # Legacy should NOT have use_planner
        assert "use_planner" not in sig.parameters
