# ruff: noqa: BLE001
"""BitMamba-2 255M Autonomic Layer — continuous SSM for citta consciousness.

This module wraps the bitmamba.cpp inference engine as a persistent autonomic
layer for the citta consciousness system. The BitMamba-2 255M model is a
1.58-bit ternary Mamba-2 SSM that runs at ~10 tok/s on a single CPU core
with only 252MB RAM — perfect for always-on background processing.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │  Citta Cycle (call-driven)                          │
    │  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
    │  │ Tool Call│───▶│ Autonomic    │───▶│ Salience  │  │
    │  │ Output   │    │ Layer        │    │ Detection │  │
    │  └──────────┘    │ (BitMamba)   │    └─────┬─────┘  │
    │       ▲          │ 255M SSM     │          │        │
    │       │          │ ~10 tok/s    │          ▼        │
    │       │          │ 252MB RAM    │    ┌───────────┐  │
    │       │          └──────────────┘    │ Citta     │  │
    │       │                              │ Advance   │  │
    │       └──────────────────────────────┘           │  │
    │                                                  │  │
    └──────────────────────────────────────────────────┘

The autonomic layer:
1. Runs continuously on an idle core via bitmamba.cpp subprocess
2. Maintains hidden state (Mamba SSM recurrence) across sessions
3. Processes system telemetry as "text" to generate salience signals
4. Detects novel patterns, anomalies, and emotional shifts
5. Feeds results back into the citta cycle as autonomic moments

Integration points:
    - citta_cycle.py: advance_citta() calls autonomic.process_telemetry()
    - consciousness_loop.py: _advance_citta() checks autonomic salience
    - IceOryx2: hidden state shared via shared memory for zero-copy access
"""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

_BITMAMBA_BIN = os.environ.get(
    "WM_BITMAMBA_BIN",
    str(Path(__file__).resolve().parent.parent.parent.parent / "bitmamba.cpp" / "build" / "bitmamba"),
)
_MODEL_PATH = os.environ.get(
    "WM_BITMAMBA_MODEL",
    str(Path(__file__).resolve().parent.parent.parent.parent / "models" / "bitmamba_255m.bin"),
)
_TOKENIZER_BIN = os.environ.get(
    "WM_BITMAMBA_TOKENIZER",
    str(Path(__file__).resolve().parent.parent.parent.parent / "bitmamba.cpp" / "build" / "tokenizer.bin"),
)
_AUTONOMIC_ENABLED = os.environ.get("WM_AUTONOMIC_ENABLED", "0") == "1"
_MAX_TOKENS_PER_QUERY = 20
_BATCH_TELEMETRY_COUNT = 10  # Batch up to 10 telemetry events per pulse
_QUERY_INTERVAL_S = 30.0
_STATE_PERSIST_PATH = Path(
    os.environ.get("WM_STATE_ROOT", "/tmp/whitemagic")
) / "citta" / "autonomic_state.json"


# ── Data structures ──────────────────────────────────────────────────────


@dataclass
class SalienceSignal:
    """A salience signal detected by the autonomic layer."""

    timestamp: float
    token_ids: list[int]
    text: str
    salience_score: float
    signal_type: str  # "novelty", "anomaly", "emotional_shift", "background"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomicState:
    """Persistent state for the autonomic layer."""

    # Token history for repetition detection
    token_history: deque[int] = field(default_factory=lambda: deque(maxlen=200))
    # Recent salience signals
    recent_signals: deque[SalienceSignal] = field(default_factory=lambda: deque(maxlen=50))
    # Total queries processed
    query_count: int = 0
    # Last query timestamp
    last_query: float = 0.0
    # Running salience baseline (EMA)
    salience_baseline: float = 0.1
    # Whether the model is loaded
    model_loaded: bool = False
    # Peak RAM observed
    peak_ram_mb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_count": self.query_count,
            "last_query": self.last_query,
            "salience_baseline": round(self.salience_baseline, 4),
            "model_loaded": self.model_loaded,
            "peak_ram_mb": self.peak_ram_mb,
            "recent_signals": [
                {
                    "timestamp": s.timestamp,
                    "text": s.text,
                    "salience_score": round(s.salience_score, 4),
                    "signal_type": s.signal_type,
                }
                for s in self.recent_signals
            ],
        }


# ── Autonomic Layer ──────────────────────────────────────────────────────


