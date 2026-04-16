"""Unit tests for PSR decomposed modules (PSR-014)."""

def test_sqlite_queries_importable():
    from whitemagic.core.memory.sqlite_queries import (
        FTS_SEARCH_QUERY,
        STORE_MEMORY_QUERY,
    )
    assert "bm25" in FTS_SEARCH_QUERY
    assert "INSERT" in STORE_MEMORY_QUERY

def test_dream_phases_importable():
    from whitemagic.core.intelligence.dream.dream_phases import PHASE_ORDER, DreamPhase
    assert len(PHASE_ORDER) == 8
    assert DreamPhase.TRIAGE in PHASE_ORDER

def test_consolidation_strategies_importable():
    from whitemagic.core.memory.consolidation_strategies import (
        STRATEGY_THRESHOLDS,
        ConsolidationStrategy,
    )
    assert ConsolidationStrategy.SIMILARITY in STRATEGY_THRESHOLDS
    assert STRATEGY_THRESHOLDS[ConsolidationStrategy.SIMILARITY] > 0

def test_async_batch_importable():
    from whitemagic.utils.async_batch import async_batch_process, async_map
    assert callable(async_batch_process)
    assert callable(async_map)

def test_simhash_fast_importable():
    from whitemagic.utils.simhash_fast import compute_simhash, find_near_duplicates
    h = compute_simhash("hello world")
    assert isinstance(h, int)
    pairs = find_near_duplicates(["hello world", "hello world", "completely different"], threshold=10)
    assert len(pairs) >= 1
