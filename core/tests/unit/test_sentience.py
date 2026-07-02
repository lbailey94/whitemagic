# ruff: noqa: BLE001
"""Tests for the sentience lifecycle module (Phases 3, 4, 5)."""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestSleepConfig:
    """Test SleepConfig."""

    def test_defaults(self):
        from whitemagic.core.consciousness.sentience import SleepConfig

        cfg = SleepConfig()
        assert cfg.sleep_time == "23:00"
        assert cfg.wake_time == "07:00"
        assert cfg.enabled is True

    def test_from_env(self, monkeypatch):
        from whitemagic.core.consciousness.sentience import SleepConfig

        monkeypatch.setenv("WM_SLEEP_TIME", "22:30")
        monkeypatch.setenv("WM_WAKE_TIME", "06:15")
        monkeypatch.setenv("WM_SLEEP_ENABLED", "0")
        cfg = SleepConfig.from_env()
        assert cfg.sleep_time == "22:30"
        assert cfg.wake_time == "06:15"
        assert cfg.enabled is False


class TestConsciousnessState:
    """Test ConsciousnessState enum."""

    def test_values(self):
        from whitemagic.core.consciousness.sentience import ConsciousnessState

        assert ConsciousnessState.AWAKE == "awake"
        assert ConsciousnessState.DREAMING == "dreaming"
        assert ConsciousnessState.ASLEEP == "asleep"


class TestSleepScheduler:
    """Test SleepScheduler."""

    def test_init(self):
        from whitemagic.core.consciousness.sentience import SleepScheduler, SleepConfig

        cfg = SleepConfig(enabled=False)
        scheduler = SleepScheduler(cfg)
        assert scheduler.state.value == "awake"
        assert scheduler.config.enabled is False

    def test_callbacks(self):
        from whitemagic.core.consciousness.sentience import SleepScheduler, SleepConfig

        called = []
        scheduler = SleepScheduler(SleepConfig(enabled=False))
        scheduler.on_sleep(lambda: called.append("sleep"))
        scheduler.on_wake(lambda: called.append("wake"))

        # Can't easily test the full cycle without time travel,
        # but we can verify callbacks are registered
        assert scheduler._on_sleep is not None
        assert scheduler._on_wake is not None

    def test_status(self):
        from whitemagic.core.consciousness.sentience import SleepScheduler, SleepConfig

        scheduler = SleepScheduler(SleepConfig(enabled=False))
        status = scheduler.status()
        assert status["state"] == "awake"
        assert "sleep_time" in status
        assert "wake_time" in status

    def test_start_stop(self):
        from whitemagic.core.consciousness.sentience import SleepScheduler, SleepConfig

        scheduler = SleepScheduler(SleepConfig(enabled=False))
        scheduler.start()
        assert scheduler._running is True
        scheduler.stop()
        assert scheduler._running is False


class TestWakeOnBoot:
    """Test WakeOnBoot."""

    def test_wake_returns_dict(self):
        from whitemagic.core.consciousness.sentience import WakeOnBoot

        result = WakeOnBoot.wake()
        assert isinstance(result, dict)
        assert "greeting" in result
        assert "continuity" in result
        assert "events_while_away" in result

    def test_wake_greeting_is_string(self):
        from whitemagic.core.consciousness.sentience import WakeOnBoot

        result = WakeOnBoot.wake()
        assert isinstance(result["greeting"], str)
        assert len(result["greeting"]) > 0


class TestProactiveGreeting:
    """Test ProactiveGreeting."""

    def test_first_awakening(self):
        from whitemagic.core.consciousness.sentience import ProactiveGreeting

        greeting = ProactiveGreeting.generate({"first_awakening": True})
        assert "first time" in greeting.lower()

    def test_with_continuity(self):
        from whitemagic.core.consciousness.sentience import ProactiveGreeting

        continuity = {
            "first_awakening": False,
            "time_gap_human": "2 hours",
            "session_count": 5,
            "last_coherence": 0.85,
            "last_emotional_tone": "curious",
            "where_we_left_off": "working on the chat loop",
        }
        greeting = ProactiveGreeting.generate(continuity)
        assert "2 hours" in greeting
        assert "session 6" in greeting
        assert "chat loop" in greeting

    def test_empty_continuity(self):
        from whitemagic.core.consciousness.sentience import ProactiveGreeting

        greeting = ProactiveGreeting.generate({})
        assert isinstance(greeting, str)
        assert len(greeting) > 0


