"""Gan Ying Event Bus - The resonance center"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Dict, Any
from enum import Enum

class EventType(Enum):
    # Autoimmune events
    PATTERN_DETECTED = "pattern_detected"
    HEALING_APPLIED = "healing_applied"
    VIOLATION_FOUND = "violation_found"
    
    # Wu Xing events
    ELEMENT_IDENTIFIED = "element_identified"
    BALANCE_CHECK = "balance_check"
    OPTIMIZATION_SUGGESTED = "optimization_suggested"
    
    # I Ching events
    HEXAGRAM_CAST = "hexagram_cast"
    DECISION_REQUESTED = "decision_requested"
    WISDOM_APPLIED = "wisdom_applied"
    
    # Memory events
    PATTERN_EXTRACTED = "pattern_extracted"
    PATTERN_LEARNED = "pattern_learned"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    
    # Solution events
    SOLUTION_FOUND = "solution_found"
    SOLUTION_APPLIED = "solution_applied"
    SOLUTION_ADDED = "solution_added"
    
    # Meta events
    RESONANCE_DETECTED = "resonance_detected"
    META_PATTERN_FOUND = "meta_pattern_found"

@dataclass
class ResonanceEvent:
    """An event that resonates through the system"""
    source: str          # Which system emitted
    event_type: EventType
    data: Dict[str, Any]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Gan Ying specific
    resonance_depth: int = 0  # How many systems have responded
    affected_systems: List[str] = field(default_factory=list)
    
    def __str__(self):
        return f"[{self.source}] {self.event_type.value} (confidence: {self.confidence:.0%})"

class GanYingBus:
    """Central resonance system - all systems connect here"""
    
    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.event_history: List[ResonanceEvent] = []
        self.max_history = 1000
        
        print("🎵 Gan Ying Bus initialized - Resonance enabled")
    
    def emit(self, event: ResonanceEvent):
        """Emit event - all listeners will hear and respond"""
        self.event_history.append(event)
        
        # Trim history if needed
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Notify all listeners for this event type
        listeners = self.listeners.get(event.event_type, [])
        
        for listener in listeners:
            try:
                listener(event)
                event.resonance_depth += 1
            except Exception as e:
                print(f"⚠️  Listener error: {e}")
    
    def listen(self, event_type: EventType, callback: Callable):
        """Register listener for event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        
    def listen_all(self, callback: Callable):
        """Listen to ALL events (for memory/logging)"""
        for event_type in EventType:
            self.listen(event_type, callback)
    
    def get_recent_events(self, count: int = 10) -> List[ResonanceEvent]:
        """Get recent events"""
        return self.event_history[-count:]
    
    def detect_resonance_patterns(self) -> List[str]:
        """Detect recurring event sequences (meta-patterns)"""
        # Simplified: Look for common sequences
        patterns = []
        
        if len(self.event_history) > 5:
            recent = self.event_history[-5:]
            sequence = " → ".join(e.event_type.value for e in recent)
            patterns.append(sequence)
        
        return patterns

# Global instance
_bus = None

def get_bus() -> GanYingBus:
    """Get global Gan Ying bus instance"""
    global _bus
    if _bus is None:
        _bus = GanYingBus()
    return _bus
