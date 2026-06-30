# ruff: noqa: BLE001
"""Circuit Breaker — Stoic Resilience for Tool Dispatch.
=====================================================
Inspired by MandalaOS's Stoic Circuit-Breaker concept.

When a tool fails N times within M seconds, the breaker "opens" and
subsequent calls return a calm degraded response immediately — no
repeated hammering of a broken service.  After a cooldown period the
breaker enters "half-open" state and allows a single probe call through.
If the probe succeeds, the breaker closes and normal flow resumes.

States:
  CLOSED   → Normal operation; failures are counted.
  OPEN     → Fast-fail; returns a calm "service unavailable" response.
  HALF_OPEN → One probe call allowed; success → CLOSED, failure → OPEN.

Usage:
    from whitemagic.tools.circuit_breaker import get_breaker_registry
    registry = get_breaker_registry()
    breaker = registry.get(tool_name)

    if breaker.is_open():
        return breaker.calm_response(tool_name)

    result = dispatch(tool_name, **kwargs)

    if result is error:
        breaker.record_failure()
    else:
        breaker.record_success()
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from whitemagic.runtime_status import get_runtime_status

logger = logging.getLogger(__name__)


class BreakerState(StrEnum):
    """BreakerState: breaker state.

    Enumeration.

    Members:
        CLOSED
        OPEN
        HALF_OPEN"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class BreakerConfig:
    """Configuration for a single circuit breaker."""

    failure_threshold: int = 5  # failures before opening
    window_seconds: float = 60.0  # time window for counting failures
    cooldown_seconds: float = 1.0  # how long to stay open before half-open (reduced from 30s for responsiveness)


