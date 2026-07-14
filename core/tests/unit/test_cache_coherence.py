"""Tests for multi-agent cache coherence: version vectors, agent IDs,
conflict resolution, agent registry, and cache invalidation events."""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

# Set test env vars before imports
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

from whitemagic.core.memory.agent_registry import (
    get_agent_registry,
    reset_agent_registry,
)
from whitemagic.core.memory.unified_types import Memory, MemoryType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLite backend for isolated testing."""
    from whitemagic.core.memory.sqlite_backend import SQLiteBackend
    db_path = tmp_path / "test_cache_coherence.db"
    backend = SQLiteBackend(db_path)
    return backend


@pytest.fixture
def registry():
    """Fresh agent registry for each test."""
    reset_agent_registry()
    reg = get_agent_registry()
    yield reg
    reset_agent_registry()


@pytest.fixture
def clean_cache_registry():
    """Reset cache registry singleton."""
    import whitemagic.core.memory.cache_registry as cr_mod
    cr_mod._registry = None
    yield
    cr_mod._registry = None


def _make_memory(mid="test-1", content="hello", version=1, agent_id="agent-A"):
    """Helper to create a Memory with version/agent_id set."""
    return Memory(
        id=mid,
        content=content,
        memory_type=MemoryType.SHORT_TERM,
        version=version,
        agent_id=agent_id,
    )


# ---------------------------------------------------------------------------
# Agent Registry Tests
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_register_new_agent(self, registry):
        info = registry.register("agent-A", name="Alpha", capabilities=["search", "store"])
        assert info.agent_id == "agent-A"
        assert info.name == "Alpha"
        assert "search" in info.capabilities
        assert info.registered_at <= datetime.now()

    def test_register_updates_existing(self, registry):
        registry.register("agent-A", name="Alpha")
        info = registry.register("agent-A", name="Alpha-2", capabilities=["search"])
        assert info.name == "Alpha-2"
        assert "search" in info.capabilities
        assert len(registry.list_agents()) == 1

    def test_deregister(self, registry):
        registry.register("agent-A")
        assert registry.deregister("agent-A") is True
        assert registry.get("agent-A") is None
        assert registry.deregister("agent-A") is False

    def test_get_unknown_returns_none(self, registry):
        assert registry.get("unknown") is None

    def test_heartbeat_known_agent(self, registry):
        registry.register("agent-A")
        assert registry.heartbeat("agent-A") is True

    def test_heartbeat_unknown_agent(self, registry):
        assert registry.heartbeat("unknown") is False

    def test_stale_agents(self, registry):
        from datetime import timedelta
        registry.register("agent-A")
        registry.register("agent-B")
        # Manually age agent-A
        with registry._lock:
            registry._agents["agent-A"].last_seen = datetime.now() - timedelta(seconds=600)
        stale = registry.stale_agents(max_age_seconds=300)
        assert "agent-A" in stale
        assert "agent-B" not in stale

    def test_list_agents(self, registry):
        registry.register("agent-A")
        registry.register("agent-B")
        agents = registry.list_agents()
        assert len(agents) == 2
        ids = {a.agent_id for a in agents}
        assert ids == {"agent-A", "agent-B"}

    def test_stats(self, registry):
        registry.register("agent-A")
        registry.register("agent-B")
        stats = registry.stats()
        assert stats["total_agents"] == 2
        assert "agent-A" in stats["agent_ids"]

    def test_clear(self, registry):
        registry.register("agent-A")
        registry.clear()
        assert len(registry.list_agents()) == 0

    def test_singleton(self):
        reset_agent_registry()
        r1 = get_agent_registry()
        r2 = get_agent_registry()
        assert r1 is r2
        reset_agent_registry()

    def test_to_dict(self, registry):
        info = registry.register("agent-A", name="Alpha", capabilities=["x"])
        d = info.to_dict()
        assert d["agent_id"] == "agent-A"
        assert d["name"] == "Alpha"
        assert "x" in d["capabilities"]


# ---------------------------------------------------------------------------
# Conflict Resolution Tests
# ---------------------------------------------------------------------------

class TestConflictResolution:
    def test_remote_higher_version_wins(self, registry):
        local = _make_memory(version=1, agent_id="agent-A")
        remote = _make_memory(version=2, agent_id="agent-B")
        result = registry.resolve_conflict(local, remote, "agent-A", "agent-B")
        assert result["winner"] == "remote"
        assert result["loser"] == "local"
        assert result["strategy"] == "last_writer_wins"

    def test_local_higher_version_wins(self, registry):
        local = _make_memory(version=3, agent_id="agent-A")
        remote = _make_memory(version=1, agent_id="agent-B")
        result = registry.resolve_conflict(local, remote, "agent-A", "agent-B")
        assert result["winner"] == "local"
        assert result["loser"] == "remote"
        assert result["strategy"] == "last_writer_wins"

    def test_tiebreaker_by_agent_id(self, registry):
        local = _make_memory(version=2, agent_id="agent-A")
        remote = _make_memory(version=2, agent_id="agent-B")
        result = registry.resolve_conflict(local, remote, "agent-A", "agent-B")
        assert result["winner"] == "remote"  # "agent-B" > "agent-A"
        assert result["strategy"] == "agent_id_tiebreaker"

    def test_tiebreaker_local_wins_on_smaller_remote_id(self, registry):
        local = _make_memory(version=2, agent_id="agent-Z")
        remote = _make_memory(version=2, agent_id="agent-A")
        result = registry.resolve_conflict(local, remote, "agent-Z", "agent-A")
        assert result["winner"] == "local"

    def test_merged_is_winning_memory(self, registry):
        local = _make_memory(version=1, content="local")
        remote = _make_memory(version=5, content="remote")
        result = registry.resolve_conflict(local, remote)
        assert result["merged"].content == "remote"


# ---------------------------------------------------------------------------
# SQLite Backend: Version/Agent_ID Persistence Tests
# ---------------------------------------------------------------------------

class TestSQLiteVersionPersistence:
    def test_store_persists_version_and_agent_id(self, tmp_db):
        mem = _make_memory(mid="mem-1", version=3, agent_id="agent-X")
        tmp_db.store(mem)
        recalled = tmp_db.recall("mem-1")
        assert recalled is not None
        assert recalled.version == 3
        assert recalled.agent_id == "agent-X"

    def test_store_defaults_version_zero(self, tmp_db):
        mem = Memory(id="mem-2", content="test", memory_type=MemoryType.SHORT_TERM)
        tmp_db.store(mem)
        recalled = tmp_db.recall("mem-2")
        assert recalled is not None
        assert recalled.version == 0
        assert recalled.agent_id == ""

    def test_store_updates_version(self, tmp_db):
        mem = _make_memory(mid="mem-3", version=1, agent_id="agent-A")
        tmp_db.store(mem)
        # Update version
        mem.version = 5
        mem.agent_id = "agent-B"
        tmp_db.store(mem)
        recalled = tmp_db.recall("mem-3")
        assert recalled.version == 5
        assert recalled.agent_id == "agent-B"

    def test_migration_adds_columns(self, tmp_path):
        """Test that version and agent_id columns are added on existing DBs."""
        import sqlite3
        db_path = tmp_path / "migration_test.db"
        # Create a DB without version/agent_id columns
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                created_at TEXT,
                updated_at TEXT,
                accessed_at TEXT,
                access_count INTEGER,
                emotional_valence REAL,
                importance REAL,
                metadata TEXT,
                title TEXT,
                galaxy TEXT DEFAULT 'universal',
                source_trust TEXT DEFAULT 'user'
            )
        """)
        conn.execute("INSERT INTO memories (id, content, memory_type, created_at, updated_at, accessed_at, access_count, emotional_valence, importance, metadata, title) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     ("old-mem", "old", "SHORT_TERM", "2026-01-01T00:00:00", "2026-01-01T00:00:00", "2026-01-01T00:00:00", 0, 0.0, 0.5, "{}", ""))
        conn.commit()
        conn.close()

        # Now initialize backend — should auto-migrate
        from whitemagic.core.memory.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(db_path)
        recalled = backend.recall("old-mem")
        assert recalled is not None
        assert recalled.version == 0  # Default from migration
        assert recalled.agent_id == ""


# ---------------------------------------------------------------------------
# UnifiedMemory.update_memory Tests
# ---------------------------------------------------------------------------

class TestUpdateMemory:
    def test_update_increments_version(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        # Create a unified memory instance with the tmp backend
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        # Store initial memory
        mem = _make_memory(mid="upd-1", version=1, agent_id="agent-A")
        tmp_db.store(mem)

        result = um.update_memory("upd-1", {"content": "updated"}, agent_id="agent-B")
        assert result["success"] is True
        assert result["version"] == 2
        assert result["memory"].content == "updated"
        assert result["memory"].agent_id == "agent-B"

    def test_update_conflict_detected(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        mem = _make_memory(mid="upd-2", version=3, agent_id="agent-A")
        tmp_db.store(mem)

        # Try to update with wrong expected_version
        result = um.update_memory("upd-2", {"content": "stale"}, agent_id="agent-B", expected_version=1)
        assert result["success"] is False
        assert result["error"] == "version_conflict"
        assert result["expected_version"] == 1
        assert result["actual_version"] == 3
        assert result["conflicting_agent"] == "agent-A"

    def test_update_with_correct_version(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        mem = _make_memory(mid="upd-3", version=2, agent_id="agent-A")
        tmp_db.store(mem)

        result = um.update_memory("upd-3", {"importance": 0.9}, agent_id="agent-B", expected_version=2)
        assert result["success"] is True
        assert result["version"] == 3
        assert result["memory"].importance == 0.9

    def test_update_nonexistent_memory(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        result = um.update_memory("nonexistent", {"content": "x"}, agent_id="agent-A")
        assert result["success"] is False
        assert result["error"] == "Memory not found"

    def test_update_does_not_change_id_or_created_at(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        original = _make_memory(mid="upd-4", version=1, agent_id="agent-A")
        original_created = original.created_at
        tmp_db.store(original)

        # Try to update id and created_at — should be ignored
        um.update_memory("upd-4", {"id": "hacked", "created_at": datetime(2000, 1, 1)}, agent_id="agent-B")
        recalled = tmp_db.recall("upd-4")
        assert recalled.id == "upd-4"
        assert recalled.created_at == original_created


# ---------------------------------------------------------------------------
# Memory Serialization Tests
# ---------------------------------------------------------------------------

class TestMemorySerialization:
    def test_to_dict_includes_version_and_agent_id(self):
        mem = _make_memory(version=5, agent_id="agent-X")
        d = mem.to_dict()
        assert d["version"] == 5
        assert d["agent_id"] == "agent-X"

    def test_from_dict_includes_version_and_agent_id(self):
        mem = _make_memory(version=7, agent_id="agent-Y")
        d = mem.to_dict()
        restored = Memory.from_dict(d)
        assert restored.version == 7
        assert restored.agent_id == "agent-Y"

    def test_from_dict_defaults(self):
        d = {
            "id": "test",
            "content": "hello",
            "memory_type": "SHORT_TERM",
            "created_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat(),
        }
        mem = Memory.from_dict(d)
        assert mem.version == 0
        assert mem.agent_id == ""


# ---------------------------------------------------------------------------
# Cache Invalidation Event Tests
# ---------------------------------------------------------------------------

class TestCacheInvalidationEvents:
    def test_cache_invalidate_event_type_exists(self):
        from whitemagic.core.resonance import EventType
        assert hasattr(EventType, "CACHE_INVALIDATE")
        assert EventType.CACHE_INVALIDATE.value == "cache_invalidate"

    def test_cache_transfer_event_type_exists(self):
        from whitemagic.core.resonance import EventType
        assert hasattr(EventType, "CACHE_TRANSFER")
        assert EventType.CACHE_TRANSFER.value == "cache_transfer"

    def test_cache_registry_subscribes_to_events(self, clean_cache_registry):
        from whitemagic.core.memory.cache_registry import (
            get_cache_registry,
        )
        from whitemagic.core.resonance import EventType, get_bus
        # Get registry — should auto-subscribe
        get_cache_registry()
        bus = get_bus()
        # Verify listener was registered
        assert EventType.CACHE_INVALIDATE in bus._listeners
        assert len(bus._listeners[EventType.CACHE_INVALIDATE]) > 0

    def test_cache_registry_invalidates_on_event(self, clean_cache_registry):
        from whitemagic.core.memory.cache_registry import get_cache_registry
        from whitemagic.core.resonance import EventType, ResonanceEvent, get_bus

        reg = get_cache_registry()

        # Track invalidate calls
        invalidated_namespaces: list[str] = []

        def mock_invalidate(ns: str) -> int:
            invalidated_namespaces.append(ns)
            return 1

        reg.register("test-cache", flush_func=lambda: None, invalidate_func=mock_invalidate)

        # Emit a CACHE_INVALIDATE event
        bus = get_bus()
        event = ResonanceEvent(
            source="test",
            event_type=EventType.CACHE_INVALIDATE,
            data={"namespace": "test-ns", "memory_id": "x", "operation": "store"},
        )
        bus.emit(event)

        # The invalidate function should have been called via the event listener
        # The event listener calls invalidate_namespace which calls all invalidate_funcs
        # Note: the listener calls _registry.invalidate_namespace(ns) which iterates _invalidate_funcs
        assert "test-ns" in invalidated_namespaces or reg.get_version("test-ns") > 0


# ---------------------------------------------------------------------------
# Store with Agent_ID Tests
# ---------------------------------------------------------------------------

class TestStoreWithAgentId:
    def test_store_sets_agent_id(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        # Mock the store hooks and embedding to avoid side effects
        with patch("whitemagic.core.memory.unified._emit_store_hooks"), \
             patch("whitemagic.core.memory.unified._get_gan_ying_event_type", return_value=None):
            mem = um.store("test content", agent_id="agent-Z")
            assert mem.agent_id == "agent-Z"
            assert mem.version == 1

            # Verify persisted
            recalled = tmp_db.recall(mem.id)
            assert recalled is not None
            assert recalled.agent_id == "agent-Z"
            assert recalled.version == 1

    def test_store_default_agent_id_empty(self, tmp_db):
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory.__new__(UnifiedMemory)
        um._galaxy_backend = tmp_db
        um.backend = tmp_db
        um._skip_holo = True
        um._holographic = None
        um._holographic_loaded = False
        um._holographic_lock = None

        with patch("whitemagic.core.memory.unified._emit_store_hooks"), \
             patch("whitemagic.core.memory.unified._get_gan_ying_event_type", return_value=None):
            mem = um.store("test content 2")
            assert mem.agent_id == ""
            assert mem.version == 1


# ---------------------------------------------------------------------------
# Concurrent Update Simulation Tests
# ---------------------------------------------------------------------------

class TestConcurrentUpdates:
    def test_two_agents_concurrent_update(self, tmp_db):
        """Simulate two agents updating the same memory concurrently."""
        from whitemagic.core.memory.unified import UnifiedMemory

        # Create two UnifiedMemory instances sharing the same backend
        def make_um():
            um = UnifiedMemory.__new__(UnifiedMemory)
            um._galaxy_backend = tmp_db
            um.backend = tmp_db
            um._skip_holo = True
            um._holographic = None
            um._holographic_loaded = False
            um._holographic_lock = None
            return um

        um_a = make_um()
        um_b = make_um()

        # Both start from version 1
        mem = _make_memory(mid="conc-1", version=1, agent_id="agent-A")
        tmp_db.store(mem)

        # Agent A reads (gets version=1)
        # Agent B reads (gets version=1)
        # Agent A writes first (version becomes 2)
        result_a = um_a.update_memory("conc-1", {"content": "A's update"}, agent_id="agent-A", expected_version=1)
        assert result_a["success"] is True
        assert result_a["version"] == 2

        # Agent B tries to write with stale expected_version=1 — should fail
        result_b = um_b.update_memory("conc-1", {"content": "B's update"}, agent_id="agent-B", expected_version=1)
        assert result_b["success"] is False
        assert result_b["error"] == "version_conflict"
        assert result_b["actual_version"] == 2

        # Agent B retries with correct version=2 — should succeed
        result_b2 = um_b.update_memory("conc-1", {"content": "B's update"}, agent_id="agent-B", expected_version=2)
        assert result_b2["success"] is True
        assert result_b2["version"] == 3

        # Verify final state
        recalled = tmp_db.recall("conc-1")
        assert recalled.version == 3
        assert recalled.agent_id == "agent-B"
        assert recalled.content == "B's update"
