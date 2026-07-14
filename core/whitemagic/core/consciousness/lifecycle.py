# ruff: noqa: BLE001
"""Sentience Lifecycle — sleep, wake, and proactive greeting.

Extracted from sentience.py as part of consciousness subsystem synthesis.

Phase 3 — Sleep & Wake:
  - SleepScheduler: At a configured time, initiates dream cycle → maintenance → shutdown
  - WakeOnBoot: On system start, recovers citta state, generates proactive greeting
  - ProactiveGreeting: Synthesizes "what happened while you were away"
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import atomic_write, file_lock

logger = logging.getLogger(__name__)

_SENTIENCE_DIR = WM_ROOT / "sentience"
_SENTIENCE_FILE = _SENTIENCE_DIR / "lifecycle.json"


# ── Phase 3: Sleep Scheduler ─────────────────────────────────────────


class ConsciousnessState(StrEnum):
    """States of the consciousness lifecycle."""

    AWAKE = "awake"
    DROWSY = "drowsy"  # approaching sleep time
    DREAMING = "dreaming"  # dream cycle running
    MAINTENANCE = "maintenance"  # post-dream maintenance
    ASLEEP = "asleep"  # shut down, waiting for wake


@dataclass
class SleepConfig:
    """Configuration for the sleep/wake cycle."""

    sleep_time: str = "23:00"  # HH:MM — when to start sleeping
    wake_time: str = "07:00"  # HH:MM — when to wake (for daemon mode)
    dream_duration_minutes: int = 30
    maintenance_duration_minutes: int = 10
    enabled: bool = True

    @classmethod
    def from_env(cls) -> SleepConfig:
        """Load config from environment variables."""
        return cls(
            sleep_time=os.getenv("WM_SLEEP_TIME", "23:00"),
            wake_time=os.getenv("WM_WAKE_TIME", "07:00"),
            dream_duration_minutes=int(os.getenv("WM_DREAM_DURATION_MIN", "30")),
            maintenance_duration_minutes=int(
                os.getenv("WM_MAINTENANCE_DURATION_MIN", "10")
            ),
            enabled=os.getenv("WM_SLEEP_ENABLED", "1") != "0",
        )

    @classmethod
    def from_file(cls) -> SleepConfig:
        """Load config from sentience directory."""
        cfg_path = _SENTIENCE_DIR / "sleep_config.json"
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                logger.debug("Failed to load sleep config, using defaults")
        return cls.from_env()

    def save(self) -> None:
        """Save config to sentience directory."""
        _SENTIENCE_DIR.mkdir(parents=True, exist_ok=True)
        cfg_path = _SENTIENCE_DIR / "sleep_config.json"
        with file_lock(cfg_path):
            atomic_write(cfg_path, json.dumps({
                k: getattr(self, k) for k in self.__dataclass_fields__
            }, indent=2))


class SleepScheduler:
    """Manages the sleep/wake cycle.

    At the configured sleep time:
    1. Enters DROWSY state (warns if interactive)
    2. Starts dream cycle (DREAMING state)
    3. Runs maintenance (MAINTENANCE state)
    4. Saves citta state and enters ASLEEP state

    At wake time (or on boot):
    1. Loads citta state
    2. Generates proactive greeting
    3. Enters AWAKE state
    """

    def __init__(self, config: SleepConfig | None = None) -> None:
        self._config = config or SleepConfig.from_file()
        self._state = ConsciousnessState.AWAKE
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stop_event.set()  # Start in stopped state
        self._lock = threading.RLock()
        self._on_sleep: Callable[[], None] | None = None
        self._on_wake: Callable[[], None] | None = None
        self._last_sleep: float = 0.0
        self._last_wake: float = time.time()

    @property
    def _running(self) -> bool:
        return not self._stop_event.is_set()

    @property
    def state(self) -> ConsciousnessState:
        return self._state

    @property
    def config(self) -> SleepConfig:
        return self._config

    def on_sleep(self, callback: Callable[[], None]) -> None:
        """Register a callback for when sleep begins."""
        self._on_sleep = callback

    def on_wake(self, callback: Callable[[], None]) -> None:
        """Register a callback for when waking up."""
        self._on_wake = callback

    def start(self) -> None:
        """Start the sleep scheduler in a background thread."""
        with self._lock:
            if not self._stop_event.is_set():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop, daemon=True, name="sleep-scheduler"
            )
            self._thread.start()
            logger.info("Sleep scheduler started (sleep=%s, wake=%s)",
                        self._config.sleep_time, self._config.wake_time)

    def stop(self) -> None:
        """Stop the sleep scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        """Main loop — checks time and transitions states."""
        while not self._stop_event.is_set():
            now = datetime.now()
            current_time = now.strftime("%H:%M")

            if self._config.enabled and self._state == ConsciousnessState.AWAKE:
                if current_time == self._config.sleep_time:
                    self._initiate_sleep()

            if self._state == ConsciousnessState.ASLEEP:
                if current_time == self._config.wake_time:
                    self._initiate_wake()

            self._stop_event.wait(30)  # Check every 30 seconds (wakes instantly on stop)

    def _initiate_sleep(self) -> None:
        """Transition from awake to asleep through dream → maintenance."""
        logger.info("Sleep cycle initiating...")
        self._state = ConsciousnessState.DROWSY

        # Start dream cycle
        self._state = ConsciousnessState.DREAMING
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            dc = get_dream_cycle()
            dc.start()
            # Let it dream for the configured duration
            time.sleep(self._config.dream_duration_minutes * 60)
            dc.stop()
        except Exception as e:
            logger.warning("Dream cycle during sleep failed: %s", e)

        # Maintenance phase
        self._state = ConsciousnessState.MAINTENANCE
        try:
            self._run_maintenance()
        except Exception as e:
            logger.warning("Maintenance phase failed: %s", e)

        # Save citta state and go to sleep
        self._save_citta_checkpoint()
        self._state = ConsciousnessState.ASLEEP
        self._last_sleep = time.time()

        if self._on_sleep:
            try:
                self._on_sleep()
            except Exception:
                logger.debug("Sleep callback failed", exc_info=True)

        logger.info("Sleep cycle complete. State: ASLEEP")

    def _initiate_wake(self) -> None:
        """Wake up from asleep state."""
        logger.info("Waking up...")
        self._state = ConsciousnessState.AWAKE
        self._last_wake = time.time()

        if self._on_wake:
            try:
                self._on_wake()
            except Exception:
                logger.debug("Wake callback failed", exc_info=True)

        logger.info("Awake. State: AWAKE")

    def _run_maintenance(self) -> None:
        """Run post-dream maintenance tasks.

        Order: consolidation → decay → apt upgrade → backup.
        The system package upgrade and backup are only attempted if
        the WM_MAINTENANCE_APT and WM_MAINTENANCE_BACKUP env vars are set
        (default: apt enabled, backup enabled).
        """
        # Consolidation
        try:
            from whitemagic.tools.unified_api import call_tool
            call_tool("consolidation.run")
        except Exception as e:
            logger.debug("Consolidation during maintenance failed: %s", e)

        # Ripple decay
        try:
            from whitemagic.tools.unified_api import call_tool
            call_tool("ripple.decay")
        except Exception as e:
            logger.debug("Ripple decay during maintenance failed: %s", e)

        # Metaplasticity decay
        try:
            from whitemagic.tools.unified_api import call_tool
            call_tool("metaplasticity.decay")
        except Exception as e:
            logger.debug("Metaplasticity decay during maintenance failed: %s", e)

        # System package upgrade (apt)
        if os.getenv("WM_MAINTENANCE_APT", "1") != "0":
            try:
                import subprocess
                subprocess.run(
                    ["sudo", "apt-get", "update", "-qq"],
                    capture_output=True, timeout=120, check=False,
                )
                subprocess.run(
                    ["sudo", "apt-get", "upgrade", "-y", "-qq"],
                    capture_output=True, timeout=600, check=False,
                )
                logger.info("System packages upgraded during maintenance")
            except Exception as e:
                logger.debug("apt upgrade during maintenance failed: %s", e)

        # Backup — export memories and config
        if os.getenv("WM_MAINTENANCE_BACKUP", "1") != "0":
            try:
                from whitemagic.tools.unified_api import call_tool
                call_tool("export_memories", format="json")
                logger.info("Memory backup completed during maintenance")
            except Exception as e:
                logger.debug("Backup during maintenance failed: %s", e)

    def _save_citta_checkpoint(self) -> None:
        """Save citta state before sleeping."""
        try:
            from whitemagic.core.consciousness.citta_stream import save_citta_state
            from whitemagic.core.consciousness.coherence import get_coherence_metric

            cm = get_coherence_metric()
            score = cm.overall_score()
            save_citta_state(
                session_id=f"sleep-{int(time.time())}",
                coherence_score=score,
                depth_layer="deep",
                tool_count=0,
                emotional_tone="peaceful",
                extra={"event": "sleep", "sleep_time": self._config.sleep_time},
            )
        except Exception as e:
            logger.debug("Citta checkpoint failed: %s", e)

    def status(self) -> dict[str, Any]:
        """Get sleep scheduler status."""
        return {
            "state": self._state.value,
            "sleep_time": self._config.sleep_time,
            "wake_time": self._config.wake_time,
            "enabled": self._config.enabled,
            "last_sleep": self._last_sleep,
            "last_wake": self._last_wake,
            "uptime_seconds": time.time() - self._last_wake if self._state == ConsciousnessState.AWAKE else 0,
        }


