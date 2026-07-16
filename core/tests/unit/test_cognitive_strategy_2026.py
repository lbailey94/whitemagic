"""Unit tests for Memory & Cognitive Systems Strategy 2026 — Phases 2-5."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure core is on path
CORE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(CORE_ROOT))


class TestAbstentionGate:
    """Tests for the abstention gate (Gap D)."""

    def test_empty_results_abstain(self):
        from whitemagic.core.memory.abstention_gate import AbstentionGate
        gate = AbstentionGate(threshold=0.15)
        result = gate.should_abstain("test query", [])
        assert result.abstain is True
        assert result.reason == "no_results"

    def test_high_relevance_does_not_abstain(self):
        from whitemagic.core.memory.abstention_gate import AbstentionGate
        gate = AbstentionGate(threshold=0.15)
        # Create a mock result with high keyword overlap
        mock_result = MagicMock()
        mock_result.content = "quantum computing applications in machine learning"
        mock_result.metadata = {}
        result = gate.should_abstain("quantum computing applications", [mock_result])
        assert result.abstain is False

    def test_low_relevance_abstains(self):
        from whitemagic.core.memory.abstention_gate import AbstentionGate
        gate = AbstentionGate(threshold=0.99)  # Very high threshold
        mock_result = MagicMock()
        mock_result.content = "completely unrelated content about cooking"
        mock_result.metadata = {}
        result = gate.should_abstain("quantum computing", [mock_result])
        assert result.abstain is True

    def test_filter_results_returns_empty_on_abstain(self):
        from whitemagic.core.memory.abstention_gate import AbstentionGate
        gate = AbstentionGate(threshold=0.99)
        mock_result = MagicMock()
        mock_result.content = "unrelated"
        mock_result.metadata = {}
        filtered, decision = gate.filter_results("test", [mock_result])
        assert filtered == []
        assert decision.abstain is True

    def test_threshold_clamping(self):
        from whitemagic.core.memory.abstention_gate import AbstentionGate
        gate = AbstentionGate(threshold=5.0)  # Above max
        assert gate.threshold == 0.5
        gate = AbstentionGate(threshold=-1.0)  # Below min
        assert gate.threshold == 0.0

    def test_to_dict(self):
        from whitemagic.core.memory.abstention_gate import AbstentionResult
        r = AbstentionResult(abstain=True, top_score=0.05, threshold=0.15, reason="test")
        d = r.to_dict()
        assert d["abstain"] is True
        assert d["top_relevance_score"] == 0.05
        assert d["threshold"] == 0.15


class TestCrossEncoderReranker:
    """Tests for the cross-encoder reranker (Gap A)."""

    def test_heuristic_bigram_overlap(self):
        from whitemagic.core.memory.cross_encoder_reranker import _compute_bigram_overlap
        score = _compute_bigram_overlap("machine learning algorithms", "machine learning is great")
        assert score > 0.0

    def test_heuristic_trigram_overlap(self):
        from whitemagic.core.memory.cross_encoder_reranker import _compute_trigram_overlap
        score = _compute_trigram_overlap("a b c d", "a b c e")
        assert score > 0.0

    def test_semantic_density(self):
        from whitemagic.core.memory.cross_encoder_reranker import _compute_semantic_density
        score = _compute_semantic_density("quantum computing research", "quantum computing research applications")
        assert score > 0.5

    def test_heuristic_cross_score_range(self):
        from whitemagic.core.memory.cross_encoder_reranker import _heuristic_cross_score
        score = _heuristic_cross_score("test query", "test content")
        assert 0.0 <= score <= 1.0

    def test_rerank_empty_results(self):
        from whitemagic.core.memory.cross_encoder_reranker import rerank_cross_encoder
        assert rerank_cross_encoder("test", []) == []

    def test_rerank_preserves_count(self):
        from whitemagic.core.memory.cross_encoder_reranker import rerank_cross_encoder
        results = []
        for i in range(5):
            m = MagicMock()
            m.content = f"content about topic {i}"
            m.metadata = {}
            results.append(m)
        reranked = rerank_cross_encoder("topic", results, use_model=False)
        assert len(reranked) == 5

    def test_rerank_adds_metadata(self):
        from whitemagic.core.memory.cross_encoder_reranker import rerank_cross_encoder
        m = MagicMock()
        m.content = "test content"
        m.metadata = {}
        rerank_cross_encoder("test", [m], use_model=False)
        assert "cross_encoder_score" in m.metadata
        assert m.metadata["cross_encoder_method"] == "heuristic"


class TestTemporalKG:
    """Tests for the temporal knowledge graph (Gap C)."""

    @pytest.fixture
    def tkg(self, tmp_path):
        from whitemagic.core.memory.temporal_kg import TemporalKnowledgeGraph
        return TemporalKnowledgeGraph(db_path=str(tmp_path / "test_tkg.db"))

    def test_assert_and_retrieve(self, tkg):
        fact_id = tkg.assert_fact("alice", "preference", "Rust")
        facts = tkg.get_current_facts("alice", "preference")
        assert len(facts) == 1
        assert facts[0].object == "Rust"
        assert facts[0].is_current

    def test_supersession(self, tkg):
        tkg.assert_fact("alice", "preference", "Python")
        tkg.assert_fact("alice", "preference", "Rust", supersede=True)

        current = tkg.get_current_facts("alice", "preference")
        assert len(current) == 1
        assert current[0].object == "Rust"

        history = tkg.get_fact_history("alice", "preference")
        assert len(history) == 2
        # Newest first
        assert history[0].object == "Rust"
        assert history[1].object == "Python"
        assert history[1].superseded_by is not None

    def test_changes_since(self, tkg):
        tkg.assert_fact("bob", "location", "Tokyo", valid_from="2026-01-01T00:00:00Z")
        tkg.assert_fact("bob", "location", "Paris", valid_from="2026-06-01T00:00:00Z")

        changes = tkg.changes_since("2026-05-01T00:00:00Z")
        assert len(changes) >= 1

    def test_fama_score_current_fact(self, tkg):
        fact_id = tkg.assert_fact("alice", "preference", "Rust", source_memory_id="mem_001")
        score = tkg.fama_score("mem_001")
        assert score > 0  # Current fact should have positive FAMA score

    def test_fama_score_superseded_fact(self, tkg):
        tkg.assert_fact("alice", "preference", "Python", source_memory_id="mem_001")
        tkg.assert_fact("alice", "preference", "Rust", source_memory_id="mem_002")
        score = tkg.fama_score("mem_001")
        assert score < 0  # Superseded fact should have negative FAMA score

    def test_fama_score_no_facts(self, tkg):
        score = tkg.fama_score("nonexistent_mem")
        assert score == 0.0

    def test_extract_and_assert_preference(self, tkg):
        fact_ids = tkg.extract_and_assert("Alice prefers Rust", memory_id="mem_001")
        assert len(fact_ids) > 0
        facts = tkg.get_current_facts("alice", "preference")
        assert any(f.object == "rust" for f in facts)

    def test_extract_and_assert_switch(self, tkg):
        fact_ids = tkg.extract_and_assert("Bob switched from Python to Go", memory_id="mem_002")
        assert len(fact_ids) > 0
        facts = tkg.get_current_facts("bob", "preference")
        assert any(f.object == "go" for f in facts)

    def test_stats(self, tkg):
        tkg.assert_fact("alice", "preference", "Rust")
        tkg.assert_fact("bob", "location", "Tokyo")
        stats = tkg.stats()
        assert stats["total_facts"] == 2
        assert stats["current_facts"] == 2
        assert stats["unique_subjects"] == 2


class TestSearchBias:
    """Tests for search bias (Phase 4)."""

    def test_working_memory_bias_no_wm(self):
        from whitemagic.core.memory.search_bias import apply_working_memory_bias
        m = MagicMock()
        m.id = "mem_001"
        m.metadata = {"rrf_score": 0.05}
        results = apply_working_memory_bias([m])
        # No working memory available → no change
        assert results[0].metadata.get("working_memory_boosted") is not True

    def test_citta_bias_neutral(self):
        from whitemagic.core.memory.search_bias import apply_citta_bias
        m = MagicMock()
        m.id = "mem_001"
        m.emotional_valence = 0.5
        m.metadata = {"rrf_score": 0.05}
        # Neutral valence (None) → no bias
        results = apply_citta_bias([m], valence=None)
        assert "citta_bias" not in results[0].metadata

    def test_citta_bias_positive_match(self):
        from whitemagic.core.memory.search_bias import apply_citta_bias
        m = MagicMock()
        m.id = "mem_001"
        m.emotional_valence = 0.5
        m.metadata = {"rrf_score": 0.05}
        results = apply_citta_bias([m], valence=0.5)
        assert results[0].metadata.get("citta_bias") == "positive_match"
        assert results[0].metadata["rrf_score"] > 0.05

    def test_citta_bias_mismatch(self):
        from whitemagic.core.memory.search_bias import apply_citta_bias
        m = MagicMock()
        m.id = "mem_001"
        m.emotional_valence = -0.5
        m.metadata = {"rrf_score": 0.05}
        results = apply_citta_bias([m], valence=0.5)
        assert results[0].metadata.get("citta_bias") == "mismatch"
        assert results[0].metadata["rrf_score"] < 0.05

    def test_apply_search_bias_empty(self):
        from whitemagic.core.memory.search_bias import apply_search_bias
        assert apply_search_bias("test", []) == []


class TestGalaxyHNSW:
    """Tests for per-galaxy HNSW indices (Phase 5)."""

    def test_create_and_search_galaxy(self, tmp_path):
        from whitemagic.core.memory.galaxy_hnsw import GalaxyHNSWManager
        import numpy as np

        manager = GalaxyHNSWManager(base_path=tmp_path)
        vec = np.random.rand(384).astype(np.float32)
        manager.add_to_galaxy("codex", "mem_001", vec)

        results = manager.search_galaxy("codex", vec, k=1)
        assert len(results) >= 1
        assert results[0][0] == "mem_001"

    def test_search_nonexistent_galaxy(self, tmp_path):
        from whitemagic.core.memory.galaxy_hnsw import GalaxyHNSWManager
        import numpy as np

        manager = GalaxyHNSWManager(base_path=tmp_path)
        vec = np.random.rand(384).astype(np.float32)
        results = manager.search_galaxy("nonexistent", vec, k=5)
        assert results == []

    def test_cross_galaxy_rrf(self, tmp_path):
        from whitemagic.core.memory.galaxy_hnsw import GalaxyHNSWManager
        import numpy as np

        rng = np.random.RandomState(42)
        manager = GalaxyHNSWManager(base_path=tmp_path)
        vec1 = rng.rand(384).astype(np.float32)
        vec2 = rng.rand(384).astype(np.float32)

        manager.add_to_galaxy("codex", "mem_001", vec1)
        manager.add_to_galaxy("research", "mem_002", vec2)

        # Search with vec1 — should find mem_001 in codex
        results = manager.cross_galaxy_rrf(vec1, galaxies=["codex", "research"], k=5)
        assert len(results) > 0
        assert results[0][0] == "mem_001"

    def test_stats(self, tmp_path):
        from whitemagic.core.memory.galaxy_hnsw import GalaxyHNSWManager
        import numpy as np

        rng = np.random.RandomState(42)
        manager = GalaxyHNSWManager(base_path=tmp_path)
        vec = rng.rand(384).astype(np.float32)
        manager.add_to_galaxy("codex", "mem_001", vec)
        stats = manager.stats()
        assert "codex" in stats


class TestRetrievalPlanUpdates:
    """Tests for retrieval plan updates (graph walk stage)."""

    def test_graph_walk_stage_exists(self):
        from whitemagic.core.memory.retrieval_plan import RetrievalStage
        assert hasattr(RetrievalStage, "GRAPH_WALK")
        assert RetrievalStage.GRAPH_WALK.value == "graph_walk"

    def test_candidate_score_has_graph_score(self):
        from whitemagic.core.memory.retrieval_plan import CandidateScore
        cs = CandidateScore(memory_id="test")
        assert hasattr(cs, "graph_score")
        assert cs.graph_score == 0.0

    def test_query_profile_has_graph_walk_weight(self):
        from whitemagic.core.memory.retrieval_plan import QueryProfile
        qp = QueryProfile()
        assert hasattr(qp, "graph_walk_weight")
        assert qp.graph_walk_weight > 0
        assert hasattr(qp, "graph_walk_hops")
        assert hasattr(qp, "graph_walk_top_k")


class TestConsolidationValidator:
    """Tests for dream cycle consolidation validation (Phase 3)."""

    def test_report_to_dict(self):
        from whitemagic.core.dreaming.consolidation_validator import ConsolidationReport
        report = ConsolidationReport(
            recall_before={"avg_results": 5.0},
            recall_after={"avg_results": 6.0},
            recall_delta=1.0,
            improved=True,
        )
        d = report.to_dict()
        assert d["improved"] is True
        assert d["recall_delta"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
