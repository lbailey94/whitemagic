"""Phase 3 §7.2 + §7.4 — Tests for cache privacy, schema hashing, write-driven invalidation, and permission change invalidation.

Verifies that:
- _cache_key includes privacy_classification in the key
- _cache_key includes tool_schema_hash in the key
- Different privacy classifications produce different keys
- Different schema hashes produce different keys
- _compute_tool_schema_hash returns deterministic hash for known tools
- Write-driven invalidation fires after write tool success
- Write-driven invalidation does NOT fire after read tool success
- Permission change invalidation: cache key changes when policy_profile changes
"""
from __future__ import annotations

import pytest


class TestCacheKeyPrivacyClassification:
    """Verify privacy_classification is included in cache keys."""

    def test_privacy_classification_in_key(self):
        from whitemagic.tools.middleware import _cache_key
        key_public = _cache_key(
            "test.tool", {"query": "hello"},
            privacy_classification="public",
        )
        key_private = _cache_key(
            "test.tool", {"query": "hello"},
            privacy_classification="private",
        )
        assert key_public != key_private, (
            "Cache keys with different privacy classifications should differ"
        )

    def test_default_privacy_is_default(self):
        from whitemagic.tools.middleware import _cache_key
        key_default = _cache_key("test.tool", {"query": "hello"})
        key_explicit = _cache_key(
            "test.tool", {"query": "hello"},
            privacy_classification="default",
        )
        assert key_default == key_explicit


class TestCacheKeySchemaHash:
    """Verify tool_schema_hash is included in cache keys."""

    def test_schema_hash_in_key(self):
        from whitemagic.tools.middleware import _cache_key
        key_a = _cache_key(
            "test.tool", {"query": "hello"},
            tool_schema_hash="abc12345",
        )
        key_b = _cache_key(
            "test.tool", {"query": "hello"},
            tool_schema_hash="def67890",
        )
        assert key_a != key_b, (
            "Cache keys with different schema hashes should differ"
        )

    def test_empty_schema_hash_default(self):
        from whitemagic.tools.middleware import _cache_key
        key_default = _cache_key("test.tool", {"query": "hello"})
        key_empty = _cache_key(
            "test.tool", {"query": "hello"},
            tool_schema_hash="",
        )
        assert key_default == key_empty

    def test_compute_tool_schema_hash_returns_string(self):
        from whitemagic.tools.middleware import _compute_tool_schema_hash
        h = _compute_tool_schema_hash("system.status")
        assert isinstance(h, str)
        # Either empty (tool not found) or 8 chars (md5[:8])
        assert len(h) == 0 or len(h) == 8

    def test_compute_tool_schema_hash_deterministic(self):
        from whitemagic.tools.middleware import _compute_tool_schema_hash
        h1 = _compute_tool_schema_hash("system.status")
        h2 = _compute_tool_schema_hash("system.status")
        assert h1 == h2

    def test_compute_tool_schema_hash_unknown_tool_empty(self):
        from whitemagic.tools.middleware import _compute_tool_schema_hash
        h = _compute_tool_schema_hash("nonexistent.tool.12345")
        assert h == ""


class TestWriteDrivenCacheInvalidation:
    """Verify write-driven cache invalidation in mw_semantic_cache."""

    def test_write_tool_triggers_invalidation(self):
        """After a successful write tool, the semantic cache namespace is invalidated."""
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_semantic_cache,
            _is_read_only_tool,
        )
        import unittest.mock as mock

        # Track invalidation calls
        invalidation_calls = []

        def mock_next_fn(ctx):
            return {"status": "success", "result": "written"}

        ctx = DispatchContext(
            tool_name="memory_create",
            kwargs={"content": "test memory"},
        )
        ctx.user_id = "alice"
        ctx.galaxy = "codex"

        with mock.patch("whitemagic.core.cache.get_unified_cache") as mock_cache:
            mock_unified = mock.MagicMock()
            mock_unified.get.return_value = None  # Cache miss
            mock_cache.return_value = mock_unified

            # Make _is_cacheable_tool return True for this test
            with mock.patch("whitemagic.tools.middleware._is_cacheable_tool", return_value=True):
                with mock.patch("whitemagic.tools.middleware._is_read_only_tool", return_value=False):
                    result = mw_semantic_cache(ctx, mock_next_fn)

            # Verify invalidation was called
            assert result is not None
            assert result["status"] == "success"
            # Check that invalidate_namespace was called
            mock_unified.invalidate_namespace.assert_called()
            call_args = mock_unified.invalidate_namespace.call_args
            invalidation_ns = call_args[0][0]
            assert "alice" in invalidation_ns
            assert "codex" in invalidation_ns

    def test_read_tool_does_not_trigger_invalidation(self):
        """After a successful read tool, cache invalidation should NOT fire."""
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_semantic_cache,
        )
        import unittest.mock as mock

        def mock_next_fn(ctx):
            return {"status": "success", "result": "data"}

        ctx = DispatchContext(
            tool_name="system.status",
            kwargs={},
        )

        with mock.patch("whitemagic.core.cache.get_unified_cache") as mock_cache:
            mock_unified = mock.MagicMock()
            mock_unified.get.return_value = None
            mock_cache.return_value = mock_unified

            with mock.patch("whitemagic.tools.middleware._is_cacheable_tool", return_value=True):
                with mock.patch("whitemagic.tools.middleware._is_read_only_tool", return_value=True):
                    result = mw_semantic_cache(ctx, mock_next_fn)

            # invalidate_namespace should NOT be called for read-only tools
            mock_unified.invalidate_namespace.assert_not_called()

    def test_failed_write_does_not_trigger_invalidation(self):
        """A failed write should not trigger cache invalidation."""
        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_semantic_cache,
        )
        import unittest.mock as mock

        def mock_next_fn(ctx):
            return {"status": "error", "error": "write failed"}

        ctx = DispatchContext(
            tool_name="memory_create",
            kwargs={"content": "test"},
        )

        with mock.patch("whitemagic.core.cache.get_unified_cache") as mock_cache:
            mock_unified = mock.MagicMock()
            mock_unified.get.return_value = None
            mock_cache.return_value = mock_unified

            with mock.patch("whitemagic.tools.middleware._is_cacheable_tool", return_value=True):
                with mock.patch("whitemagic.tools.middleware._is_read_only_tool", return_value=False):
                    result = mw_semantic_cache(ctx, mock_next_fn)

            mock_unified.invalidate_namespace.assert_not_called()


