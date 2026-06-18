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
"""Unified Nervous System & Biological Event Bus (Consolidated v21.5).
==================================================================
Central coordinator for all biological subsystems, providing event-driven
communication and lifecycle management.

Consolidated from nervous_system.py, nervous_system_v21.py, and biological_event_bus.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# --- EVENT BUS TYPES ---

class EventType(Enum):
    """Standardized event types for biological communication."""
    DREAM_PHASE_COMPLETE = "dream_phase_complete"
    IMMUNE_ALERT = "immune_alert"
    MEMORY_DECAY = "memory_decay"
    RESONANCE_SHIFT = "resonance_shift"
    EMERGENCE_DETECTED = "emergence_detected"
    COHERENCE_CHANGE = "coherence_change"
    SELECTION_PRESSURE = "selection_pressure"
    PATTERN_IMMUNITY = "pattern_immunity"

@dataclass
class BiologicalEvent:
    """Single biological event with metadata."""
    event_type: EventType
    data: dict[str, Any]
    source_subsystem: str
    timestamp: float = field(default_factory=time.time)
    priority: int = 1

# --- BIOLOGICAL EVENT BUS ---

class BiologicalEventBus:
    """High-performance event bus for biological subsystem coordination."""

    def __init__(self):
        self.is_active = False
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._stats = {"events_published": 0, "events_processed": 0, "errors": 0}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bio_event")

    async def start(self) -> None:
        """
        Perform the start operation.
        
        Returns:
            None
        """
        self.is_active = True
        asyncio.create_task(self._process_events())
        logger.info("🧠 Biological Event Bus started")

    async def stop(self) -> None:
        """
        Perform the stop operation.
        
        Returns:
            None
        """
        self.is_active = False
        self._executor.shutdown(wait=True)

    def subscribe(self, event_type: EventType, handler: Callable, subsystem: str) -> None:
        """
        Perform the subscribe operation.
        
        Args:
            event_type: Parameter description.
            handler: Parameter description.
            subsystem: Parameter description.
        
        Returns:
            None
        """
        if event_type not in self._subscribers: self._subscribers[event_type] = []

        async def safe_handler(event: BiologicalEvent):
            """
            Perform the safe handler operation.
            
            Args:
                event: Parameter description.
            """
            try:
                if asyncio.iscoroutinefunction(handler): await handler(event)
                else: await asyncio.get_event_loop().run_in_executor(self._executor, handler, event)
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Event handler error in {subsystem}: {e}")

        self._subscribers[event_type].append(safe_handler)

    async def publish(self, event_type: EventType, data: dict[str, Any], source: str, priority: int = 1) -> bool:
        """
        Perform the publish operation.
        
        Args:
            event_type: Parameter description.
            data: Parameter description.
            source: Parameter description.
            priority: Parameter description.
        
        Returns:
            bool
        """
        if not self.is_active: return False
        event = BiologicalEvent(event_type=event_type, data=data, source_subsystem=source, priority=priority)
        await self._event_queue.put(event)
        self._stats["events_published"] += 1
        return True

    async def _process_events(self) -> None:
        while self.is_active:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                handlers = self._subscribers.get(event.event_type, [])
                if handlers:
                    tasks = [handler(event) for handler in handlers]
                    await asyncio.gather(*tasks, return_exceptions=True)
                self._stats["events_processed"] += 1
            except TimeoutError: continue
            except Exception as e: logger.error(f"Event processing error: {e}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.
        
        Returns:
            dict[str, Any]
        """
        return {**self._stats, "subscribers_count": sum(len(h) for h in self._subscribers.values())}

# --- UNIFIED NERVOUS SYSTEM ---

class UnifiedNervousSystem:
    """Central coordinator for all 7 biological subsystems."""

    def __init__(self):
        self.is_active = False
        self.event_bus: BiologicalEventBus | None = None
        self._stats = {"pulses": 0, "errors": 0}
        self.subsystems: dict[str, Any] = {}

    async def start(self) -> None:
        """
        Perform the start operation.
        
        Returns:
            None
        """
        if self.is_active: return
        self.event_bus = await get_event_bus()
        self.is_active = True
        logger.info("🧠 Unified Nervous System initialized")

    async def stop(self) -> None:
        """
        Perform the stop operation.
        
        Returns:
            None
        """
        self.is_active = False
        if self.event_bus: await self.event_bus.stop()

    async def pulse(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Perform the pulse operation.
        
        Args:
            context: Parameter description.
        
        Returns:
            dict[str, Any]
        """
        if not self.is_active: return {"status": "inactive"}
        self._stats["pulses"] += 1
        return {"status": "ok", "pulses": self._stats["pulses"], "timestamp": time.time()}

# --- SINGLETONS ---
_event_bus: BiologicalEventBus | None = None
_nervous_system: UnifiedNervousSystem | None = None
_lock = asyncio.Lock()

async def get_event_bus() -> BiologicalEventBus:
    """
    Get the event bus.
    
    Returns:
        BiologicalEventBus
    """
    global _event_bus
    if _event_bus is None:
        async with _lock:
            if _event_bus is None:
                _event_bus = BiologicalEventBus()
                await _event_bus.start()
    return _event_bus

async def get_nervous_system() -> UnifiedNervousSystem:
    """
    Get the nervous system.
    
    Returns:
        UnifiedNervousSystem
    """
    global _nervous_system
    if _nervous_system is None:
        async with _lock:
            if _nervous_system is None:
                _nervous_system = UnifiedNervousSystem()
                await _nervous_system.start()
    return _nervous_system

# Legacy compatibility
def get_nervous_system_sync() -> UnifiedNervousSystem:
    """
    Get the nervous system sync.
    
    Returns:
        UnifiedNervousSystem
    """
    return _nervous_system or UnifiedNervousSystem()
