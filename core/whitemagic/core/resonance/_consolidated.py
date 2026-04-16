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
"""Resonance Subsystem (Consolidated v3.2).
=========================================
Unified gateway for Gan Ying event bus, cascade protocols, and salience arbitration.

Consolidated from resonance/ sub-package. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# --- TYPES ---

class EventType(Enum):
    INTERNAL_STATE_CHANGED = "internal_state_changed"
    EMERGENCE_DETECTED = "emergence_detected"
    CASCADE_TRIGGERED = "cascade_triggered"
    SYMPATHETIC_RESONANCE = "sympathetic_resonance"
    BEAUTY_DETECTED = "beauty_detected"
    JOY_TRIGGERED = "joy_triggered"
    LOVE_ACTIVATED = "love_activated"

@dataclass
class ResonanceEvent:
    source: str
    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    cascade_depth: int = 0
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

# --- GAN YING BUS ---

class GanYingBus:
    """Enhanced event bus for resonant communication and emergent pattern detection."""
    def __init__(self):
        self._listeners: dict[EventType, list[Callable]] = {}
        self._history: list[ResonanceEvent] = []
        self._lock = threading.Lock()

    def emit(self, event: ResonanceEvent):
        with self._lock:
            self._history.append(event)
            if len(self._history) > 1000: self._history.pop(0)

        # Dispatch to listeners
        listeners = self._listeners.get(event.event_type, [])
        for listener in listeners:
            try: listener(event)
            except Exception: pass

    def listen(self, event_type: EventType, callback: Callable):
        with self._lock:
            if event_type not in self._listeners: self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

# --- SINGLETONS ---
_bus: GanYingBus | None = None

def get_bus() -> GanYingBus:
    global _bus
    if _bus is None: _bus = GanYingBus()
    return _bus

get_event_bus = get_bus # Compatibility alias

def emit_event(source: str, event_type: EventType, data: dict[str, Any]):
    get_bus().emit(ResonanceEvent(source=source, event_type=event_type, data=data))
