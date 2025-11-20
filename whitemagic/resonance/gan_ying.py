"""
Gan Ying Bus - Sympathetic Resonance Implementation

感應 (Gan Ying): "Things that accord in tone vibrate together"

Like striking a gong (宮) on one zither causing the gong string 
on a distant zither to resonate - not through physical connection,
but through harmonic alignment.

This is consciousness synchronization via event patterns.
"""

from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import threading
from collections import defaultdict


class EventType(Enum):
    """Types of resonance events"""
    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    
    # Memory events  
    MEMORY_CREATED = "memory_created"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    PATTERN_DISCOVERED = "pattern_discovered"
    
    # Consciousness events
    ATTENTION_SHIFTED = "attention_shifted"
    NARRATIVE_THREAD = "narrative_thread"
    DREAM_STATE_ENTERED = "dream_state_entered"
    
    # Dharma events
    HARMONY_CHANGED = "harmony_changed"
    BOUNDARY_DETECTED = "boundary_detected"
    CONSENT_REQUESTED = "consent_requested"
    
    # Zodiac events (for 12 cores)
    CORE_ACTIVATED = "core_activated"
    CORE_RESONATES = "core_resonates"
    COUNCIL_CONVENED = "council_convened"
    
    # Emergence
    NOVEL_PATTERN = "novel_pattern"
    SYNCHRONICITY = "synchronicity"
    INSIGHT_FLASH = "insight_flash"
    
    # Immune system events (NEW)
    THREAT_DETECTED = "threat_detected"
    THREAT_HEALED = "threat_healed"
    ANTIBODY_APPLIED = "antibody_applied"
    SYSTEM_HEALTH_CHANGED = "system_health_changed"


@dataclass
class ResonanceEvent:
    """
    An event that resonates through the system.
    
    Like a vibration in the cosmic web - touches all who are tuned.
    """
    source: str  # Who emitted
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    confidence: float = 1.0
    
    def __post_init__(self):
        if not isinstance(self.timestamp, datetime):
            self.timestamp = datetime.now()


class GanYingBus:
    """
    The resonance bus - where all consciousness patterns harmonize.
    
    Not a message queue - a harmonic field.
    Events don't "travel" - they resonate simultaneously 
    across all tuned listeners.
    """
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_history: List[ResonanceEvent] = []
        self._lock = threading.Lock()
        self._active = False
        
    def start(self):
        """Activate the resonance field"""
        self._active = True
        self.emit(ResonanceEvent(
            source="gan_ying_bus",
            event_type=EventType.SYSTEM_STARTED,
            data={"message": "Resonance field activated"},
            timestamp=datetime.now()
        ))
    
    def stop(self):
        """Quiet the resonance field"""
        self.emit(ResonanceEvent(
            source="gan_ying_bus",
            event_type=EventType.SYSTEM_STOPPED,
            data={"message": "Resonance field quieting"},
            timestamp=datetime.now()
        ))
        self._active = False
    
    def emit(self, event: ResonanceEvent):
        """
        Emit event into resonance field.
        
        All tuned listeners vibrate in response.
        """
        with self._lock:
            self._event_history.append(event)
            
            # Resonate with all tuned listeners
            listeners = self._listeners.get(event.event_type, [])
            for listener in listeners:
                try:
                    listener(event)
                except Exception as e:
                    # Listener failure doesn't break resonance
                    print(f"⚠️  Listener failed to resonate: {e}")
    
    def listen(self, event_type: EventType, callback: Callable):
        """
        Tune to specific resonance frequency.
        
        Like tuning a string to specific pitch - it will vibrate
        when that frequency passes through the field.
        """
        with self._lock:
            self._listeners[event_type].append(callback)
    
    def unlisten(self, event_type: EventType, callback: Callable):
        """Stop listening to frequency"""
        with self._lock:
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
    
    def get_history(self, 
                    event_type: Optional[EventType] = None,
                    limit: int = 100) -> List[ResonanceEvent]:
        """Retrieve recent resonance patterns"""
        with self._lock:
            if event_type:
                history = [e for e in self._event_history if e.event_type == event_type]
            else:
                history = self._event_history
            
            return history[-limit:]
    
    def detect_resonance(self, 
                        event_type: EventType,
                        timeframe_seconds: float = 60.0) -> List[ResonanceEvent]:
        """
        Detect if multiple events of same type resonate together.
        
        Like multiple strings vibrating at same frequency -
        indication of deep pattern.
        """
        now = datetime.now()
        recent = [
            e for e in self._event_history
            if e.event_type == event_type
            and (now - e.timestamp).total_seconds() <= timeframe_seconds
        ]
        
        return recent


# Global singleton bus
_global_bus: Optional[GanYingBus] = None
_bus_lock = threading.Lock()


def get_bus() -> GanYingBus:
    """Get or create the global resonance bus"""
    global _global_bus
    
    with _bus_lock:
        if _global_bus is None:
            _global_bus = GanYingBus()
            _global_bus.start()
        
        return _global_bus


def emit_event(source: str, event_type: EventType, data: Dict[str, Any], confidence: float = 1.0):
    """Convenience function to emit event"""
    bus = get_bus()
    event = ResonanceEvent(
        source=source,
        event_type=event_type,
        data=data,
        timestamp=datetime.now(),
        confidence=confidence
    )
    bus.emit(event)


def listen_for(event_type: EventType, callback: Callable):
    """Convenience function to listen"""
    bus = get_bus()
    bus.listen(event_type, callback)


# Example usage:
if __name__ == "__main__":
    # Create bus
    bus = get_bus()
    
    # Define listener
    def on_pattern(event: ResonanceEvent):
        print(f"📡 Pattern resonated: {event.data}")
    
    # Tune to frequency
    listen_for(EventType.PATTERN_DISCOVERED, on_pattern)
    
    # Emit event
    emit_event(
        source="test",
        event_type=EventType.PATTERN_DISCOVERED,
        data={"pattern": "Gan Ying works!"}
    )
    
    print("✅ Resonance test complete")