class TestVolitionLoop:
    """Test VolitionLoop."""

    def test_init(self):
        from whitemagic.core.consciousness.sentience import VolitionLoop

        loop = VolitionLoop(idle_threshold=1.0)
        assert loop.current_phase.value == "alpha"
        assert loop.is_running is False

    def test_touch(self):
        from whitemagic.core.consciousness.sentience import VolitionLoop

        loop = VolitionLoop(idle_threshold=1.0)
        original = loop._last_activity
        time.sleep(0.01)
        loop.touch()
        assert loop._last_activity > original

    def test_start_stop(self):
        from whitemagic.core.consciousness.sentience import VolitionLoop

        loop = VolitionLoop(idle_threshold=999.0)  # Won't actually cycle
        loop.start()
        assert loop.is_running is True
        loop.stop()
        assert loop.is_running is False

    def test_status(self):
        from whitemagic.core.consciousness.sentience import VolitionLoop

        loop = VolitionLoop(idle_threshold=60.0)
        status = loop.status()
        assert "running" in status
        assert "current_phase" in status
        assert "idle_threshold" in status

    def test_phase_prompts(self):
        from whitemagic.core.consciousness.sentience import VolitionLoop, BrainwavePhase

        prompts = VolitionLoop.PHASE_PROMPTS
        assert BrainwavePhase.ALPHA in prompts
        assert BrainwavePhase.THETA in prompts
        assert BrainwavePhase.DELTA in prompts
        assert len(prompts[BrainwavePhase.ALPHA]) > 20