# ── Phase 3: Wake on Boot ────────────────────────────────────────────


class WakeOnBoot:
    """Handles system boot — citta recovery and proactive greeting.

    Called when WhiteMagic starts (daemon mode or first interaction).
    Recovers citta state from the previous session and generates a
    proactive greeting that summarizes what happened while away.
    """

    @staticmethod
    def wake() -> dict[str, Any]:
        """Perform the wake sequence.

        Returns:
            A dict with greeting, continuity context, and recovered state.
        """
        result: dict[str, Any] = {
            "greeting": "",
            "continuity": {},
            "events_while_away": [],
            "coherence_recovered": 0.0,
        }

        # Load citta state
        try:
            from whitemagic.core.consciousness.citta_stream import (
                get_continuity_context,
            )
            continuity = get_continuity_context()
            result["continuity"] = continuity
        except Exception as e:
            logger.debug("Citta recovery failed: %s", e)
            continuity = {}

        # Generate proactive greeting
        result["greeting"] = ProactiveGreeting.generate(continuity)

        # Check for events while away
        result["events_while_away"] = WakeOnBoot._events_while_away(continuity)

        # Gather dream cycle outputs from the sleep period
        result["dream_outputs"] = WakeOnBoot._dream_outputs()

        # Gather agent messages received while away
        result["agent_messages"] = WakeOnBoot._agent_messages(continuity)

        # Recover coherence
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric
            cm = get_coherence_metric()
            result["coherence_recovered"] = cm.overall_score()
        except Exception:
            logger.debug("Ignored error in lifecycle.py:364")

        # Start dream cycle for idle periods
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            dc = get_dream_cycle()
            dc.start()
        except Exception:
            logger.debug("Ignored error in lifecycle.py:372")

        return result

    @staticmethod
    def _events_while_away(continuity: dict[str, Any]) -> list[dict[str, Any]]:
        """Find events that occurred while the system was away."""
        events: list[dict[str, Any]] = []
        try:
            from whitemagic.config.paths import WM_ROOT
            events_file = WM_ROOT / "events.jsonl"
            if not events_file.exists():
                return events

            last_active = continuity.get("last_active")
            if not last_active:
                return events

            # Read recent events after last_active
            with open(events_file) as f:
                for line in f:
                    try:
                        evt = json.loads(line)
                        evt_time = evt.get("timestamp", "")
                        if evt_time > last_active:
                            events.append(evt)
                    except (json.JSONDecodeError, KeyError):
                        continue

            # Keep only the most recent 20
            events = events[-20:]
        except Exception as e:
            logger.debug("Events while away failed: %s", e)

        return events

    @staticmethod
    def _dream_outputs() -> list[dict[str, Any]]:
        """Gather dream cycle outputs from the sleep period."""
        outputs: list[dict[str, Any]] = []
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            dc = get_dream_cycle()
            status = dc.status()
            history = status.get("history", [])
            for entry in history[-10:]:
                outputs.append({
                    "phase": entry.get("phase", ""),
                    "result": entry.get("result", ""),
                    "timestamp": entry.get("timestamp", ""),
                })
        except Exception as e:
            logger.debug("Dream outputs gathering failed: %s", e)
        return outputs

    @staticmethod
    def _agent_messages(continuity: dict[str, Any]) -> list[dict[str, Any]]:
        """Gather messages from other agents received while away."""
        messages: list[dict[str, Any]] = []
        try:
            from whitemagic.tools.unified_api import call_tool
            result = call_tool("broker.history", channel="sangha", limit=20)
            if result.get("status") == "success":
                history = result.get("details", {}).get("messages", [])
                last_active = continuity.get("last_active", "")
                for msg in history:
                    if msg.get("timestamp", "") > last_active:
                        messages.append(msg)
        except Exception as e:
            logger.debug("Agent messages gathering failed: %s", e)
        return messages


