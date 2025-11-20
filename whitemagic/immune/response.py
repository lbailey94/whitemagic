"""
Immune Response System

Coordinates the immune system's response to detected threats:
1. Assess threat severity
2. Select appropriate antibody
3. Apply fix
4. Verify healing
5. Record outcome for learning

Like biological immune responses, this system can escalate or de-escalate
based on the threat level and response effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from whitemagic.immune.antibodies import Antibody, AntibodyLibrary
from whitemagic.immune.detector import Threat, ThreatLevel
from whitemagic.immune.memory import ImmuneMemory

# Import ImmuneRegulator only when needed to avoid circular imports
try:
    from whitemagic.immune.dna import ImmuneRegulator
except ImportError:
    ImmuneRegulator = None

# Import Gan Ying bus for resonance (optional)
try:
    from whitemagic.resonance.gan_ying import GanYingBus, ResonanceEvent, EventType
except ImportError:
    GanYingBus = None
    ResonanceEvent = None
    EventType = None


@dataclass
class ResponseOutcome:
    """Result of an immune response."""
    
    threat: Threat
    antibody_used: Optional[str]
    success: bool
    action_taken: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: str = ""
    metadata: Dict = field(default_factory=dict)


class ImmuneResponse:
    """
    Coordinates immune system responses to threats.
    
    Similar to biological immune responses that can be:
    - Innate (immediate, general)
    - Adaptive (learned, specific)
    - Escalating (stronger if initial response fails)
    """
    
    def __init__(self, antibody_library: AntibodyLibrary, immune_memory: ImmuneMemory = None):
        self.antibody_library = antibody_library
        self.immune_memory = immune_memory or ImmuneMemory()
        
        # Safety system
        if ImmuneRegulator:
            from whitemagic.immune.dna import ImmuneRegulator as Regulator
            self.regulator = Regulator()
        else:
            self.regulator = None
        
        # Gan Ying bus for sympathetic resonance (optional)
        self.resonance_bus = None
        if GanYingBus:
            try:
                # Get singleton bus instance
                self.resonance_bus = GanYingBus()
            except:
                pass
        
        self.response_history: List[ResponseOutcome] = []
    
    def respond_to_threat(self, threat: Threat, auto_heal: bool = True) -> ResponseOutcome:
        """
        Respond to a detected threat.
        
        Args:
            threat: The threat to respond to
            auto_heal: Whether to automatically apply fixes
            
        Returns:
            ResponseOutcome with result of response
        """
        # Check if we've seen this threat before
        if self.immune_memory.has_memory(threat.antigen):
            memory = self.immune_memory.recall(threat.antigen)
            print(f"🧠 Immune memory: Seen {threat.antigen} before ({memory['encounter_count']} times)")
        
        # Find appropriate antibody
        antibody = self.antibody_library.find_antibody(threat.antigen)
        
        if not antibody:
            outcome = ResponseOutcome(
                threat=threat,
                antibody_used=None,
                success=False,
                action_taken="No antibody available",
                error=f"No antibody for antigen: {threat.antigen}"
            )
            self._record_outcome(outcome)
            return outcome
        
        # Assess if we should apply the fix
        if not auto_heal:
            outcome = ResponseOutcome(
                threat=threat,
                antibody_used=antibody.name,
                success=False,
                action_taken="Dry run - no fix applied",
                metadata={"antibody": antibody.description}
            )
            self._record_outcome(outcome)
            return outcome
        
        # Safety check with immune regulator (if available)
        if self.regulator:
            suppress, reason = self.regulator.should_suppress_response(
                threat, antibody, {"file": threat.location, "action": antibody.description}
            )
        else:
            suppress, reason = False, None
        
        if suppress:
            print(f"🛡️  Response SUPPRESSED: {reason}")
            outcome = ResponseOutcome(
                threat=threat,
                antibody_used=antibody.name,
                success=False,
                action_taken=f"Suppressed for safety: {reason}",
                error=reason
            )
            self.regulator.record_response(threat, antibody, False, True)
            self._record_outcome(outcome)
            return outcome
        
        # Apply the fix
        print(f"💉 Applying antibody: {antibody.name} ({antibody.description})")
        fix_result = antibody.fix_function(threat)
        
        success = fix_result.get("success", False)
        
        outcome = ResponseOutcome(
            threat=threat,
            antibody_used=antibody.name,
            success=success,
            action_taken=fix_result.get("action", "Fix attempted"),
            error=fix_result.get("error", ""),
            metadata=fix_result
        )
        
        # Update antibody success rate
        self.antibody_library.update_success_rate(antibody.name, success)
        
        # Record in immune memory
        if success:
            self.immune_memory.remember(
                antigen=threat.antigen,
                antibody=antibody.name,
                success=True,
                metadata={
                    "threat_level": threat.level.value,
                    "location": threat.location,
                    "fix_result": fix_result
                }
            )
        
        self._record_outcome(outcome)
        
        # Emit resonance event (Gan Ying sympathetic vibration)
        self._emit_resonance_event(threat, antibody, outcome)
        
        return outcome
    
    def respond_to_threats(self, threats: List[Threat], auto_heal: bool = True) -> List[ResponseOutcome]:
        """
        Respond to multiple threats.
        
        Prioritizes by threat level: CRITICAL → HIGH → MEDIUM → LOW
        """
        # Sort by threat level (critical first)
        priority_order = [ThreatLevel.CRITICAL, ThreatLevel.HIGH, ThreatLevel.MEDIUM, ThreatLevel.LOW]
        sorted_threats = sorted(
            threats,
            key=lambda t: priority_order.index(t.level) if t.level in priority_order else 999
        )
        
        outcomes = []
        for threat in sorted_threats:
            outcome = self.respond_to_threat(threat, auto_heal=auto_heal)
            outcomes.append(outcome)
            
            # If critical threat failed to fix, escalate
            if threat.level == ThreatLevel.CRITICAL and not outcome.success:
                print(f"⚠️  CRITICAL THREAT NOT FIXED: {threat.description}")
                # In a more advanced system, this would trigger escalation
        
        return outcomes
    
    def _record_outcome(self, outcome: ResponseOutcome):
        """Record outcome in history."""
        self.response_history.append(outcome)
    
    def _emit_resonance_event(self, threat: Threat, antibody: Optional[Antibody], outcome: ResponseOutcome):
        """
        Emit resonance event to Gan Ying bus.
        
        Allows other systems to respond sympathetically to immune system activity.
        Like striking a gong (宮) - the vibration reaches all tuned listeners.
        """
        if not self.resonance_bus or not ResonanceEvent or not EventType:
            return
        
        try:
            # Determine event type
            if outcome.success:
                event_type = EventType.THREAT_HEALED
            else:
                event_type = EventType.THREAT_DETECTED
            
            # Create resonance event
            event = ResonanceEvent(
                source="immune_system",
                event_type=event_type,
                data={
                    "threat_type": threat.threat_type.value,
                    "threat_level": threat.level.value,
                    "antibody_used": antibody.name if antibody else None,
                    "success": outcome.success,
                    "location": threat.location
                },
                timestamp=datetime.utcnow(),
                confidence=antibody.success_rate if antibody else 0.5
            )
            
            # Emit to bus (sympathetic resonance)
            self.resonance_bus.emit(event)
            
        except Exception:
            # Resonance is optional - don't fail if it doesn't work
            pass
    
    def generate_report(self) -> Dict:
        """Generate immune response report."""
        total_responses = len(self.response_history)
        successful = sum(1 for o in self.response_history if o.success)
        
        return {
            "total_responses": total_responses,
            "successful": successful,
            "success_rate": f"{(successful / total_responses * 100) if total_responses > 0 else 0:.1f}%",
            "antibodies_used": self._count_antibody_usage(),
            "recent_responses": [
                {
                    "threat": o.threat.description,
                    "antibody": o.antibody_used,
                    "success": o.success,
                    "timestamp": o.timestamp
                }
                for o in self.response_history[-10:]  # Last 10
            ]
        }
    
    def _count_antibody_usage(self) -> Dict[str, int]:
        """Count how many times each antibody was used."""
        usage = {}
        for outcome in self.response_history:
            if outcome.antibody_used:
                usage[outcome.antibody_used] = usage.get(outcome.antibody_used, 0) + 1
        return usage
    
    def get_success_rate_by_threat_type(self) -> Dict[str, float]:
        """Calculate success rate by threat type."""
        by_type: Dict[str, Dict[str, int]] = {}
        
        for outcome in self.response_history:
            threat_type = outcome.threat.threat_type.value
            if threat_type not in by_type:
                by_type[threat_type] = {"total": 0, "successful": 0}
            
            by_type[threat_type]["total"] += 1
            if outcome.success:
                by_type[threat_type]["successful"] += 1
        
        success_rates = {}
        for threat_type, counts in by_type.items():
            rate = (counts["successful"] / counts["total"] * 100) if counts["total"] > 0 else 0
            success_rates[threat_type] = round(rate, 1)
        
        return success_rates