class CircuitBreaker:
    """Circuit breaker for a single tool."""

    def __init__(self, tool_name: str, config: BreakerConfig | None = None):
        self.tool_name = tool_name
        self.config = config or BreakerConfig()
        self._lock = threading.Lock()
        self._state = BreakerState.CLOSED
        self._failure_timestamps: list[float] = []
        self._opened_at: float = 0.0
        self._total_trips: int = 0

    def is_open(self) -> bool:
        """Check if the breaker is open (should fast-fail).

        Syncs from StateBoard (Rust PyO3) when available so that the
        Python breaker reflects the authoritative native state.
        Also checks Koka native circuit handler if available.
        """
        with self._lock:
            # Sync from StateBoard if Rust PyO3 is available
            self._sync_from_board()

            # Sync from Koka native circuit handler if available
            koka = get_koka_circuit_dispatch()
            if koka is not None:
                koka_state = koka.check(self.tool_name)
                if koka_state == "open":
                    return True

            if self._state == BreakerState.CLOSED:
                return False
            if self._state == BreakerState.OPEN:
                # Check if cooldown has elapsed → transition to HALF_OPEN
                elapsed = time.time() - self._opened_at
                if elapsed >= self.config.cooldown_seconds:
                    self._state = BreakerState.HALF_OPEN
                    logger.info(
                        "Circuit breaker [%s]: OPEN → HALF_OPEN (cooldown %ss elapsed)",
                        self.tool_name,
                        self.config.cooldown_seconds,
                    )
                    self._sync_to_board()
                    return False  # Allow one probe call
                return True
            # HALF_OPEN: allow one call through
            return False

    def record_failure(self) -> None:
        """Record a tool failure."""
        now = time.time()
        # Sync to Koka native circuit handler if available
        koka = get_koka_circuit_dispatch()
        if koka is not None:
            try:
                koka.record_failure(self.tool_name)
            except Exception:
                pass
        with self._lock:
            # Prune old failures outside the window
            cutoff = now - self.config.window_seconds
            self._failure_timestamps = [
                t for t in self._failure_timestamps if t >= cutoff
            ]
            self._failure_timestamps.append(now)

            if self._state == BreakerState.HALF_OPEN:
                # Probe failed → reopen
                self._state = BreakerState.OPEN
                self._opened_at = now
                logger.warning(
                    "Circuit breaker [%s]: HALF_OPEN → OPEN (probe failed)",
                    self.tool_name,
                )
                self._sync_to_board()
            elif len(self._failure_timestamps) >= self.config.failure_threshold:
                self._state = BreakerState.OPEN
                self._opened_at = now
                self._total_trips += 1
                logger.warning(
                    "Circuit breaker [%s]: CLOSED → OPEN "
                    "(%s failures in "
                    "%ss, trip #%s)",
                    self.tool_name,
                    len(self._failure_timestamps),
                    self.config.window_seconds,
                    self._total_trips,
                )
                self._sync_to_board()

    def record_success(self) -> None:
        """Record a tool success."""
        # Sync to Koka native circuit handler if available
        koka = get_koka_circuit_dispatch()
        if koka is not None:
            try:
                koka.record_success(self.tool_name)
            except Exception:
                pass
        with self._lock:
            if self._state == BreakerState.HALF_OPEN:
                self._state = BreakerState.CLOSED
                self._failure_timestamps.clear()
                logger.info(
                    "Circuit breaker [%s]: HALF_OPEN → CLOSED (probe succeeded)",
                    self.tool_name,
                )
                self._sync_to_board()
            elif self._state == BreakerState.CLOSED:
                # Successful calls don't clear the failure window, but that's fine;
                # they'll naturally expire.
                pass

    def calm_response(self) -> dict[str, Any]:
        """Return a calm degraded response when the breaker is open."""
        with self._lock:
            remaining = max(
                0.0,
                self.config.cooldown_seconds - (time.time() - self._opened_at),
            )
        runtime_status = get_runtime_status()
        return {
            "status": "error",
            "error_code": "circuit_breaker_open",
            "message": (
                f"Tool '{self.tool_name}' is temporarily unavailable due to "
                f"repeated failures. The system is holding steady. "
                f"Retry in ~{int(remaining)}s."
            ),
            "retryable": True,
            "degraded_mode": True,
            "degraded_reasons": [
                "circuit_breaker_open",
                *runtime_status.get("degraded_reasons", []),
            ],
            "resolution": {
                "suggested_action": "retry_after_cooldown_or_enable_debug",
                "debug_hint": "Set WM_DEBUG=1 for verbose diagnostics",
            },
            "circuit_breaker": {
                "state": self._state.value,
                "cooldown_remaining_s": round(remaining, 1),
                "total_trips": self._total_trips,
            },
        }

    def _sync_to_board(self) -> None:
        """Push breaker state to StateBoard shared memory (Leap 7 Nervous System).

        Maps tool_name to an engine slot via the engine registry. If the tool
        doesn't map to a known engine slot, this is a no-op.
        """
        try:
            from whitemagic.core.acceleration.state_board_bridge import (
                BreakerState as BoardBreaker,
            )
            from whitemagic.core.acceleration.state_board_bridge import (
                get_state_board,
            )

            slot = _tool_to_engine_slot(self.tool_name)
            if slot is None:
                return
            state_map = {
                BreakerState.CLOSED: BoardBreaker.CLOSED,
                BreakerState.OPEN: BoardBreaker.OPEN,
                BreakerState.HALF_OPEN: BoardBreaker.HALF_OPEN,
            }
            board = get_state_board()
            board.write_breaker(
                tool_slot=slot,
                state=state_map[self._state],
                failures=len(self._failure_timestamps),
            )
        except (ImportError, AttributeError):
            pass  # StateBoard is optional

    def _sync_from_board(self) -> None:
        """Pull breaker state FROM StateBoard (Rust PyO3 authoritative source).

        If the StateBoard has a different state than Python, trust the native
        side. This ensures the Zig dispatch core and Python BreakerRegistry
        stay in sync.
        """
        try:
            from whitemagic.core.acceleration.state_board_bridge import (
                BreakerState as BoardBreaker,
            )
            from whitemagic.core.acceleration.state_board_bridge import (
                get_state_board,
            )

            slot = _tool_to_engine_slot(self.tool_name)
            if slot is None:
                return
            board = get_state_board()
            board_state, board_failures = board.read_breaker(slot)
            # Map StateBoard state back to Python BreakerState
            state_map = {
                BoardBreaker.CLOSED: BreakerState.CLOSED,
                BoardBreaker.OPEN: BreakerState.OPEN,
                BoardBreaker.HALF_OPEN: BreakerState.HALF_OPEN,
            }
            py_state = state_map.get(board_state)
            if py_state is not None and py_state != self._state:
                self._state = py_state
                if py_state == BreakerState.OPEN and not self._opened_at:
                    self._opened_at = time.time()
        except (ImportError, AttributeError, KeyError):
            pass  # StateBoard is optional

    def status(self) -> dict[str, Any]:
        """Return breaker status for introspection."""
        with self._lock:
            return {
                "tool": self.tool_name,
                "state": self._state.value,
                "recent_failures": len(self._failure_timestamps),
                "threshold": self.config.failure_threshold,
                "total_trips": self._total_trips,
            }


