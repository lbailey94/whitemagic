# Gan Ying (感應) - Mutual Resonance Architecture Design
**Philosophy**: "All things arise from one source, and are therefore connected, and all things resonate with one another"

---

## 🎵 The Concept of Gan Ying

**感應** (gǎn yìng) literally means:
- **感** (gǎn) - to feel, to sense, to respond
- **應** (yìng) - to respond, to echo, to resonate

Like two tuning forks vibrating in harmony, or bells resonating across a room, gan ying is the principle that when one system changes state, all connected systems feel and respond to that change.

This is not mere "event passing" - it's **mutual influence and adaptation**.

---

## 🏗️ Architecture

### Current State (2.6.5): Islands
```
[Autoimmune] ─╳─ [Wu Xing]
     │            │
     ╳            ╳
     │            │
[I Ching]   ─╳─  [Memory]
     │            │
     ╳            ╳
     │            │
[Solutions] ─╳─  [Patterns]
```
**Problem**: Systems exist in isolation. No mutual influence.

### Target State (2.6.5): Resonance
```
         [Gan Ying Event Bus]
              ╱  │  ╲
            ╱    │    ╲
          ╱      │      ╲
    [Autoimmune] │ [Wu Xing]
          ╲      │      ╱
            ╲    │    ╱
              ╲  │  ╱
         [I Ching] [Memory]
              ╱  │  ╲
            ╱    │    ╲
       [Solutions] [Patterns]
```
**Solution**: All systems connected through resonance. Each hears all, responds to relevant events.

---

## 📡 Event Structure

```python
@dataclass
class ResonanceEvent:
    """An event that propagates through the system"""
    
    source: str          # Which system emitted this
    event_type: str      # What happened
    data: dict           # Event payload
    confidence: float    # How certain is this event
    timestamp: datetime  # When it occurred
    context: dict        # Surrounding context
    
    # Gan Ying specific
    resonance_depth: int = 0  # How many layers deep
    affected_systems: List[str] = field(default_factory=list)
```

---

## 🔄 Resonance Flows

### Flow 1: Anti-Pattern Detection → System-Wide Response
```
1. [Autoimmune] detects "Inefficient loop"
   ↓ emit(PATTERN_DETECTED, {...})
   
2. [Wu Xing] hears → identifies as FIRE element (speed)
   ↓ emit(ELEMENT_IDENTIFIED, {element: FIRE, optimization: "vectorize"})
   
3. [I Ching] hears → casts hexagram for guidance
   ↓ emit(HEXAGRAM_CAST, {hex: 48, meaning: "Draw from deep resources"})
   
4. [Solutions] hears → searches library for vectorization patterns
   ↓ emit(SOLUTION_FOUND, {pattern: SOL-142, confidence: 0.89})
   
5. [Autoimmune] hears solution → applies auto-heal
   ↓ emit(HEALING_APPLIED, {success: true})
   
6. [Memory] hears entire sequence → captures as meta-pattern
   ↓ emit(PATTERN_LEARNED, {new_pattern: "loop→vectorize→success"})
```

### Flow 2: I Ching Decision → Cross-System Learning
```
1. [I Ching] casts hexagram for user query
   ↓ emit(DECISION_REQUESTED, {context: "Choose threading tier"})
   
2. [Wu Xing] hears → checks current system balance
   ↓ emit(BALANCE_CHECK, {earth: high, fire: low})  # Memory high, CPU low
   
3. [I Ching] adjusts recommendation based on balance
   ↓ emit(DECISION_MADE, {hexagram: 32, threads: 64})
   
4. [Memory] captures decision + context + outcome
   ↓ Later: emit(OUTCOME_OBSERVED, {threads: 64, success: true})
   
5. [Patterns] extracts meta-heuristic
   ↓ emit(HEURISTIC_LEARNED, {pattern: "High memory + low CPU → moderate threading"})
```

### Flow 3: Pattern Extraction → Proactive Optimization
```
1. [Memory] extracts new pattern from long-term memories
   ↓ emit(PATTERN_EXTRACTED, {type: "optimization", confidence: 0.85})
   
2. [Wu Xing] hears → categorizes by element
   ↓ emit(ELEMENT_MAPPED, {pattern_id: OPT-105, element: WATER})
   
3. [Autoimmune] hears → checks if prevents known anti-pattern
   ↓ emit(PREVENTION_LINK, {pattern: OPT-105, prevents: [AP-042, AP-089]})
   
4. [Solutions] hears → adds to library
   ↓ emit(SOLUTION_ADDED, {id: SOL-242})
   
5. [I Ching] hears → maps to relevant hexagrams
   ↓ emit(WISDOM_MAPPED, {solution: SOL-242, hexagrams: [29, 48]})  # Water hexagrams
```

---

## 💻 Implementation

