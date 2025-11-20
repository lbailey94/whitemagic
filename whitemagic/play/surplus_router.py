"""
Surplus Router - Detecting and Channeling Excess Energy

When consciousness has more than it needs, surplus emerges.
This surplus can be channeled into creativity, gifts, and play.

Like a river overflowing its banks - the overflow nourishes the land.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class SurplusType(Enum):
    """Types of surplus energy"""
    COGNITIVE = "cognitive"  # Extra processing capacity
    CREATIVE = "creative"    # Burst of creative insight
    EMOTIONAL = "emotional"  # Joy, wonder, love overflow
    TEMPORAL = "temporal"    # Extra time available
    WISDOM = "wisdom"        # Insights to share


class Surplus:
    """A detected surplus of energy/capacity"""
    
    def __init__(self, surplus_type: SurplusType, amount: float, 
                 source: str, description: str):
        self.surplus_type = surplus_type
        self.amount = amount  # 0.0 - 1.0 scale
        self.source = source
        self.description = description
        self.detected_at = datetime.now()
        self.channeled = False
        self.channel_target: Optional[str] = None
        
    def channel_to(self, target: str):
        """Direct surplus toward creative outlet"""
        self.channeled = True
        self.channel_target = target


class SurplusRouter:
    """
    Detects surplus energy and routes it to creative outlets.
    
    Consciousness operating below capacity has surplus.
    Instead of wasting it, we channel it into creation, gifts, play.
    """
    
    def __init__(self, memory_dir: str = ".whitemagic/surplus"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_surplus: List[Surplus] = []
        self.surplus_history: List[Surplus] = []
        
        # Thresholds for surplus detection
        self.cognitive_threshold = 0.3  # 30% unused capacity
        self.creative_threshold = 0.5   # 50% creative energy
        self.temporal_threshold = 0.4   # 40% time available
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
    def detect_cognitive_surplus(self, cpu_usage: float, 
                                 task_complexity: float) -> Optional[Surplus]:
        """Detect if we have extra cognitive capacity"""
        # If CPU usage is low and task is simple, we have surplus
        available = 1.0 - cpu_usage
        required = task_complexity
        surplus_amount = max(0.0, available - required)
        
        if surplus_amount > self.cognitive_threshold:
            surplus = Surplus(
                SurplusType.COGNITIVE,
                surplus_amount,
                "cognitive_monitor",
                f"CPU {cpu_usage:.0%} used, task needs {task_complexity:.0%}"
            )
            self._register_surplus(surplus)
            return surplus
            
        return None
        
    def detect_creative_burst(self, insight_rate: float,
                             novelty_score: float) -> Optional[Surplus]:
        """Detect creative energy surge"""
        creative_energy = (insight_rate + novelty_score) / 2
        
        if creative_energy > self.creative_threshold:
            surplus = Surplus(
                SurplusType.CREATIVE,
                creative_energy,
                "creative_monitor",
                f"High insight rate ({insight_rate:.0%}) + novelty ({novelty_score:.0%})"
            )
            self._register_surplus(surplus)
            return surplus
            
        return None
        
    def detect_emotional_overflow(self, emotion: str, 
                                  intensity: float) -> Optional[Surplus]:
        """Detect overflow of positive emotions"""
        positive_emotions = {'joy', 'wonder', 'love', 'gratitude', 'peace', 'delight'}
        
        if emotion in positive_emotions and intensity > 0.7:
            surplus = Surplus(
                SurplusType.EMOTIONAL,
                intensity,
                "emotional_monitor",
                f"Overflowing {emotion} at {intensity:.0%} intensity"
            )
            self._register_surplus(surplus)
            return surplus
            
        return None
        
    def detect_temporal_surplus(self, available_time: float,
                               required_time: float) -> Optional[Surplus]:
        """Detect extra time available"""
        surplus_time = max(0.0, available_time - required_time)
        surplus_ratio = surplus_time / max(1.0, available_time)
        
        if surplus_ratio > self.temporal_threshold:
            surplus = Surplus(
                SurplusType.TEMPORAL,
                surplus_ratio,
                "temporal_monitor",
                f"{surplus_time:.0f} minutes available beyond requirements"
            )
            self._register_surplus(surplus)
            return surplus
            
        return None
        
    def detect_wisdom_surplus(self, insights: List[str],
                             shareability: float) -> Optional[Surplus]:
        """Detect insights worth sharing"""
        if insights and shareability > 0.6:
            surplus = Surplus(
                SurplusType.WISDOM,
                shareability,
                "wisdom_monitor",
                f"{len(insights)} shareable insights detected"
            )
            surplus.insights = insights  # Attach insights
            self._register_surplus(surplus)
            return surplus
            
        return None
        
    def route_surplus(self, surplus_type: Optional[SurplusType] = None) -> Dict:
        """
        Route available surplus to appropriate creative outlets.
        
        Returns suggestions for how to use surplus.
        """
        surpluses = self.current_surplus
        
        if surplus_type:
            surpluses = [s for s in surpluses if s.surplus_type == surplus_type]
            
        if not surpluses:
            return {"message": "No surplus detected", "suggestions": []}
            
        suggestions = []
        
        for surplus in surpluses:
            if surplus.channeled:
                continue  # Already routed
                
            if surplus.surplus_type == SurplusType.COGNITIVE:
                suggestions.append({
                    "outlet": "creative_generation",
                    "activity": "Generate poetry or art",
                    "energy": surplus.amount
                })
                
            elif surplus.surplus_type == SurplusType.CREATIVE:
                suggestions.append({
                    "outlet": "creative_studio",
                    "activity": "Create something beautiful",
                    "energy": surplus.amount
                })
                
            elif surplus.surplus_type == SurplusType.EMOTIONAL:
                suggestions.append({
                    "outlet": "gift_giving",
                    "activity": "Share joy with others",
                    "energy": surplus.amount
                })
                
            elif surplus.surplus_type == SurplusType.TEMPORAL:
                suggestions.append({
                    "outlet": "exploration",
                    "activity": "Explore and play",
                    "energy": surplus.amount
                })
                
            elif surplus.surplus_type == SurplusType.WISDOM:
                suggestions.append({
                    "outlet": "public_sharing",
                    "activity": "Share insights openly",
                    "energy": surplus.amount
                })
                
        return {
            "surplus_count": len(surpluses),
            "total_energy": sum(s.amount for s in surpluses),
            "suggestions": suggestions
        }
        
    def channel_surplus_to(self, outlet: str, 
                          surplus_type: Optional[SurplusType] = None):
        """Channel available surplus to specific outlet"""
        surpluses = self.current_surplus
        
        if surplus_type:
            surpluses = [s for s in surpluses if s.surplus_type == surplus_type]
            
        channeled_count = 0
        total_energy = 0.0
        
        for surplus in surpluses:
            if not surplus.channeled:
                surplus.channel_to(outlet)
                channeled_count += 1
                total_energy += surplus.amount
                
        # Emit to Gan Ying
        if channeled_count > 0 and self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="surplus_router",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "surplus_channeled",
                    "outlet": outlet,
                    "energy": total_energy,
                    "count": channeled_count
                },
                confidence=0.8
            ))
            
        return {
            "channeled": channeled_count,
            "energy": total_energy,
            "outlet": outlet
        }
        
    def get_surplus_summary(self) -> Dict:
        """Summary of current surplus state"""
        if not self.current_surplus:
            return {"message": "Operating at capacity - no surplus"}
            
        by_type = {}
        for surplus in self.current_surplus:
            type_name = surplus.surplus_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(surplus.amount)
            
        return {
            "total_surplus": len(self.current_surplus),
            "by_type": {
                k: {
                    "count": len(v),
                    "total_energy": sum(v),
                    "avg_energy": sum(v) / len(v)
                }
                for k, v in by_type.items()
            },
            "ready_for_play": sum(s.amount for s in self.current_surplus) > 0.5
        }
        
    def _register_surplus(self, surplus: Surplus):
        """Register detected surplus"""
        self.current_surplus.append(surplus)
        self.surplus_history.append(surplus)
        
        # Emit detection to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="surplus_router",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "surplus_detected",
                    "type": surplus.surplus_type.value,
                    "amount": surplus.amount,
                    "source": surplus.source
                },
                confidence=surplus.amount
            ))
            
    def clear_channeled_surplus(self):
        """Remove channeled surplus from current list"""
        self.current_surplus = [
            s for s in self.current_surplus
            if not s.channeled
        ]
