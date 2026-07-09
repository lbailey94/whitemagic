"""Tests for the Unified Cache Bridge — Rust and Python backends."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from whitemagic.core.cache.unified_cache_bridge import (
    PyUnifiedCache,
    UnifiedCacheBridge,
    get_unified_cache,
    is_rust_cache_available,
)


# ---------------------------------------------------------------------------
# Python fallback cache tests
# ---------------------------------------------------------------------------


class TestPyUnifiedCache:
    """Test the pure-Python fallback cache."""

    def test_basic_set_get(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("semantic", "key1", "value1", ttl_seconds=60)
        assert cache.get("semantic", "key1") == "value1"

    def test_cache_miss(self):
        cache = PyUnifiedCache(max_size=100)
        assert cache.get("semantic", "nonexistent") is None

    def test_ttl_expiry(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("semantic", "key1", "value1", ttl_seconds=0.1)
        time.sleep(0.15)
        assert cache.get("semantic", "key1") is None

    def test_namespace_isolation(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("semantic", "key1", "semantic_value", ttl_seconds=60)
        cache.set("query", "key1", "query_value", ttl_seconds=60)
        assert cache.get("semantic", "key1") == "semantic_value"
        assert cache.get("query", "key1") == "query_value"

    def test_lru_eviction(self):
        cache = PyUnifiedCache(max_size=3)
        cache.set("ns", "k1", "v1", ttl_seconds=60)
        cache.set("ns", "k2", "v2", ttl_seconds=60)
        cache.set("ns", "k3", "v3", ttl_seconds=60)
        # Access k1 to make it more recently used
        cache.get("ns", "k1")
        # Add k4 — should evict k2 (least recently used)
        cache.set("ns", "k4", "v4", ttl_seconds=60)
        assert cache.get("ns", "k1") == "v1"  # Still cached
        assert cache.get("ns", "k2") is None  # Evicted
        assert cache.get("ns", "k4") == "v4"

    def test_invalidate(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("semantic", "key1", "value1", ttl_seconds=60)
        assert cache.invalidate("semantic", "key1") is True
        assert cache.get("semantic", "key1") is None
        assert cache.invalidate("semantic", "nonexistent") is False

    def test_invalidate_namespace(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("semantic", "k1", "v1", ttl_seconds=60)
        cache.set("semantic", "k2", "v2", ttl_seconds=60)
        cache.set("query", "k1", "qv1", ttl_seconds=60)
        count = cache.invalidate_namespace("semantic")
        assert count == 2
        assert cache.get("semantic", "k1") is None
        assert cache.get("semantic", "k2") is None
        assert cache.get("query", "k1") == "qv1"  # Other namespace untouched

    def test_clear(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("ns", "k1", "v1", ttl_seconds=60)
        cache.clear()
        assert cache.is_empty()
        assert cache.len() == 0

    def test_cleanup_expired(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("ns", "k1", "v1", ttl_seconds=0.1)
        cache.set("ns", "k2", "v2", ttl_seconds=60)
        time.sleep(0.15)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("ns", "k2") == "v2"  # Still alive

    def test_stats(self):
        cache = PyUnifiedCache(max_size=100)
        cache.set("ns", "k1", "v1", ttl_seconds=60)
        cache.get("ns", "k1")  # Hit
        cache.get("ns", "miss")  # Miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["backend"] == "python"
        assert stats["size"] == 1

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "cache.json")
            cache1 = PyUnifiedCache(max_size=100, persist_path=path)
            cache1.set("semantic", "k1", "v1", ttl_seconds=3600)
            count = cache1.persist()
            assert count == 1

            # New cache instance loads from disk
            cache2 = PyUnifiedCache(max_size=100, persist_path=path)
            assert cache2.get("semantic", "k1") == "v1"

    def test_make_key_deterministic(self):
        k1 = PyUnifiedCache.make_key("semantic", "my_key")
        k2 = PyUnifiedCache.make_key("semantic", "my_key")
        assert k1 == k2
        k3 = PyUnifiedCache.make_key("query", "my_key")
        assert k1 != k3  # Different namespace


# ---------------------------------------------------------------------------
# UnifiedCacheBridge tests
# ---------------------------------------------------------------------------


class TestUnifiedCacheBridge:
    """Test the bridge that wraps Rust or Python cache."""

    def test_get_singleton(self):
        cache1 = get_unified_cache()
        cache2 = get_unified_cache()
        assert cache1 is cache2  # Same instance

    def test_backend_detection(self):
        cache = get_unified_cache()
        assert cache.backend in ("rust", "python")
        assert isinstance(cache.is_rust, bool)

    def test_set_get_json(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        data = {"result": "42 is the answer", "tokens_saved": 100}
        cache.set_json("semantic", "test_key", data, ttl_seconds=60)
        retrieved = cache.get_json("semantic", "test_key")
        assert retrieved is not None
        assert retrieved["result"] == "42 is the answer"
        assert retrieved["tokens_saved"] == 100

    def test_set_get_raw(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("semantic", "raw_key", "raw_value", ttl_seconds=60)
        assert cache.get("semantic", "raw_key") == "raw_value"

    def test_cache_miss_returns_none(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        assert cache.get("semantic", "nonexistent") is None
        assert cache.get_json("semantic", "nonexistent") is None

    def test_invalidate(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("semantic", "k1", "v1", ttl_seconds=60)
        assert cache.invalidate("semantic", "k1") is True
        assert cache.get("semantic", "k1") is None

    def test_invalidate_namespace(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("semantic", "k1", "v1", ttl_seconds=60)
        cache.set("semantic", "k2", "v2", ttl_seconds=60)
        cache.set("query", "k1", "qv1", ttl_seconds=60)
        count = cache.invalidate_namespace("semantic")
        assert count == 2
        assert cache.get("query", "k1") == "qv1"

    def test_clear(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("ns", "k1", "v1", ttl_seconds=60)
        cache.clear()
        assert cache.get("ns", "k1") is None

    def test_stats(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("ns", "k1", "v1", ttl_seconds=60)
        cache.get("ns", "k1")
        cache.get("ns", "miss")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["backend"] in ("rust", "python")

    def test_namespace_isolation(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("semantic", "k1", "sem_val", ttl_seconds=60)
        cache.set("query", "k1", "qry_val", ttl_seconds=60)
        assert cache.get("semantic", "k1") == "sem_val"
        assert cache.get("query", "k1") == "qry_val"

    def test_ttl_expiry(self):
        cache = UnifiedCacheBridge(max_size=100, persist=False)
        cache.set("ns", "k1", "v1", ttl_seconds=0.1)
        time.sleep(0.15)
        assert cache.get("ns", "k1") is None

    def test_rust_cache_available_check(self):
        assert isinstance(is_rust_cache_available(), bool)


# ---------------------------------------------------------------------------
# Semantic cache middleware integration with unified cache
# ---------------------------------------------------------------------------


@pytest.mark.xdist_group(name="semantic_cache")
class TestSemanticCacheUnifiedIntegration:
    """Test that mw_semantic_cache uses the unified cache bridge."""

    def test_cache_hit_via_unified_cache(self):
        """Pre-populate unified cache, verify middleware short-circuits."""
        from whitemagic.tools.middleware import (
            DispatchContext,
            _cache_key,
            mw_semantic_cache,
        )

        cache = UnifiedCacheBridge(max_size=100, persist=False)
        key = _cache_key("llama.chat", {"prompt": "test unified cache"})
        payload = json.dumps(
            {
                "result": "unified cache answer",
                "tokens_saved": 42,
                "tool": "llama.chat",
            }
        )
        cache.set("semantic", key, payload, ttl_seconds=3600)

        dispatched = False

        def next_fn(ctx):
            nonlocal dispatched
            dispatched = True
            return {"status": "success", "result": "should not see this"}

        ctx = DispatchContext(
            tool_name="llama.chat",
            kwargs={"prompt": "test unified cache"},
        )

        with patch("whitemagic.core.cache.get_unified_cache", return_value=cache):
            result = mw_semantic_cache(ctx, next_fn)
            assert not dispatched
            assert result["method"] == "semantic_cache"
            assert result["result"] == "unified cache answer"
            assert result["tokens_saved"] == 42

    def test_cache_miss_dispatches_and_caches(self):
        """On cache miss, should dispatch and store in unified cache."""
        from whitemagic.tools.middleware import (
            DispatchContext,
            _cache_key,
            mw_semantic_cache,
        )

        cache = UnifiedCacheBridge(max_size=100, persist=False)

        def next_fn(ctx):
            return {"status": "success", "result": "fresh answer"}

        ctx = DispatchContext(
            tool_name="llama.chat",
            kwargs={"prompt": "test cache miss and store"},
        )

        with patch("whitemagic.core.cache.get_unified_cache", return_value=cache):
            result = mw_semantic_cache(ctx, next_fn)
            assert result["status"] == "success"
            assert result["result"] == "fresh answer"

            # Verify it was cached
            key = _cache_key("llama.chat", {"prompt": "test cache miss and store"})
            cached = cache.get_json("semantic", key)
            assert cached is not None
            assert cached["result"] == "fresh answer"
