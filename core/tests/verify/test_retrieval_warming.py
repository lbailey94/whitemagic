"""P5.3 — Retrieval warming tests.

Verifies that the RetrievalIndexCache:
- Stores actual HNSW index references (not placeholder strings)
- Tracks hit/miss/warm/failure/eviction telemetry
- Provides namespace isolation
- Invalidates correctly on writes
"""
import time
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.core.memory.retrieval_cache import RetrievalIndexCache


class TestRetrievalIndexCacheTelemetry:
    """Test telemetry counters."""

    def test_hit_miss_counters(self):
        cache = RetrievalIndexCache(ttl_seconds=10)
        assert cache.get("user1", "galaxy1") is None
        assert cache._telemetry["misses"] == 1
        assert cache._telemetry["hits"] == 0

        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        assert cache.get("user1", "galaxy1") is not None
        assert cache._telemetry["hits"] == 1
        assert cache._telemetry["misses"] == 1

    def test_eviction_counter_on_invalidate(self):
        cache = RetrievalIndexCache()
        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        assert cache.invalidate("user1", "galaxy1") is True
        assert cache._telemetry["evictions"] == 1
        assert cache.invalidate("user1", "galaxy1") is False
        assert cache._telemetry["evictions"] == 1

    def test_eviction_counter_on_ttl_expiry(self):
        cache = RetrievalIndexCache(ttl_seconds=0.01)
        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        time.sleep(0.02)
        assert cache.get("user1", "galaxy1") is None
        assert cache._telemetry["evictions"] == 1

    def test_warm_counters(self):
        cache = RetrievalIndexCache()
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = MagicMock()
            assert cache.warm_galaxy("user1", "galaxy1") is True
            assert cache._telemetry["warmed"] == 1
            assert cache._telemetry["warm_failures"] == 0
            # Second call returns False (already cached)
            assert cache.warm_galaxy("user1", "galaxy1") is False
            assert cache._telemetry["warmed"] == 1

    def test_warm_failure_counter(self):
        cache = RetrievalIndexCache()
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = None
            assert cache.warm_galaxy("user1", "galaxy1") is False
            assert cache._telemetry["warm_failures"] == 1
            assert cache._telemetry["warmed"] == 0

    def test_stats_includes_telemetry(self):
        cache = RetrievalIndexCache()
        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        cache.get("user1", "galaxy1")
        stats = cache.stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "warmed" in stats
        assert "warm_failures" in stats
        assert "evictions" in stats
        assert stats["hits"] == 1


class TestRetrievalIndexCacheNamespace:
    """Test namespace isolation."""

    def test_user_isolation(self):
        cache = RetrievalIndexCache()
        cache.put("user1", "galaxy1", {"hnsw_index": "idx1"})
        cache.put("user2", "galaxy1", {"hnsw_index": "idx2"})
        e1 = cache.get("user1", "galaxy1")
        e2 = cache.get("user2", "galaxy1")
        assert e1["hnsw_index"] == "idx1"
        assert e2["hnsw_index"] == "idx2"

    def test_invalidate_user_only(self):
        cache = RetrievalIndexCache()
        cache.put("user1", "galaxy1", {"hnsw_index": "idx1"})
        cache.put("user1", "galaxy2", {"hnsw_index": "idx2"})
        cache.put("user2", "galaxy1", {"hnsw_index": "idx3"})
        count = cache.invalidate_user("user1")
        assert count == 2
        assert cache.get("user1", "galaxy1") is None
        assert cache.get("user1", "galaxy2") is None
        assert cache.get("user2", "galaxy1") is not None

    def test_invalidate_all(self):
        cache = RetrievalIndexCache()
        cache.put("user1", "galaxy1", {"hnsw_index": "idx1"})
        cache.put("user2", "galaxy2", {"hnsw_index": "idx2"})
        count = cache.invalidate_all()
        assert count == 2
        assert cache.get("user1", "galaxy1") is None
        assert cache.get("user2", "galaxy2") is None


class TestRetrievalIndexCacheWarmGalaxy:
    """Test warm_galaxy stores actual index references."""

    def test_warm_stores_actual_index(self):
        cache = RetrievalIndexCache()
        mock_index = MagicMock(name="hnsw_index")
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = mock_index
            assert cache.warm_galaxy("user1", "galaxy1") is True
            entry = cache.get("user1", "galaxy1")
            assert entry is not None
            assert entry["hnsw_index"] is mock_index
            assert entry["hnsw_index"] is not None

    def test_warm_idempotent(self):
        cache = RetrievalIndexCache()
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = MagicMock()
            assert cache.warm_galaxy("user1", "galaxy1") is True
            assert cache.warm_galaxy("user1", "galaxy1") is False

    def test_warm_galaxies_batch(self):
        cache = RetrievalIndexCache()
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = MagicMock()
            result = cache.warm_galaxies("user1", ["galaxy1", "galaxy2"])
            assert result == {"galaxy1": True, "galaxy2": True}

    def test_warm_no_private_backend_access(self):
        """Ensure warm_galaxy does not access _get_galaxy_backend."""
        cache = RetrievalIndexCache()
        with patch(
            "whitemagic.core.memory.galaxy_hnsw.get_galaxy_hnsw_manager"
        ) as mock:
            mock_manager = MagicMock()
            mock.return_value = mock_manager
            mock_manager._get_or_create_index.return_value = MagicMock()
            cache.warm_galaxy("user1", "galaxy1")
            # Should not import unified memory or call _get_galaxy_backend
            mock_manager._get_galaxy_backend.assert_not_called()


class TestRetrievalIndexCachePrune:
    """Test prune_expired."""

    def test_prune_removes_expired(self):
        cache = RetrievalIndexCache(ttl_seconds=0.01)
        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        cache.put("user1", "galaxy2", {"hnsw_index": "test"})
        time.sleep(0.02)
        pruned = cache.prune_expired()
        assert pruned == 2
        assert cache._telemetry["evictions"] == 2

    def test_prune_keeps_valid(self):
        cache = RetrievalIndexCache(ttl_seconds=10)
        cache.put("user1", "galaxy1", {"hnsw_index": "test"})
        pruned = cache.prune_expired()
        assert pruned == 0
        assert cache.get("user1", "galaxy1") is not None
