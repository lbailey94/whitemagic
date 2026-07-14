"""Tests for CurrentStateTracker and state MCP tools."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# We need to patch WM_ROOT before importing current_state
_TMP_ROOT: Path | None = None


@pytest.fixture(autouse=True)
def _tmp_state_dir(tmp_path, monkeypatch):
    """Use a temp directory for state files during tests."""
    global _TMP_ROOT
    _TMP_ROOT = tmp_path

    # Patch WM_ROOT in current_state module
    import whitemagic.core.memory.current_state as cs_mod
    monkeypatch.setattr(cs_mod, "WM_ROOT", tmp_path)
    monkeypatch.setattr(cs_mod, "_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cs_mod, "_STATE_FILE", tmp_path / "state" / "current_state.json")
    monkeypatch.setattr(cs_mod, "_WM_FILE", tmp_path / "state" / "working_memory.json")

    # Reset singleton
    cs_mod.CurrentStateTracker._instance = None

    yield

    # Cleanup
    cs_mod.CurrentStateTracker._instance = None


class TestCurrentState:
    """Test the CurrentState dataclass."""

    def test_default_state(self):
        from whitemagic.core.memory.current_state import CurrentState

        state = CurrentState()
        assert state.current_task == ""
        assert state.active_tasks == []
        assert state.next_steps == []
        assert state.recent_files == []
        assert state.context == {}

    def test_to_dict_roundtrip(self):
        from whitemagic.core.memory.current_state import CurrentState

        state = CurrentState(
            current_task="Fixing memory bug",
            active_tasks=["audit", "fix"],
            next_steps=["test", "deploy"],
            context={"branch": "main"},
        )
        d = state.to_dict()
        assert d["current_task"] == "Fixing memory bug"
        assert d["active_tasks"] == ["audit", "fix"]
        assert d["next_steps"] == ["test", "deploy"]
        assert d["context"]["branch"] == "main"

        restored = CurrentState.from_dict(d)
        assert restored.current_task == "Fixing memory bug"
        assert restored.active_tasks == ["audit", "fix"]

    def test_context_block_formatting(self):
        from whitemagic.core.memory.current_state import CurrentState

        state = CurrentState(
            current_task="Improving memory systems",
            active_tasks=["Audit architecture", "Fix short-term memory"],
            next_steps=["Test improvements", "Deploy"],
            recent_files=[{"path": "/tmp/test.py", "timestamp": "2026-07-12T22:00:00Z"}],
            last_session_summary="Worked on memory improvements",
        )
        block = state.to_context_block()
        assert "Improving memory systems" in block
        assert "Audit architecture" in block
        assert "Test improvements" in block
        assert "/tmp/test.py" in block
        assert "Worked on memory improvements" in block
        assert "state.current" in block


class TestCurrentStateTracker:
    """Test the CurrentStateTracker singleton."""

    def test_singleton(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        t1 = get_state_tracker()
        t2 = get_state_tracker()
        assert t1 is t2

    def test_set_current_task(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.set_current_task("Fix memory bug")
        state = tracker.get_state()
        assert state["current_task"] == "Fix memory bug"
        assert state["current_task_started"] != ""

    def test_complete_task(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.set_current_task("Fix memory bug")
        tracker.add_active_task("Fix memory bug")
        tracker.complete_task("Fix memory bug")
        state = tracker.get_state()
        assert state["current_task"] == ""
        assert "Fix memory bug" not in state["active_tasks"]

    def test_add_next_step(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.add_next_step("Write tests")
        tracker.add_next_step("Deploy")
        state = tracker.get_state()
        assert "Write tests" in state["next_steps"]
        assert "Deploy" in state["next_steps"]

    def test_record_file_modification(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.record_file_modification("/tmp/test.py", "Added new function")
        state = tracker.get_state()
        assert len(state["recent_files"]) == 1
        assert state["recent_files"][0]["path"] == "/tmp/test.py"
        assert state["recent_files"][0]["description"] == "Added new function"

    def test_record_file_dedup(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.record_file_modification("/tmp/test.py", "First edit")
        tracker.record_file_modification("/tmp/test.py", "Second edit")
        state = tracker.get_state()
        assert len(state["recent_files"]) == 1
        assert state["recent_files"][0]["description"] == "Second edit"

    def test_set_context(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.set_context("branch", "feature/memory")
        tracker.set_context("version", "24.3.0")
        state = tracker.get_state()
        assert state["context"]["branch"] == "feature/memory"
        assert state["context"]["version"] == "24.3.0"

    def test_record_decision(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.record_decision("Use CurrentStateTracker over .md files", "More dynamic")
        state = tracker.get_state()
        assert any(e["event_type"] == "decision" for e in state["recent_events"])

    def test_record_error(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.record_error("Import failed", "Missing module")
        state = tracker.get_state()
        assert any(e["event_type"] == "error" for e in state["recent_events"])

    def test_persistence(self):
        from whitemagic.core.memory.current_state import (
            CurrentStateTracker,
            get_state_tracker,
        )

        tracker = get_state_tracker()
        tracker.set_current_task("Persistent task")
        tracker.add_next_step("Step 1")

        # Reset singleton and reload
        CurrentStateTracker._instance = None
        tracker2 = get_state_tracker()
        state = tracker2.get_state()
        assert state["current_task"] == "Persistent task"
        assert "Step 1" in state["next_steps"]

    def test_update_from_session_handoff(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.update_from_session_handoff(
            summary="Fixed memory bugs",
            next_steps=["Test everything", "Deploy"],
            active_tasks=["Testing"],
            session_id="abc123",
            files_modified=["/tmp/file1.py"],
        )
        state = tracker.get_state()
        assert state["last_session_summary"] == "Fixed memory bugs"
        assert state["last_session_id"] == "abc123"
        assert "Test everything" in state["next_steps"]
        assert "Testing" in state["active_tasks"]

    def test_clear_next_steps(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.add_next_step("Step 1")
        tracker.add_next_step("Step 2")
        tracker.clear_next_steps()
        state = tracker.get_state()
        assert state["next_steps"] == []

    def test_recent_events_capped(self):
        from whitemagic.core.memory.current_state import (
            _MAX_RECENT_EVENTS,
            get_state_tracker,
        )

        tracker = get_state_tracker()
        for i in range(_MAX_RECENT_EVENTS + 10):
            tracker.record_decision(f"Decision {i}")
        state = tracker.get_state()
        assert len(state["recent_events"]) <= _MAX_RECENT_EVENTS

    def test_context_block_has_state_info(self):
        from whitemagic.core.memory.current_state import get_state_tracker

        tracker = get_state_tracker()
        tracker.set_current_task("Test task")
        tracker.add_next_step("Do thing")
        block = tracker.get_context_block()
        assert "Test task" in block
        assert "Do thing" in block


class TestStateMCPHandlers:
    """Test the MCP tool handlers."""

    def test_handle_state_current(self):
        from whitemagic.tools.handlers.state_tools import handle_state_current

        result = handle_state_current()
        assert result["status"] == "success"
        assert "state" in result
        assert "formatted" in result
        assert isinstance(result["state"], dict)

    def test_handle_state_update_current_task(self):
        from whitemagic.tools.handlers.state_tools import handle_state_update

        result = handle_state_update(current_task="Building tests")
        assert result["status"] == "success"
        assert "current_task: Building tests" in result["updates"]

    def test_handle_state_update_next_step(self):
        from whitemagic.tools.handlers.state_tools import handle_state_update

        result = handle_state_update(add_next_step="Run tests")
        assert result["status"] == "success"
        state = result["state"]
        assert "Run tests" in state["next_steps"]

    def test_handle_state_update_file(self):
        from whitemagic.tools.handlers.state_tools import handle_state_update

        result = handle_state_update(record_file="/tmp/test.py", file_description="New test")
        assert result["status"] == "success"
        state = result["state"]
        assert any(f["path"] == "/tmp/test.py" for f in state["recent_files"])

    def test_handle_state_context_get_all(self):
        from whitemagic.tools.handlers.state_tools import handle_state_context

        result = handle_state_context()
        assert result["status"] == "success"
        assert "context" in result

    def test_handle_state_context_set(self):
        from whitemagic.tools.handlers.state_tools import handle_state_context

        result = handle_state_context(key="test_key", value="test_value")
        assert result["status"] == "success"
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"

    def test_handle_state_context_get_specific(self):
        from whitemagic.tools.handlers.state_tools import handle_state_context

        # Set first
        handle_state_context(key="my_key", value="my_value")
        # Then get
        result = handle_state_context(key="my_key")
        assert result["status"] == "success"
        assert result["value"] == "my_value"

    def test_handle_state_update_no_args(self):
        from whitemagic.tools.handlers.state_tools import handle_state_update

        result = handle_state_update()
        assert result["status"] == "success"
        assert "No updates" in result["message"]


class TestSearchImprovements:
    """Test that search results include richer fields."""

    def test_search_returns_title_and_tags(self):
        """Verify search result format includes title, tags, galaxy, importance."""
        # Mock the recall function
        from unittest.mock import MagicMock

        from whitemagic.tools.handlers.memory import handle_search_memories

        mock_memory = MagicMock()
        mock_memory.id = "test-id-123"
        mock_memory.title = "Test Memory"
        mock_memory.content = "This is test content that is longer than 200 chars " + "x" * 250
        mock_memory.galaxy = "codex"
        mock_memory.tags = {"test", "unit"}
        mock_memory.importance = 0.8
        mock_memory.galactic_distance = 0.5
        mock_memory.is_private = False
        mock_memory.model_exclude = False

        with patch("whitemagic.core.memory.unified.recall", return_value=[mock_memory]):
            result = handle_search_memories(query="test")

        assert result["status"] == "success"
        assert result["count"] == 1
        mem = result["memories"][0]
        assert mem["title"] == "Test Memory"
        assert mem["galaxy"] == "codex"
        assert "test" in mem["tags"]
        assert mem["importance"] == 0.8

    def test_search_full_content_option(self):
        """Verify full_content option increases preview length."""
        from unittest.mock import MagicMock

        from whitemagic.tools.handlers.memory import handle_search_memories

        long_content = "A" * 600
        mock_memory = MagicMock()
        mock_memory.id = "test-id-456"
        mock_memory.title = "Long Memory"
        mock_memory.content = long_content
        mock_memory.galaxy = "codex"
        mock_memory.tags = set()
        mock_memory.importance = 0.5
        mock_memory.galactic_distance = 0.3
        mock_memory.is_private = False
        mock_memory.model_exclude = False

        with patch("whitemagic.core.memory.unified.recall", return_value=[mock_memory]):
            # Default (200 chars)
            result_default = handle_search_memories(query="test")
            # Full content (500 chars)
            result_full = handle_search_memories(query="test", full_content=True)

        default_content = result_default["memories"][0]["content"]
        full_content = result_full["memories"][0]["content"]
        assert len(default_content) == 200
        assert len(full_content) == 500


class TestSessionRecorderImprovements:
    """Test that session recorder middleware records meaningful content."""

    def test_meaningful_content_from_args(self):
        """Verify middleware extracts content from tool args."""
        from whitemagic.tools.middleware import DispatchContext, mw_session_recorder

        # Create a mock context
        ctx = DispatchContext(
            tool_name="create_memory",
            kwargs={"content": "Important decision about architecture"},
            meta={},
        )

        # Mock next_fn to return success
        def next_fn(ctx):
            return {"status": "success", "memory_id": "abc"}

        # Mock the recorder
        recorded_calls = []

        with patch("whitemagic.core.memory.session_recorder.get_session_recorder") as mock_recorder:
            recorder = mock_recorder.return_value
            recorder.record_ai = lambda content, turn_type, importance: recorded_calls.append((content, turn_type, importance))
            recorder.record_user = lambda **kw: recorded_calls.append((kw.get("content", ""), kw.get("turn_type", ""), kw.get("importance", 0)))

            mw_session_recorder(ctx, next_fn)

        # Verify meaningful content was recorded (not just "Tool: create_memory → success")
        assert any("Important decision about architecture" in str(c[0]) for c in recorded_calls)

    def test_file_modification_tracked(self):
        """Verify middleware auto-tracks file modifications in state."""
        from whitemagic.tools.middleware import DispatchContext, mw_session_recorder

        ctx = DispatchContext(
            tool_name="write_file",
            kwargs={"file_path": "/tmp/test_write.py", "content": "print('hello')"},
            meta={},
        )

        def next_fn(ctx):
            return {"status": "success"}

        with patch("whitemagic.core.memory.session_recorder.get_session_recorder") as mock_recorder, \
             patch("whitemagic.core.memory.current_state.get_state_tracker") as mock_tracker:
            mock_recorder.return_value.record_ai = MagicMock()
            mock_recorder.return_value.record_user = MagicMock()
            tracker = mock_tracker.return_value

            mw_session_recorder(ctx, next_fn)

            tracker.record_file_modification.assert_called_once_with(
                "/tmp/test_write.py",
                description="print('hello')",
            )
