"""Current State Tracker — Living short-term context for AI agents.

Maintains a dynamic, auto-updated snapshot of the current work state:
- Current task/objective
- Recent file modifications
- Active goals and next steps
- Last session summary
- Working memory contents (persisted across sessions)

This replaces reliance on static .md docs (AGENTS.md, strategy docs) for
short-term context. Instead of reading potentially-stale documentation,
AI agents query the current state tracker for an accurate, live picture
of what's happening and what to work on next.

Design principles:
1. **Auto-capture** — state updates automatically as work happens, no manual calls needed
2. **Memory-backed** — state is stored both as a JSON file (fast access) and as a
   memory in the sessions galaxy (searchable, associative)
3. **Injected on connect** — state is injected into MCP server instructions so
   AI clients get context immediately on connecting
4. **Queryable** — the `state.current` MCP tool returns the full snapshot
5. **Bounded** — recent activity is capped to prevent unbounded growth

Persistence:
- JSON state file: WM_ROOT/state/current_state.json
- Memory record: sessions galaxy, tagged "current_state"
- Working memory: WM_ROOT/state/working_memory.json
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

_STATE_DIR = WM_ROOT / "state"
_STATE_FILE = _STATE_DIR / "current_state.json"
_WM_FILE = _STATE_DIR / "working_memory.json"
_MAX_RECENT_FILES = 20
_MAX_RECENT_EVENTS = 50
_MAX_NEXT_STEPS = 10
_MAX_ACTIVE_TASKS = 5
_STATE_MEMORY_TAG = "current_state"


@dataclass
class StateEvent:
    """A single state change event."""
    timestamp: str
    event_type: str  # "file_modified", "task_started", "task_completed", "decision", "error"
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class CurrentState:
    """The current work state snapshot."""
    # What's being worked on right now
    current_task: str = ""
    current_task_started: str = ""

    # Active tasks (not yet completed)
    active_tasks: list[str] = field(default_factory=list)

    # What to work on next
    next_steps: list[str] = field(default_factory=list)

    # Recent file modifications (path, timestamp)
    recent_files: list[dict[str, str]] = field(default_factory=list)

    # Recent state change events
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    # Last session summary
    last_session_summary: str = ""
    last_session_id: str = ""
    last_session_ended: str = ""

    # Working context (key-value pairs set by AI or tools)
    context: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_task": self.current_task,
            "current_task_started": self.current_task_started,
            "active_tasks": self.active_tasks,
            "next_steps": self.next_steps,
            "recent_files": self.recent_files,
            "recent_events": self.recent_events,
            "last_session_summary": self.last_session_summary,
            "last_session_id": self.last_session_id,
            "last_session_ended": self.last_session_ended,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CurrentState:
        return cls(
            current_task=d.get("current_task", ""),
            current_task_started=d.get("current_task_started", ""),
            active_tasks=d.get("active_tasks", []),
            next_steps=d.get("next_steps", []),
            recent_files=d.get("recent_files", []),
            recent_events=d.get("recent_events", []),
            last_session_summary=d.get("last_session_summary", ""),
            last_session_id=d.get("last_session_id", ""),
            last_session_ended=d.get("last_session_ended", ""),
            context=d.get("context", {}),
            created_at=d.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=d.get("updated_at", datetime.now(UTC).isoformat()),
        )

    def to_context_block(self) -> str:
        """Format as a context block for MCP server instructions injection."""
        lines: list[str] = []
        lines.append("## Current Work State")
        lines.append("")

        if self.current_task:
            lines.append(f"**Current task**: {self.current_task}")
            if self.current_task_started:
                lines.append(f"  (started: {self.current_task_started})")
            lines.append("")

        if self.active_tasks:
            lines.append(f"**Active tasks** ({len(self.active_tasks)}):")
            for t in self.active_tasks[:_MAX_ACTIVE_TASKS]:
                lines.append(f"  - {t}")
            lines.append("")

        if self.next_steps:
            lines.append(f"**Next steps** ({len(self.next_steps)}):")
            for i, step in enumerate(self.next_steps[:_MAX_NEXT_STEPS], 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        if self.recent_files:
            lines.append(f"**Recently modified files** ({len(self.recent_files)}):")
            for f in self.recent_files[-10:]:
                lines.append(f"  - {f.get('path', '?')} ({f.get('timestamp', '?')})")
            lines.append("")

        if self.last_session_summary:
            lines.append(f"**Last session**: {self.last_session_summary}")
            if self.last_session_ended:
                lines.append(f"  (ended: {self.last_session_ended})")
            lines.append("")

        if self.context:
            lines.append("**Context**:")
            for k, v in self.context.items():
                lines.append(f"  - {k}: {v}")
            lines.append("")

        if self.recent_events:
            lines.append(f"**Recent events** ({len(self.recent_events)}):")
            for e in self.recent_events[-5:]:
                lines.append(f"  - [{e.get('event_type', '?')}] {e.get('description', '?')}")
            lines.append("")

        lines.append("Use `state.current` to get the full live state. Use `state.update` to modify it.")
        return "\n".join(lines)


class CurrentStateTracker:
    """Singleton tracker for the current work state.

    Auto-persists to disk on every update. Thread-safe.
    """

    _instance: CurrentStateTracker | None = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._state = CurrentState()
        self._state_lock = threading.RLock()
        self._load()

    @classmethod
    def get_instance(cls) -> CurrentStateTracker:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        """Load state from disk."""
        if _STATE_FILE.exists():
            try:
                data = _json_loads(_STATE_FILE.read_text(encoding="utf-8"))
                self._state = CurrentState.from_dict(data)
                logger.debug("Current state loaded from %s", _STATE_FILE)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to load current state: %s", e)

    def _save(self) -> None:
        """Save state to disk."""
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._state.updated_at = datetime.now(UTC).isoformat()
        try:
            _STATE_FILE.write_text(
                _json_dumps(self._state.to_dict(), indent=2),
                encoding="utf-8",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to save current state: %s", e)

    def _save_memory(self) -> None:
        """Save state as a memory in the sessions galaxy (best-effort)."""
        try:
            from whitemagic.core.memory.unified import remember
            from whitemagic.core.memory.unified_types import MemoryType

            remember(
                content=self._state.to_context_block(),
                title="Current Work State",
                memory_type=MemoryType.SHORT_TERM,
                tags={_STATE_MEMORY_TAG, "state", "short_term"},
                importance=0.9,
                galaxy="sessions",
            )
        except Exception:  # noqa: BLE001
            logger.debug("State memory save failed (best-effort)", exc_info=True)

    def _add_event(self, event_type: str, description: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a state change event."""
        event = StateEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type=event_type,
            description=description,
            metadata=metadata or {},
        )
        self._state.recent_events.append(event.to_dict())
        if len(self._state.recent_events) > _MAX_RECENT_EVENTS:
            self._state.recent_events = self._state.recent_events[-_MAX_RECENT_EVENTS:]

    # ── Public API ───────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        """Get the current state as a dict."""
        with self._state_lock:
            return self._state.to_dict()

    def get_context_block(self) -> str:
        """Get the current state as a formatted context block for injection."""
        with self._state_lock:
            return self._state.to_context_block()

    def set_current_task(self, task: str) -> None:
        """Set the current task/objective."""
        with self._state_lock:
            if self._state.current_task and self._state.current_task != task:
                self._add_event("task_switch", f"Switched from '{self._state.current_task}' to '{task}'")
            self._state.current_task = task
            self._state.current_task_started = datetime.now(UTC).isoformat()
            self._add_event("task_started", f"Task started: {task}")
            self._save()
        self._save_memory()

    def complete_task(self, task: str) -> None:
        """Mark a task as completed."""
        with self._state_lock:
            if task in self._state.active_tasks:
                self._state.active_tasks.remove(task)
            if self._state.current_task == task:
                self._state.current_task = ""
            self._add_event("task_completed", f"Task completed: {task}")
            self._save()
        self._save_memory()

    def add_active_task(self, task: str) -> None:
        """Add an active task."""
        with self._state_lock:
            if task not in self._state.active_tasks:
                self._state.active_tasks.append(task)
                if len(self._state.active_tasks) > _MAX_ACTIVE_TASKS:
                    self._state.active_tasks = self._state.active_tasks[-_MAX_ACTIVE_TASKS:]
                self._add_event("task_added", f"Active task added: {task}")
                self._save()
        self._save_memory()

    def add_next_step(self, step: str) -> None:
        """Add a next step."""
        with self._state_lock:
            if step not in self._state.next_steps:
                self._state.next_steps.append(step)
                if len(self._state.next_steps) > _MAX_NEXT_STEPS:
                    self._state.next_steps = self._state.next_steps[-_MAX_NEXT_STEPS:]
                self._save()
        self._save_memory()

    def record_file_modification(self, path: str, description: str = "") -> None:
        """Record a file modification."""
        with self._state_lock:
            entry = {
                "path": path,
                "timestamp": datetime.now(UTC).isoformat(),
                "description": description,
            }
            # Remove existing entry for same path (avoid duplicates)
            self._state.recent_files = [f for f in self._state.recent_files if f.get("path") != path]
            self._state.recent_files.append(entry)
            if len(self._state.recent_files) > _MAX_RECENT_FILES:
                self._state.recent_files = self._state.recent_files[-_MAX_RECENT_FILES:]
            self._add_event("file_modified", f"Modified: {path}", {"description": description} if description else {})
            self._save()
        self._save_memory()

    def set_context(self, key: str, value: Any) -> None:
        """Set a context key-value pair."""
        with self._state_lock:
            self._state.context[key] = value
            self._save()
        self._save_memory()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        with self._state_lock:
            return self._state.context.get(key, default)

    def update_from_session_handoff(
        self,
        summary: str,
        next_steps: list[str],
        active_tasks: list[str],
        session_id: str = "",
        files_modified: list[str] | None = None,
    ) -> None:
        """Update state from a session handoff."""
        with self._state_lock:
            self._state.last_session_summary = summary
            self._state.last_session_id = session_id
            self._state.last_session_ended = datetime.now(UTC).isoformat()
            if next_steps:
                self._state.next_steps = next_steps[:_MAX_NEXT_STEPS]
            if active_tasks:
                self._state.active_tasks = active_tasks[:_MAX_ACTIVE_TASKS]
            if files_modified:
                for f in files_modified:
                    entry = {
                        "path": f,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "description": "from previous session",
                    }
                    self._state.recent_files = [x for x in self._state.recent_files if x.get("path") != f]
                    self._state.recent_files.append(entry)
                if len(self._state.recent_files) > _MAX_RECENT_FILES:
                    self._state.recent_files = self._state.recent_files[-_MAX_RECENT_FILES:]
            self._add_event("session_handoff", f"Loaded handoff from session {session_id}")
            self._save()
        self._save_memory()

    def record_decision(self, decision: str, rationale: str = "") -> None:
        """Record a decision made during work."""
        with self._state_lock:
            self._add_event("decision", decision, {"rationale": rationale} if rationale else {})
            self._save()
        self._save_memory()

    def record_error(self, error: str, context: str = "") -> None:
        """Record an error encountered during work."""
        with self._state_lock:
            self._add_event("error", error, {"context": context} if context else {})
            self._save()
        self._save_memory()

    def clear_next_steps(self) -> None:
        """Clear all next steps (after they've been addressed)."""
        with self._state_lock:
            self._state.next_steps = []
            self._save()
        self._save_memory()

    def update(self, **kwargs: Any) -> None:
        """Generic update method for MCP tool."""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key) and value is not None:
                    setattr(self._state, key, value)
            self._save()
        self._save_memory()


def get_state_tracker() -> CurrentStateTracker:
    """Get the global CurrentStateTracker singleton."""
    return CurrentStateTracker.get_instance()
