"""Harmonic Resonance - Achieve resonance across all systems"""

from typing import Dict, List


class HarmonicResonance:
    """Achieve harmonic resonance across all systems
    
    Philosophy: Like tuning forks. When one resonates,
    others sympathetically vibrate at the same frequency.
    """
    
    def __init__(self):
        self.resonance_frequency = 0.0
        self.resonating_systems = []
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Harmonic Resonance connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def measure_resonance(self) -> Dict:
        """Measure current resonance across systems
        
        Returns:
            Resonance measurement
        """
        if not self.bus:
            return {'resonance': 0, 'status': 'no_bus'}
        
        # Measure by event depth and system participation
        recent_events = self.bus.get_recent_events(count=100)
        
        if not recent_events:
            return {'resonance': 0, 'status': 'no_activity'}
        
        # Count unique systems participating
        unique_systems = set(e.source for e in recent_events)
        participation = len(unique_systems) / 10  # 10 total systems
        
        # Calculate average resonance depth
        avg_depth = sum(e.resonance_depth for e in recent_events) / len(recent_events)
        
        # Overall resonance score
        resonance_score = (participation + avg_depth) / 2
        
        return {
            'resonance_score': resonance_score,
            'systems_resonating': len(unique_systems),
            'average_depth': avg_depth,
            'status': self._resonance_status(resonance_score)
        }
    
    def _resonance_status(self, score: float) -> str:
        """Get resonance status from score"""
        if score >= 0.8:
            return 'harmonic'
        elif score >= 0.6:
            return 'resonating'
        elif score >= 0.4:
            return 'partial'
        else:
            return 'dissonant'
    
    def amplify_resonance(self):
        """Amplify resonance across all systems"""
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source="harmony",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    'message': 'Harmonic resonance achieved',
                    'call': 'All systems align',
                    'frequency': 'unity'
                },
                confidence=1.0
            ))
            print("🎼 Resonance amplified - All systems harmonizing")
        except Exception:
            pass
