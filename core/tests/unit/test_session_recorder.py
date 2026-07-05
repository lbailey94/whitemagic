"""Tests for SessionRecorder — chronological conversation memory."""

# ruff: noqa: BLE001
import os
import tempfile

import pytest

# Set temp state root BEFORE any whitemagic imports
_tmp = tempfile.mkdtemp(prefix="wm_sr_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"
os.environ["WM_SKIP_POLYGLOT"] = "1"


@pytest.fixture
def recorder(fresh_state_root):
    """Fresh SessionRecorder for each test (with isolated DB)."""
    from whitemagic.core.memory.session_recorder import SessionRecorder
    return SessionRecorder()


@pytest.fixture
def populated_recorder(recorder):
    """Recorder with 10 turns (5 user, 5 AI)."""
    for i in range(5):
        recorder.record_user(
            content=f"User message number {i}",
            turn_type="question" if i == 0 else "message",
            importance=0.3 + i * 0.1,
        )
        recorder.record_ai(
            content=f"AI response number {i}. Here is the answer to your question.",
            turn_type="answer" if i == 0 else "message",
            importance=0.4 + i * 0.1,
        )
    return recorder


class TestRecording:
    def test_record_user(self, recorder):
        mem_id = recorder.record_user("Hello world", turn_type="question")
        assert mem_id is not None
        assert len(mem_id) > 0
        assert recorder.sequence == 1

    def test_record_ai(self, recorder):
        mem_id = recorder.record_ai("Hi there!", turn_type="answer")
        assert mem_id is not None
        assert recorder.sequence == 1

    def test_sequence_increments(self, recorder):
        recorder.record_user("first")
        recorder.record_ai("second")
        recorder.record_user("third")
        assert recorder.sequence == 3

    def test_session_id_is_uuid(self, recorder):
        assert len(recorder.session_id) == 36  # UUID4 format

    def test_custom_session_id(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="my-custom-session")
        assert r.session_id == "my-custom-session"

    def test_tags_applied(self, recorder):
        mem_id = recorder.record_user("test", tags={"custom-tag"})
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory()
        mem = um.backend.recall(mem_id)
        assert mem is not None
        assert "user" in mem.tags
        assert f"session:{recorder.session_id}" in mem.tags
        assert "turn_type:message" in mem.tags
        assert "custom-tag" in mem.tags

    def test_metadata_stored(self, recorder):
        mem_id = recorder.record_ai("response", turn_type="decision", importance=0.9)
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory()
        mem = um.backend.recall(mem_id)
        assert mem is not None
        assert mem.metadata["session_id"] == recorder.session_id
        assert mem.metadata["sequence"] == 1
        assert mem.metadata["role"] == "ai"
        assert mem.metadata["turn_type"] == "decision"

    def test_galaxy_is_sessions(self, recorder):
        mem_id = recorder.record_user("test")
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory()
        mem = um.backend.recall(mem_id)
        assert mem is not None
        assert mem.galaxy == "sessions"

    def test_memory_type_is_citta(self, recorder):
        mem_id = recorder.record_user("test")
        from whitemagic.core.memory.unified import UnifiedMemory
        um = UnifiedMemory()
        mem = um.backend.recall(mem_id)
        assert mem is not None
        assert mem.memory_type.name == "CITTA"


class TestRecall:
    def test_recall_recent_returns_turns(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=5)
        assert len(turns) == 5
        # Should be in chronological order (oldest→newest)
        assert turns[0]["sequence"] < turns[-1]["sequence"]

    def test_recall_recent_limit(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=3)
        assert len(turns) == 3
        # Should be the last 3 turns
        assert turns[-1]["sequence"] == 10

    def test_recall_recent_empty(self, recorder):
        turns = recorder.recall_recent(n=10)
        assert turns == []

    def test_recall_has_role(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=10)
        roles = {t["role"] for t in turns}
        assert "user" in roles
        assert "ai" in roles

    def test_recall_has_content(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=2)
        assert "content" in turns[0]
        assert "User message" in turns[-1]["content"] or "AI response" in turns[-1]["content"]

    def test_recall_has_preview(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=1)
        assert "preview" in turns[0]
        assert len(turns[0]["preview"]) <= 200

    def test_recall_chronological_order(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=10)
        sequences = [t["sequence"] for t in turns]
        assert sequences == sorted(sequences)


class TestProgressiveRecall:
    def test_progressive_within_budget(self, populated_recorder):
        turns = populated_recorder.recall_progressive(token_budget=500)
        assert len(turns) > 0
        assert len(turns) <= 10
        # Each turn should have compact fields
        assert "title" in turns[0]
        assert "preview" in turns[0]

    def test_progressive_small_budget(self, populated_recorder):
        turns = populated_recorder.recall_progressive(token_budget=50)
        # Should fit only a few turns
        assert len(turns) <= 3

    def test_progressive_large_budget(self, populated_recorder):
        turns = populated_recorder.recall_progressive(token_budget=5000)
        # Should fit all 10 turns
        assert len(turns) == 10

    def test_progressive_empty(self, recorder):
        turns = recorder.recall_progressive(token_budget=2000)
        assert turns == []


class TestSelectiveRecall:
    def test_selective_by_importance(self, populated_recorder):
        turns = populated_recorder.recall_selective(min_importance=0.7)
        # Only turns with importance >= 0.7 (turns 5-10 roughly)
        assert all(t["importance"] >= 0.7 for t in turns)
        assert len(turns) > 0

    def test_selective_by_type(self, populated_recorder):
        turns = populated_recorder.recall_selective(
            turn_types=["question", "answer"],
            min_importance=0.0,
        )
        types = {t["turn_type"] for t in turns}
        assert types == {"question", "answer"}

    def test_selective_empty(self, recorder):
        turns = recorder.recall_selective(min_importance=0.9)
        assert turns == []


class TestQueryRecall:
    def test_query_recall(self, populated_recorder):
        turns = populated_recorder.recall_by_query("user message number 3", limit=5)
        assert len(turns) > 0
        assert "User message number 3" in turns[0]["content"]


class TestFormatContext:
    def test_format_compact(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=3)
        formatted = populated_recorder.format_context(turns, full=False)
        assert "[8]" in formatted or "[9]" in formatted or "[10]" in formatted
        assert "user/" in formatted or "ai/" in formatted

    def test_format_full(self, populated_recorder):
        turns = populated_recorder.recall_recent(n=2)
        formatted = populated_recorder.format_context(turns, full=True)
        assert "User message" in formatted or "AI response" in formatted

    def test_format_empty(self, recorder):
        formatted = recorder.format_context([])
        assert formatted == ""


class TestStats:
    def test_stats_basic(self, populated_recorder):
        stats = populated_recorder.get_stats()
        assert stats["total_turns"] == 10
        assert stats["sequence"] == 10
        assert "user" in stats["roles"]
        assert "ai" in stats["roles"]
        assert stats["roles"]["user"] == 5
        assert stats["roles"]["ai"] == 5

    def test_stats_empty(self, recorder):
        stats = recorder.get_stats()
        assert stats["total_turns"] == 0
        assert stats["sequence"] == 0


class TestBackfill:
    def test_backfill_assigns_sequences(self, recorder):
        # Create memories without sequence numbers by directly storing
        from whitemagic.core.memory.unified import UnifiedMemory
        from whitemagic.core.memory.unified_types import Memory, MemoryType
        from uuid import uuid4

        um = UnifiedMemory()
        for i in range(5):
            mem = Memory(
                id=str(uuid4()),
                content=f"Old memory {i}",
                memory_type=MemoryType.CITTA,
                title=f"old-{i}",
                galaxy="sessions",
                tags={"user", f"session:{recorder.session_id}"},
            )
            um.backend.store(mem)

        # Backfill
        updated = recorder.backfill_sequences()
        assert updated == 5

        # Verify sequences assigned
        turns = recorder.recall_recent(n=10)
        seqs = [t["sequence"] for t in turns]
        assert all(s > 0 for s in seqs)


class TestSingleton:
    def test_get_session_recorder(self):
        from whitemagic.core.memory.session_recorder import (
            get_session_recorder,
            reset_session_recorder,
        )
        reset_session_recorder()
        r1 = get_session_recorder()
        r2 = get_session_recorder()
        assert r1 is r2

    def test_custom_session_via_get(self):
        from whitemagic.core.memory.session_recorder import get_session_recorder
        r = get_session_recorder(session_id="test-123")
        assert r.session_id == "test-123"


class TestSequenceRestoration:
    def test_restores_sequence_on_reinit(self, populated_recorder):
        sid = populated_recorder.session_id
        seq = populated_recorder.sequence

        from whitemagic.core.memory.session_recorder import SessionRecorder
        r2 = SessionRecorder(session_id=sid)
        assert r2.sequence == seq


class TestCrossSessionContinuity:
    def test_continuity_finds_previous_session(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        # Create and populate a previous session
        prev = SessionRecorder(session_id="prev-session-1")
        prev.record_user("Hello from previous session", turn_type="message")
        prev.record_ai("Hi! Working on session memory", turn_type="answer")
        prev.record_user("Let's implement it", turn_type="decision", importance=0.9)

        # Create a new session
        new = SessionRecorder(session_id="new-session-2")
        result = new.get_continuity_turns(n=10)

        assert result["first_awakening"] is False
        assert result["previous_session_id"] == "prev-session-1"
        assert result["count"] == 3
        assert len(result["turns"]) == 3
        assert "formatted" in result
        assert "Hello from previous session" in result["formatted"]

    def test_continuity_first_awakening(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        # Use a unique session ID that won't have prior data
        r = SessionRecorder(session_id="lone-session-unique-xyz")
        result = r.get_continuity_turns(n=10)
        # In shared test DB, other sessions may exist from other tests.
        # The key assertion is that we don't find OURSELVES as a previous session.
        if result["previous_session_id"]:
            assert result["previous_session_id"] != "lone-session-unique-xyz"
        else:
            assert result["first_awakening"] is True
            assert result["count"] == 0

    def test_continuity_excludes_current_session(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="current-only-unique-abc")
        r.record_user("This is the current session", turn_type="message")
        result = r.get_continuity_turns(n=10)
        # Must not find itself as a previous session
        if result["previous_session_id"]:
            assert result["previous_session_id"] != "current-only-unique-abc"

    def test_continuity_limits_n(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        prev = SessionRecorder(session_id="prev-long-session-unique")
        for i in range(20):
            prev.record_user(f"Message {i}", turn_type="message")

        new = SessionRecorder(session_id="new-limited-unique")
        result = new.get_continuity_turns(n=5)
        # Should find some previous session and return at most 5 turns
        assert result["count"] <= 5
        if result["previous_session_id"] == "prev-long-session-unique":
            assert result["turns"][-1]["sequence"] == 20


class TestSleepConsolidation:
    def test_consolidate_dry_run(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="consolidate-dry-test")
        r.record_user("Let's build X", turn_type="decision", importance=0.9)
        r.record_ai("Working on it", turn_type="answer", importance=0.5)
        r.record_user("Found a bug!", turn_type="error", importance=0.8)
        r.record_ai("Fixed it", turn_type="message", importance=0.3)

        result = r.consolidate_session(min_importance=0.7, dry_run=True)

        assert result["dry_run"] is True
        assert result["promoted"] == 2  # decision + error, not answer/message
        types = [t["turn_type"] for t in result["turns_promoted"]]
        assert "decision" in types
        assert "error" in types
        assert "answer" not in types
        assert "message" not in types

    def test_consolidate_promotes_to_codex(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="consolidate-real-test")
        r.record_user("Important decision", turn_type="decision", importance=0.9)
        r.record_ai("Low importance reply", turn_type="message", importance=0.3)

        result = r.consolidate_session(min_importance=0.7, dry_run=False)

        assert result["dry_run"] is False
        assert result["promoted"] == 1
        assert result["turns_promoted"][0]["turn_type"] == "decision"
        assert "source_id" in result["turns_promoted"][0]

    def test_consolidate_skips_low_importance(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="consolidate-skip-test")
        r.record_user("Low importance", turn_type="decision", importance=0.3)
        r.record_user("High importance", turn_type="decision", importance=0.9)

        result = r.consolidate_session(min_importance=0.7, dry_run=True)

        assert result["promoted"] == 1
        assert result["turns_promoted"][0]["importance"] == 0.9

    def test_consolidate_skips_message_and_context_types(self):
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="consolidate-type-test")
        r.record_user("Just chatting", turn_type="message", importance=0.9)
        r.record_ai("Some context", turn_type="context", importance=0.9)
        r.record_user("A decision", turn_type="decision", importance=0.9)

        result = r.consolidate_session(min_importance=0.7, dry_run=True)

        assert result["promoted"] == 1
        assert result["turns_promoted"][0]["turn_type"] == "decision"


class TestEmotionalAutoTagging:
    def test_auto_emotional_valence_fallback(self):
        """When citta is unavailable, valence should default to 0.0."""
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="emotional-test")
        valence = r.get_auto_emotional_valence()
        # Should be 0.0 when citta cycle is not available
        assert valence == 0.0

    def test_record_user_auto_tags_valence(self):
        """record_user should auto-assign emotional_valence when not specified."""
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="emotional-auto-test")
        mem_id = r.record_user("Test message", turn_type="message")
        turns = r.recall_recent(n=1)
        assert len(turns) == 1
        # Should have some emotional_valence (0.0 when citta unavailable)
        assert "emotional_valence" in turns[0]
        assert turns[0]["emotional_valence"] == 0.0

    def test_explicit_valence_overrides_auto(self):
        """When emotional_valence is explicitly passed, it should override auto."""
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="emotional-explicit-test")
        r.record_user("Happy message", turn_type="message", emotional_valence=0.9)
        turns = r.recall_recent(n=1)
        assert turns[0]["emotional_valence"] == 0.9

    def test_tone_valence_mapping(self):
        """Test the emotional tone to valence mapping."""
        from whitemagic.core.memory.session_recorder import SessionRecorder
        r = SessionRecorder(session_id="tone-map-test")
        assert r._EMOTIONAL_TONE_VALENCE["sattvic"] == 0.7
        assert r._EMOTIONAL_TONE_VALENCE["grief"] == -0.7
        assert r._EMOTIONAL_TONE_VALENCE["neutral"] == 0.0
        assert r._EMOTIONAL_TONE_VALENCE["breakthrough"] == 0.8
