"""Pattern Distributor - Distribute patterns via Gan Ying"""

from typing import Dict, List


class PatternDistributor:
    """Distribute learned patterns across all systems via Gan Ying
    
    Philosophy: When one system learns, broadcast to all.
    """
    
    def __init__(self):
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Pattern Distributor connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def distribute_pattern(
        self,
        source_system: str,
        pattern: Dict,
        confidence: float = 0.8
    ):
        """Distribute pattern to all systems
        
        Args:
            source_system: System that learned pattern
            pattern: Pattern dict
            confidence: Confidence score
        """
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source=f"learning_{source_system}",
                event_type=EventType.PATTERN_EXTRACTED,
                data={
                    'pattern': pattern,
                    'source_system': source_system,
                    'distributed': True,
                    'learn_from': 'All systems should integrate this pattern'
                },
                confidence=confidence
            ))
            print(f"📡 Pattern distributed from {source_system} to all systems")
        except Exception as e:
            print(f"⚠️  Distribution failed: {e}")
    
    def listen_for_patterns(self, callback):
        """Listen for patterns from other systems
        
        Args:
            callback: Function to call when pattern received
        """
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import EventType
            self.bus.listen(EventType.PATTERN_EXTRACTED, callback)
            print("👂 Listening for distributed patterns")
        except Exception:
            pass
