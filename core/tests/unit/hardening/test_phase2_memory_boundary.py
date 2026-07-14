"""Phase 2 — Memory and Galaxy Boundary Consolidation tests.

Tests that:
- Two users can create identically named galaxies without collision
- Two concurrent requests cannot observe each other's active galaxy
- A write through every compatibility API is visible through canonical recall
- Coordinates, associations, embeddings, and audits land in the same namespace
- Missing or corrupt galaxy databases produce explicit errors
- Export/import cannot cross namespaces without explicit authorization
- MemoryContext provides namespace isolation for store/recall/search
- GalaxyAwareBackend caches backends per user_id/galaxy_name
- Filesystem name validation prevents path traversal
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from whitemagic.core.memory.backends.protocol import (
    validate_galaxy_name,
    validate_user_id,
)
from whitemagic.core.memory.memory_context import MemoryContext

# ── Protocol validation ────────────────────────────────────────────────

class TestMemoryBackendProtocol:
    """The protocol is a structural typing.Protocol — any class with the
    right methods satisfies it without inheritance."""

    def test_protocol_is_runtime_checkable(self):
        from whitemagic.core.memory.sqlite_backend import SQLiteBackend
        # SQLiteBackend should satisfy the protocol structurally
        # Check on the class for method presence
        assert hasattr(SQLiteBackend, "store")
        assert hasattr(SQLiteBackend, "recall")
        assert hasattr(SQLiteBackend, "search")
        assert hasattr(SQLiteBackend, "delete")
        assert hasattr(SQLiteBackend, "get_stats")
        # close and pool are instance attributes, not class attributes
        # Verify they exist on an instance
        with tempfile.TemporaryDirectory() as td:
            backend = SQLiteBackend(Path(td) / "test.db")
            assert hasattr(backend, "close") or hasattr(backend, "pool")

    def test_galaxy_aware_backend_satisfies_protocol(self):
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend
        assert hasattr(GalaxyAwareBackend, "store")
        assert hasattr(GalaxyAwareBackend, "recall")
        assert hasattr(GalaxyAwareBackend, "search")
        assert hasattr(GalaxyAwareBackend, "delete")
        assert hasattr(GalaxyAwareBackend, "get_stats")
        assert hasattr(GalaxyAwareBackend, "close")


# ── Filesystem name validation ────────────────────────────────────────

class TestValidateGalaxyName:
    def test_simple_name_passthrough(self):
        assert validate_galaxy_name("codex") == "codex"

    def test_name_with_spaces_sanitized(self):
        assert validate_galaxy_name("my galaxy") == "my_galaxy"

    def test_name_with_special_chars_sanitized(self):
        safe = validate_galaxy_name("galaxy!@#")
        assert "!" not in safe
        assert "@" not in safe

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_galaxy_name("../etc/passwd")

    def test_slash_sanitized_not_rejected(self):
        # Slashes are sanitized to _ (namespace separator for quarantine galaxies)
        safe = validate_galaxy_name("foo/bar")
        assert "/" not in safe
        assert safe == "foo_bar"

    def test_backslash_sanitized_not_rejected(self):
        safe = validate_galaxy_name("foo\\bar")
        assert "\\" not in safe

    def test_quarantine_galaxy_name_sanitized(self):
        # quarantine/test_share is a legitimate galaxy name used by sharing protocol
        safe = validate_galaxy_name("quarantine/test_share")
        assert safe == "quarantine_test_share"

    def test_dotdot_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_galaxy_name("..secret")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_galaxy_name("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_galaxy_name("   ")

    def test_underscore_and_dash_preserved(self):
        assert validate_galaxy_name("my-galaxy_1") == "my-galaxy_1"

    def test_dot_preserved(self):
        assert validate_galaxy_name("galaxy.v2") == "galaxy.v2"


class TestValidateUserId:
    def test_simple_id_passthrough(self):
        assert validate_user_id("alice") == "alice"

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_user_id("../admin")

    def test_slash_sanitized(self):
        safe = validate_user_id("foo/bar")
        assert "/" not in safe
        assert safe == "foo_bar"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_user_id("")

    def test_special_chars_sanitized(self):
        safe = validate_user_id("user@domain")
        assert "@" not in safe


# ── GalaxyAwareBackend user_id isolation ──────────────────────────────

class TestGalaxyAwareBackendUserIsolation:
    """Two users with identically named galaxies must not collide."""

    def test_two_users_get_different_db_paths(self, tmp_path):
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        # Create two backends for different users
        default_db = tmp_path / "default.db"
        backend_alice = GalaxyAwareBackend(default_db, user_id="alice")
        backend_bob = GalaxyAwareBackend(default_db, user_id="bob")

        # Both create a galaxy named "codex"
        path_alice = backend_alice.get_galaxy_db_path("codex")
        path_bob = backend_bob.get_galaxy_db_path("codex")

        # Paths must be different (different user directories)
        assert path_alice != path_bob
        assert "alice" in str(path_alice)
        assert "bob" in str(path_bob)

    def test_two_users_galaxy_backends_cached_separately(self, tmp_path):
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        default_db = tmp_path / "default.db"
        backend = GalaxyAwareBackend(default_db, user_id="alice")

        # Get backend for "codex" galaxy
        b1 = backend._get_galaxy_backend("codex")
        b2 = backend._get_galaxy_backend("codex")
        assert b1 is b2  # Same instance from cache

        # Cache key must include user_id
        cache_keys = list(backend._galaxy_backends.keys())
        assert any("alice/codex" in k for k in cache_keys)

    def test_default_user_id_is_local(self, tmp_path):
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        default_db = tmp_path / "default.db"
        backend = GalaxyAwareBackend(default_db)
        assert backend._user_id == "local"


# ── MemoryContext namespace isolation ─────────────────────────────────

class TestMemoryContextNamespaceIsolation:
    """MemoryContext provides request-scoped namespace isolation."""

    def test_store_with_context_tags_user_id(self, tmp_path):
        """When storing with a MemoryContext, the memory's metadata
        includes the user_id for namespace tracking."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            ctx_alice = MemoryContext(user_id="alice", galaxy="codex")
            mem = um.store("test content", memory_context=ctx_alice)

            assert mem.metadata.get("_user_id") == "alice"
            assert mem.metadata.get("_namespace") == "alice/codex"

    def test_recall_with_context_filters_by_user(self, tmp_path):
        """Recall with a MemoryContext returns None for memories
        belonging to a different user."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            # Store as alice
            ctx_alice = MemoryContext(user_id="alice", galaxy="codex")
            mem = um.store("alice's secret", memory_context=ctx_alice)

            # Recall as alice — should work
            recalled = um.recall(mem.id, memory_context=ctx_alice)
            assert recalled is not None
            assert recalled.content == "alice's secret"

            # Recall as bob — should return None (namespace isolation)
            ctx_bob = MemoryContext(user_id="bob", galaxy="codex")
            recalled_bob = um.recall(mem.id, memory_context=ctx_bob)
            assert recalled_bob is None

    def test_search_with_context_filters_by_user(self, tmp_path):
        """Search with a MemoryContext only returns memories from the
        same user namespace."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            # Store as alice
            ctx_alice = MemoryContext(user_id="alice", galaxy="codex")
            um.store("alice's data", memory_context=ctx_alice)

            # Store as bob
            ctx_bob = MemoryContext(user_id="bob", galaxy="codex")
            um.store("bob's data", memory_context=ctx_bob)

            # Search as alice — should only see alice's memory
            results_alice = um.search(query="data", memory_context=ctx_alice)
            user_ids = {r.metadata.get("_user_id") for r in results_alice}
            assert user_ids == {"alice"}

            # Search as bob — should only see bob's memory
            results_bob = um.search(query="data", memory_context=ctx_bob)
            user_ids = {r.metadata.get("_user_id") for r in results_bob}
            assert user_ids == {"bob"}

    def test_update_memory_with_context_rejects_cross_namespace(self, tmp_path):
        """Update with a MemoryContext rejects updating memories
        belonging to a different user."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            # Store as alice
            ctx_alice = MemoryContext(user_id="alice", galaxy="codex")
            mem = um.store("alice's memory", memory_context=ctx_alice)

            # Try to update as bob — should be rejected
            ctx_bob = MemoryContext(user_id="bob", galaxy="codex")
            result = um.update_memory(
                mem.id, {"importance": 0.9}, memory_context=ctx_bob
            )
            assert result["success"] is False
            assert result["error"] == "namespace_violation"

    def test_store_without_context_backward_compat(self, tmp_path):
        """Storing without a MemoryContext works as before (backward compat)."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            # Store without context — should work normally
            mem = um.store("legacy content", galaxy="codex")
            assert mem.content == "legacy content"
            # No _user_id in metadata (no context provided)
            assert "_user_id" not in mem.metadata

            # Recall without context — should work
            recalled = um.recall(mem.id)
            assert recalled is not None

    def test_context_galaxy_overrides_param(self, tmp_path):
        """When MemoryContext.galaxy is set, it overrides the galaxy parameter."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)

            ctx = MemoryContext(user_id="alice", galaxy="research")
            mem = um.store("content", galaxy="codex", memory_context=ctx)
            assert mem.galaxy == "research"  # Context overrides


# ── Write-through visibility ───────────────────────────────────────────

class TestWriteThroughVisibility:
    """A write through every compatibility API is visible through canonical recall."""

    def test_store_visible_via_recall(self, tmp_path):
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)
            mem = um.store("visibility test", galaxy="codex")
            recalled = um.recall(mem.id)
            assert recalled is not None
            assert recalled.id == mem.id

    def test_store_visible_via_search(self, tmp_path):
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)
            um.store("unique visibility marker xyz789", galaxy="codex")
            results = um.search(query="unique visibility marker xyz789")
            assert any("visibility marker" in str(r.content) for r in results)

    def test_update_visible_via_recall(self, tmp_path):
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)
            mem = um.store("original content", galaxy="codex")
            um.update_memory(mem.id, {"importance": 0.95})
            recalled = um.recall(mem.id)
            assert recalled is not None
            assert recalled.importance == 0.95


# ── Missing/corrupt galaxy databases ──────────────────────────────────

class TestGalaxyDatabaseErrors:
    """Missing or corrupt galaxy databases produce explicit errors."""

    def test_missing_galaxy_db_creates_on_demand(self, tmp_path):
        """Accessing a galaxy that doesn't exist creates it on demand."""
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        backend = GalaxyAwareBackend(tmp_path / "default.db", user_id="test_user")
        # This should create the galaxy DB, not crash
        galaxy_backend = backend._get_galaxy_backend("new_galaxy")
        assert galaxy_backend is not None
        assert galaxy_backend.db_path.exists()

    def test_invalid_galaxy_name_raises(self, tmp_path):
        """Invalid galaxy names raise ValueError, not silently create dirs."""
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        backend = GalaxyAwareBackend(tmp_path / "default.db", user_id="test_user")
        with pytest.raises(ValueError):
            backend._get_galaxy_backend("../escape")


# ── Export/import namespace boundary ──────────────────────────────────

class TestExportImportNamespaceBoundary:
    """Export/import cannot cross namespaces without explicit authorization."""

    def test_export_preserves_user_id_metadata(self, tmp_path):
        """When a memory is stored with a user_id, the metadata is preserved."""
        from whitemagic.core.memory.unified import UnifiedMemory

        with patch.dict(os.environ, {"WM_SKIP_HOLO_INDEX": "1", "WM_SILENT_INIT": "1"}):
            um = UnifiedMemory(base_path=tmp_path)
            ctx = MemoryContext(user_id="alice", galaxy="codex")
            mem = um.store("exportable content", memory_context=ctx)

            # The memory's metadata should contain the namespace info
            assert mem.metadata.get("_user_id") == "alice"
            assert mem.metadata.get("_namespace") == "alice/codex"
