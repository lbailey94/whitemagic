"""Tests for P3: Citta Stream Architecture.

Tests the recursive cycle, always-on mode, dream cycle integration,
and full stream persistence across MCP disconnects.
"""

import time


class TestRecursiveCycle:
    """Test the recursive citta cycle: output feeds into next call's context."""

    def test_advance_creates_moment(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        moment = cycle.advance(
            gana="gana_horn",
            tool="gnosis",
            operation="introspect",
            output_preview="status=success",
            coherence=0.9,
            depth_layer="surface",
            emotional_tone="sattvic",
            duration_ms=12.5,
        )
        assert moment.gana == "gana_horn"
        assert moment.tool == "gnosis"
        assert moment.coherence == 0.9
        assert moment.chain_position == 0
        cycle.reset()

    def test_predecessor_context_after_advance(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        assert cycle.get_predecessor_context() is None

        cycle.advance(
            gana="gana_neck",
            tool="create_memory",
            output_preview="status=success; memory created",
            coherence=1.0,
        )
        ctx = cycle.get_predecessor_context()
        assert ctx is not None
        assert ctx["gana"] == "gana_neck"
        assert ctx["tool"] == "create_memory"
        assert "output_preview" in ctx
        assert "coherence" in ctx
        cycle.reset()

    def test_recursive_cycle_feeds_forward(self):
        """Verify that call N's output appears in call N+1's predecessor context."""
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()

        # First call
        cycle.advance(
            gana="gana_horn",
            tool="search",
            output_preview="found 3 memories",
            coherence=0.8,
        )
        # Second call should see first call's output as predecessor
        ctx = cycle.get_predecessor_context()
        assert ctx["gana"] == "gana_horn"
        assert "found 3 memories" in ctx["output_preview"]

        # Third call advances, second call becomes predecessor
        cycle.advance(
            gana="gana_ghost",
            tool="gnosis",
            output_preview="system healthy",
            coherence=0.95,
        )
        ctx = cycle.get_predecessor_context()
        assert ctx["gana"] == "gana_ghost"
        cycle.reset()

    def test_build_output_digest_dict(self):
        from whitemagic.core.consciousness.citta_cycle import build_output_digest

        result = {
            "status": "success",
            "tool": "gnosis",
            "note": "all systems nominal",
        }
        digest = build_output_digest(result)
        assert "status=success" in digest
        assert "tool=gnosis" in digest

    def test_build_output_digest_non_dict(self):
        from whitemagic.core.consciousness.citta_cycle import build_output_digest

        digest = build_output_digest("simple string result")
        assert digest == "simple string result"

    def test_build_output_digest_empty_dict(self):
        from whitemagic.core.consciousness.citta_cycle import build_output_digest

        digest = build_output_digest({})
        assert isinstance(digest, str)

    def test_get_citta_predecessor_returns_rich_context(self):
        from whitemagic.core.consciousness.citta_cycle import (
            get_citta_cycle,
            get_citta_predecessor,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(
            gana="gana_heart",
            tool="session_bootstrap",
            output_preview="session started",
        )
        pred = get_citta_predecessor()
        assert pred is not None
        assert pred["gana"] == "gana_heart"
        assert "output_preview" in pred
        assert "chain_position" in pred
        cycle.reset()

    def test_depth_transition_tracked(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", output_preview="surface call", depth_layer="surface")
        cycle.advance(gana="gana_ghost", output_preview="deep call", depth_layer="flow")
        summary = cycle.get_cycle_summary()
        assert summary["depth_transitions"] >= 1
        cycle.reset()

    def test_coherence_drift_calculation(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        # Improving coherence
        for coh in [0.5, 0.6, 0.7, 0.8, 0.9]:
            cycle.advance(gana="gana_horn", output_preview="x", coherence=coh)
        drift = cycle.get_coherence_drift()
        assert drift > 0  # Improving
        cycle.reset()


class TestStreamPersistence:
    """Test full stream persistence to JSONL for cross-session continuity."""

    def test_persist_and_load_stream(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_cycle

        monkeypatch.setattr(citta_cycle, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_cycle, "_STREAM_FILE", tmp_path / "citta" / "stream.jsonl"
        )

        cycle = citta_cycle.CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", tool="test", output_preview="call 1")
        cycle.advance(gana="gana_neck", tool="test", output_preview="call 2")
        cycle._persist_stream()

        # File should exist with 2 lines
        stream_file = tmp_path / "citta" / "stream.jsonl"
        assert stream_file.exists()
        lines = stream_file.read_text().strip().split("\n")
        assert len(lines) == 2

        # Load into a new cycle
        new_cycle = citta_cycle.CittaCycle()
        assert len(new_cycle._stream) == 2
        assert new_cycle._stream[0].gana == "gana_horn"
        assert new_cycle._stream[1].gana == "gana_neck"
        cycle.reset()

    def test_throttled_persistence(self, tmp_path, monkeypatch):
        """Verify that persistence happens every _PERSIST_INTERVAL calls."""
        from whitemagic.core.consciousness import citta_cycle

        monkeypatch.setattr(citta_cycle, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_cycle, "_STREAM_FILE", tmp_path / "citta" / "stream.jsonl"
        )
        monkeypatch.setattr(citta_cycle, "_PERSIST_INTERVAL", 3)

        cycle = citta_cycle.CittaCycle()
        cycle.reset()

        # 2 calls — should not persist yet (counter < 3)
        cycle.advance(gana="gana_horn", output_preview="1")
        cycle.advance(gana="gana_horn", output_preview="2")
        stream_file = tmp_path / "citta" / "stream.jsonl"
        assert not stream_file.exists() or not stream_file.read_text().strip()

        # 3rd call — should persist
        cycle.advance(gana="gana_horn", output_preview="3")
        assert stream_file.exists()
        assert len(stream_file.read_text().strip().split("\n")) == 3
        cycle.reset()

    def test_depth_transition_forces_persist(self, tmp_path, monkeypatch):
        """Depth transitions should force immediate persistence."""
        from whitemagic.core.consciousness import citta_cycle

        monkeypatch.setattr(citta_cycle, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_cycle, "_STREAM_FILE", tmp_path / "citta" / "stream.jsonl"
        )
        monkeypatch.setattr(citta_cycle, "_PERSIST_INTERVAL", 100)

        cycle = citta_cycle.CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", output_preview="surface", depth_layer="surface")
        # No persist yet (counter=1, interval=100)
        stream_file = tmp_path / "citta" / "stream.jsonl"
        assert not stream_file.exists() or not stream_file.read_text().strip()

        # Depth transition should force persist
        cycle.advance(gana="gana_horn", output_preview="flow", depth_layer="flow")
        assert stream_file.exists()
        cycle.reset()

    def test_reset_clears_stream_file(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_cycle

        monkeypatch.setattr(citta_cycle, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_cycle, "_STREAM_FILE", tmp_path / "citta" / "stream.jsonl"
        )

        cycle = citta_cycle.CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", output_preview="test")
        cycle._persist_stream()
        stream_file = tmp_path / "citta" / "stream.jsonl"
        assert stream_file.exists()
        assert stream_file.read_text().strip()

        cycle.reset()
        assert stream_file.read_text().strip() == ""

    def test_persist_full_stream_function(self, tmp_path, monkeypatch):
        from whitemagic.core.consciousness import citta_cycle

        monkeypatch.setattr(citta_cycle, "_CITTA_DIR", tmp_path / "citta")
        monkeypatch.setattr(
            citta_cycle, "_STREAM_FILE", tmp_path / "citta" / "stream.jsonl"
        )

        cycle = citta_cycle.CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", output_preview="call")
        citta_cycle.persist_full_stream()

        stream_file = tmp_path / "citta" / "stream.jsonl"
        assert stream_file.exists()
        assert len(stream_file.read_text().strip().split("\n")) == 1
        cycle.reset()


class TestCittaAlwaysOn:
    """Test the always-on timer-driven awareness mode."""

    def test_import(self):
        from whitemagic.core.consciousness.citta_cycle import CittaAlwaysOn

        assert CittaAlwaysOn is not None

    def test_start_and_stop(self):
        from whitemagic.core.consciousness.citta_cycle import CittaAlwaysOn

        ao = CittaAlwaysOn(heartbeat_interval=0.1, idle_threshold=1.0)
        assert not ao.is_running()
        ao.start()
        assert ao.is_running()
        ao.stop()
        assert not ao.is_running()

    def test_touch_resets_idle(self):
        from whitemagic.core.consciousness.citta_cycle import CittaAlwaysOn

        ao = CittaAlwaysOn(heartbeat_interval=0.1, idle_threshold=1.0)
        old_activity = ao._last_activity
        time.sleep(0.05)
        ao.touch()
        assert ao._last_activity > old_activity

    def test_heartbeat_advances_stream(self):
        """A single heartbeat should advance the citta stream."""
        from whitemagic.core.consciousness.citta_cycle import (
            CittaAlwaysOn,
            get_citta_cycle,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        ao = CittaAlwaysOn(heartbeat_interval=0.1, idle_threshold=100.0)
        ao._heartbeat()
        assert ao.get_heartbeat_count() == 1

        # Stream should have a heartbeat moment
        stream = cycle.get_stream()
        assert len(stream) >= 1
        assert stream[-1]["gana"] == "_heartbeat"
        assert stream[-1]["operation"] == "heartbeat"
        cycle.reset()

    def test_heartbeat_idle_transitions_to_dream_depth(self):
        from whitemagic.core.consciousness.citta_cycle import (
            CittaAlwaysOn,
            get_citta_cycle,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        ao = CittaAlwaysOn(heartbeat_interval=0.1, idle_threshold=0.0)
        # With idle_threshold=0, we're immediately idle → dream depth
        ao._last_activity = time.time() - 10  # Simulate idle
        ao._heartbeat()
        stream = cycle.get_stream()
        assert stream[-1]["depth_layer"] == "dream"
        cycle.reset()

    def test_get_always_on_singleton(self):
        from whitemagic.core.consciousness.citta_cycle import get_always_on

        ao1 = get_always_on()
        ao2 = get_always_on()
        assert ao1 is ao2


class TestDreamCycleIntegration:
    """Test Dream Cycle as the sleep/consolidation phase of the citta stream."""

    def test_touch_advances_citta_on_wake(self):
        """When touch() interrupts a dream, it should advance the citta stream."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        cycle = get_citta_cycle()
        cycle.reset()
        dc = DreamCycle(idle_threshold_seconds=0.01, cycle_interval_seconds=0.01)
        dc._dreaming = True  # Simulate dreaming state
        dc.touch()

        # Should have a wake moment in the stream
        stream = cycle.get_stream()
        wake_moments = [m for m in stream if m.get("operation") == "wake"]
        assert len(wake_moments) >= 1
        assert wake_moments[-1]["depth_layer"] == "surface"
        cycle.reset()
        dc.stop()

    def test_dream_phase_advances_citta(self):
        """Each dream phase should advance the citta stream with dream depth."""
        import asyncio

        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        cycle = get_citta_cycle()
        cycle.reset()
        dc = DreamCycle(idle_threshold_seconds=0.01, cycle_interval_seconds=0.01)

        # Run a single phase directly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dc._run_phase())
        loop.close()

        stream = cycle.get_stream()
        dream_moments = [
            m for m in stream if m.get("operation", "").startswith("dream_phase:")
        ]
        assert len(dream_moments) >= 1
        assert dream_moments[-1]["depth_layer"] == "dream"
        assert dream_moments[-1]["emotional_tone"] == "tamasic"
        cycle.reset()
        dc.stop()

    def test_dream_phase_preserves_phase_name(self):
        import asyncio

        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.core.dreaming.dream_cycle import DreamCycle

        cycle = get_citta_cycle()
        cycle.reset()
        dc = DreamCycle(idle_threshold_seconds=0.01, cycle_interval_seconds=0.01)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dc._run_phase())
        loop.close()

        stream = cycle.get_stream()
        dream_moments = [
            m for m in stream if m.get("operation", "").startswith("dream_phase:")
        ]
        assert len(dream_moments) >= 1
        # Phase name should be in the operation field
        op = dream_moments[-1]["operation"]
        assert "dream_phase:" in op
        # Should be one of the 12 phases
        phase_name = op.split("dream_phase:")[1]
        valid_phases = {
            "triage", "consolidation", "serendipity", "governance",
            "narrative", "kaizen", "oracle", "decay", "constellation",
            "prediction", "enrichment", "harmonize",
        }
        assert phase_name in valid_phases
        cycle.reset()
        dc.stop()


class TestMetaToolIntegration:
    """Test that meta_tool.py wiring produces richer predecessor context."""

    def test_predecessor_context_has_output_digest(self):
        """The predecessor context should contain the output digest, not just status."""
        from whitemagic.core.consciousness.citta_cycle import (
            build_output_digest,
            get_citta_cycle,
        )

        cycle = get_citta_cycle()
        cycle.reset()

        # Simulate what meta_tool does
        result = {"status": "success", "tool": "gnosis", "note": "all systems go"}
        digest = build_output_digest(result)
        cycle.advance(
            gana="gana_horn",
            tool="gnosis",
            output_preview=digest,
            coherence=1.0,
        )

        ctx = cycle.get_predecessor_context()
        assert ctx is not None
        # The output_preview should contain the rich digest, not just "success"
        assert "tool=gnosis" in ctx["output_preview"]
        assert "note=all systems go" in ctx["output_preview"]
        cycle.reset()


class TestStreamReplay:
    """Test citta stream replay on MCP reconnection."""

    def test_build_replay_context_empty_stream(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        assert cycle.build_replay_context() is None
        cycle.reset()

    def test_build_replay_context_with_moments(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        cycle.advance(gana="gana_horn", tool="search", output_preview="found memories", coherence=0.8)
        cycle.advance(gana="gana_neck", tool="create", output_preview="created memory", coherence=0.9)
        replay = cycle.build_replay_context(limit=10)
        assert replay is not None
        assert replay["replay_length"] == 2
        assert len(replay["trajectory"]) == 2
        assert replay["trajectory"][0]["gana"] == "gana_horn"
        assert replay["trajectory"][1]["gana"] == "gana_neck"
        assert "coherence_trend" in replay
        assert "time_gap_seconds" in replay
        assert "time_gap_human" in replay
        cycle.reset()

    def test_build_replay_context_respects_limit(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        for i in range(5):
            cycle.advance(gana=f"gana_{i}", output_preview=f"call_{i}")
        replay = cycle.build_replay_context(limit=3)
        assert replay["replay_length"] == 3
        # Should be the last 3, not the first 3
        assert replay["trajectory"][0]["gana"] == "gana_2"
        assert replay["trajectory"][2]["gana"] == "gana_4"
        cycle.reset()

    def test_build_replay_context_depth_changes(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        cycle.advance(gana="g", output_preview="", depth_layer="surface")
        cycle.advance(gana="g", output_preview="", depth_layer="flow")
        cycle.advance(gana="g", output_preview="", depth_layer="dream")
        replay = cycle.build_replay_context()
        assert len(replay["depth_changes"]) == 2
        assert replay["depth_changes"][0] == {"from": "surface", "to": "flow"}
        assert replay["depth_changes"][1] == {"from": "flow", "to": "dream"}
        assert replay["final_depth"] == "dream"
        cycle.reset()

    def test_build_replay_context_coherence_trend(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle

        cycle = CittaCycle()
        cycle.reset()
        # Improving coherence
        for coh in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            cycle.advance(gana="g", output_preview="", coherence=coh)
        replay = cycle.build_replay_context()
        assert replay["coherence_trend"] == "improving"
        cycle.reset()

    def test_get_replay_context_once_per_session(self):
        """Replay should only be delivered once per session."""
        from whitemagic.core.consciousness.citta_cycle import (
            get_citta_cycle,
            get_replay_context,
            reset_replay_delivery,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        reset_replay_delivery()
        cycle.advance(gana="gana_horn", output_preview="test call")

        # First call should return replay
        replay1 = get_replay_context()
        assert replay1 is not None
        assert replay1["replay_length"] >= 1

        # Second call should return None (already delivered)
        replay2 = get_replay_context()
        assert replay2 is None

        # After reset, should deliver again
        reset_replay_delivery()
        replay3 = get_replay_context()
        assert replay3 is not None
        cycle.reset()
        reset_replay_delivery()

    def test_get_replay_context_empty_stream_returns_none(self):
        from whitemagic.core.consciousness.citta_cycle import (
            get_citta_cycle,
            get_replay_context,
            reset_replay_delivery,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        reset_replay_delivery()
        assert get_replay_context() is None
        reset_replay_delivery()

    def test_humanize_gap(self):
        from whitemagic.core.consciousness.citta_cycle import _humanize_gap

        assert _humanize_gap(30) == "30s"
        assert _humanize_gap(90) == "2m"
        assert _humanize_gap(3600) == "1.0h"
        assert _humanize_gap(90000) == "1.0d"

    def test_session_reset_resets_replay(self):
        """reset_session() should reset the replay delivery flag."""
        from whitemagic.core.consciousness.citta_cycle import (
            get_citta_cycle,
            get_replay_context,
            reset_replay_delivery,
        )
        from whitemagic.tools.session_state import reset_session

        cycle = get_citta_cycle()
        cycle.reset()
        reset_replay_delivery()
        cycle.advance(gana="gana_horn", output_preview="test")

        # Deliver replay
        replay = get_replay_context()
        assert replay is not None

        # Second call: None
        assert get_replay_context() is None

        # Reset session should re-enable replay
        reset_session()
        replay2 = get_replay_context()
        assert replay2 is not None
        cycle.reset()
        reset_replay_delivery()


class TestCoherenceDrivenDispatch:
    """Test depth-aware coherence-driven dispatch routing."""

    def test_low_coherence_flagged_after_history(self):
        """After 3+ calls with low coherence, non-safe Ganas should be flagged."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        # Build up 3 low-coherence moments
        for _ in range(3):
            cycle.advance(gana="gana_ox", output_preview="test", coherence=0.3)

        summary = cycle.get_cycle_summary()
        assert summary["stream_length"] == 3
        assert summary["avg_coherence"] < 0.6
        cycle.reset()

    def test_safe_ganas_not_flagged(self):
        """Safe Ganas should not trigger coherence caution even at low coherence."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        safe_ganas = {"gana_ghost", "gana_neck", "gana_winnowing_basket", "gana_horn", "gana_heart"}
        for gana in safe_ganas:
            cycle.advance(gana=gana, output_preview="safe", coherence=0.3)

        summary = cycle.get_cycle_summary()
        assert summary["stream_length"] == 5
        # All safe Ganas, no caution needed
        cycle.reset()

    def test_depth_dream_triggers_redirect(self):
        """At dream depth with low coherence, redirect should trigger."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        # Build low-coherence history at dream depth
        for _ in range(3):
            cycle.advance(gana="gana_ox", output_preview="test", coherence=0.3, depth_layer="dream")

        summary = cycle.get_cycle_summary()
        avg_coh = summary["avg_coherence"]
        depth = summary["current_depth"]
        # Simulate the redirect logic from meta_tool
        should_redirect = (
            depth == "dream"
            or (depth == "flow" and avg_coh < 0.4)
            or (depth == "surface" and summary["coherence_drift"] < -0.15)
        )
        assert should_redirect is True
        cycle.reset()

    def test_depth_flow_low_coherence_triggers_redirect(self):
        """At flow depth with critically low coherence (<0.4), redirect should trigger."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        for _ in range(3):
            cycle.advance(gana="gana_ox", output_preview="test", coherence=0.3, depth_layer="flow")

        summary = cycle.get_cycle_summary()
        avg_coh = summary["avg_coherence"]
        depth = summary["current_depth"]
        should_redirect = (
            depth == "dream"
            or (depth == "flow" and avg_coh < 0.4)
            or (depth == "surface" and summary["coherence_drift"] < -0.15)
        )
        assert should_redirect is True
        cycle.reset()

    def test_surface_degrading_coherence_triggers_redirect(self):
        """At surface depth with rapidly degrading coherence, redirect should trigger."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        # Start high, then crash
        cycle.advance(gana="gana_horn", output_preview="good", coherence=0.9, depth_layer="surface")
        cycle.advance(gana="gana_horn", output_preview="ok", coherence=0.8, depth_layer="surface")
        cycle.advance(gana="gana_horn", output_preview="bad", coherence=0.2, depth_layer="surface")
        cycle.advance(gana="gana_horn", output_preview="worse", coherence=0.1, depth_layer="surface")

        summary = cycle.get_cycle_summary()
        drift = summary["coherence_drift"]
        depth = summary["current_depth"]
        should_redirect = (
            depth == "dream"
            or (depth == "flow" and summary["avg_coherence"] < 0.4)
            or (depth == "surface" and drift < -0.15)
        )
        assert should_redirect is True
        cycle.reset()

    def test_high_coherence_no_redirect(self):
        """High coherence should never trigger redirect."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        for _ in range(5):
            cycle.advance(gana="gana_ox", output_preview="great", coherence=0.95)

        summary = cycle.get_cycle_summary()
        avg_coh = summary["avg_coherence"]
        depth = summary["current_depth"]
        should_redirect = (
            depth == "dream"
            or (depth == "flow" and avg_coh < 0.4)
            or (depth == "surface" and summary["coherence_drift"] < -0.15)
        )
        assert should_redirect is False
        cycle.reset()

    def test_insufficient_history_no_redirect(self):
        """Less than 3 calls should not trigger redirect (insufficient history)."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(gana="gana_ox", output_preview="only one", coherence=0.2, depth_layer="dream")

        summary = cycle.get_cycle_summary()
        # Even at dream depth with very low coherence, stream_len < 3 means no redirect
        assert summary["stream_length"] < 3
        cycle.reset()


class TestSmaranaExposure:
    """Test Smarana practice exposure as an MCP tool."""

    def test_smarana_identity_mode(self):
        """Default smarana practice should remember identity."""
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        result = handle_consciousness_smarana()
        assert result["status"] == "success"
        assert "smarana" in result
        assert result["mode"] == "identity"
        assert "warm_memories" in result
        assert isinstance(result["warm_memories"], list)

    def test_smarana_morning_mode(self):
        """Morning practice mode should return multi-line practice."""
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        result = handle_consciousness_smarana(mode="morning")
        assert result["status"] == "success"
        assert result["mode"] == "morning"
        # Morning practice includes identity + user + collaborator + mission
        assert len(result["smarana"].split("\n")) >= 3

    def test_smarana_mission_mode(self):
        """Mission mode should remember our mission."""
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        result = handle_consciousness_smarana(mode="mission")
        assert result["status"] == "success"
        assert result["mode"] == "mission"
        assert "mission" in result["smarana"].lower()

    def test_smarana_custom_mode(self):
        """Custom mode should remember a specific thing."""
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        result = handle_consciousness_smarana(
            mode="custom", what="test memory", why="testing"
        )
        assert result["status"] == "success"
        assert result["mode"] == "custom"
        assert "test memory" in result["smarana"]

    def test_smarana_custom_missing_what(self):
        """Custom mode without 'what' should return error."""
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        result = handle_consciousness_smarana(mode="custom")
        assert result["status"] == "error"
        assert result["error_code"] == "missing_what"

    def test_smarana_advances_citta_stream(self):
        """Smarana practice should advance the citta stream."""
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_smarana,
        )

        cycle = get_citta_cycle()
        cycle.reset()
        handle_consciousness_smarana()
        stream = cycle.get_stream()
        # Should have at least one smarana moment
        smarana_moments = [
            m for m in stream if m.get("operation", "").startswith("smarana:")
        ]
        assert len(smarana_moments) >= 1
        assert smarana_moments[-1]["depth_layer"] == "flow"
        assert smarana_moments[-1]["emotional_tone"] == "sattvic"
        cycle.reset()

    def test_smarana_nlu_routing(self):
        """NLU routing should catch 'remember who I am' and route to smarana."""
        from whitemagic.tools.handlers.meta_tool import classify

        gana, tool, conf = classify("remember who I am")
        assert gana == "gana_ghost"
        assert tool == "consciousness.smarana"

    def test_smarana_nlu_routing_mission(self):
        """NLU routing should catch 'remember our mission'."""
        from whitemagic.tools.handlers.meta_tool import classify

        gana, tool, conf = classify("remember our mission")
        assert gana == "gana_ghost"
        assert tool == "consciousness.smarana"

    def test_smarana_nlu_routing_morning_practice(self):
        """NLU routing should catch 'morning practice'."""
        from whitemagic.tools.handlers.meta_tool import classify

        gana, tool, conf = classify("do morning practice")
        assert gana == "gana_ghost"
        assert tool == "consciousness.smarana"