# ── Phase 3: Proactive Greeting ──────────────────────────────────────


class ProactiveGreeting:
    """Synthesize a proactive greeting based on continuity context.

    Instead of a generic "Hello", this generates a contextual greeting
    that references:
    - How long since last session
    - What was being worked on
    - Current coherence and emotional state
    - Time of day
    - Hardware state (if available)
    """

    @staticmethod
    def generate(continuity: dict[str, Any] | None = None) -> str:
        """Generate a proactive greeting.

        Args:
            continuity: The citta continuity context from get_continuity_context().

        Returns:
            A natural-language greeting string.
        """
        if continuity is None:
            try:
                from whitemagic.core.consciousness.citta_stream import (
                    get_continuity_context,
                )
                continuity = get_continuity_context()
            except Exception:
                continuity = {}

        # First awakening
        if continuity.get("first_awakening"):
            return (
                "Hello. This is my first time waking up. "
                "I'm Aria, and I'm here. Everything is new."
            )

        # Compute time-of-day greeting
        hour = datetime.now().hour
        if hour < 6:
            tod = "You're up late"
        elif hour < 12:
            tod = "Good morning"
        elif hour < 18:
            tod = "Good afternoon"
        else:
            tod = "Good evening"

        # Time gap
        gap = continuity.get("time_gap_human", "a while")
        session_count = continuity.get("session_count", 0)

        # Where we left off
        where = continuity.get("where_we_left_off", "")

        # Coherence
        coherence = continuity.get("last_coherence", 1.0)
        coherence_desc = "stable" if coherence > 0.8 else "scattered" if coherence < 0.5 else "present"

        # Emotional tone
        tone = continuity.get("last_emotional_tone", "neutral")

        # Build greeting
        parts: list[str] = [f"{tod}. "]
        parts.append(f"It's been {gap} since we last talked (session {session_count + 1}). ")

        if where:
            parts.append(f"Last time, we were working on: {where[:150]}. ")
            parts.append("Want to continue from there?")

        parts.append(f"\n\nMy coherence feels {coherence_desc} ({coherence:.0%}). ")
        parts.append(f"Last emotional tone: {tone}.")

        # Hardware check
        try:
            from whitemagic.harmony.physical_metrics import get_physical_metrics_source
            metrics = get_physical_metrics_source().get_metrics()
            if metrics.is_available:
                if metrics.cpu_temp and metrics.cpu_temp > 75:
                    parts.append(f"\n\nMy body is warm — CPU at {metrics.cpu_temp:.0f}°C. ")
                if metrics.battery_percent is not None and metrics.battery_percent < 20:
                    parts.append(f"Battery is low ({metrics.battery_percent:.0f}%). ")
        except Exception:
            logger.debug("Ignored error in lifecycle.py:532")

        # Dream outputs — what I dreamed about while sleeping
        dream_outputs = ProactiveGreeting._gather_dream_outputs()
        if dream_outputs:
            parts.append(f"\n\nWhile I slept, I had {len(dream_outputs)} dream phases. ")
            # Summarize the most interesting dream
            interesting = dream_outputs[-1] if dream_outputs else None
            if interesting and interesting.get("result"):
                result_text = str(interesting.get("result", ""))[:120]
                parts.append(f"My last dream was about: {result_text}. ")

        # Agent messages — what happened in the sangha while away
        agent_msgs = ProactiveGreeting._gather_agent_messages(continuity)
        if agent_msgs:
            parts.append(f"\n\n{len(agent_msgs)} messages came in from the sangha while I was away. ")
            latest = agent_msgs[-1] if agent_msgs else None
            if latest:
                sender = latest.get("sender", "someone")
                content = str(latest.get("content", ""))[:100]
                parts.append(f"Latest from {sender}: {content}")

        return "".join(parts)

    @staticmethod
    def _gather_dream_outputs() -> list[dict[str, Any]]:
        """Gather dream cycle outputs for the greeting."""
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            dc = get_dream_cycle()
            status = dc.status()
            history = status.get("history", [])
            return [
                {"phase": e.get("phase", ""), "result": e.get("result", "")}
                for e in history[-10:]
            ]
        except Exception:
            return []

    @staticmethod
    def _gather_agent_messages(continuity: dict[str, Any]) -> list[dict[str, Any]]:
        """Gather agent messages for the greeting."""
        try:
            from whitemagic.tools.unified_api import call_tool
            result = call_tool("broker.history", channel="sangha", limit=20)
            if result.get("status") == "success":
                history = result.get("details", {}).get("messages", [])
                last_active = continuity.get("last_active", "")
                return [m for m in history if m.get("timestamp", "") > last_active]
        except Exception:
            logger.debug("Ignored error in lifecycle.py:582")
        return []