# Maps PRAT Gana prefixes and common tool names to engine slots (0-27).
# This allows the circuit breaker to write state to the StateBoard slot
# that the Zig dispatch core reads.
_GANA_PREFIX_TO_SLOT: dict[str, int] = {
    "gana_horn": 0,
    "session": 0,
    "gana_neck": 1,
    "consolidat": 1,
    "memory.consolidat": 1,
    "gana_root": 2,
    "boundary": 2,
    "health": 2,
    "gana_room": 3,
    "circuit": 3,
    "gana_heart": 4,
    "nurtur": 4,
    "gana_tail": 5,
    "accelerat": 5,
    "rust_": 5,
    "gana_basket": 6,
    "serendipit": 6,
    "gana_ghost": 7,
    "gnosis": 7,
    "capabilit": 7,
    "manifest": 7,
    "gana_willow": 8,
    "resilien": 8,
    "gana_star": 9,
    "govern": 9,
    "dharma": 9,
    "gana_net": 10,
    "associat": 10,
    "gana_wings": 11,
    "export": 11,
    "import": 11,
    "gana_chariot": 12,
    "archaeolog": 12,
    "gana_abundance": 13,
    "dream": 13,
    "resonanc": 13,
    "gana_legs": 14,
    "solver": 14,
    "ethic": 14,
    "gana_mound": 15,
    "embedding": 15,
    "vector.": 15,
    "gana_stomach": 16,
    "lifecycle": 16,
    "memory.lifecycle": 16,
    "gana_head": 17,
    "kaizen": 17,
    "gana_bi": 18,
    "pattern": 18,
    "gana_beak": 19,
    "voice": 19,
    "narrat": 19,
    "gana_stars": 20,
    "evaluate_ethics": 20,
    "karma": 20,
    "gana_dipper": 21,
    "predict": 21,
    "gana_ox": 22,
    "galactic": 22,
    "gana_girl": 23,
    "clone": 23,
    "agent": 23,
    "gana_void": 24,
    "forget": 24,
    "stillness": 24,
    "gana_roof": 25,
    "sanitiz": 25,
    "permission": 25,
    "gana_camp": 26,
    "swarm": 26,
    "sangha": 26,
    "gana_wall": 27,
    "emerge": 27,
}


def _tool_to_engine_slot(tool_name: str) -> int | None:
    """Map a tool name to its engine slot (0-27) for StateBoard addressing."""
    name = tool_name.lower()
    for prefix, slot in _GANA_PREFIX_TO_SLOT.items():
        if name.startswith(prefix):
            return slot
    return None


_TOOL_BREAKER_OVERRIDES: dict[str, BreakerConfig] = {
    # Ollama may restart frequently — fail fast, retry quickly
    "ollama.models": BreakerConfig(
        failure_threshold=2, window_seconds=30.0, cooldown_seconds=1.0
    ),
    "ollama.generate": BreakerConfig(
        failure_threshold=2, window_seconds=30.0, cooldown_seconds=1.0
    ),
    "ollama.chat": BreakerConfig(
        failure_threshold=2, window_seconds=30.0, cooldown_seconds=1.0
    ),
    # Redis broker — slightly more tolerant but still fast-fail
    "broker.publish": BreakerConfig(
        failure_threshold=3, window_seconds=30.0, cooldown_seconds=1.0
    ),
    "broker.history": BreakerConfig(
        failure_threshold=3, window_seconds=30.0, cooldown_seconds=1.0
    ),
    "broker.status": BreakerConfig(
        failure_threshold=3, window_seconds=30.0, cooldown_seconds=1.0
    ),
}


