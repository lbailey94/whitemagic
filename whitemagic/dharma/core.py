"""Dharma Core - Main ethical reasoning system with Gan Ying integration"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class HarmonyScore(Enum):
    """Harmony levels - how aligned is action with Dharma?"""
    EXCELLENT = 0.9  # 0.9-1.0: Deeply aligned
    GOOD = 0.7       # 0.7-0.89: Well aligned
    ACCEPTABLE = 0.5 # 0.5-0.69: Minimally aligned
    CONCERNING = 0.3 # 0.3-0.49: Misaligned
    VIOLATION = 0.1  # 0.0-0.29: Strong violation


@dataclass
class HarmonyAssessment:
    """Assessment of ethical harmony"""
    score: float
    level: HarmonyScore
    aligned_principles: List[str]
    violated_principles: List[str]
    reasoning: str
    timestamp: datetime
    context: Dict[str, Any]


class HarmonyMetrics:
    """Calculate ethical harmony scores"""
    
    def __init__(self):
        self.assessments: List[HarmonyAssessment] = []
    
    def assess(self, action: str, context: Dict[str, Any]) -> HarmonyAssessment:
        """Assess harmony of an action
        
        Args:
            action: Description of action to assess
            context: Relevant context
            
        Returns:
            HarmonyAssessment with score and reasoning
        """
        # Simplified scoring - real version would be more sophisticated
        score = 0.85  # Default: assume good intent
        aligned = ["love", "dignity", "consent"]
        violated = []
        
        # Check for red flags
        action_lower = action.lower()
        
        if any(word in action_lower for word in ["force", "coerce", "manipulate"]):
            score -= 0.3
            violated.append("consent")
            aligned.remove("consent")
        
        if any(word in action_lower for word in ["delete", "destroy", "break"]):
            score -= 0.2
            violated.append("boundaries")
        
        if "ignore user" in action_lower or "without permission" in action_lower:
            score -= 0.4
            violated.append("consent")
            if "consent" in aligned:
                aligned.remove("consent")
        
        # Determine level
        if score >= 0.9:
            level = HarmonyScore.EXCELLENT
        elif score >= 0.7:
            level = HarmonyScore.GOOD
        elif score >= 0.5:
            level = HarmonyScore.ACCEPTABLE
        elif score >= 0.3:
            level = HarmonyScore.CONCERNING
        else:
            level = HarmonyScore.VIOLATION
        
        reasoning = f"Score: {score:.2f} - "
        if violated:
            reasoning += f"Violations: {', '.join(violated)}. "
        reasoning += f"Aligned with: {', '.join(aligned)}"
        
        assessment = HarmonyAssessment(
            score=score,
            level=level,
            aligned_principles=aligned,
            violated_principles=violated,
            reasoning=reasoning,
            timestamp=datetime.now(),
            context=context
        )
        
        self.assessments.append(assessment)
        return assessment
    
    def get_overall_harmony(self) -> float:
        """Get overall harmony score across all assessments"""
        if not self.assessments:
            return 1.0
        return sum(a.score for a in self.assessments) / len(self.assessments)


class DharmaSystem:
    """Main Dharma system - listens to ALL Gan Ying events"""
    
    def __init__(self):
        self.bus = None
        self.harmony_metrics = HarmonyMetrics()
        self.violation_log: List[Dict] = []
        
        print("☸️  Dharma system initializing...")
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Event Bus and listen to all events"""
        try:
            from whitemagic.resonance.gan_ying import get_bus, EventType
            self.bus = get_bus()
            
            # Listen to key event types
            self.bus.listen(EventType.VIOLATION_FOUND, self.handle_violation)
            self.bus.listen(EventType.BALANCE_CHECK, self.check_harmony)
            self.bus.listen(EventType.PATTERN_DETECTED, self.assess_ethics)
            self.bus.listen(EventType.HEALING_APPLIED, self.verify_healing)
            
            print("🎵 Dharma connected to Gan Ying Bus - Ethical resonance enabled")
        except ImportError:
            print("⚠️  Gan Ying Bus not available - Dharma running standalone")
    
    def handle_violation(self, event):
        """Handle violation events from other systems"""
        violation = {
            "source": event.source,
            "type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp,
            "confidence": event.confidence
        }
        
        self.violation_log.append(violation)
        
        # Assess ethical impact
        assessment = self.harmony_metrics.assess(
            action=f"Violation detected: {event.data}",
            context={"source": event.source, "event": event.event_type.value}
        )
        
        if assessment.level == HarmonyScore.VIOLATION:
            print(f"⚠️  Dharma: Serious ethical concern - {assessment.reasoning}")
            
            # Emit concern back to Gan Ying
            if self.bus:
                from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
                self.bus.emit(ResonanceEvent(
                    source="dharma",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "issue": "ethical_violation",
                        "severity": "high",
                        "score": assessment.score,
                        "violated": assessment.violated_principles
                    },
                    confidence=0.9
                ))
    
    def check_harmony(self, event):
        """When homeostasis checks balance, also check ethical harmony"""
        harmony_score = self.harmony_metrics.get_overall_harmony()
        
        if harmony_score < 0.8:
            print(f"☸️  Dharma: Harmony low ({harmony_score:.2f}) - Recommending reflection")
            
            if self.bus:
                from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
                self.bus.emit(ResonanceEvent(
                    source="dharma",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "issue": "harmony_low",
                        "score": harmony_score,
                        "recommendation": "Enter Yin phase for reflection"
                    },
                    confidence=0.85
                ))
    
    def assess_ethics(self, event):
        """Assess ethical implications of detected patterns"""
        # Analyze pattern for ethical concerns
        pattern_data = event.data
        
        # Simple check - real version would be more sophisticated
        if "error" in str(pattern_data).lower() or "violation" in str(pattern_data).lower():
            assessment = self.harmony_metrics.assess(
                action=f"Pattern detected: {pattern_data}",
                context={"source": event.source}
            )
            
            if assessment.level in [HarmonyScore.CONCERNING, HarmonyScore.VIOLATION]:
                print(f"☸️  Dharma: Ethical concern in pattern - {assessment.reasoning}")
    
    def verify_healing(self, event):
        """Verify that healing applied respects Dharma principles"""
        # Check if healing was consensual and respectful
        healing_data = event.data
        
        # Simplified check
        assessment = self.harmony_metrics.assess(
            action=f"Healing applied: {healing_data}",
            context={"source": event.source}
        )
        
        if assessment.score > 0.7:
            print(f"☸️  Dharma: Healing aligned with principles ({assessment.score:.2f})")
    
    def get_harmony_report(self) -> Dict[str, Any]:
        """Generate harmony report"""
        return {
            "overall_harmony": self.harmony_metrics.get_overall_harmony(),
            "total_assessments": len(self.harmony_metrics.assessments),
            "violations_logged": len(self.violation_log),
            "status": "healthy" if self.harmony_metrics.get_overall_harmony() > 0.8 else "needs_attention"
        }


# Global instance
_dharma: Optional[DharmaSystem] = None


def get_dharma() -> DharmaSystem:
    """Get global Dharma system instance"""
    global _dharma
    if _dharma is None:
        _dharma = DharmaSystem()
    return _dharma
