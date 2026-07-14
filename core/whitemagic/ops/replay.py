"""Deterministic Replay — Record and replay tool execution traces.

Phase 8 WI 1 of the Codebase Hardening Strategy.

Records the full execution context of a tool call including:
- Request (tool name, arguments, user/agent/galaxy/policy)
- Middleware decisions (which middleware ran, short-circuits, errors)
- Backend choice (which backend handled the call)
- Native fallback (if a native bridge was used and fell back)
- Output (the full result envelope)

Replay mode re-executes the tool call with the recorded context,
suppressing external side effects (writes, network, native bridges).

Usage::

    from whitemagic.ops.replay import ReplayRecorder, ReplayPlayer

    # Record
    recorder = ReplayRecorder()
    with recorder.record("search_memories", query="test", user_id="alice"):
        result = dispatch("search_memories", query="test", user_id="alice")
    trace = recorder.last_trace

    # Replay
    player = ReplayPlayer()
    replayed = player.replay(trace)
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_WM_REPLAY_RECORD = "WM_REPLAY_RECORD"
_WM_REPLAY_DIR = os.getenv("WM_REPLAY_DIR", "")


@dataclass
class MiddlewareDecision:
    """A single middleware's decision in the pipeline."""

    name: str
    action: str  # "pass", "short_circuit", "error"
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """A complete trace of a tool execution for replay."""

    trace_id: str
    tool_name: str
    arguments: dict[str, Any]
    user_id: str
    agent_id: str
    galaxy: str
    policy_profile: str
    requested_mode: str
    middleware_decisions: list[MiddlewareDecision] = field(default_factory=list)
    backend_choice: str = ""
    native_fallback: bool = False
    native_bridge_name: str = ""
    result_envelope: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    timestamp: float = 0.0
    side_effects_suppressed: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["middleware_decisions"] = [asdict(m) for m in self.middleware_decisions]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionTrace:
        mw_list = [MiddlewareDecision(**m) for m in d.pop("middleware_decisions", [])]
        return cls(**d, middleware_decisions=mw_list)


