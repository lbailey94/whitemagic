"""System adapters - Connect existing systems to Gan Ying bus"""

from typing import Optional
from .gan_ying import GanYingBus, ResonanceEvent, EventType

class AutoimmuneAdapter:
    """Connect Autoimmune system to resonance"""
    
    def __init__(self, autoimmune_system, bus: GanYingBus):
        self.system = autoimmune_system
        self.bus = bus
        
        # Listen for solutions
        bus.listen(EventType.SOLUTION_FOUND, self.on_solution_found)
        bus.listen(EventType.OPTIMIZATION_SUGGESTED, self.on_optimization)
        
    def scan_and_emit(self, target):
        """Scan and emit violations as events"""
        violations = self.system.scan_directory(target)
        
        for v in violations:
            self.bus.emit(ResonanceEvent(
                source="autoimmune",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "pattern_id": v.pattern.pattern_id,
                    "file": str(v.file_path),
                    "confidence": v.pattern.confidence
                },
                confidence=v.pattern.confidence
            ))
    
    def on_solution_found(self, event: ResonanceEvent):
        """Hear when solutions found, apply if relevant"""
        print(f"��️  Autoimmune heard: {event}")

class WuXingAdapter:
    """Connect Wu Xing system to resonance"""
    
    def __init__(self, wu_xing_system, bus: GanYingBus):
        self.system = wu_xing_system
        self.bus = bus
        
        # Listen for patterns to categorize
        bus.listen(EventType.PATTERN_DETECTED, self.on_pattern_detected)
    
    def on_pattern_detected(self, event: ResonanceEvent):
        """Categorize pattern by element"""
        # Simplified categorization
        element = "FIRE"  # Would analyze event.data
        
        self.bus.emit(ResonanceEvent(
            source="wu_xing",
            event_type=EventType.ELEMENT_IDENTIFIED,
            data={"element": element, "pattern": event.data},
            confidence=0.8
        ))

class IChingAdapter:
    """Connect I Ching oracle to resonance"""
    
    def __init__(self, oracle, bus: GanYingBus):
        self.oracle = oracle
        self.bus = bus
        
        # Listen for decision requests
        bus.listen(EventType.DECISION_REQUESTED, self.on_decision_requested)
    
    def on_decision_requested(self, event: ResonanceEvent):
        """Cast hexagram for guidance"""
        # Would actually cast based on context
        hexagram = 48  # The Well (resources)
        
        self.bus.emit(ResonanceEvent(
            source="i_ching",
            event_type=EventType.HEXAGRAM_CAST,
            data={"hexagram": hexagram, "wisdom": "Draw from deep resources"},
            confidence=0.85
        ))

class MemoryAdapter:
    """Connect Memory system to resonance"""
    
    def __init__(self, memory_system, bus: GanYingBus):
        self.system = memory_system
        self.bus = bus
        
        # Listen to EVERYTHING (memory captures all)
        bus.listen_all(self.on_any_event)
    
    def on_any_event(self, event: ResonanceEvent):
        """Capture all events for learning"""
        # Memory system observes everything
        pass  # Would store event in memory

class SolutionAdapter:
    """Connect Solution library to resonance"""
    
    def __init__(self, solution_library, bus: GanYingBus):
        self.library = solution_library
        self.bus = bus
        
        # Listen for patterns needing solutions
        bus.listen(EventType.PATTERN_DETECTED, self.on_pattern_detected)
    
    def on_pattern_detected(self, event: ResonanceEvent):
        """Search for relevant solutions"""
        # Would search library
        solution = "SOL-142"  # Vectorization
        
        self.bus.emit(ResonanceEvent(
            source="solutions",
            event_type=EventType.SOLUTION_FOUND,
            data={"solution_id": solution, "pattern": event.data},
            confidence=0.89
        ))
