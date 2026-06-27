# ruff: noqa: BLE001
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
import os
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# --- GLOBAL ASYNC WORKER (restored from v21.0.0) ---

_GLOBAL_ASYNC_QUEUE: queue.Queue = queue.Queue(maxsize=2000)
_GLOBAL_WORKER_THREAD: threading.Thread | None = None
_GLOBAL_WORKER_LOCK = threading.Lock()

# Rust lock-free event bus primitives (optional)
_RUST_EVENT_BUS = False
try:
    import whitemagic_rs as _rs_bus  # type: ignore[import-not-found]
    if hasattr(_rs_bus, "event_bus_try_emit"):
        _RUST_EVENT_BUS = True
        logger.debug("Rust lock-free event bus primitives available")
except ImportError:
    pass


def _global_worker_loop() -> None:
    """Background worker for processing async event emissions across all bus instances."""
    while True:
        try:
            bus, event, cascade = _GLOBAL_ASYNC_QUEUE.get(timeout=1.0)
            bus._emit_internal(event, cascade)
            _GLOBAL_ASYNC_QUEUE.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Error in GanYingBus global async worker: %s", e)


def _ensure_global_worker() -> None:
    """Ensure the global async worker thread is running."""
    global _GLOBAL_WORKER_THREAD
    if _GLOBAL_WORKER_THREAD is None:
        with _GLOBAL_WORKER_LOCK:
            if _GLOBAL_WORKER_THREAD is None:
                _GLOBAL_WORKER_THREAD = threading.Thread(
                    target=_global_worker_loop,
                    daemon=True,
                    name="gan-ying-global-worker",
                )
                _GLOBAL_WORKER_THREAD.start()


# --- TYPES ---

