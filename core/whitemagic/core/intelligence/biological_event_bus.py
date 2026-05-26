"""Biological Event Bus - Central coordination for 7 subsystems.

This implements the event bus architecture for V021 Unified Nervous System.
Provides publish/subscribe pattern for cross-system communication with
Rust-accelerated dispatch and circuit breaker protection.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

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
    data: Dict[str, Any]
    source_subsystem: str
    timestamp: float
    priority: int = 1  # 1=low, 5=high
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class BiologicalEventBus:
    """High-performance event bus for biological subsystem coordination."""
    
    def __init__(self):
        self.is_active = False
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "errors": 0,
            "queue_depth": 0
        }
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bio_event")
        self._rust_dispatcher = None
        self._circuit_breaker_state = {"failures": 0, "last_failure": 0, "state": "closed"}
        
    async def start(self) -> None:
        """Start the event bus with Rust dispatcher if available."""
        self.is_active = True
        
        # Try to initialize Rust dispatcher for performance
        try:
            import whitemagic_rs
            if hasattr(whitemagic_rs, "tokio_event_dispatcher"):
                self._rust_dispatcher = whitemagic_rs.tokio_event_dispatcher()
                logger.info("🦀 Rust event dispatcher initialized")
            else:
                logger.info("🐍 Using Python event dispatcher (Rust function unavailable)")
        except ImportError:
            logger.info("🐍 Using Python event dispatcher (Rust unavailable)")
            
        # Start event processing loop
        asyncio.create_task(self._process_events())
        logger.info("🧠 Biological Event Bus started")
        
    async def stop(self) -> None:
        """Stop the event bus gracefully."""
        self.is_active = False
        self._executor.shutdown(wait=True)
        logger.info("🧠 Biological Event Bus stopped")
        
    def subscribe(self, event_type: EventType, handler: Callable, subsystem: str) -> None:
        """Subscribe to specific event types."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
            
        # Wrap handler with subsystem identification and error handling
        async def safe_handler(event: BiologicalEvent):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    # Run sync handlers in thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, handler, event
                    )
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Event handler error in {subsystem}: {e}")
                
        self._subscribers[event_type].append(safe_handler)
        logger.debug(f"📡 {subsystem} subscribed to {event_type.value}")
        
    async def publish(self, event_type: EventType, data: Dict[str, Any], 
                      source: str, priority: int = 1) -> bool:
        """Publish an event to the bus."""
        if not self.is_active:
            return False
            
        event = BiologicalEvent(
            event_type=event_type,
            data=data,
            source_subsystem=source,
            timestamp=time.time(),
            priority=priority
        )
        
        # Check circuit breaker
        if self._circuit_breaker_state["state"] == "open":
            if time.time() - self._circuit_breaker_state["last_failure"] > 30:
                # Try to close circuit breaker after 30s
                self._circuit_breaker_state["state"] = "half_open"
            else:
                logger.warning("🔌 Circuit breaker open, event dropped")
                return False
                
        try:
            if self._rust_dispatcher:
                # Use Rust dispatcher for performance
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, self._rust_dispatch, event
                )
            else:
                # Python dispatch
                await self._event_queue.put(event)
                
            self._stats["events_published"] += 1
            return True
            
        except Exception as e:
            self._circuit_breaker_state["failures"] += 1
            self._circuit_breaker_state["last_failure"] = time.time()
            
            if self._circuit_breaker_state["failures"] > 5:
                self._circuit_breaker_state["state"] = "open"
                
            self._stats["errors"] += 1
            logger.error(f"Event publish failed: {e}")
            return False
            
    def _rust_dispatch(self, event: BiologicalEvent) -> None:
        """Dispatch event using Rust tokio dispatcher."""
        if self._rust_dispatcher:
            # Convert to dict for Rust serialization
            event_dict = {
                "type": event.event_type.value,
                "data": event.data,
                "source": event.source_subsystem,
                "timestamp": event.timestamp,
                "priority": event.priority
            }
            self._rust_dispatcher.dispatch(event_dict)
            
    async def _process_events(self) -> None:
        """Main event processing loop."""
        while self.is_active:
            try:
                # Get event with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )
                
                # Find subscribers
                handlers = self._subscribers.get(event.event_type, [])
                
                # Dispatch to all subscribers in parallel
                if handlers:
                    tasks = [handler(event) for handler in handlers]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                self._stats["events_processed"] += 1
                self._stats["queue_depth"] = self._event_queue.qsize()
                
            except asyncio.TimeoutError:
                # No events, continue
                continue
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Event processing error: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "subscribers_count": sum(len(handlers) for handlers in self._subscribers.values()),
            "circuit_breaker_state": self._circuit_breaker_state["state"],
            "rust_dispatcher_available": self._rust_dispatcher is not None
        }

# Global event bus instance
_event_bus: Optional[BiologicalEventBus] = None

async def get_event_bus() -> BiologicalEventBus:
    """Get the global biological event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = BiologicalEventBus()
        await _event_bus.start()
    return _event_bus

# Integration helpers for specific subsystem connections

async def connect_dream_to_immune():
    """Connect Dream System to Immune System (VC2)."""
    bus = await get_event_bus()
    
    # Immune system subscribes to dream events
    async def dream_phase_handler(event: BiologicalEvent):
        """Trigger immune scan on suspicious dream constellations."""
        if event.data.get("phase") == "serendipity":
            suspicious = event.data.get("suspicious_constellations", [])
            if suspicious:
                # Publish immune alert
                await bus.publish(
                    EventType.IMMUNE_ALERT,
                    {"scan_targets": suspicious, "trigger": "dream_serendipity"},
                    "dream_system",
                    priority=3
                )
                
    bus.subscribe(EventType.DREAM_PHASE_COMPLETE, dream_phase_handler, "immune_system")

async def connect_metabolism_to_evolution():
    """Connect Memory Metabolism to Evolution System (VC3)."""
    bus = await get_event_bus()
    
    # Evolution system subscribes to memory decay
    async def memory_decay_handler(event: BiologicalEvent):
        """Convert memory decay into selection pressure."""
        decay_rate = event.data.get("decay_rate", 0)
        if decay_rate > 0.1:  # Significant decay
            await bus.publish(
                EventType.SELECTION_PRESSURE,
                {"pressure_type": "memory_decay", "strength": decay_rate},
                "metabolism_system",
                priority=2
            )
            
    bus.subscribe(EventType.MEMORY_DECAY, memory_decay_handler, "evolution_system")

async def connect_resonance_to_emergence():
    """Connect Resonance to Emergence (VC4)."""
    bus = await get_event_bus()
    
    # Emergence system subscribes to resonance shifts
    async def resonance_shift_handler(event: BiologicalEvent):
        """Modulate emergence thresholds based on harmony."""
        harmony_level = event.data.get("harmony_level", 0.5)
        # Higher harmony lowers emergence threshold
        threshold_modifier = 1.0 - (harmony_level * 0.3)
        
        await bus.publish(
            EventType.EMERGENCE_DETECTED,
            {"threshold_modifier": threshold_modifier, "trigger": "resonance_shift"},
            "resonance_system",
            priority=2
        )
        
    bus.subscribe(EventType.RESONANCE_SHIFT, resonance_shift_handler, "emergence_system")
