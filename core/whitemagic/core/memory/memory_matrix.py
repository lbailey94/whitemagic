# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Memory Matrix - Consolidated v14.5.
====================================
Unified subsystem for tracking interactions, seen files, and session continuity.
Consolidated from memory_matrix/ sub-package. Part of Milestone 4.3.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads
from whitemagic.utils.fileio import atomic_write, file_lock

logger = logging.getLogger(__name__)

# --- COMPONENT: SEEN REGISTRY ---

@dataclass
class SeenEntry:
    path: str
    last_seen: str
    file_type: str
    content_hash: str | None = None
    times_seen: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

class SeenRegistry:
    """Tracks files and resources viewed by the user or system."""
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or (WM_ROOT / "matrix" / "seen.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, SeenEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with file_lock(self.storage_path):
                    data = _json_loads(self.storage_path.read_text()) or {}
                for path, entry_data in data.items():
                    self._entries[path] = SeenEntry(**entry_data)
            except Exception as e:
                logger.debug("Memory matrix load failed: %s", e)

    def _save(self) -> None:
        data = {path: asdict(entry) for path, entry in self._entries.items()}
        with file_lock(self.storage_path):
            atomic_write(self.storage_path, _json_dumps(data, indent=2))

    def mark_seen(self, path: str, content_hash: str | None = None, context: str | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        if path in self._entries:
            entry = self._entries[path]
            entry.last_seen = now
            entry.times_seen += 1
            if content_hash: entry.content_hash = content_hash
        else:
            suffix = Path(path).suffix.lower() if "." in path else "unknown"
            self._entries[path] = SeenEntry(
                path=path, last_seen=now, file_type=suffix, content_hash=content_hash
            )
        if context: self._entries[path].metadata["last_context"] = context
        self._save()

    def have_seen(self, path: str) -> bool: return path in self._entries
    def stats(self) -> dict[str, Any]: return {"total_seen": len(self._entries)}
    def get_recent(self, limit: int = 10) -> list[SeenEntry]:
        return sorted(self._entries.values(), key=lambda e: e.last_seen, reverse=True)[:limit]

# --- COMPONENT: TIMELINE ---

@dataclass
class TimelineEvent:
    id: str
    timestamp: str
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict: return asdict(self)
    @classmethod
    def from_dict(cls, data: dict) -> TimelineEvent: return cls(**data)

class ChronologicalTimeline:
    """Time-based memory organization."""
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or (WM_ROOT / "matrix" / "timeline.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[TimelineEvent] = []
        self._event_counter = 0
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with file_lock(self.storage_path):
                    data = _json_loads(self.storage_path.read_text())
                self._events = [TimelineEvent.from_dict(e) for e in data.get("events", [])]
                self._event_counter = data.get("counter", len(self._events))
            except Exception as e:
                logger.debug("Timeline load failed: %s", e)

    def _save(self) -> None:
        data = {
            "version": "1.0",
            "updated": datetime.now(UTC).isoformat(),
            "counter": self._event_counter,
            "total_events": len(self._events),
            "events": [e.to_dict() for e in self._events],
        }
        with file_lock(self.storage_path):
            atomic_write(self.storage_path, _json_dumps(data, indent=2))

    def add_event(self, event_type: str, data: dict[str, Any] | None = None, tags: list[str] | None = None, timestamp: str | None = None) -> TimelineEvent:
        self._event_counter += 1
        event = TimelineEvent(
            id=f"evt_{self._event_counter}",
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            event_type=event_type,
            data=data or {},
            tags=tags or [],
        )
        self._events.append(event)
        self._save()
        return event

    def get_by_tag(self, tag: str) -> list[TimelineEvent]:
        return [e for e in self._events if tag in e.tags]
    def stats(self) -> dict[str, Any]: return {"total_events": len(self._events)}

# --- COMPONENT: EMBEDDING INDEX (Simplified) ---

class SimpleEmbeddingIndex:
    """Lightweight embedding index for file content."""
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or (WM_ROOT / "matrix" / "embeddings.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, list[float]] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with file_lock(self.storage_path):
                    self._index = _json_loads(self.storage_path.read_text()) or {}
            except Exception as e:
                logger.debug("Embedding index load failed: %s", e)

    def stats(self) -> dict[str, Any]: return {"total_embeddings": len(self._index)}
    def search(self, query: str, limit: int = 10) -> list[tuple[str, float, str]]:
        """Search memory matrix — not yet implemented."""
        raise NotImplementedError("MemoryMatrix search is not yet implemented.")

# --- HUB: MEMORY MATRIX ---

@dataclass
class SessionContext:
    session_id: str
    started: str
    last_activity: str
    interactions: int = 0
    files_seen: int = 0
    memories_accessed: int = 0
    searches_performed: int = 0

class MemoryMatrix:
    """Unified memory management system hub."""
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or (WM_ROOT / "matrix")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.seen = SeenRegistry(self.storage_dir / "seen.json")
        self.embeddings = SimpleEmbeddingIndex(self.storage_dir / "embeddings.json")
        self.timeline = ChronologicalTimeline(self.storage_dir / "timeline.json")
        self._session: SessionContext | None = None
        self._load_session()

    def _load_session(self) -> None:
        session_file = self.storage_dir / "current_session.json"
        if session_file.exists():
            try:
                with file_lock(session_file):
                    data = _json_loads(session_file.read_text()) or {}
                allowed = {f.name for f in fields(SessionContext)}
                filtered = {k: v for k, v in data.items() if k in allowed}
                if {"session_id", "started", "last_activity"}.issubset(filtered.keys()):
                    self._session = SessionContext(**filtered)
                else: self._new_session()
            except Exception as e:
                logger.debug("Session load failed: %s", e)
                self._new_session()
        else: self._new_session()

    def _new_session(self) -> None:
        now = datetime.now(UTC).isoformat()
        self._session = SessionContext(
            session_id=f"session_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            started=now,
            last_activity=now,
        )
        self._save_session()
        self.timeline.add_event("session_start", {"session_id": self._session.session_id}, tags=["session", "start"])

    def _save_session(self) -> None:
        if self._session:
            session_file = self.storage_dir / "current_session.json"
            data = asdict(self._session)
            with file_lock(session_file):
                atomic_write(session_file, _json_dumps(data, indent=2))

    def record_interaction(self, interaction_type: str, target: str, data: dict[str, Any] | None = None, context: str | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        if self._session:
            self._session.last_activity = now
            self._session.interactions += 1
        self.timeline.add_event(interaction_type, {"target": target, "context": context, "session_id": self._session.session_id if self._session else None, **(data or {})}, tags=[interaction_type, "interaction"])
        if interaction_type in ("read_file", "view_image"):
            self.seen.mark_seen(target, context=context)
            if self._session: self._session.files_seen += 1
        self._save_session()

    def stats(self) -> dict[str, Any]:
        return {
            "seen_registry": self.seen.stats(),
            "embedding_index": self.embeddings.stats(),
            "timeline": self.timeline.stats(),
            "current_session": asdict(self._session) if self._session else None,
        }

# --- SINGLETONS ---
_matrix_instance: MemoryMatrix | None = None
_matrix_lock = Lock()

def get_matrix() -> MemoryMatrix:
    global _matrix_instance
    with _matrix_lock:
        if _matrix_instance is None: _matrix_instance = MemoryMatrix()
        return _matrix_instance