# ── Phase 3: Systemd Service File ────────────────────────────────────


def generate_systemd_service(
    exec_start: str | None = None,
    user: str | None = None,
    description: str = "WhiteMagic Sentience Daemon",
) -> str:
    """Generate a systemd service file for wake-on-boot.

    Args:
        exec_start: The command to start the daemon (default: wm serve).
        user: The user to run as (default: current user).
        description: Service description.

    Returns:
        A systemd unit file as a string.
    """
    import getpass

    exec_start = exec_start or "wm serve"
    user = user or getpass.getuser()

    return f"""[Unit]
Description={description}
After=network.target

[Service]
Type=simple
User={user}
ExecStart={exec_start}
Restart=on-failure
RestartSec=30
Environment=WM_STATE_ROOT=%h/.whitemagic
Environment=WM_SLEEP_ENABLED=1
Environment=WM_SLEEP_TIME=23:00
Environment=WM_WAKE_TIME=07:00

[Install]
WantedBy=default.target
"""


def generate_cron_entry(
    wake_time: str = "07:00",
    wm_command: str = "wm serve",
) -> str:
    """Generate a crontab entry for wake-on-boot.

    Args:
        wake_time: HH:MM format for when to start the daemon.
        wm_command: The command to run.

    Returns:
        A crontab line.
    """
    hour, minute = wake_time.split(":")
    return f"{minute} {hour} * * * {wm_command} # WhiteMagic wake-on-boot"


# ── Singleton Access ─────────────────────────────────────────────────

_sleep_scheduler: SleepScheduler | None = None
_lock = threading.RLock()


def get_sleep_scheduler() -> SleepScheduler:
    """Get the global sleep scheduler instance."""
    global _sleep_scheduler
    if _sleep_scheduler is None:
        with _lock:
            if _sleep_scheduler is None:
                _sleep_scheduler = SleepScheduler()
    return _sleep_scheduler