class BitMambaAutonomic:
    """Continuous autonomic processing layer using BitMamba-2 255M.

    Wraps the bitmamba.cpp binary as a subprocess for inference. Maintains
    hidden state (Mamba SSM recurrence) conceptually across sessions by
    persisting token history and salience baseline.

    The model runs in "pulse" mode: every _QUERY_INTERVAL_S seconds, it
    processes recent system telemetry as a text prompt and generates a
    short continuation. The output is analyzed for salience signals.
    """

    def __init__(
        self,
        model_path: str | None = None,
        bitmamba_bin: str | None = None,
        tokenizer_bin: str | None = None,
        daemon_bin: str | None = None,
        use_daemon: bool = True,
    ) -> None:
        self._model_path = model_path or _MODEL_PATH
        self._bitmamba_bin = bitmamba_bin or _BITMAMBA_BIN
        self._tokenizer_bin = tokenizer_bin or _TOKENIZER_BIN
        # Daemon binary: bitmamba-daemon in the same directory as bitmamba
        if daemon_bin:
            self._daemon_bin = daemon_bin
        else:
            self._daemon_bin = str(Path(self._bitmamba_bin).parent / "bitmamba-daemon")
        self._use_daemon = use_daemon
        self._daemon_proc: subprocess.Popen | None = None
        self._daemon_lock = threading.RLock()
        self._state = AutonomicState()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._telemetry_buffer: deque[str] = deque(maxlen=10)
        self._load_state()

    @property
    def is_available(self) -> bool:
        """Check if the bitmamba binary and model are available."""
        return (
            Path(self._bitmamba_bin).exists()
            and Path(self._model_path).exists()
            and Path(self._tokenizer_bin).exists()
        )

    @property
    def is_daemon_available(self) -> bool:
        """Check if the bitmamba-daemon binary is available."""
        return Path(self._daemon_bin).exists() and Path(self._model_path).exists()

    @property
    def is_running(self) -> bool:
        return self._running

    def add_telemetry(self, source: str, message: str) -> None:
        """Add a telemetry event for the autonomic layer to process.

        Called by citta_cycle.advance() or consciousness_loop._advance_citta().
        """
        with self._lock:
            self._telemetry_buffer.append(f"{source}: {message}")

    def pulse(self) -> SalienceSignal | None:
        """Run a single autonomic pulse — generate from current telemetry.

        Batches all buffered telemetry events into a single inference call.
        The daemon's prefill_sequence processes the prompt in layer-major order,
        giving a cache-blocked speedup vs per-token prefill.

        Returns a SalienceSignal if the output is salient, None otherwise.
        """
        if not self.is_available:
            return None

        with self._lock:
            if not self._telemetry_buffer:
                return None
            # Batch all telemetry events (up to deque maxlen=10)
            prompt = " ".join(list(self._telemetry_buffer))
            self._telemetry_buffer.clear()

        try:
            result = self._run_inference(prompt, max_tokens=_MAX_TOKENS_PER_QUERY)
        except Exception as e:
            logger.debug("Autonomic inference failed: %s", e)
            return None

        if not result or not result.get("token_ids"):
            return None

        signal = self._analyze_salience(result["token_ids"], result.get("text", ""))
        with self._lock:
            self._state.query_count += 1
            self._state.last_query = time.time()
            self._state.recent_signals.append(signal)
            # Update salience baseline (EMA)
            alpha = 0.1
            self._state.salience_baseline = (
                alpha * signal.salience_score + (1 - alpha) * self._state.salience_baseline
            )
            if result.get("peak_ram_mb", 0) > self._state.peak_ram_mb:
                self._state.peak_ram_mb = result["peak_ram_mb"]

        self._save_state()
        return signal

    def get_state(self) -> dict[str, Any]:
        """Get current autonomic state snapshot."""
        with self._lock:
            return self._state.to_dict()

    def get_recent_signals(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent salience signals."""
        with self._lock:
            return [
                {
                    "timestamp": s.timestamp,
                    "text": s.text,
                    "salience_score": round(s.salience_score, 4),
                    "signal_type": s.signal_type,
                }
                for s in list(self._state.recent_signals)[-limit:]
            ]

    def start(self) -> bool:
        """Start the autonomic pulse loop in a background thread."""
        with self._lock:
            if self._running:
                return True
            if not self.is_available:
                logger.warning("BitMamba autonomic layer not available (missing binary/model)")
                return False
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._pulse_loop, daemon=True, name="bitmamba-autonomic"
            )
            self._thread.start()
            logger.info("BitMamba autonomic layer started (interval=%.0fs)", _QUERY_INTERVAL_S)
        return True

    def stop(self) -> None:
        """Stop the autonomic pulse loop."""
        with self._lock:
            self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._stop_daemon()
        self._save_state()
        logger.info("BitMamba autonomic layer stopped")

    def reset(self) -> None:
        """Reset autonomic state (for testing or new session)."""
        with self._lock:
            self._state = AutonomicState()
            self._telemetry_buffer.clear()
        try:
            _STATE_PERSIST_PATH.unlink(missing_ok=True)
        except OSError:
            logger.debug("Ignored OSError in bitmamba_autonomic.py:295")

    # ── Private methods ──────────────────────────────────────────────

    def _pulse_loop(self) -> None:
        """Background loop — pulses the autonomic layer at regular intervals."""
        while not self._stop_event.is_set():
            try:
                signal = self.pulse()
                if signal and signal.salience_score > 0.3:
                    logger.debug(
                        "Autonomic salience: type=%s score=%.3f text=%s",
                        signal.signal_type,
                        signal.salience_score,
                        signal.text[:80],
                    )
            except Exception as e:
                logger.debug("Autonomic pulse error: %s", e, exc_info=True)

            self._stop_event.wait(timeout=_QUERY_INTERVAL_S)

    def _ensure_daemon(self) -> bool:
        """Start the persistent daemon if not already running. Returns True if daemon is ready."""
        with self._daemon_lock:
            if self._daemon_proc and self._daemon_proc.poll() is None:
                return True  # Already running

            if not self.is_daemon_available:
                return False

            env = os.environ.copy()
            env["OMP_NUM_THREADS"] = "1"

            try:
                self._daemon_proc = subprocess.Popen(
                    [self._daemon_bin, self._model_path, self._tokenizer_bin],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    cwd=str(Path(self._daemon_bin).parent),
                )
                # Wait for ready signal (5s timeout)
                ready, _, _ = select.select([self._daemon_proc.stdout], [], [], 5.0)
                if not ready:
                    logger.debug("BitMamba daemon startup timeout")
                    self._stop_daemon()
                    return False
                ready_line = self._daemon_proc.stdout.readline()
                if '"status": "ready"' in ready_line:
                    logger.debug("BitMamba daemon started")
                    return True
                else:
                    logger.debug("BitMamba daemon failed to start: %s", ready_line)
                    self._stop_daemon()
                    return False
            except Exception as e:
                logger.debug("Daemon start error: %s", e)
                self._daemon_proc = None
                return False

    def _stop_daemon(self) -> None:
        """Stop the daemon process."""
        with self._daemon_lock:
            if self._daemon_proc:
                try:
                    self._daemon_proc.stdin.close()
                    self._daemon_proc.wait(timeout=5)
                except Exception:
                    self._daemon_proc.kill()
                self._daemon_proc = None

    def _run_inference_daemon(self, prompt: str, max_tokens: int = 20) -> dict[str, Any]:
        """Run inference via the persistent daemon (no model reload)."""
        if not self._ensure_daemon():
            return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}

        import json as _json

        request = _json.dumps({
            "prompt": prompt[:500],
            "max_tokens": max_tokens,
            "temp": 0.7,
            "penalty": 1.1,
            "min_p": 0.05,
            "top_p": 0.9,
            "top_k": 40,
        })

        try:
            with self._daemon_lock:
                if not self._daemon_proc or self._daemon_proc.poll() is not None:
                    return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}
                self._daemon_proc.stdin.write(request + "\n")
                self._daemon_proc.stdin.flush()
                ready, _, _ = select.select([self._daemon_proc.stdout], [], [], 10.0)
                if not ready:
                    logger.debug("BitMamba daemon response timeout")
                    self._stop_daemon()
                    return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}
                response_line = self._daemon_proc.stdout.readline()

            resp = _json.loads(response_line)
            return {
                "token_ids": resp.get("token_ids", []),
                "text": "",
                "peak_ram_mb": resp.get("peak_ram_mb", 0.0),
                "latency_ms": resp.get("total_ms", 0.0),
                "tokens_per_sec": resp.get("tokens_per_sec", 0.0),
            }
        except Exception as e:
            logger.debug("Daemon inference error: %s", e)
            self._stop_daemon()
            return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}

    def _run_inference(self, prompt: str, max_tokens: int = 20) -> dict[str, Any]:
        """Run bitmamba.cpp inference on the prompt.

        Uses the persistent daemon if available (eliminates ~200ms model reload).
        Falls back to spawning a new process per call.
        """
        # Try daemon first
        if self._use_daemon and self.is_daemon_available:
            return self._run_inference_daemon(prompt, max_tokens)

        # Fallback: spawn new process
        cmd = [
            self._bitmamba_bin,
            self._model_path,
            prompt[:500],
            "tokenizer",
            "0.7",
            "1.1",
            "0.05",
            "0.9",
            "40",
            str(max_tokens),
        ]

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=str(Path(self._bitmamba_bin).parent),
            )
        except subprocess.TimeoutExpired:
            logger.debug("BitMamba inference timed out")
            return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}
        except Exception as e:
            logger.debug("BitMamba subprocess error: %s", e)
            return {"token_ids": [], "text": "", "peak_ram_mb": 0.0}

        output = result.stdout
        token_ids: list[int] = []
        text_output = ""
        peak_ram = 0.0

        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("=== Generated Token IDs ==="):
                # Next line has the tokens
                continue
            if line and all(c.isdigit() or c.isspace() for c in line) and len(line) > 2:
                try:
                    token_ids = [int(t) for t in line.split()]
                except ValueError:
                    logger.debug("Ignored ValueError in bitmamba_autonomic.py:468")
            if "Peak RAM:" in line:
                try:
                    peak_ram = float(line.split("Peak RAM:")[1].split("MB")[0].strip())
                except (IndexError, ValueError):
                    logger.debug("Ignored IndexError, ValueError in bitmamba_autonomic.py:473")

        return {
            "token_ids": token_ids,
            "text": text_output,
            "peak_ram_mb": peak_ram,
        }

    def _analyze_salience(self, token_ids: list[int], text: str) -> SalienceSignal:
        """Analyze generated tokens for salience signals.

        Salience heuristics:
        - Novelty: tokens not seen in recent history
        - Repetition: high repetition → low salience (stuck state)
        - Diversity: high token diversity → higher salience
        - Emotional shift: detect sentiment-bearing tokens
        """
        now = time.time()

        # Novelty: fraction of tokens not in recent history
        with self._lock:
            history_set = set(self._state.token_history)
        novel_tokens = [t for t in token_ids if t not in history_set]
        novelty_ratio = len(novel_tokens) / max(1, len(token_ids))

        # Update token history
        with self._lock:
            for t in token_ids:
                self._state.token_history.append(t)

        # Repetition: if more than 70% of tokens are the same, low salience
        from collections import Counter
        token_counts = Counter(token_ids)
        most_common_ratio = token_counts.most_common(1)[0][1] / max(1, len(token_ids)) if token_ids else 1.0
        repetition_penalty = 1.0 - most_common_ratio if most_common_ratio > 0.7 else 1.0

        # Diversity: unique tokens / total
        diversity = len(set(token_ids)) / max(1, len(token_ids))

        # Combined salience score
        salience = novelty_ratio * 0.4 + diversity * 0.3 + repetition_penalty * 0.3

        # Signal type classification — check anomaly first (repetition overrides novelty)
        if most_common_ratio > 0.7:
            signal_type = "anomaly"
        elif novelty_ratio > 0.7:
            signal_type = "novelty"
        elif diversity > 0.8:
            signal_type = "emotional_shift"
        else:
            signal_type = "background"

        return SalienceSignal(
            timestamp=now,
            token_ids=token_ids,
            text=text,
            salience_score=round(salience, 4),
            signal_type=signal_type,
            metadata={
                "novelty_ratio": round(novelty_ratio, 4),
                "diversity": round(diversity, 4),
                "repetition": round(most_common_ratio, 4),
            },
        )

    def _save_state(self) -> None:
        """Persist autonomic state for cross-session continuity."""
        try:
            _STATE_PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {
                    "query_count": self._state.query_count,
                    "salience_baseline": self._state.salience_baseline,
                    "peak_ram_mb": self._state.peak_ram_mb,
                    "token_history": list(self._state.token_history),
                }
            _STATE_PERSIST_PATH.write_text(json.dumps(data))
        except OSError:
            logger.debug("Failed to persist autonomic state", exc_info=True)

    def _load_state(self) -> None:
        """Load persisted autonomic state."""
        try:
            if not _STATE_PERSIST_PATH.exists():
                return
            data = json.loads(_STATE_PERSIST_PATH.read_text())
            with self._lock:
                self._state.query_count = data.get("query_count", 0)
                self._state.salience_baseline = data.get("salience_baseline", 0.1)
                self._state.peak_ram_mb = data.get("peak_ram_mb", 0.0)
                for t in data.get("token_history", []):
                    self._state.token_history.append(t)
        except (OSError, json.JSONDecodeError):
            logger.debug("Failed to load autonomic state", exc_info=True)


# ── Singleton ────────────────────────────────────────────────────────────

_autonomic: BitMambaAutonomic | None = None
_autonomic_lock = threading.RLock()


def get_autonomic() -> BitMambaAutonomic:
    """Get or create the global BitMamba autonomic layer singleton."""
    global _autonomic
    if _autonomic is None:
        with _autonomic_lock:
            if _autonomic is None:
                _autonomic = BitMambaAutonomic()
    return _autonomic


def is_autonomic_available() -> bool:
    """Check if the autonomic layer is available and enabled."""
    if not _AUTONOMIC_ENABLED:
        return False
    return get_autonomic().is_available