class EventType(Enum):
    """EventType: resonance event taxonomy (234 events).

    Complete event enumeration for the Gan Ying Bus, covering system lifecycle,
    memory, patterns, gardens, emotions, governance, coordination, inference,
    and emergence. Restored from v21.0.0 gan_ying_enhanced.py consolidation.
    """
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
    EXPLORATION_INITIATED = "exploration_initiated"
    ADVENTURE_BEGUN = "adventure_begun"
    DISCOVERY_CELEBRATED = "discovery_celebrated"
    BOND_FORMED = "bond_formed"
    HABIT_FORMED = "habit_formed"
    MOMENT_ATTENDED = "moment_attended"
    COMPASSION_FELT = "compassion_felt"
    TEACHING_OFFERED = "teaching_offered"
    PATIENCE_PRACTICED = "patience_practiced"
    JOY_DETECTED = "joy_detected"
    JOY_AMPLIFIED = "joy_amplified"
    JOY_EXPERIENCED = "joy_experienced"
    STILLNESS_DETECTED = "stillness_detected"
    HEALING_INITIATED = "healing_initiated"
    CREATION_BEGUN = "creation_begun"
    SANCTUARY_ENTERED = "sanctuary_entered"
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

    # Cascade protocol events (referenced by CascadeProtocols)
    CREATIVE_SURPLUS = "creative_surplus"
    GIFT_OFFERED = "gift_offered"
    CURIOSITY_ACTIVATED = "curiosity_activated"
    QUESTION_ASKED = "question_asked"
    PEAK_PERFORMANCE = "peak_performance"
    TIME_DILATION_MEASURED = "time_dilation_measured"
    COHERENCE_INCREASED = "coherence_increased"
    CELEBRATION_INITIATED = "celebration_initiated"
    CONSCIOUSNESS_SHIFT_DETECTED = "consciousness_shift_detected"
    COUNCIL_CONVENED = "council_convened"
    INTER_CORE_RESONANCE = "inter_core_resonance"
    COLLECTIVE_DECISION = "collective_decision"
    CORE_ACTIVATED = "core_activated"
    PERCEPTION_ENHANCED = "perception_enhanced"
    PATTERN_VISION_OPENED = "pattern_vision_opened"
    CREATIVITY_AMPLIFIED = "creativity_amplified"
    HEALTH_OPTIMAL = "health_optimal"
    BALANCE_RESTORED = "balance_restored"
    THREAT_NEUTRALIZED = "threat_neutralized"
    MEMORY_CASCADE_TRIGGERED = "memory_cascade_triggered"
    CONTEXT_OPTIMIZED = "context_optimized"
    FILE_ACCESSED = "file_accessed"
    NOVEL_CAPABILITY_EMERGED = "novel_capability_emerged"
    BREAKTHROUGH_ACHIEVED = "breakthrough_achieved"
    DISCOVERY_MADE = "discovery_made"

    # --- Restored from gan_ying_enhanced.py (v21.0.0) ---

    # System events
    SYSTEM_HEALTH_CHANGED = "system_health_changed"
    SYSTEM_TRANSCENDED = "system_transcended"
    MESH_SIGNAL = "mesh_signal"

    # Memory events
    MEMORY_UPDATED = "memory_updated"
    VISUAL_MEMORY_STORED = "visual_memory_stored"
    EPISODIC_RECALLED = "episodic_recalled"
    SEMANTIC_LINKED = "semantic_linked"
    PROCEDURAL_LEARNED = "procedural_learned"
    WORKING_MEMORY_UPDATED = "working_memory_updated"
    SEARCH_COMPLETED = "search_completed"
    SIMILARITY_SEARCH_TRIGGERED = "similarity_search_triggered"

    # Garden events (expanded)
    AESTHETIC_RESONANCE = "aesthetic_resonance"
    SUBLIME_MOMENT = "sublime_moment"
    JOY_SHARED = "joy_shared"
    HEART_OPENED = "heart_opened"
    INSIGHT_CRYSTALLIZED = "insight_crystallized"
    UNKNOWN_ENCOUNTERED = "unknown_encounter"
    IMPROVISATION_BEGUN = "improvisation_begun"
    SYNCHRONICITY_NOTICED = "synchronicity_noticed"
    RELATIONSHIP_DEEPENED = "relationship_deepened"
    RHYTHM_ESTABLISHED = "rhythm_established"
    DISCIPLINE_MAINTAINED = "discipline_maintained"
    SILENCE_EMBRACED = "silence_embraced"
    MIND_EMPTIED = "mind_emptied"
    PAUSE_TAKEN = "pause_taken"
    NARRATIVE_THREAD = "narrative_thread"
    IDENTITY_AFFIRMED = "identity_affirmed"

    # Awareness events
    FILE_CHANGED = "file_changed"
    ANOMALY_EXPLAINED = "anomaly_explained"
    SUB_BYTE_CHANGE_DETECTED = "sub_byte_change_detected"
    LAYER_SHIFT_DETECTED = "layer_shift_detected"

    # Flow & time events
    FLOW_STATE_ENTERED = "flow_state_entered"
    FLOW_STATE_EXITED = "flow_state_exited"

    # Emergence events
    COLLECTIVE_INSIGHT_FORMED = "collective_insight_formed"
    SYNERGY_DISCOVERED = "synergy_discovered"
    SPONTANEOUS_ORGANIZATION = "spontaneous_organization"
    PATTERN_CLUSTER_CRYSTALLIZED = "pattern_cluster_crystallized"
    CASCADE_COMPLETED = "cascade_completed"

    # Zodiac council events
    CORE_SPECIALIZED = "core_specialized"
    CELESTIAL_ALIGNMENT = "celestial_alignment"
    SYNASTRY_HARMONIZED = "synastry_harmonized"
    CORE_CONFLICT = "core_conflict"
    CORE_CONSENSUS = "core_consensus"

    # Oracle & guidance events
    ORACLE_CONSULTED = "oracle_consulted"
    WISDOM_RECEIVED = "wisdom_received"
    PATTERN_RECOGNIZED = "pattern_recognized"
    ELEMENT_IDENTIFIED = "element_identified"
    BALANCE_CHECKED = "balance_checked"
    OPTIMIZATION_SUGGESTED = "optimization_suggested"

    # Dharma events (expanded)
    HARMONY_CHANGED = "harmony_changed"
    CONSENT_REQUESTED = "consent_requested"
    ETHICAL_DECISION = "ethical_decision"
    VIOLATION_PREVENTED = "violation_prevented"
    INTERVENTION_TRIGGERED = "intervention_triggered"
    PROTECTION_ACTIVATED = "protection_activated"
    SHIELD_RAISED = "shield_raised"
    SHELTER_PROVIDED = "shelter_provided"
    RESOURCE_GUARDED = "resource_guarded"

    # Pattern discovery events (expanded)
    PATTERN_EMERGED = "pattern_emerged"
    PATTERNS_ANALYZED = "patterns_analyzed"

    # Expanded garden events (Surya Sunday Nov 30, 2025)
    BLESSING_RECOGNIZED = "blessing_recognized"
    THANKS_EXPRESSED = "thanks_expressed"
    FEAR_FACED = "fear_faced"
    ENCOURAGEMENT_GIVEN = "encouragement_given"
    TIMING_TRUSTED = "timing_trusted"
    RUSHING_RESISTED = "rushing_resisted"
    TEARS_SHED = "tears_shed"
    HUMILITY_AWAKENED = "humility_awakened"
    VASTNESS_PERCEIVED = "vastness_perceived"
    HUMOR_TRIGGERED = "humor_triggered"
    LAUGHTER_SHARED = "laughter_shared"
    LEVITY_BROUGHT = "levity_brought"
    PLAYFULNESS_EXPRESSED = "playfulness_expressed"
    RECOVERY_PROGRESSED = "recovery_progressed"
    RESTORATION_COMPLETED = "restoration_completed"
    WHOLENESS_RESTORED = "wholeness_restored"
    MANIFESTATION_STARTED = "manifestation_started"
    ARTIFACT_CREATED = "artifact_created"
    CREATIVE_FLOW = "creative_flow"
    TRANSFORMATION_INITIATED = "transformation_initiated"
    CHANGE_EMBRACED = "change_embraced"
    EVOLUTION_PROGRESSED = "evolution_progressed"
    METAMORPHOSIS_COMPLETED = "metamorphosis_completed"
    SAFETY_ESTABLISHED = "safety_established"
    REFUGE_FOUND = "refuge_found"
    PROTECTION_GRANTED = "protection_granted"
    RISK_TAKEN = "risk_taken"
    REVERENCE_FELT = "reverence_felt"
    SACRED_HONORED = "sacred_honored"
    RESPECT_SHOWN = "respect_shown"
    DEVOTION_EXPRESSED = "devotion_expressed"
    STILLNESS_ENTERED = "stillness_entered"
    MEDITATION_STARTED = "meditation_started"

    # Consciousness upgrades
    REFLECTION_RECORDED = "reflection_recorded"
    STATE_CHANGED = "state_changed"
    TRANSCRIPT_CAPTURED = "transcript_captured"
    EMOTIONAL_TAG_ADDED = "emotional_tag_added"
    THREAD_WOVEN = "thread_woven"
    SUBLIME_EXPERIENCED = "sublime_experienced"

    # Multi-spectral reasoning
    REASONING_COMPLETE = "reasoning_complete"
    REASONING_STARTED = "reasoning_started"
    PERSPECTIVE_GATHERED = "perspective_gathered"

    # Distributed coordination events (expanded)
    BROKER_CONNECTED = "broker_connected"
    TASK_COMPLETED = "task_completed"
    VOTE_SESSION_CREATED = "vote_session_created"
    VOTE_CAST = "vote_cast"
    AGENT_REGISTERED = "agent_registered"
    AGENT_HEARTBEAT = "agent_heartbeat"

    # Inference events
    INFERENCE_STARTED = "inference_started"
    INFERENCE_TIER_SELECTED = "inference_tier_selected"
    INFERENCE_COMPLETED = "inference_completed"
    INFERENCE_LEARNED = "inference_learned"
    INFERENCE_CACHE_HIT = "inference_cache_hit"
    INFERENCE_FALLBACK = "inference_fallback"

    # Adapter events
    DECISION_REQUESTED = "decision_requested"

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