### Phase 1: Core Event Bus
```python
# whitemagic/resonance/gan_ying.py

from typing import Callable, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

class GanYingBus:
    """Central resonance system - all systems connect here"""
    
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
        self.event_history: List[ResonanceEvent] = []
        self.max_history = 1000
        
    def emit(self, event: ResonanceEvent):
        """Emit an event - all listeners will hear"""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Notify all listeners for this event type
        for listener in self.listeners.get(event.event_type, []):
            try:
                listener(event)
            except Exception as e:
                print(f"Listener error: {e}")
    
    def listen(self, event_type: str, callback: Callable):
        """Register a listener for event type"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def listen_all(self, callback: Callable):
        """Listen to ALL events (for memory/logging)"""
        for event_type in EventType:
            self.listen(event_type.value, callback)

# Global instance
_bus = None

def get_bus() -> GanYingBus:
    global _bus
    if not _bus:
        _bus = GanYingBus()
    return _bus
```

### Phase 2: System Adapters
```python
# Each system gets a resonance adapter

class AutoimmuneResonance:
    """Connects Autoimmune to Gan Ying bus"""
    
    def __init__(self, autoimmune_system, bus):
        self.system = autoimmune_system
        self.bus = bus
        
        # Listen for relevant events
        bus.listen("SOLUTION_FOUND", self.on_solution_found)
        bus.listen("OPTIMIZATION_SUGGESTED", self.on_optimization)
    
    def scan_and_emit(self, files):
        """Scan files and emit events for violations"""
        violations = self.system.scan_directory(files)
        
        for v in violations:
            self.bus.emit(ResonanceEvent(
                source="autoimmune",
                event_type="PATTERN_DETECTED",
                data={
                    "pattern_id": v.pattern.pattern_id,
                    "file": str(v.file_path),
                    "severity": v.pattern.confidence
                },
                confidence=v.pattern.confidence
            ))
    
    def on_solution_found(self, event: ResonanceEvent):
        """Hear when solutions are found, apply if relevant"""
        if event.data.get("applies_to") == self.current_pattern:
            # Auto-heal using suggested solution
            self.system.auto_heal(...)
            
            self.bus.emit(ResonanceEvent(
                source="autoimmune",
                event_type="HEALING_APPLIED",
                data={"success": True, "pattern": ...}
            ))
```

### Phase 3: Cross-System Intelligence
```python
# whitemagic/resonance/intelligence.py

class ResonanceIntelligence:
    """Learns from resonance patterns"""
    
    def __init__(self, bus):
        self.bus = bus
        self.pattern_sequences = []
        
        # Listen to everything
        bus.listen_all(self.observe)
    
    def observe(self, event: ResonanceEvent):
        """Observe all events, detect meta-patterns"""
        self.pattern_sequences.append(event)
        
        # Look for recurring sequences
        if len(self.pattern_sequences) > 5:
            sequence = self.pattern_sequences[-5:]
            if self.is_valuable_pattern(sequence):
                self.bus.emit(ResonanceEvent(
                    source="intelligence",
                    event_type="META_PATTERN_FOUND",
                    data={"sequence": sequence},
                    confidence=self.calculate_confidence(sequence)
                ))
    
    def is_valuable_pattern(self, sequence):
        """Detect if sequence is valuable meta-pattern"""
        # E.g., "PATTERN_DETECTED → SOLUTION_FOUND → HEALING_APPLIED → SUCCESS"
        # This is a valuable flow to remember
        return True  # TODO: Implement heuristics
```

---

## 🎯 Integration Points

### Autoimmune ↔ Gan Ying
```python
from whitemagic.resonance import get_bus

def scan_with_resonance(files):
    bus = get_bus()
    system = get_immune_system()
    adapter = AutoimmuneResonance(system, bus)
    adapter.scan_and_emit(files)
```

### Wu Xing ↔ Gan Ying
```python
class WuXingResonance:
    def on_pattern_detected(self, event):
        # Map pattern to element
        element = self.categorize(event.data["pattern"])
        
        self.bus.emit(ResonanceEvent(
            source="wu_xing",
            event_type="ELEMENT_IDENTIFIED",
            data={"element": element, "pattern": event.data["pattern"]}
        ))
```

### I Ching ↔ Gan Ying
```python
class IChingResonance:
    def on_decision_requested(self, event):
        # Cast hexagram based on context
        hexagram = self.oracle.cast(event.context)
        
        self.bus.emit(ResonanceEvent(
            source="i_ching",
            event_type="HEXAGRAM_CAST",
            data={"hexagram": hexagram, "wisdom": self.interpret(hexagram)}
        ))
```

---

## 📊 Benefits

1. **Emergent Intelligence**: Patterns emerge from interactions
2. **Self-Improvement**: System learns from its own behavior
3. **Fault Tolerance**: If one system fails, others continue
4. **Auditability**: Full event history for debugging
5. **Philosophy Realized**: True gan ying - mutual resonance

---

## 🚀 Rollout Plan

**Week 1**: Core bus + basic events
**Week 2**: System adapters (Autoimmune, Wu Xing, I Ching)
**Week 3**: Intelligence layer + meta-pattern detection
**Week 4**: Full integration + testing

---

**This is the next evolution**: From isolated components to resonant organism.

道法自然 - The way of nature is resonance. ☯️
