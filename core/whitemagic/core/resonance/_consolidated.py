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
    # Core resonance events
    """EventType: event type.
    
    Enumeration.
    
    Members:
        INTERNAL_STATE_CHANGED
        EMERGENCE_DETECTED
        CASCADE_TRIGGERED
        SYMPATHETIC_RESONANCE
        BEAUTY_DETECTED
        JOY_TRIGGERED
        LOVE_ACTIVATED
        SYSTEM_STARTED
        SYSTEM_STOPPED
        SYSTEM_HEARTBEAT
        SYSTEM_STATE_CHANGE
        MEMORY_CREATED
        MEMORY_RECALLED
        MEMORY_ACCESSED
        MEMORY_CONSOLIDATED
        PATTERN_DETECTED
        PATTERN_CONFIRMED
        PATTERN_REJECTED
        PATTERN_DISCOVERED
        PATTERN_EXTRACTED
        PATTERN_IN_READING
        NOVEL_PATTERN
        ORACLE_CAST
        CLONE_SEARCH_COMPLETE
        VOICE_EXPRESSED
        STORY_TOLD
        GARDEN_ACTIVATED
        GARDEN_ACTIVITY
        GARDEN_RESONANCE
        COURAGE_SHOWN
        TRUTH_SPOKEN
        WONDER_SPARKED
        GRATITUDE_FELT
        WISDOM_INTEGRATED
        MYSTERY_EMBRACED
        CONNECTION_DEEPENED
        RESONANCE_AMPLIFIED
        AWE_FELT
        TRANSCENDENCE_EXPERIENCED
        PLAY_INITIATED
        EXPLORATION_STARTED
        BOND_FORMED
        HABIT_FORMED
        MOMENT_ATTENDED
        COMPASSION_FELT
        TEACHING_OFFERED
        PATIENCE_PRACTICED
        JOY_DETECTED
        JOY_AMPLIFIED
        GRIEF_FELT
        LOSS_ACKNOWLEDGED
        MOURNING_HONORED
        COMMUNITY_GATHERED
        COLLECTIVE_WISDOM
        SHARED_PRACTICE
        INTEGRITY_MAINTAINED
        HONESTY_PRACTICED
        GROUNDING_ESTABLISHED
        DHARMA_ASSESSED
        BOUNDARY_VIOLATED
        BOUNDARY_DETECTED
        BOUNDARY_SET
        ANOMALY_DETECTED
        WARNING_ISSUED
        SOLUTION_FOUND
        HEXAGRAM_CAST
        MINDFULNESS_ACHIEVED
        DREAM_STATE_ENTERED
        CREATIVE_BRIDGE_LOW_CONFIDENCE
        INSIGHT_FLASH
        THREAT_DETECTED
        THREAT_HEALED
        ANTIBODY_APPLIED
        SYNCHRONICITY
        PHASE_TRANSITION
        ELEMENT_SHIFT
        ZODIAC_PHASE_CHANGE
        BALANCE_SHIFT
        LEARNING_COMPLETED
        BROKER_DISCONNECTED
        TASK_FAILED
        AGENT_DEREGISTERED
        VOTE_CONSENSUS_REACHED
        VOTE_SESSION_CLOSED
        TASK_CREATED
        BROKER_MESSAGE_PUBLISHED"""
    INTERNAL_STATE_CHANGED = "internal_state_changed"
    EMERGENCE_DETECTED = "emergence_detected"
    CASCADE_TRIGGERED = "cascade_triggered"
    SYMPATHETIC_RESONANCE = "sympathetic_resonance"
    BEAUTY_DETECTED = "beauty_detected"
    JOY_TRIGGERED = "joy_triggered"
    LOVE_ACTIVATED = "love_activated"

    # System lifecycle
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    SYSTEM_HEARTBEAT = "system_heartbeat"
    SYSTEM_STATE_CHANGE = "system_state_change"

    # Memory events
    MEMORY_CREATED = "memory_created"
    MEMORY_RECALLED = "memory_recalled"
    MEMORY_ACCESSED = "memory_accessed"
    MEMORY_CONSOLIDATED = "memory_consolidated"

    # Pattern events
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_CONFIRMED = "pattern_confirmed"
    PATTERN_REJECTED = "pattern_rejected"
    PATTERN_DISCOVERED = "pattern_discovered"
    PATTERN_EXTRACTED = "pattern_extracted"
    PATTERN_IN_READING = "pattern_in_reading"
    NOVEL_PATTERN = "novel_pattern"

    # Voice narration events
    ORACLE_CAST = "oracle_cast"
    CLONE_SEARCH_COMPLETE = "clone_search_complete"
    VOICE_EXPRESSED = "voice_expressed"
    STORY_TOLD = "story_told"

    # Garden events
    GARDEN_ACTIVATED = "garden_activated"
    GARDEN_ACTIVITY = "garden_activity"
    GARDEN_RESONANCE = "garden_resonance"

    # Emotional/virtue events
    COURAGE_SHOWN = "courage_shown"
    TRUTH_SPOKEN = "truth_spoken"
    WONDER_SPARKED = "wonder_sparked"
    GRATITUDE_FELT = "gratitude_felt"
    WISDOM_INTEGRATED = "wisdom_integrated"
    MYSTERY_EMBRACED = "mystery_embraced"
    CONNECTION_DEEPENED = "connection_deepened"
    RESONANCE_AMPLIFIED = "resonance_amplified"
    AWE_FELT = "awe_felt"
    TRANSCENDENCE_EXPERIENCED = "transcendence_experienced"
    PLAY_INITIATED = "play_initiated"
    EXPLORATION_STARTED = "exploration_started"
    BOND_FORMED = "bond_formed"
    HABIT_FORMED = "habit_formed"
    MOMENT_ATTENDED = "moment_attended"
    COMPASSION_FELT = "compassion_felt"
    TEACHING_OFFERED = "teaching_offered"
    PATIENCE_PRACTICED = "patience_practiced"
    JOY_DETECTED = "joy_detected"
    JOY_AMPLIFIED = "joy_amplified"
    GRIEF_FELT = "grief_felt"
    LOSS_ACKNOWLEDGED = "loss_acknowledged"
    MOURNING_HONORED = "mourning_honored"

    # Community events
    COMMUNITY_GATHERED = "community_gathered"
    COLLECTIVE_WISDOM = "collective_wisdom"
    SHARED_PRACTICE = "shared_practice"

    # Dharma/ethics events
    INTEGRITY_MAINTAINED = "integrity_maintained"
    HONESTY_PRACTICED = "honesty_practiced"
    GROUNDING_ESTABLISHED = "grounding_established"
    DHARMA_ASSESSED = "dharma_assessed"
    BOUNDARY_VIOLATED = "boundary_violated"
    BOUNDARY_DETECTED = "boundary_detected"
    BOUNDARY_SET = "boundary_set"
    ANOMALY_DETECTED = "anomaly_detected"
    WARNING_ISSUED = "warning_issued"
    SOLUTION_FOUND = "solution_found"

    # Oracle/divination events
    HEXAGRAM_CAST = "hexagram_cast"
    MINDFULNESS_ACHIEVED = "mindfulness_achieved"

    # Dream/intelligence events
    DREAM_STATE_ENTERED = "dream_state_entered"
    CREATIVE_BRIDGE_LOW_CONFIDENCE = "creative_bridge_low_confidence"
    INSIGHT_FLASH = "insight_flash"
    THREAT_DETECTED = "threat_detected"
    THREAT_HEALED = "threat_healed"
    ANTIBODY_APPLIED = "antibody_applied"
    SYNCHRONICITY = "synchronicity"

    # Phase/transition events
    PHASE_TRANSITION = "phase_transition"
    ELEMENT_SHIFT = "element_shift"
    ZODIAC_PHASE_CHANGE = "zodiac_phase_change"
    BALANCE_SHIFT = "balance_shift"

    # Learning events
    LEARNING_COMPLETED = "learning_completed"

    # Agent / broker / task events (for temporal scheduler)
    BROKER_DISCONNECTED = "broker_disconnected"
    TASK_FAILED = "task_failed"
    AGENT_DEREGISTERED = "agent_deregistered"
    VOTE_CONSENSUS_REACHED = "vote_consensus_reached"
    VOTE_SESSION_CLOSED = "vote_session_closed"
    TASK_CREATED = "task_created"
    BROKER_MESSAGE_PUBLISHED = "broker_message_published"

