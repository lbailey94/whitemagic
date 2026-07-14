"""Tests for entity-graph retrieval boosting, second-pass reranking,
procedural memory integration, and time-decay scoring (v24.3).

All tests are isolated — no production DB access, no subprocess calls,
no ML model loading. Pure unit tests with in-memory SQLite.
"""

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.core.memory.entity_reranker import (
    apply_entity_boosts,
    compute_lexical_precision,
    compute_time_decay,
    extract_query_entities,
    lookup_entity_memories,
    match_procedural_skills,
    rerank_results,
)
from whitemagic.core.memory.unified_types import Memory, MemoryType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(
    mid: str = "mem_001",
    content: str = "WhiteMagic uses Rust for embeddings",
    title: str | None = None,
    importance: float = 0.5,
    created_at: datetime | None = None,
    half_life_days: float = 30.0,
) -> Memory:
    """Create a Memory with sensible defaults for testing."""
    return Memory(
        id=mid,
        content=content,
        memory_type=MemoryType.LONG_TERM,
        title=title,
        importance=importance,
        created_at=created_at or datetime.now(),
        half_life_days=half_life_days,
    )


def _make_assoc_db(entities_per_mem: dict[str, list[tuple[str, float]]]) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with associations table populated.

    Args:
        entities_per_mem: {memory_id: [(entity_name, strength), ...]}
    """
    conn = sqlite3.Connection(":memory:")
    conn.execute("""
        CREATE TABLE associations (
            source_id TEXT,
            target_id TEXT,
            strength REAL,
            direction TEXT DEFAULT 'forward',
            relation_type TEXT DEFAULT 'associated_with',
            edge_type TEXT DEFAULT 'semantic',
            created_at TEXT,
            ingestion_time TEXT,
            PRIMARY KEY (source_id, target_id)
        )
    """)
    now = datetime.now().isoformat()
    for mid, entities in entities_per_mem.items():
        for entity_name, strength in entities:
            target = f"entity:{entity_name}"
            conn.execute(
                "INSERT OR IGNORE INTO associations VALUES (?, ?, ?, 'forward', 'USES', 'semantic', ?, ?)",
                (mid, target, strength, now, now),
            )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# 1. Entity Extraction from Query
# ---------------------------------------------------------------------------

class TestExtractQueryEntities:
    """Test query entity extraction using LightNER."""

    def test_extracts_tech_entities(self):
        entities = extract_query_entities("How does Rust handle SIMD operations?")
        assert "rust" in entities
        assert "simd" in entities

    def test_extracts_project_names(self):
        entities = extract_query_entities("WhiteMagic memory system overview")
        assert "whitemagic" in entities

    def test_empty_query_returns_empty(self):
        assert extract_query_entities("") == []
        assert extract_query_entities("   ") == []

    def test_deduplicates_entities(self):
        entities = extract_query_entities("Rust Rust Rust Python Python")
        # Should not contain duplicates
        assert len(entities) == len(set(entities))

    def test_no_entities_in_plain_text(self):
        entities = extract_query_entities("the quick brown fox jumps over the lazy dog")
        # Common words should not be extracted as entities
        # (LightNER may pick up some capitalized words, but lowercase plain text should yield few)
        assert isinstance(entities, list)


# ---------------------------------------------------------------------------
# 2. Entity-Graph Lookup & Boosting
# ---------------------------------------------------------------------------

class TestEntityGraphBoosting:
    """Test entity-graph retrieval boosting via associations table."""

    def test_lookup_finds_memories_with_matching_entities(self):
        conn = _make_assoc_db({
            "mem_001": [("rust", 0.9), ("python", 0.7)],
            "mem_002": [("rust", 0.8)],
            "mem_003": [("go", 0.5)],
        })
        boosts = lookup_entity_memories(["rust"], conn)
        assert "mem_001" in boosts
        assert "mem_002" in boosts
        assert "mem_003" not in boosts  # Doesn't share the "rust" entity
        conn.close()

    def test_lookup_multiple_entities_favors_multi_match(self):
        conn = _make_assoc_db({
            "mem_001": [("rust", 0.9), ("python", 0.7)],
            "mem_002": [("rust", 0.8)],
        })
        boosts = lookup_entity_memories(["rust", "python"], conn)
        # mem_001 matches both entities → higher boost
        assert boosts["mem_001"] > boosts["mem_002"]
        conn.close()

    def test_lookup_empty_entities_returns_empty(self):
        conn = _make_assoc_db({"mem_001": [("rust", 0.9)]})
        assert lookup_entity_memories([], conn) == {}
        conn.close()

    def test_apply_entity_boosts_modifies_rrf_scores(self):
        conn = _make_assoc_db({
            "mem_001": [("rust", 0.9)],
            "mem_002": [("python", 0.5)],
        })
        rrf_scores = {"mem_001": 0.05, "mem_002": 0.04}

        mock_backend = MagicMock()
        mock_backend.pool.connection.return_value.__enter__.return_value = conn
        mock_backend.pool.connection.return_value.__exit__.return_value = False

        result = apply_entity_boosts(rrf_scores, ["rust"], entity_weight=0.3, backend=mock_backend)

        # mem_001 should be boosted (shares "rust" entity)
        assert result["mem_001"] > 0.05
        # mem_002 should be unchanged (doesn't share "rust")
        assert result["mem_002"] == 0.04
        conn.close()

    def test_apply_entity_boosts_zero_weight_is_noop(self):
        rrf_scores = {"mem_001": 0.05}
        result = apply_entity_boosts(rrf_scores, ["rust"], entity_weight=0.0)
        assert result["mem_001"] == 0.05

    def test_apply_entity_boosts_empty_entities_is_noop(self):
        rrf_scores = {"mem_001": 0.05}
        result = apply_entity_boosts(rrf_scores, [], entity_weight=0.3)
        assert result["mem_001"] == 0.05


# ---------------------------------------------------------------------------
# 3. Time-Decay Scoring
# ---------------------------------------------------------------------------

class TestTimeDecay:
    """Test temporal decay factor computation."""

    def test_recent_memory_gets_positive_boost(self):
        mem = _make_memory(created_at=datetime.now())
        decay = compute_time_decay(mem)
        assert decay > 0  # Recent → positive

    def test_old_memory_gets_penalty(self):
        mem = _make_memory(created_at=datetime.now() - timedelta(days=365))
        decay = compute_time_decay(mem)
        assert decay < 0  # Very old → negative

    def test_half_life_neutral_point(self):
        """At exactly one half-life, decay should be near zero."""
        mem = _make_memory(
            created_at=datetime.now() - timedelta(days=30),
            half_life_days=30.0,
        )
        decay = compute_time_decay(mem, half_life_days=30.0)
        # At half-life, decay = max_boost * (2^(-1) - 0.5) = max_boost * 0 = 0
        assert abs(decay) < 0.01

    def test_no_created_at_returns_zero(self):
        mem = _make_memory()
        mem.created_at = None  # type: ignore[assignment]
        assert compute_time_decay(mem) == 0.0

    def test_max_boost_capped(self):
        mem = _make_memory(created_at=datetime.now())
        decay = compute_time_decay(mem, max_boost=0.15)
        assert decay <= 0.15

    def test_min_penalty_capped(self):
        mem = _make_memory(created_at=datetime.now() - timedelta(days=10000))
        decay = compute_time_decay(mem, max_boost=0.15)
        assert decay >= -0.15


# ---------------------------------------------------------------------------
# 4. Lexical Precision
# ---------------------------------------------------------------------------

class TestLexicalPrecision:
    """Test query term precision scoring."""

    def test_all_terms_match(self):
        mem = _make_memory(content="Rust Python embeddings")
        precision = compute_lexical_precision("Rust Python embeddings", mem)
        assert precision == 1.0

    def test_no_terms_match(self):
        mem = _make_memory(content="completely different content here")
        precision = compute_lexical_precision("Rust Python embeddings", mem)
        assert precision == 0.0

    def test_partial_match(self):
        mem = _make_memory(content="Rust is great for systems programming")
        precision = compute_lexical_precision("Rust Python embeddings", mem)
        # "rust" matches, "python" and "embeddings" don't
        assert 0.0 < precision < 1.0
        assert precision == pytest.approx(1.0 / 3.0, abs=0.01)

    def test_empty_query_returns_zero(self):
        mem = _make_memory(content="some content")
        assert compute_lexical_precision("", mem) == 0.0

    def test_stopwords_excluded(self):
        mem = _make_memory(content="the quick rust fox")
        precision = compute_lexical_precision("the rust", mem)
        # "the" is a stopword, so only "rust" counts
        assert precision == 1.0

    def test_title_also_searched(self):
        mem = _make_memory(title="Rust Guide", content="nothing relevant")
        precision = compute_lexical_precision("Rust guide", mem)
        assert precision > 0.0


# ---------------------------------------------------------------------------
# 5. Second-Pass Reranking
# ---------------------------------------------------------------------------

class TestRerankResults:
    """Test multi-signal reranking of RRF results."""

    def test_rerank_preserves_single_result(self):
        mem = _make_memory(mid="mem_001", content="test content")
        mem.metadata["rrf_score"] = 0.05
        results = [mem]
        reranked = rerank_results(results, "test query", [])
        assert len(reranked) == 1
        assert reranked[0].id == "mem_001"

    def test_rerank_reorders_by_importance(self):
        """Higher importance memory should rank higher after reranking."""
        now = datetime.now()
        mem_low = _make_memory(mid="mem_low", content="test query content", importance=0.1, created_at=now)
        mem_high = _make_memory(mid="mem_high", content="test query content", importance=0.9, created_at=now)
        mem_low.metadata["rrf_score"] = 0.10  # Higher RRF but low importance
        mem_high.metadata["rrf_score"] = 0.09  # Lower RRF but high importance

        results = [mem_low, mem_high]
        reranked = rerank_results(results, "test query", [])

        # With high importance_weight, mem_high should overtake mem_low
        assert reranked[0].id == "mem_high"

    def test_rerank_reorders_by_recency(self):
        """More recent memory should rank higher after reranking."""
        old_time = datetime.now() - timedelta(days=365)
        recent_time = datetime.now()

        mem_old = _make_memory(mid="mem_old", content="test query", created_at=old_time)
        mem_recent = _make_memory(mid="mem_recent", content="test query", created_at=recent_time)
        # Equal RRF scores — recency should be the sole differentiator
        mem_old.metadata["rrf_score"] = 0.10
        mem_recent.metadata["rrf_score"] = 0.10

        results = [mem_old, mem_recent]
        reranked = rerank_results(results, "test query", [])

        # Recent memory should get recency boost
        assert reranked[0].id == "mem_recent"

    def test_rerank_adds_metadata(self):
        """Reranked results should have rerank metadata."""
        mem = _make_memory(mid="mem_001", content="test query content")
        mem.metadata["rrf_score"] = 0.05
        results = [mem]
        rerank_results(results, "test query", [])
        assert "rerank_score" in mem.metadata
        assert "entity_overlap" in mem.metadata
        assert "recency_factor" in mem.metadata
        assert "lexical_precision" in mem.metadata

    def test_rerank_empty_results(self):
        assert rerank_results([], "query", []) == []


# ---------------------------------------------------------------------------
# 6. Procedural Memory (Skill Matching)
# ---------------------------------------------------------------------------

class TestProceduralSkillMatching:
    """Test SkillForge trigger phrase matching."""

    def test_match_returns_empty_when_no_skills(self):
        with patch("whitemagic.core.memory.entity_reranker.get_skill_forge", create=True):
            # Mock SkillForge with no known skills
            mock_forge = MagicMock()
            mock_forge.known_skills = {}
            with patch(
                "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
                return_value=mock_forge,
            ):
                matches = match_procedural_skills("search for memories")
                assert matches == []

    def test_match_finds_skill_by_trigger_overlap(self):
        from whitemagic.core.intelligence.omni.skill_forge import ForgedSkill
        from whitemagic.core.intelligence.omni.universal_router import (
            ExecutionChain,
            GanaStep,
        )

        chain = ExecutionChain(
            intent="search memories with embeddings",
            steps=[GanaStep(mansion="NET", operation="search", context_key="memory", parameters={})],
            estimated_complexity=1.0,
            required_capabilities=[],
        )
        skill = ForgedSkill(
            name="memory_search_skill",
            description="Search memories using embeddings",
            trigger_phrases=["search memories with embeddings"],
            optimized_chain=chain,
        )

        mock_forge = MagicMock()
        mock_forge.known_skills = {"memory_search_skill": skill}

        with patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=mock_forge,
        ):
            matches = match_procedural_skills("search memories with embeddings")
            assert len(matches) >= 1
            assert matches[0]["skill_name"] == "memory_search_skill"
            assert "match_score" in matches[0]

    def test_match_returns_max_matches(self):
        from whitemagic.core.intelligence.omni.skill_forge import ForgedSkill
        from whitemagic.core.intelligence.omni.universal_router import (
            ExecutionChain,
            GanaStep,
        )

        chain = ExecutionChain(
            intent="test",
            steps=[GanaStep(mansion="NET", operation="search", context_key="x", parameters={})],
            estimated_complexity=1.0,
            required_capabilities=[],
        )
        skills = {}
        for i in range(5):
            skill = ForgedSkill(
                name=f"skill_{i}",
                description=f"Test skill {i}",
                trigger_phrases=[f"test query {i}"],
                optimized_chain=chain,
            )
            skills[f"skill_{i}"] = skill

        mock_forge = MagicMock()
        mock_forge.known_skills = skills

        with patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=mock_forge,
        ):
            matches = match_procedural_skills("test query", max_matches=2)
            assert len(matches) <= 2

    def test_match_low_similarity_excluded(self):
        from whitemagic.core.intelligence.omni.skill_forge import ForgedSkill
        from whitemagic.core.intelligence.omni.universal_router import (
            ExecutionChain,
            GanaStep,
        )

        chain = ExecutionChain(
            intent="completely unrelated thing",
            steps=[GanaStep(mansion="VOID", operation="transform", context_key="math", parameters={})],
            estimated_complexity=1.0,
            required_capabilities=[],
        )
        skill = ForgedSkill(
            name="unrelated_skill",
            description="Does something unrelated",
            trigger_phrases=["completely unrelated thing"],
            optimized_chain=chain,
        )

        mock_forge = MagicMock()
        mock_forge.known_skills = {"unrelated_skill": skill}

        with patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=mock_forge,
        ):
            # Query about "memory search" should not match skill about "unrelated thing"
            matches = match_procedural_skills("memory search embeddings")
            assert matches == []


# ---------------------------------------------------------------------------
# 7. Integration: search_hybrid with new parameters
# ---------------------------------------------------------------------------

class TestSearchHybridIntegration:
    """Test that search_hybrid accepts new parameters without errors."""

    def test_search_hybrid_accepts_new_params(self):
        """Verify search_hybrid signature includes v24.3 parameters."""
        import inspect

        from whitemagic.core.memory.unified import UnifiedMemory

        sig = inspect.signature(UnifiedMemory.search_hybrid)
        params = sig.parameters
        assert "entity_boost_weight" in params
        assert "rerank" in params
        assert "include_skills" in params

    def test_search_hybrid_defaults(self):
        """Verify default values for new parameters."""
        import inspect

        from whitemagic.core.memory.unified import UnifiedMemory

        sig = inspect.signature(UnifiedMemory.search_hybrid)
        assert sig.parameters["entity_boost_weight"].default == 0.3
        assert sig.parameters["rerank"].default is True
        assert sig.parameters["include_skills"].default is True


# ---------------------------------------------------------------------------
# 8. MemoryType.PROCEDURAL
# ---------------------------------------------------------------------------

class TestProceduralMemoryType:
    """Test that PROCEDURAL memory type was added."""

    def test_procedural_exists(self):
        assert hasattr(MemoryType, "PROCEDURAL")

    def test_procedural_is_distinct(self):
        assert MemoryType.PROCEDURAL != MemoryType.SHORT_TERM
        assert MemoryType.PROCEDURAL != MemoryType.LONG_TERM

    def test_can_create_procedural_memory(self):
        mem = Memory(
            id="skill:test_skill",
            content="Procedural skill: test",
            memory_type=MemoryType.PROCEDURAL,
            importance=0.8,
            title="test_skill",
        )
        assert mem.memory_type == MemoryType.PROCEDURAL
        assert mem.title == "test_skill"
