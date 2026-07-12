"""Unit tests for galaxy snapshot/restore (P4.2)."""

import pytest

from whitemagic.core.memory.unified import UnifiedMemory, reset_singleton, get_unified_memory
from whitemagic.core.memory.unified_types import MemoryType


@pytest.fixture
def um():
    """Fresh UnifiedMemory instance for testing."""
    reset_singleton()
    instance = get_unified_memory()
    yield instance
    reset_singleton()


class TestGalaxySnapshot:
    """Test galaxy_snapshot method."""

    def test_snapshot_returns_valid_structure(self, um):
        snap = um.galaxy_snapshot(galaxy="test")
        assert "galaxy_meta" in snap
        assert "memories" in snap
        assert "associations" in snap
        meta = snap["galaxy_meta"]
        assert meta["format"] == "snapshot_v1"
        assert "memory_count" in meta
        assert "association_count" in meta
        assert "snapshot_at" in meta

    def test_snapshot_includes_memories(self, um):
        um.store("test content for snapshot", title="Test Mem", galaxy="test")
        snap = um.galaxy_snapshot(galaxy="test")
        assert snap["galaxy_meta"]["memory_count"] >= 1
        mem = snap["memories"][0]
        assert "id" in mem
        assert "title" in mem
        assert "content" in mem
        assert "coords" in mem
        assert "tags" in mem

    def test_snapshot_includes_associations(self, um):
        m1 = um.store("memory one", galaxy="test")
        m2 = um.store("memory two", galaxy="test")
        # Add an association via the galaxy-specific backend
        galaxy_backend = um._galaxy_backend._get_backend_for_galaxy("test")
        with galaxy_backend.pool.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO associations (source_id, target_id, strength) VALUES (?, ?, ?)",
                (m1.id, m2.id, 0.8),
            )
        snap = um.galaxy_snapshot(galaxy="test")
        assert snap["galaxy_meta"]["association_count"] >= 1
        assoc = snap["associations"][0]
        assert "source_id" in assoc
        assert "target_id" in assoc
        assert "strength" in assoc


class TestGalaxyRestore:
    """Test galaxy_restore method."""

    def test_restore_creates_memories(self, um):
        snapshot = {
            "galaxy_meta": {"galaxy": "test_restore"},
            "memories": [
                {
                    "id": "fake-id-1",
                    "title": "Restored Memory",
                    "content": "restored content",
                    "importance": 0.8,
                    "memory_type": "LONG_TERM",
                    "tags": ["test", "restore"],
                    "galaxy": "test_restore",
                    "emotional_valence": 0.5,
                    "metadata": {},
                    "coords": None,
                },
            ],
            "associations": [],
        }
        result = um.galaxy_restore(snapshot, target_galaxy="test_restore")
        assert result["memories_restored"] == 1
        assert result["galaxy"] == "test_restore"

    def test_restore_with_target_galaxy(self, um):
        snapshot = {
            "galaxy_meta": {"galaxy": "original"},
            "memories": [
                {
                    "id": "fake-id-2",
                    "title": "Branched Memory",
                    "content": "branched content",
                    "importance": 0.5,
                    "memory_type": "SHORT_TERM",
                    "tags": [],
                    "galaxy": "original",
                    "metadata": {},
                    "coords": None,
                },
            ],
            "associations": [],
        }
        result = um.galaxy_restore(snapshot, target_galaxy="branched_galaxy")
        assert result["galaxy"] == "branched_galaxy"
        assert result["memories_restored"] == 1

    def test_restore_associations(self, um):
        snapshot = {
            "galaxy_meta": {"galaxy": "test_assoc"},
            "memories": [
                {
                    "id": "src-1",
                    "title": "Source",
                    "content": "source content",
                    "importance": 0.5,
                    "memory_type": "SHORT_TERM",
                    "tags": [],
                    "galaxy": "test_assoc",
                    "metadata": {},
                    "coords": None,
                },
                {
                    "id": "tgt-1",
                    "title": "Target",
                    "content": "target content",
                    "importance": 0.5,
                    "memory_type": "SHORT_TERM",
                    "tags": [],
                    "galaxy": "test_assoc",
                    "metadata": {},
                    "coords": None,
                },
            ],
            "associations": [
                {"source_id": "src-1", "target_id": "tgt-1", "strength": 0.9},
            ],
        }
        result = um.galaxy_restore(snapshot, target_galaxy="test_assoc")
        assert result["memories_restored"] == 2
        assert result["associations_restored"] == 1

    def test_restore_empty_snapshot(self, um):
        snapshot = {
            "galaxy_meta": {"galaxy": "empty"},
            "memories": [],
            "associations": [],
        }
        result = um.galaxy_restore(snapshot)
        assert result["memories_restored"] == 0
        assert result["associations_restored"] == 0

    def test_snapshot_restore_roundtrip(self, um):
        """Snapshot a galaxy, restore it into a different galaxy, verify memories exist."""
        um.store("roundtrip test content", title="Roundtrip", galaxy="roundtrip_src")
        snap = um.galaxy_snapshot(galaxy="roundtrip_src")
        assert snap["galaxy_meta"]["memory_count"] >= 1

        result = um.galaxy_restore(snap, target_galaxy="roundtrip_dst")
        assert result["memories_restored"] >= 1

        # Verify the restored galaxy has the content via listing all memories
        results = um._galaxy_backend.search(query=None, galaxy="roundtrip_dst", limit=100)
        assert len(results) >= 1
        assert any("roundtrip" in (m.title or "").lower() for m in results)


class TestGalaxySnapshotHandlers:
    """Test MCP tool handlers."""

    def test_handle_galaxy_snapshot(self, um):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_snapshot

        um.store("handler test", galaxy="handler_test")
        result = handle_galaxy_snapshot(galaxy="handler_test")
        assert result["status"] == "success"
        assert result["memory_count"] >= 1
        assert "snapshot" in result

    def test_handle_galaxy_restore(self, um):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_restore

        snapshot = {
            "galaxy_meta": {"galaxy": "handler_restore"},
            "memories": [
                {
                    "id": "h-1",
                    "title": "Handler Restore Test",
                    "content": "handler restore content",
                    "importance": 0.5,
                    "memory_type": "SHORT_TERM",
                    "tags": [],
                    "galaxy": "handler_restore",
                    "metadata": {},
                    "coords": None,
                },
            ],
            "associations": [],
        }
        result = handle_galaxy_restore(snapshot=snapshot, target_galaxy="handler_restore")
        assert result["status"] == "success"
        assert result["memories_restored"] == 1

    def test_handle_galaxy_restore_missing_snapshot(self):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_restore

        result = handle_galaxy_restore()
        assert result["status"] == "error"