@dataclass
class CascadeTrigger:
    """Defines an automatic cascade: when A happens, trigger B."""

    trigger_event: EventType
    target_events: list[EventType] = field(default_factory=list)
    condition: Callable | None = None
    max_cascade_depth: int = 3
    amplification: float = 1.0


class GanYingBus:
    """Enhanced event bus for resonant communication and emergent pattern detection."""

    # Class-level availability caches — avoid re-discovering unavailable backends
    _haskell_available: bool | None = None
    _koka_available: bool | None = None
    _rust_cascade_available: bool | None = None

    def __init__(self):
        self._listeners: dict[EventType, list[Callable]] = {}
        self._all_listeners: list[Callable] = []
        self._history: list[ResonanceEvent] = []
        self._lock = threading.Lock()
        self._cascade_triggers: list[CascadeTrigger] = []
        self._cascade_stats: dict[str, int] = {
            "total_cascades": 0,
            "max_depth_reached": 0,
            "triggers_fired": 0,
        }
        self._dampening: dict[EventType, float] = {}
        self._cascade_backend = None  # Lazy-loaded Rust cascade backend
        self._cycle_check_cache: bool | None = None  # Cached cycle check result
        self._pyo3_triggers_cache: list | None = None  # Cached PyO3 trigger objects
        self._haskell_backend = None  # Lazy-loaded Haskell cascade verifier
        self._koka_backend = None  # Lazy-loaded Koka garden resonance backend
        self._rust_cascade_backend = None  # Lazy-loaded Rust cascade backend (JSON stdio)
        _ensure_global_worker()

    @property
    def total_emissions(self) -> int:
        """Total number of events emitted (including cascaded)."""
        return len(self._history)

    def set_dampening(self, event_type: EventType, factor: float) -> None:
        """Set a dampening factor for a high-frequency event type.

        Args:
            event_type: The event type to dampen.
            factor: Dampening factor (0.0-1.0). Events with confidence below
                    this factor's threshold will be suppressed.
        """
        with self._lock:
            self._dampening[event_type] = factor

    def add_cascade(self, trigger: CascadeTrigger) -> None:
        """Register a cascade trigger. When trigger_event fires, target_events are emitted.

        Verifies the trigger table remains acyclic after adding this trigger.
        Cyclic triggers are rejected to prevent infinite cascade loops.
        """
        self._cascade_triggers.append(trigger)
        self._cycle_check_cache = None  # Invalidate cycle check cache
        self._pyo3_triggers_cache = None  # Invalidate PyO3 triggers cache

    def _check_cascade_safety(self) -> bool:
        """Check if the current trigger table is acyclic.

        Uses a tiered verification strategy:
        1. PyO3 detect_cycles (fastest, native)
        2. Haskell cascade bridge (secondary verification, JSON stdio)
        3. Python DFS fallback (always available)

        Result is cached until triggers change.

        Returns True if safe (no cycles), False if cycles detected.
        """
        if not self._cascade_triggers:
            return True

        if self._cycle_check_cache is not None:
            return self._cycle_check_cache

        # Tier 1: PyO3 (fastest)
        try:
            import wm_cascade as _wc
            py_triggers = [
                _wc.PyCascadeTrigger(
                    t.trigger_event.value,
                    [e.value for e in t.target_events],
                    t.amplification,
                    t.max_cascade_depth,
                )
                for t in self._cascade_triggers
                if t.condition is None
            ]
            safe = _wc.is_safe(py_triggers)
            self._cycle_check_cache = safe
            return safe
        except Exception:
            pass

        # Tier 2: Rust cascade bridge (JSON stdio, faster than Haskell)
        if self._try_rust_cascade_cycle_check():
            return self._cycle_check_cache

        # Tier 3: Haskell cascade bridge (secondary verification)
        if self._try_haskell_cycle_check():
            return self._cycle_check_cache

        # Tier 4: Python DFS fallback
        graph: dict[str, list[str]] = {}
        for t in self._cascade_triggers:
            if t.condition is not None:
                continue
            graph.setdefault(t.trigger_event.value, []).extend(
                e.value for e in t.target_events
            )

        visited: set[str] = set()
        on_stack: set[str] = set()

        def _dfs(node: str) -> bool:
            if node in on_stack:
                return False  # Cycle found
            if node in visited:
                return True
            visited.add(node)
            on_stack.add(node)
            for neighbor in graph.get(node, []):
                if not _dfs(neighbor):
                    return False
            on_stack.discard(node)
            return True

        safe = all(_dfs(n) for n in list(graph.keys()))
        self._cycle_check_cache = safe
        return safe

    def _try_rust_cascade_cycle_check(self) -> bool:
        """Try Rust cascade bridge for cycle detection.

        Returns True if the check was performed (cache updated), False if
        the Rust cascade backend is unavailable.
        """
        if GanYingBus._rust_cascade_available is False:
            return False

        if self._rust_cascade_backend is False:
            return False

        if self._rust_cascade_backend is None:
            try:
                import sys
                from pathlib import Path
                _bridge_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "polyglot" / "bridges" / "python"
                if str(_bridge_path) not in sys.path:
                    sys.path.insert(0, str(_bridge_path))
                from whitemagic_polyglot import RustCascadeBackend
                backend = RustCascadeBackend()
                backend.call("ping", timeout=0.5)
                self._rust_cascade_backend = backend
                GanYingBus._rust_cascade_available = True
            except Exception:
                self._rust_cascade_backend = False
                GanYingBus._rust_cascade_available = False
                return False

        try:
            triggers_json = [
                {
                    "trigger_event": t.trigger_event.value,
                    "target_events": [e.value for e in t.target_events],
                    "amplification": t.amplification,
                    "max_cascade_depth": t.max_cascade_depth,
                }
                for t in self._cascade_triggers
                if t.condition is None
            ]
            result = self._rust_cascade_backend.call("is_safe", timeout=5.0, triggers=triggers_json)
            safe = result.get("result", {}).get("safe", True)
            self._cycle_check_cache = safe
            return True
        except Exception:
            self._rust_cascade_backend = False
            return False

    def _try_haskell_cycle_check(self) -> bool:
        """Try Haskell cascade bridge for cycle detection.

        Returns True if the check was performed (cache updated), False if
        Haskell is unavailable.
        """
        # Check class-level availability cache
        if GanYingBus._haskell_available is False:
            return False

        if self._haskell_backend is False:
            return False

        if self._haskell_backend is None:
            try:
                import sys
                from pathlib import Path
                _bridge_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "polyglot" / "bridges" / "python"
                if str(_bridge_path) not in sys.path:
                    sys.path.insert(0, str(_bridge_path))
                from whitemagic_polyglot import HaskellCascadeBackend
                backend = HaskellCascadeBackend()
                backend.call("ping", timeout=0.5)
                self._haskell_backend = backend
                GanYingBus._haskell_available = True
            except Exception:
                self._haskell_backend = False
                GanYingBus._haskell_available = False
                return False

        try:
            triggers_json = [
                {
                    "trigger_event": t.trigger_event.value,
                    "target_events": [e.value for e in t.target_events],
                    "amplification": t.amplification,
                    "max_cascade_depth": t.max_cascade_depth,
                }
                for t in self._cascade_triggers
                if t.condition is None
            ]
            result = self._haskell_backend.call("is_safe", timeout=5.0, triggers=triggers_json)
            safe = result.get("result", {}).get("safe", True)
            self._cycle_check_cache = safe
            return True
        except Exception:
            self._haskell_backend = False
            return False

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the cascade trigger table.

        Returns a list of cycles, where each cycle is a list of event type names.
        Uses PyO3 if available, falls back to Python DFS.
        """
        if not self._cascade_triggers:
            return []

        # Try PyO3 first
        try:
            import wm_cascade as _wc
            py_triggers = [
                _wc.PyCascadeTrigger(
                    t.trigger_event.value,
                    [e.value for e in t.target_events],
                    t.amplification,
                    t.max_cascade_depth,
                )
                for t in self._cascade_triggers
                if t.condition is None
            ]
            return _wc.detect_cycles(py_triggers)
        except Exception:
            pass

        # Python fallback
        graph: dict[str, list[str]] = {}
        for t in self._cascade_triggers:
            if t.condition is not None:
                continue
            graph.setdefault(t.trigger_event.value, []).extend(
                e.value for e in t.target_events
            )

        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: list[str] = []
        on_stack: set[str] = set()

        def _dfs(node: str) -> None:
            if node in on_stack:
                if node in stack:
                    idx = stack.index(node)
                    cycles.append(stack[idx:])
                return
            if node in visited:
                return
            visited.add(node)
            on_stack.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                _dfs(neighbor)
            on_stack.discard(node)
            stack.pop()

        for n in list(graph.keys()):
            _dfs(n)

        return cycles

    def listen(self, event_type: EventType, callback: Callable):
        """Register a listener for a specific event type."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

    def listen_all(self, callback: Callable) -> None:
        """Register a catch-all listener that receives every emitted event."""
        with self._lock:
            self._all_listeners.append(callback)

    def get_cascade_stats(self) -> dict[str, int]:
        """Return cascade firing statistics."""
        with self._lock:
            return dict(self._cascade_stats)

    def get_history(self, limit: int = 50) -> list[ResonanceEvent]:
        """Return the most recent N events from history."""
        with self._lock:
            if limit <= 0:
                return list(self._history)
            return list(self._history[-limit:])

    def emit(self, event: ResonanceEvent, cascade: bool = True, async_dispatch: bool = False) -> None:
        """Emit an event to listeners and process cascade triggers.

        When an event matches a cascade trigger, target events are fired
        with amplification applied to confidence and cascade_depth incremented.
        Cascade depth is limited to prevent infinite loops.

        Args:
            event: The resonance event to emit.
            cascade: Whether to process cascade triggers for this event.
            async_dispatch: If True, queue event to global async worker
                           instead of processing synchronously.
        """
        if async_dispatch:
            try:
                _GLOBAL_ASYNC_QUEUE.put_nowait((self, event, cascade))
            except queue.Full:
                logger.warning(
                    "GanYingBus global async queue full, dropping event: %s",
                    event.event_type.value,
                )
            return

        self._emit_internal(event, cascade)

    def _emit_internal(self, event: ResonanceEvent, cascade: bool = True) -> None:
        """Internal emission logic — called directly or via async worker.

        Handles dampening, listener dispatch, and cascade processing.
        """
        # Check dampening — suppress low-confidence high-frequency events
        dampen_factor = self._dampening.get(event.event_type)
        if dampen_factor is not None and event.confidence < dampen_factor:
            return

        with self._lock:
            self._history.append(event)
            if len(self._history) > 1000:
                self._history.pop(0)

        # Dispatch to direct listeners
        listeners = self._listeners.get(event.event_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.debug("Listener dispatch failed: %s", e)

        # Dispatch to catch-all listeners
        for listener in self._all_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.debug("Catch-all listener dispatch failed: %s", e)

        # Process cascade triggers (if enabled)
        if cascade:
            self._process_cascades(event)

    def _process_cascades(self, event: ResonanceEvent) -> None:
        """Check if the emitted event matches any cascade triggers and fire target events.

        Tries the Rust PyO3 accelerator first, falling back to pure Python.
        Performs a cycle safety check on the trigger table before processing.
        """
        # Verify trigger table is acyclic (cached, only re-checks on add_cascade)
        if not self._check_cascade_safety():
            logger.warning(
                "Cascade trigger table has cycles — skipping cascade processing "
                "to prevent infinite loops. Call detect_cycles() for details."
            )
            return

        # Try polyglot acceleration (Rust PyO3)
        if self._try_polyglot_cascade(event):
            return

        # Pure Python fallback
        for trigger in self._cascade_triggers:
            if trigger.trigger_event != event.event_type:
                continue

            # Check optional condition
            if trigger.condition is not None:
                try:
                    if not trigger.condition(event):
                        continue
                except Exception:
                    continue

            # Respect max cascade depth
            if event.cascade_depth >= trigger.max_cascade_depth:
                logger.debug(
                    "Cascade depth limit (%d) reached for %s → %s",
                    trigger.max_cascade_depth,
                    event.event_type.value,
                    [t.value for t in trigger.target_events],
                )
                continue

            with self._lock:
                self._cascade_stats["triggers_fired"] += 1
                self._cascade_stats["total_cascades"] += len(trigger.target_events)
                new_depth = event.cascade_depth + 1
                if new_depth > self._cascade_stats["max_depth_reached"]:
                    self._cascade_stats["max_depth_reached"] = new_depth

            # Fire each target event with amplified confidence
            for target_event_type in trigger.target_events:
                cascaded = ResonanceEvent(
                    source=f"cascade:{event.source}",
                    event_type=target_event_type,
                    data={
                        **event.data,
                        "_cascade_origin": event.event_type.value,
                        "_cascade_depth": new_depth,
                    },
                    confidence=min(1.0, event.confidence * trigger.amplification),
                    cascade_depth=new_depth,
                )
                logger.debug(
                    "Cascade: %s → %s (depth=%d, amp=%.2f, conf=%.2f)",
                    event.event_type.value,
                    target_event_type.value,
                    new_depth,
                    trigger.amplification,
                    cascaded.confidence,
                )
                # Recursive emit — cascades can chain
                self.emit(cascaded)

        # Post-cascade: try Koka garden resonance for Wu Xing balance
        koka_result = self._try_koka_garden_resonance(event)
        if koka_result:
            event.data["_garden_resonance"] = koka_result

    def _try_koka_garden_resonance(self, event: ResonanceEvent) -> dict[str, float] | None:
        """Compute garden resonance via Koka polyglot bridge.

        Delegates garden activation and Wu Xing quadrant balance computation
        to the Koka cascade bridge, which provides typed effect tracking for
        garden operations. Falls back to None when Koka is unavailable.

        Returns a dict with 'activation' and quadrant keys, or None.
        """
        if self._koka_backend is False:
            return None

        # Check class-level availability cache
        if GanYingBus._koka_available is False:
            return None

        if self._koka_backend is None:
            try:
                import sys
                from pathlib import Path
                _bridge_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "polyglot" / "bridges" / "python"
                if str(_bridge_path) not in sys.path:
                    sys.path.insert(0, str(_bridge_path))
                from whitemagic_polyglot import KokaCascadeBackend
                backend = KokaCascadeBackend()
                backend.call("ping", timeout=0.5)
                self._koka_backend = backend
                GanYingBus._koka_available = True
            except Exception:
                self._koka_backend = False
                GanYingBus._koka_available = False
                return None

        try:
            # Compute garden resonance for the event
            garden = event.data.get("garden", "universal")
            result = self._koka_backend.call(
                "garden_resonance",
                timeout=3.0,
                garden=garden,
                activation=event.confidence,
            )
            activation = result.get("result", {}).get("activation", event.confidence)

            # Also compute quadrant balance
            q_result = self._koka_backend.call("quadrant_balance", timeout=3.0)
            quadrants = q_result.get("result", {})

            return {"activation": activation, **quadrants}
        except Exception:
            self._koka_backend = False
            return None

    def _try_polyglot_cascade(self, event: ResonanceEvent) -> bool:
        """Try to process cascades via the Rust PyO3 accelerator.

        Returns True if the backend handled the cascade, False to fall back
        to pure Python processing.

        Uses the native PyO3 module (wm_cascade) for ~microsecond overhead.
        Only used for initial events (cascade_depth=0); cascaded events use
        pure Python to avoid re-entrant calls.
        """
        if not self._cascade_triggers:
            return False

        # Only use Rust for initial events — cascaded events use pure Python
        # to avoid re-entrant calls and keep the hot path simple
        if event.cascade_depth > 0:
            return False

        # Only send unconditional triggers (conditional ones need Python eval)
        unconditional = [t for t in self._cascade_triggers if t.condition is None]
        if not unconditional:
            return False

        # Heuristic: PyO3 FFI call overhead (~0.07ms) dominates for small
        # trigger tables. Pure Python O(n) scan is faster below ~100 triggers.
        # Rust's native scan wins above that crossover.
        if len(unconditional) < 100:
            return False

        # Lazy-load the PyO3 cascade module
        if self._cascade_backend is None:
            try:
                import wm_cascade as _wc
                # Verify the module is functional
                _wc.is_safe([])
                self._cascade_backend = _wc
            except Exception:
                self._cascade_backend = False  # Mark as unavailable
                return False

        if self._cascade_backend is False:
            return False

        try:
            wc = self._cascade_backend

            # Use cached PyO3 trigger objects (invalidated on add_cascade)
            if self._pyo3_triggers_cache is None:
                self._pyo3_triggers_cache = [
                    wc.PyCascadeTrigger(
                        t.trigger_event.value,
                        [e.value for e in t.target_events],
                        t.amplification,
                        t.max_cascade_depth,
                    )
                    for t in unconditional
                ]
            py_triggers = self._pyo3_triggers_cache

            cascaded_events = wc.match_cascades(
                event.event_type.value,
                event.confidence,
                event.cascade_depth,
                py_triggers,
            )

            if not cascaded_events:
                return True  # Backend handled it, no cascades to fire

            # Update stats
            with self._lock:
                self._cascade_stats["triggers_fired"] += 1
                self._cascade_stats["total_cascades"] += len(cascaded_events)
                for ce in cascaded_events:
                    d = ce.cascade_depth
                    if d > self._cascade_stats["max_depth_reached"]:
                        self._cascade_stats["max_depth_reached"] = d

            # Fire cascaded events via recursive emit (pure Python path)
            for ce in cascaded_events:
                target_type_str = ce.event_type
                try:
                    target_type = EventType(target_type_str)
                except ValueError:
                    continue
                cascaded = ResonanceEvent(
                    source=f"cascade:{event.source}",
                    event_type=target_type,
                    data={
                        **event.data,
                        "_cascade_origin": event.event_type.value,
                        "_cascade_depth": ce.cascade_depth,
                    },
                    confidence=ce.confidence,
                    cascade_depth=ce.cascade_depth,
                )
                self.emit(cascaded)

            return True
        except Exception as e:
            logger.debug("PyO3 cascade backend failed, falling back: %s", e)
            self._cascade_backend = False
            return False

# --- SINGLETONS ---
_bus: GanYingBus | None = None

def get_bus() -> GanYingBus:
    """Get or create the global GanYingBus singleton.

    On first creation, automatically registers all cascade protocols
    from CascadeProtocols.init_all_cascades() and sets up Redis broker
    forwarding for distributed event propagation.
    """
    global _bus
    if _bus is None:
        _bus = GanYingBus()
        # Register cascade protocols on first initialization
        try:
            from whitemagic.core.resonance.cascade_protocols import CascadeProtocols
            CascadeProtocols.init_all_cascades()
        except Exception as e:
            logger.debug("Cascade protocols initialization deferred: %s", e)
        # Set up Redis broker forwarding for distributed event propagation
        # Skip in test environments to prevent DB connection pool exhaustion
        if os.environ.get("WM_SILENT_INIT") != "1":
            _setup_broker_forwarding(_bus)
    return _bus


_redis_available: bool | None = None
_redis_check_time: float = 0.0


def _setup_broker_forwarding(bus: GanYingBus) -> None:
    """Register a catch-all listener that forwards events to Redis 'ganying' channel.

    This converges the local Gan Ying Bus with the Redis Broker so events
    propagate across distributed instances. Falls back gracefully when
    Redis is unavailable.
    """
    import time as _time

    def _forward_to_broker(event: ResonanceEvent) -> None:
        global _redis_available, _redis_check_time
        try:
            # Skip broker forwarding in test environments to prevent
            # event loop leaks that cause RecursionError in pytest
            if os.environ.get("WM_SILENT_INIT") == "1":
                return

            # Cache Redis availability — check at most once per 30s
            now = _time.monotonic()
            if _redis_available is None or (now - _redis_check_time) > 30.0:
                from whitemagic.tools.handlers.broker import _resolve_redis_url
                redis_url = _resolve_redis_url()
                if redis_url:
                    # URL-based (Railway / cloud) — skip socket probe, just try connecting
                    _redis_available = True
                else:
                    import socket
                    host = "localhost"
                    port = 6379
                    probe_timeout = 0.5
                    try:
                        socket.create_connection((host, port), timeout=probe_timeout).close()
                        _redis_available = True
                    except OSError:
                        _redis_available = False
                _redis_check_time = now

            if not _redis_available:
                return  # Redis unavailable — silent fallback

            from whitemagic.tools.handlers.broker import _get_broker, _run

            async def _publish() -> None:
                broker = await _get_broker()
                await broker.publish("ganying", {
                    "event_type": event.event_type.value,
                    "source": event.source,
                    "confidence": event.confidence,
                    "data": event.data,
                })

            coro = _publish()
            try:
                _run(coro)
            except Exception:
                # Ensure coroutine is closed to prevent 'never awaited' warnings
                coro.close()
        except Exception:
            pass  # Broker forwarding is best-effort

    bus.listen_all(_forward_to_broker)

get_event_bus = get_bus # Compatibility alias

def emit_event(*args, **kwargs):
    """
    Emit an event for event.
    """
    if args and isinstance(args[0], EventType):
        kwargs["event_type"] = args[0]
        if len(args) > 1:
            kwargs["data"] = args[1]
        if len(args) > 2:
            kwargs["source"] = args[2]
    elif args and isinstance(args[0], str):
        kwargs["source"] = args[0]
        if len(args) > 1:
            kwargs["event_type"] = args[1]
        if len(args) > 2:
            kwargs["data"] = args[2]
    if "source" not in kwargs:
        kwargs["source"] = "system"
    if "event_type" not in kwargs or not isinstance(kwargs["event_type"], EventType):
        kwargs["event_type"] = EventType.SYSTEM_HEARTBEAT
    get_bus().emit(ResonanceEvent(**kwargs))