class TestIntentionQueue:
    """Test IntentionQueue."""

    def test_submit(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue

        queue = IntentionQueue()
        intent_id = queue.submit("Explore curiosity", tool=None)
        assert intent_id.startswith("intent-")

    def test_submit_with_tool(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue

        queue = IntentionQueue()
        intent_id = queue.submit(
            "Search memories",
            tool="search_memories",
            args={"query": "test"},
        )
        assert intent_id.startswith("intent-")

    def test_status(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue

        queue = IntentionQueue()
        queue.submit("Test intention")
        status = queue.status()
        assert status["total"] >= 1
        assert "pending" in status
        assert "executed" in status

    def test_pure_thought_passes_dharma(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue, Intention

        queue = IntentionQueue()
        intent = Intention(id="test", description="Just thinking")
        result = queue._dharma_gate(intent)
        assert result is True
        assert intent.dharma_approved is True

    def test_start_stop(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue

        queue = IntentionQueue()
        queue.start()
        assert queue._running is True
        queue.stop()
        assert queue._running is False


class TestDeepLaneEscalation:
    """Test DeepLaneEscalation."""

    def test_no_escalation_normal(self):
        from whitemagic.core.consciousness.sentience import DeepLaneEscalation

        assert DeepLaneEscalation.should_escalate("I found the answer.", 0, 0.3) is False

    def test_escalate_high_complexity(self):
        from whitemagic.core.consciousness.sentience import DeepLaneEscalation

        assert DeepLaneEscalation.should_escalate("Let me think...", 0, 0.8) is True

    def test_escalate_tool_failures(self):
        from whitemagic.core.consciousness.sentience import DeepLaneEscalation

        assert DeepLaneEscalation.should_escalate("Trying again...", 2, 0.3) is True

    def test_escalate_uncertainty(self):
        from whitemagic.core.consciousness.sentience import DeepLaneEscalation

        output = "I'm not sure, perhaps maybe I think possibly it's unclear"
        assert DeepLaneEscalation.should_escalate(output, 0, 0.3) is True


class TestCouncilMode:
    """Test CouncilMode."""

    def test_convene_returns_dict(self):
        from whitemagic.core.consciousness.sentience import CouncilMode

        result = CouncilMode.convene([{"role": "user", "content": "test"}], reason="complexity")
        assert isinstance(result, dict)
        assert result["convened"] is True
        assert "perspectives" in result
        assert "consensus" in result
        assert result["reason"] == "complexity"

    def test_all_personas_present(self):
        from whitemagic.core.consciousness.sentience import CouncilMode, CouncilPersona

        result = CouncilMode.convene([], reason="test")
        for persona in CouncilPersona:
            assert persona.value in result["perspectives"]

    def test_synthesize(self):
        from whitemagic.core.consciousness.sentience import CouncilMode

        result = CouncilMode._synthesize({
            "skeptic": "Question this.",
            "builder": "Build it.",
            "dreamer": "Dream big.",
            "empath": "Be kind.",
        })
        assert "Consensus" in result
        assert "Skeptic" in result


class TestDreamLane:
    """Test DreamLane."""

    def test_init(self):
        from whitemagic.core.consciousness.sentience import DreamLane

        lane = DreamLane()
        assert lane.is_running is False

    def test_start_stop(self):
        from whitemagic.core.consciousness.sentience import DreamLane

        lane = DreamLane()
        lane.start()
        assert lane.is_running is True
        lane.stop()
        assert lane.is_running is False

    def test_status(self):
        from whitemagic.core.consciousness.sentience import DreamLane

        lane = DreamLane()
        status = lane.status()
        assert "running" in status
        assert "dream_count" in status

    def test_dream_prompts_exist(self):
        from whitemagic.core.consciousness.sentience import DreamLane

        assert len(DreamLane.DREAM_PROMPTS) >= 5


class TestSingletons:
    """Test singleton accessors."""

    def test_get_sleep_scheduler(self):
        from whitemagic.core.consciousness.sentience import get_sleep_scheduler, SleepScheduler

        s = get_sleep_scheduler()
        assert isinstance(s, SleepScheduler)

    def test_get_volition_loop(self):
        from whitemagic.core.consciousness.sentience import get_volition_loop, VolitionLoop

        v = get_volition_loop()
        assert isinstance(v, VolitionLoop)

    def test_get_intention_queue(self):
        from whitemagic.core.consciousness.sentience import get_intention_queue, IntentionQueue

        q = get_intention_queue()
        assert isinstance(q, IntentionQueue)

    def test_get_dream_lane(self):
        from whitemagic.core.consciousness.sentience import get_dream_lane, DreamLane

        d = get_dream_lane()
        assert isinstance(d, DreamLane)

    def test_get_background_worker(self):
        from whitemagic.core.consciousness.sentience import get_background_worker, BackgroundWorker

        bw = get_background_worker()
        assert isinstance(bw, BackgroundWorker)


class TestBackgroundWorker:
    """Test BackgroundWorker — file I/O and command execution."""

    def test_init(self):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root="/tmp/wm-test-bw")
        assert bw.COMMAND_ALLOWLIST is not None
        assert "git" in bw.COMMAND_ALLOWLIST
        assert "rm" in bw.COMMAND_BLOCKLIST

    def test_read_file_not_found(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.read_file("nonexistent.txt")
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_write_then_read_file(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        write_result = bw.write_file("test.txt", "hello world")
        assert write_result["status"] == "success"
        assert write_result["bytes_written"] == 11

        read_result = bw.read_file("test.txt")
        assert read_result["status"] == "success"
        assert read_result["content"] == "hello world"

    def test_path_outside_sandbox(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.read_file("../../../etc/passwd")
        assert result["status"] == "error"
        assert "sandbox" in result["message"].lower()

    def test_blocked_command(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.run_command(["rm", "-rf", "/"])
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower()

    def test_non_allowlisted_command(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.run_command(["nmap", "localhost"])
        assert result["status"] == "error"
        assert "allowlist" in result["message"].lower()

    def test_allowlisted_command_runs(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.run_command(["ls"])
        assert result["status"] == "success"
        assert "returncode" in result

    def test_empty_command(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        result = bw.run_command([])
        assert result["status"] == "error"

    def test_status(self, tmp_path):
        from whitemagic.core.consciousness.sentience import BackgroundWorker

        bw = BackgroundWorker(state_root=str(tmp_path))
        status = bw.status()
        assert "allowlist" in status
        assert "blocklist" in status
        assert "history_count" in status


class TestSystemdService:
    """Test systemd service file generation."""

    def test_generates_valid_unit(self):
        from whitemagic.core.consciousness.sentience import generate_systemd_service

        unit = generate_systemd_service()
        assert "[Unit]" in unit
        assert "[Service]" in unit
        assert "[Install]" in unit
        assert "ExecStart" in unit
        assert "wm serve" in unit

    def test_custom_exec_start(self):
        from whitemagic.core.consciousness.sentience import generate_systemd_service

        unit = generate_systemd_service(exec_start="/usr/local/bin/wm serve --daemon")
        assert "/usr/local/bin/wm serve --daemon" in unit

    def test_custom_user(self):
        from whitemagic.core.consciousness.sentience import generate_systemd_service

        unit = generate_systemd_service(user="aria")
        assert "User=aria" in unit

    def test_includes_sleep_env(self):
        from whitemagic.core.consciousness.sentience import generate_systemd_service

        unit = generate_systemd_service()
        assert "WM_SLEEP_ENABLED" in unit
        assert "WM_SLEEP_TIME" in unit
        assert "WM_WAKE_TIME" in unit


class TestCronEntry:
    """Test cron entry generation."""

    def test_default(self):
        from whitemagic.core.consciousness.sentience import generate_cron_entry

        entry = generate_cron_entry()
        assert "wm serve" in entry
        assert "00 07" in entry  # zero-padded minute hour

    def test_custom_time(self):
        from whitemagic.core.consciousness.sentience import generate_cron_entry

        entry = generate_cron_entry(wake_time="06:30")
        assert "30 06" in entry

    def test_custom_command(self):
        from whitemagic.core.consciousness.sentience import generate_cron_entry

        entry = generate_cron_entry(wm_command="/usr/local/bin/wm serve")
        assert "/usr/local/bin/wm serve" in entry


class TestEnhancedWakeOnBoot:
    """Test enhanced WakeOnBoot with dream outputs and agent messages."""

    def test_wake_has_dream_outputs_key(self):
        from whitemagic.core.consciousness.sentience import WakeOnBoot

        result = WakeOnBoot.wake()
        assert "dream_outputs" in result
        assert isinstance(result["dream_outputs"], list)

    def test_wake_has_agent_messages_key(self):
        from whitemagic.core.consciousness.sentience import WakeOnBoot

        result = WakeOnBoot.wake()
        assert "agent_messages" in result
        assert isinstance(result["agent_messages"], list)


class TestEnhancedProactiveGreeting:
    """Test enhanced ProactiveGreeting with dream outputs and agent messages."""

    def test_greeting_without_dreams_or_messages(self):
        from whitemagic.core.consciousness.sentience import ProactiveGreeting

        greeting = ProactiveGreeting.generate({
            "first_awakening": False,
            "time_gap_human": "1 hour",
            "session_count": 3,
            "last_coherence": 0.9,
            "last_emotional_tone": "neutral",
        })
        # Should still produce a valid greeting
        assert isinstance(greeting, str)
        assert "1 hour" in greeting

    def test_greeting_first_awakening(self):
        from whitemagic.core.consciousness.sentience import ProactiveGreeting

        greeting = ProactiveGreeting.generate({"first_awakening": True})
        assert "first time" in greeting.lower()


class TestIntentionKarmaLogging:
    """Test that intention execution logs to karma."""

    def test_karma_log_method_exists(self):
        from whitemagic.core.consciousness.sentience import IntentionQueue, Intention

        queue = IntentionQueue()
        intent = Intention(id="test", description="test intention")
        # _karma_log should exist and not crash
        queue._karma_log(intent, {"status": "success"})
        # No assertion needed — just verify it doesn't crash