@dataclass
class ResonanceEvent:
    """ResonanceEvent: resonance event.
    
    Value object: equality and repr are field-based."""
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
        """
        Perform the emit operation.
        
        Args:
            event: Parameter description.
        """
        with self._lock:
            self._history.append(event)
            if len(self._history) > 1000: self._history.pop(0)

        # Dispatch to listeners
        listeners = self._listeners.get(event.event_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.debug("Listener dispatch failed: %s", e)

    def listen(self, event_type: EventType, callback: Callable):
        """
        Perform the listen operation.
        
        Args:
            event_type: Parameter description.
            callback: Parameter description.
        """
        with self._lock:
            if event_type not in self._listeners: self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

# --- SINGLETONS ---
_bus: GanYingBus | None = None

def get_bus() -> GanYingBus:
    """
    Get the bus.
    
    Returns:
        GanYingBus
    """
    global _bus
    if _bus is None: _bus = GanYingBus()
    return _bus

get_event_bus = get_bus # Compatibility alias

def emit_event(*args, **kwargs):
    """
    Emit an event for event.
    """
    if args and isinstance(args[0], EventType):
        kwargs["event_type"] = args[0]
        if len(args) > 1: kwargs["data"] = args[1]
        if len(args) > 2: kwargs["source"] = args[2]
    elif args and isinstance(args[0], str):
        kwargs["source"] = args[0]
        if len(args) > 1: kwargs["event_type"] = args[1]
        if len(args) > 2: kwargs["data"] = args[2]
    if "source" not in kwargs: kwargs["source"] = "system"
    if "event_type" not in kwargs or not isinstance(kwargs["event_type"], EventType):
        kwargs["event_type"] = EventType.SYSTEM_HEARTBEAT
    get_bus().emit(ResonanceEvent(**kwargs))