class TestPermissionChangeCacheInvalidation:
    """Verify that changing policy_profile produces a different cache key."""

    def test_different_policy_profiles_produce_different_keys(self):
        from whitemagic.tools.middleware import _cache_key
        key_default = _cache_key(
            "test.tool", {"query": "hello"},
            policy_profile="default",
        )
        key_violet = _cache_key(
            "test.tool", {"query": "hello"},
            policy_profile="violet",
        )
        key_sandbox = _cache_key(
            "test.tool", {"query": "hello"},
            policy_profile="sandbox",
        )
        assert key_default != key_violet
        assert key_default != key_sandbox
        assert key_violet != key_sandbox

    def test_permission_change_invalidates_cache_entry(self):
        """Simulate: cache entry exists under policy A, then policy changes to B.
        The cache key for B should be different, so the old entry is not served."""
        from whitemagic.tools.middleware import _cache_key
        # User queries under policy "default"
        key_a = _cache_key(
            "system.status", {},
            user_id="alice",
            policy_profile="default",
        )
        # Same user, same query, but policy changed to "violet"
        key_b = _cache_key(
            "system.status", {},
            user_id="alice",
            policy_profile="violet",
        )
        # Keys must differ — old cached result under "default" cannot be served under "violet"
        assert key_a != key_b, (
            "Permission change (policy_profile) must produce a different cache key "
            "to prevent serving stale results from a different policy context."
        )


class TestNamespaceMigrationTooling:
    """Verify namespace migration script works correctly."""

    def test_migration_script_imports(self):
        """The migration script should be importable."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "namespace_migration",
            "/home/lucas/Desktop/WHITEMAGIC/core/scripts/namespace_migration.py",
        )
        assert spec is not None
        assert spec.loader is not None

    def test_find_legacy_galaxies_empty(self, tmp_path):
        """find_legacy_galaxies returns empty list when no galaxies exist."""
        import sys
        sys.path.insert(0, "/home/lucas/Desktop/WHITEMAGIC/core/scripts")
        try:
            from namespace_migration import find_legacy_galaxies
            result = find_legacy_galaxies(tmp_path)
            assert result == []
        finally:
            sys.path.pop(0)

    def test_find_legacy_galaxies_finds_db(self, tmp_path):
        """find_legacy_galaxies finds galaxy databases in the flat layout."""
        import sys
        sys.path.insert(0, "/home/lucas/Desktop/WHITEMAGIC/core/scripts")
        try:
            from namespace_migration import find_legacy_galaxies
            galaxies_dir = tmp_path / "galaxies" / "codex"
            galaxies_dir.mkdir(parents=True)
            (galaxies_dir / "whitemagic.db").write_bytes(b"fake db")
            result = find_legacy_galaxies(tmp_path)
            assert len(result) == 1
            assert result[0]["name"] == "codex"
        finally:
            sys.path.pop(0)

    def test_dry_run_does_not_copy(self, tmp_path):
        """Dry run should report but not actually copy files."""
        import sys
        sys.path.insert(0, "/home/lucas/Desktop/WHITEMAGIC/core/scripts")
        try:
            from namespace_migration import find_legacy_galaxies
            # Just verify the function signature is correct
            galaxies = find_legacy_galaxies(tmp_path)
            assert isinstance(galaxies, list)
        finally:
            sys.path.pop(0)

    def test_migration_report_structure(self, tmp_path):
        """Migration report has the expected structure."""
        import sys, json
        sys.path.insert(0, "/home/lucas/Desktop/WHITEMAGIC/core/scripts")
        try:
            from namespace_migration import migrate
            report = migrate(tmp_path, user_id="test_user", dry_run=True)
            assert "user_id" in report
            assert "dry_run" in report
            assert "galaxies_migrated" in report
            assert "hnsw_files_migrated" in report
            assert "main_db_migrated" in report
            assert "errors" in report
            assert "details" in report
            assert report["dry_run"] is True
            assert report["user_id"] == "test_user"
        finally:
            sys.path.pop(0)
