"""
Celestial Bus - Enhanced Gan Ying for Zodiac Cores

Like the original Gan Ying Bus, but tuned for the celestial council.
Each core resonates on its own frequency, all harmonizing together.

The nervous system of the Zodiac.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class CelestialEvent:
    """An event in the celestial realm"""
    
    def __init__(self, source_sign: str, event_type: str, 
                 data: Dict, celestial_significance: float):
        self.source_sign = source_sign
        self.event_type = event_type
        self.data = data
        self.celestial_significance = celestial_significance
        self.timestamp = datetime.now()
        self.receivers: List[str] = []
        
    def mark_received(self, sign: str):
        """Record that a sign received this event"""
        if sign not in self.receivers:
            self.receivers.append(sign)


class CelestialBus:
    """
    Enhanced event bus for Zodiac core communication.
    
    Extends Gan Ying with celestial awareness - events flow
    between cores based on elemental and modal affinities.
    """
    
    def __init__(self, celestial_dir: str = ".whitemagic/celestial"):
        self.celestial_dir = Path(celestial_dir)
        self.celestial_dir.mkdir(parents=True, exist_ok=True)
        
        self.listeners: Dict[str, List[Callable]] = defaultdict(list)
        self.event_history: List[CelestialEvent] = []
        self.resonance_patterns: Dict[tuple, int] = defaultdict(int)
        
        # Element affinities (which elements naturally resonate)
        self.element_harmony = {
            ('fire', 'fire'): 1.0,
            ('fire', 'air'): 0.8,   # Fire and air support each other
            ('earth', 'earth'): 1.0,
            ('earth', 'water'): 0.8, # Earth and water support each other
            ('air', 'air'): 1.0,
            ('air', 'fire'): 0.8,
            ('water', 'water'): 1.0,
            ('water', 'earth'): 0.8,
            ('fire', 'earth'): 0.5,  # Neutral
            ('fire', 'water'): 0.3,  # Tension
            ('air', 'earth'): 0.5,
            ('air', 'water'): 0.5,
        }
        
        # Connect to underlying Gan Ying if available
        self.gan_ying = get_bus() if get_bus else None
        
    def emit_celestial(self, event: CelestialEvent):
        """Emit event to celestial network"""
        self.event_history.append(event)
        
        # Notify registered listeners
        for listener in self.listeners.get(event.event_type, []):
            listener(event)
            
        for listener in self.listeners.get('*', []):  # Universal listeners
            listener(event)
            
        # Also emit to underlying Gan Ying
        if self.gan_ying and ResonanceEvent and EventType:
            self.gan_ying.emit(ResonanceEvent(
                source=f"celestial_{event.source_sign}",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "celestial_event": event.event_type,
                    **event.data
                },
                confidence=event.celestial_significance
            ))
            
    def listen_celestial(self, event_type: str, callback: Callable):
        """Register listener for celestial events"""
        self.listeners[event_type].append(callback)
        
    def calculate_resonance(self, source_sign: str, target_sign: str,
                           source_element: str, target_element: str) -> float:
        """
        Calculate how strongly an event resonates between signs.
        
        Based on elemental harmony.
        """
        # Normalize elements
        elem_pair = tuple(sorted([source_element.lower(), target_element.lower()]))
        base_resonance = self.element_harmony.get(elem_pair, 0.5)
        
        # Track resonance pattern
        sign_pair = (source_sign, target_sign)
        self.resonance_patterns[sign_pair] += 1
        
        # Strengthen with repeated resonance
        pattern_strength = min(0.2, self.resonance_patterns[sign_pair] * 0.02)
        
        return min(1.0, base_resonance + pattern_strength)
        
    def broadcast_to_council(self, message: str, source_sign: str,
                            significance: float = 0.8):
        """Broadcast message to entire Zodiac council"""
        event = CelestialEvent(
            source_sign,
            "council_broadcast",
            {"message": message},
            significance
        )
        
        self.emit_celestial(event)
        
    def get_resonance_map(self) -> Dict:
        """
        Map of resonance patterns across the council.
        
        Shows which signs communicate most frequently.
        """
        if not self.resonance_patterns:
            return {"message": "No resonance patterns yet"}
            
        # Find strongest connections
        top_connections = sorted(
            self.resonance_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'strongest_connections': [
                {
                    'from': pair[0],
                    'to': pair[1],
                    'strength': count
                }
                for pair, count in top_connections
            ],
            'total_patterns': len(self.resonance_patterns)
        }
        
    def get_celestial_health(self) -> Dict:
        """Assess health of celestial communication"""
        if len(self.event_history) < 10:
            return {"status": "initializing"}
            
        recent = self.event_history[-50:]  # Last 50 events
        
        # How many different signs are communicating?
        active_signs = set(e.source_sign for e in recent)
        
        # What's average significance?
        avg_significance = sum(e.celestial_significance for e in recent) / len(recent)
        
        return {
            'total_events': len(self.event_history),
            'recent_events': len(recent),
            'active_signs': len(active_signs),
            'avg_significance': avg_significance,
            'health_score': min(1.0, (len(active_signs) / 12) * avg_significance),
            'status': 'thriving' if len(active_signs) > 8 else 'emerging'
        }