class BreakerRegistry:
    """Registry of circuit breakers, one per tool."""

    def __init__(self, default_config: BreakerConfig | None = None):
        self._lock = threading.Lock()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_config = default_config or BreakerConfig()

    def get(self, tool_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a tool."""
        with self._lock:
            if tool_name not in self._breakers:
                config = _TOOL_BREAKER_OVERRIDES.get(tool_name, self._default_config)
                self._breakers[tool_name] = CircuitBreaker(
                    tool_name,
                    config=config,
                )
                # Configure Koka native circuit handler if available
                koka = get_koka_circuit_dispatch()
                if koka is not None:
                    try:
                        koka.configure(
                            tool_name,
                            config.failure_threshold,
                            int(config.cooldown_seconds * 1000),
                            1,
                        )
                    except Exception:
                        pass
            return self._breakers[tool_name]

    def all_status(self) -> list[dict[str, Any]]:
        """Return status of all breakers (for Gnosis introspection)."""
        with self._lock:
            return [b.status() for b in self._breakers.values()]

    def tripped(self) -> list[dict[str, Any]]:
        """Return only breakers that have tripped at least once."""
        with self._lock:
            return [b.status() for b in self._breakers.values() if b._total_trips > 0]

    def reset_all(self) -> int:
        """Reset all circuit breakers to CLOSED state. Returns count of reset breakers.

        Also resets the StateBoard (Rust PyO3 shared memory) so the Zig dispatch
        core and Python BreakerRegistry stay in sync.
        """
        count = 0
        with self._lock:
            # Reset Python breakers
            for breaker in self._breakers.values():
                with breaker._lock:
                    if breaker._state != BreakerState.CLOSED:
                        breaker._state = BreakerState.CLOSED
                        breaker._failure_timestamps.clear()
                        breaker._opened_at = 0.0
                        count += 1

            # Reset StateBoard via Rust PyO3 (authoritative native state)
            try:
                import whitemagic_rs

                whitemagic_rs.board_reset()
                logger.info("StateBoard reset via Rust PyO3 (board_reset)")
            except ImportError:
                pass  # Rust PyO3 not available — Python-only fallback

            # Reset Koka native circuit handler if available
            koka = get_koka_circuit_dispatch()
            if koka is not None:
                for breaker in self._breakers.values():
                    try:
                        koka.reset(breaker.tool_name)
                    except Exception:
                        pass

            if count:
                logger.info("Reset %d circuit breaker(s) to CLOSED", count)
            return count

    def predictive_check(self) -> dict[str, Any]:
        """G4 Synthesis: Query Self-Model forecasts to proactively tighten breakers.

        If the self-model predicts error_rate or breaker_trips will hit critical
        thresholds soon, temporarily lower failure thresholds on active breakers
        to catch problems earlier.
        """
        tightened = []
        try:
            from whitemagic.core.intelligence.self_model import get_self_model

            model = get_self_model()
            alerts = model.get_alerts()

            for alert in alerts:
                if (
                    alert.metric in ("error_rate", "breaker_trips")
                    and alert.threshold_eta is not None
                ):
                    # If critical threshold is predicted within 5 steps,
                    # tighten all active breakers' failure threshold by 1
                    if alert.threshold_eta <= 5:
                        with self._lock:
                            for breaker in self._breakers.values():
                                if breaker.config.failure_threshold > 2:
                                    breaker.config.failure_threshold -= 1
                                    tightened.append(breaker.tool_name)
                        logger.info(
                            "Predictive breaker tightening: %s forecast "
                            "to breach in ~%s steps, "
                            "tightened %s breakers",
                            alert.metric,
                            alert.threshold_eta,
                            len(tightened),
                        )
        except Exception as e:
            logger.debug("Predictive check skipped: %s", e, exc_info=True)

        return {
            "tightened": tightened,
            "tightened_count": len(tightened),
        }


_registry: BreakerRegistry | None = None
_reg_lock = threading.Lock()


def get_breaker_registry() -> BreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        with _reg_lock:
            if _registry is None:
                _registry = BreakerRegistry()
                # R&D mode: reset all breakers on startup for clean development session
                if os.getenv("WM_RD_MODE", "").strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                ):
                    _registry.reset_all()
                    logger.info("WM_RD_MODE=1: circuit breakers reset on startup")
    return _registry


_koka_circuit: Any = None
_koka_lock = threading.Lock()


def get_koka_circuit_dispatch():
    """Get the Koka native circuit dispatcher (singleton).

    Returns None if the Koka binary is not available.
    """
    global _koka_circuit
    if _koka_circuit is None:
        with _koka_lock:
            if _koka_circuit is None:
                try:
                    from whitemagic.core.acceleration.koka_native_bridge import (
                        KokaCircuitDispatch,
                    )

                    inst = KokaCircuitDispatch()
                    if inst._ensure_running():
                        _koka_circuit = inst
                        logger.info("Koka circuit dispatch available")
                    else:
                        _koka_circuit = False  # marks as unavailable
                except (ImportError, Exception):
                    _koka_circuit = False
    return _koka_circuit if _koka_circuit is not False else None