class ReplayRecorder:
    """Records tool execution traces for deterministic replay.

    When WM_REPLAY_RECORD=1 is set, the recorder automatically
    captures traces and writes them to the replay directory.
    """

    def __init__(self, replay_dir: str | None = None) -> None:
        self._replay_dir = replay_dir or _WM_REPLAY_DIR
        self._traces: list[ExecutionTrace] = []
        self._current: ExecutionTrace | None = None
        self._t0: float = 0.0

    @property
    def traces(self) -> list[ExecutionTrace]:
        return list(self._traces)

    @property
    def last_trace(self) -> ExecutionTrace | None:
        return self._traces[-1] if self._traces else None

    @property
    def is_recording(self) -> bool:
        return self._current is not None

    def record(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> _RecordContext:
        """Context manager that records a tool execution trace."""
        return _RecordContext(self, tool_name, kwargs)

    def add_middleware_decision(self, decision: MiddlewareDecision) -> None:
        if self._current is not None:
            self._current.middleware_decisions.append(decision)

    def set_backend(self, backend: str, native_fallback: bool = False, bridge_name: str = "") -> None:
        if self._current is not None:
            self._current.backend_choice = backend
            self._current.native_fallback = native_fallback
            self._current.native_bridge_name = bridge_name

    def set_result(self, envelope: dict[str, Any]) -> None:
        if self._current is not None:
            self._current.result_envelope = envelope

    def _persist(self, trace: ExecutionTrace) -> None:
        if not self._replay_dir:
            return
        p = Path(self._replay_dir)
        p.mkdir(parents=True, exist_ok=True)
        fname = p / f"trace_{trace.trace_id}.json"
        fname.write_text(trace.to_json())

    def _begin(self, tool_name: str, kwargs: dict[str, Any]) -> None:
        self._current = ExecutionTrace(
            trace_id=str(uuid4()),
            tool_name=tool_name,
            arguments={k: v for k, v in kwargs.items() if not k.startswith("_")},
            user_id=kwargs.get("user_id", kwargs.get("_user_id", "local")),
            agent_id=kwargs.get("_agent_id", "default"),
            galaxy=kwargs.get("galaxy", kwargs.get("_galaxy", "default")),
            policy_profile=kwargs.get("_policy_profile", "default"),
            requested_mode=kwargs.get("_mode", "full"),
            timestamp=time.time(),
        )
        self._t0 = time.perf_counter()

    def _end(self, result: dict[str, Any] | None) -> ExecutionTrace:
        assert self._current is not None
        self._current.duration_s = time.perf_counter() - self._t0
        self._current.result_envelope = result or {}
        self._traces.append(self._current)
        self._persist(self._current)
        trace = self._current
        self._current = None
        return trace


class _RecordContext:
    """Context manager for recording a tool execution."""

    def __init__(self, recorder: ReplayRecorder, tool_name: str, kwargs: dict[str, Any]) -> None:
        self._recorder = recorder
        self._tool_name = tool_name
        self._kwargs = kwargs

    def __enter__(self) -> ReplayRecorder:
        self._recorder._begin(self._tool_name, self._kwargs)
        return self._recorder

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._recorder.set_result({
                "status": "error",
                "error_code": "replay_recorded_exception",
                "error_type": exc_type.__name__ if exc_type else "",
                "message": str(exc_val) if exc_val else "",
            })
        self._recorder._end(self._recorder._current.result_envelope if self._recorder._current else {})


class ReplayPlayer:
    """Replays a recorded execution trace without external side effects.

    Replay mode:
    - Suppresses write operations (dry_run=True)
    - Skips native bridge calls (uses Python fallback)
    - Skips network calls
    - Reconstructs the result from the recorded trace or re-executes
      in dry_run mode

    Usage::

        player = ReplayPlayer()
        result = player.replay(trace)
        # Or replay from file:
        result = player.replay_file("traces/trace_abc123.json")
    """

    def __init__(self) -> None:
        self._replayed: list[ExecutionTrace] = []

    @property
    def replayed_traces(self) -> list[ExecutionTrace]:
        return list(self._replayed)

    def replay(self, trace: ExecutionTrace) -> dict[str, Any]:
        """Replay a single trace, suppressing side effects."""
        logger.info("Replaying trace %s for tool %s", trace.trace_id, trace.tool_name)

        # If the trace has a recorded result, return it directly
        # (deterministic replay = same output)
        if trace.result_envelope:
            result = dict(trace.result_envelope)
            result["replayed"] = True
            result["replay_trace_id"] = trace.trace_id
            self._replayed.append(trace)
            return result

        # No recorded result — re-execute in dry_run mode
        return self._re_execute(trace)

    def replay_file(self, path: str) -> dict[str, Any]:
        """Load a trace from JSON file and replay it."""
        p = Path(path)
        data = json.loads(p.read_text())
        trace = ExecutionTrace.from_dict(data)
        return self.replay(trace)

    def replay_batch(self, traces: list[ExecutionTrace]) -> list[dict[str, Any]]:
        """Replay multiple traces in order."""
        return [self.replay(t) for t in traces]

    def _re_execute(self, trace: ExecutionTrace) -> dict[str, Any]:
        """Re-execute the tool call in dry_run mode."""
        try:
            from whitemagic.tools.dispatch_table import dispatch

            kwargs = dict(trace.arguments)
            kwargs["dry_run"] = True
            kwargs["_user_id"] = trace.user_id
            kwargs["_agent_id"] = trace.agent_id
            kwargs["_galaxy"] = trace.galaxy
            kwargs["_policy_profile"] = trace.policy_profile

            result = dispatch(trace.tool_name, **kwargs)
            if isinstance(result, dict):
                result["replayed"] = True
                result["replay_trace_id"] = trace.trace_id
                result["side_effects_suppressed"] = True
                self._replayed.append(trace)
                return result
            return {
                "status": "error",
                "error_code": "replay_no_result",
                "message": f"Replay of {trace.tool_name} returned no result",
                "replay_trace_id": trace.trace_id,
            }
        except Exception as e:
            logger.warning("Replay re-execute failed for %s: %s", trace.tool_name, e)
            return {
                "status": "error",
                "error_code": "replay_execution_error",
                "message": str(e),
                "replay_trace_id": trace.trace_id,
            }


# Singleton recorder for global recording
_recorder: ReplayRecorder | None = None


def get_recorder() -> ReplayRecorder:
    """Get the global ReplayRecorder singleton."""
    global _recorder
    if _recorder is None:
        _recorder = ReplayRecorder()
    return _recorder


def is_replay_recording() -> bool:
    """Check if replay recording is enabled via env var."""
    return os.environ.get(_WM_REPLAY_RECORD, "0") in ("1", "true", "yes")
