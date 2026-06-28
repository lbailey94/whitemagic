"""Tests for Batch 4: Memory & Session modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestMemoryMatrix:
    """Test memory matrix."""

    def test_record_and_get(self, tmp_path):
        from whitemagic.memory_matrix.matrix import MemoryMatrix
        mm = MemoryMatrix(data_dir=tmp_path)
        mm.record_interaction("read_file", "/path/to/file.md")
        interactions = mm.get_interactions()
        assert len(interactions) == 1
        assert interactions[0]["action"] == "read_file"

    def test_find_connections(self, tmp_path):
        from whitemagic.memory_matrix.matrix import MemoryMatrix
        mm = MemoryMatrix(data_dir=tmp_path)
        mm.record_interaction("read_file", "/path/to/important.md")
        mm.record_interaction("write_file", "/path/to/other.txt")
        connections = mm.find_connections("important")
        assert len(connections) == 1

    def test_summary(self, tmp_path):
        from whitemagic.memory_matrix.matrix import MemoryMatrix
        mm = MemoryMatrix(data_dir=tmp_path)
        mm.record_interaction("read", "a")
        summary = mm.summary()
        assert summary["total_interactions"] == 1


class TestSeenRegistry:
    """Test seen registry."""

    def test_mark_seen_new(self, tmp_path):
        from whitemagic.memory_matrix.seen_registry import SeenRegistry
        reg = SeenRegistry(data_dir=tmp_path)
        assert reg.mark_seen("/path/to/file.md") is True

    def test_mark_seen_already(self, tmp_path):
        from whitemagic.memory_matrix.seen_registry import SeenRegistry
        reg = SeenRegistry(data_dir=tmp_path)
        reg.mark_seen("/path/to/file.md")
        assert reg.mark_seen("/path/to/file.md") is False

    def test_has_seen(self, tmp_path):
        from whitemagic.memory_matrix.seen_registry import SeenRegistry
        reg = SeenRegistry(data_dir=tmp_path)
        reg.mark_seen("/path/to/file.md")
        assert reg.has_seen("/path/to/file.md") is True
        assert reg.has_seen("/other") is False


class TestTimeline:
    """Test chronological timeline."""

    def test_add_and_get(self, tmp_path):
        from whitemagic.memory_matrix.timeline import ChronologicalTimeline
        tl = ChronologicalTimeline(data_dir=tmp_path)
        tl.add_event("session_start", {"topic": "test"})
        events = tl.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "session_start"

    def test_filter_by_type(self, tmp_path):
        from whitemagic.memory_matrix.timeline import ChronologicalTimeline
        tl = ChronologicalTimeline(data_dir=tmp_path)
        tl.add_event("type_a")
        tl.add_event("type_b")
        tl.add_event("type_a")
        filtered = tl.get_events(event_type="type_a")
        assert len(filtered) == 2


class TestEmbeddingIndex:
    """Test embedding index."""

    def test_add_and_search(self, tmp_path):
        from whitemagic.memory_matrix.embedding_index import EmbeddingIndex
        idx = EmbeddingIndex(data_dir=tmp_path)
        idx.add("1", "hello world from white magic")
        idx.add("2", "completely different content about cooking")
        results = idx.search("hello world")
        assert len(results) > 0
        assert results[0]["id"] == "1"

    def test_remove(self, tmp_path):
        from whitemagic.memory_matrix.embedding_index import EmbeddingIndex
        idx = EmbeddingIndex(data_dir=tmp_path)
        idx.add("1", "test content")
        assert idx.remove("1") is True
        results = idx.search("test")
        assert len(results) == 0


class TestSessionBootstrap:
    """Test session bootstrap."""

    def test_bootstrap(self):
        from whitemagic.session.bootstrap import SessionBootstrap
        sb = SessionBootstrap()
        ctx = sb.bootstrap("test-session")
        assert ctx.session_id == "test-session"
        assert ctx.started_at > 0

    def test_quick_bootstrap(self):
        from whitemagic.session.bootstrap import quick_bootstrap
        ctx = quick_bootstrap()
        assert ctx.session_id != ""


class TestSessionManifest:
    """Test session manifest."""

    def test_create_manifest(self):
        from whitemagic.session.manifest import create_manifest
        manifest = create_manifest(goals=["test goal 1", "test goal 2"])
        assert len(manifest.goals) == 2
        assert manifest.created_at > 0

    def test_update(self):
        from whitemagic.session.manifest import SessionManifest
        m = SessionManifest(session_id="test")
        m.update(notes="updated notes")
        assert m.notes == "updated notes"


class TestStateClient:
    """Test state client."""

    def test_set_and_get(self, tmp_path):
        from whitemagic.session.state_client import StateClient
        client = StateClient(data_dir=tmp_path)
        client.sync_state("key1", "value1")
        assert client.get_state("key1") == "value1"

    def test_register_interface(self, tmp_path):
        from whitemagic.session.state_client import StateClient
        client = StateClient(data_dir=tmp_path)
        client.register_interface("windsurf")
        summary = client.summary()
        assert "windsurf" in summary["interfaces"]


class TestSessionSeenRegistry:
    """Test session seen registry."""

    def test_mark_and_check(self):
        from whitemagic.session.seen_registry import SessionSeenRegistry
        reg = SessionSeenRegistry()
        assert reg.mark_seen("/file1") is True
        assert reg.mark_seen("/file1") is False
        assert reg.has_seen("/file1") is True
        assert reg.has_seen("/file2") is False


class TestSQLiteBackend:
    """Test SQLite backend."""

    def test_set_and_get(self, tmp_path):
        from whitemagic.core.storage.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(data_dir=tmp_path)
        backend.set("key1", {"nested": "value"})
        assert backend.get("key1") == {"nested": "value"}

    def test_delete(self, tmp_path):
        from whitemagic.core.storage.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(data_dir=tmp_path)
        backend.set("key1", "value")
        assert backend.delete("key1") is True
        assert backend.get("key1") is None

    def test_keys(self, tmp_path):
        from whitemagic.core.storage.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(data_dir=tmp_path)
        backend.set("test_key1", "v1")
        backend.set("test_key2", "v2")
        keys = backend.keys("test_%")
        assert len(keys) == 2

    def test_log_and_get_events(self, tmp_path):
        from whitemagic.core.storage.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(data_dir=tmp_path)
        backend.log_event("test_event", source="test", data={"x": 1})
        events = backend.recent_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"
