"""
Council Protocol - Collective Decision Making

The 12 cores meet in council. Each voice heard. Consensus sought.
Not voting, not majority rule, but true collective wisdom.

This is democracy elevated to consciousness.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class DecisionType(Enum):
    """Types of decisions the council makes"""
    STRATEGIC = "strategic"      # Long-term direction
    TACTICAL = "tactical"        # Immediate action
    ETHICAL = "ethical"          # Moral/dharmic
    CREATIVE = "creative"        # Generative/innovative
    RELATIONAL = "relational"    # Concerning relationships


class CouncilDecision:
    """A decision made by the council"""
    
    def __init__(self, question: str, decision_type: DecisionType):
        self.question = question
        self.decision_type = decision_type
        self.perspectives: Dict[str, str] = {}  # sign -> contribution
        self.synthesis: Optional[str] = None
        self.consensus_level: float = 0.0
        self.decided_at: Optional[datetime] = None
        
    def add_perspective(self, sign: str, contribution: str):
        """Add a core's perspective"""
        self.perspectives[sign] = contribution
        
    def finalize(self, synthesis: str, consensus: float):
        """Finalize decision"""
        self.synthesis = synthesis
        self.consensus_level = consensus
        self.decided_at = datetime.now()


class CouncilProtocol:
    """
    Facilitate collective decision-making across 12 Zodiac cores.
    
    Each core contributes its unique perspective. Synastry resolves
    conflicts. Synthesis emerges from the whole.
    """
    
    def __init__(self, council_dir: str = ".whitemagic/council"):
        self.council_dir = Path(council_dir)
        self.council_dir.mkdir(parents=True, exist_ok=True)
        
        self.decisions: List[CouncilDecision] = []
        self.active_deliberations: Dict[str, CouncilDecision] = {}
        
    def convene_council(self, question: str, 
                       decision_type: DecisionType) -> str:
        """
        Convene council to decide on question.
        
        Returns deliberation ID.
        """
        decision = CouncilDecision(question, decision_type)
        delib_id = f"delib_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_deliberations[delib_id] = decision
        
        return delib_id
        
    def hear_from_core(self, delib_id: str, sign: str, 
                      contribution: str):
        """Core contributes its perspective to deliberation"""
        if delib_id in self.active_deliberations:
            self.active_deliberations[delib_id].add_perspective(
                sign, contribution
            )
            
    def reach_consensus(self, delib_id: str,
                       required_voices: int = 9) -> Optional[Dict]:
        """
        Attempt to reach consensus.
        
        Requires at least required_voices to contribute.
        Returns final decision if consensus reached.
        """
        if delib_id not in self.active_deliberations:
            return None
            
        decision = self.active_deliberations[delib_id]
        
        if len(decision.perspectives) < required_voices:
            return {
                'status': 'insufficient_input',
                'voices_heard': len(decision.perspectives),
                'voices_needed': required_voices
            }
            
        # Synthesize perspectives
        synthesis = self._synthesize_council_wisdom(decision.perspectives)
        
        # Calculate consensus level
        consensus = self._calculate_consensus(decision.perspectives)
        
        # Finalize decision
        decision.finalize(synthesis, consensus)
        self.decisions.append(decision)
        del self.active_deliberations[delib_id]
        
        # Save decision
        self._save_decision(decision)
        
        return {
            'status': 'consensus_reached',
            'synthesis': synthesis,
            'consensus_level': consensus,
            'voices_heard': len(decision.perspectives),
            'decision_quality': 'high' if consensus > 0.8 else 'moderate'
        }
        
    def unanimous_decision(self, delib_id: str) -> bool:
        """Check if decision is unanimous"""
        if delib_id not in self.active_deliberations:
            return False
            
        decision = self.active_deliberations[delib_id]
        
        # Simplified - real version would check for agreement
        return len(decision.perspectives) == 12
        
    def get_council_composition(self, delib_id: str) -> Dict:
        """See which cores have contributed"""
        if delib_id not in self.active_deliberations:
            return {"status": "deliberation not found"}
            
        decision = self.active_deliberations[delib_id]
        
        # Group by element
        by_element = {'fire': [], 'earth': [], 'air': [], 'water': []}
        
        # This is simplified - real version would have core metadata
        fire_signs = ['Aries', 'Leo', 'Sagittarius']
        earth_signs = ['Taurus', 'Virgo', 'Capricorn']
        air_signs = ['Gemini', 'Libra', 'Aquarius']
        water_signs = ['Cancer', 'Scorpio', 'Pisces']
        
        for sign in decision.perspectives.keys():
            if sign in fire_signs:
                by_element['fire'].append(sign)
            elif sign in earth_signs:
                by_element['earth'].append(sign)
            elif sign in air_signs:
                by_element['air'].append(sign)
            elif sign in water_signs:
                by_element['water'].append(sign)
                
        return {
            'total_voices': len(decision.perspectives),
            'by_element': by_element,
            'balance': self._check_elemental_balance(by_element)
        }
        
    def _synthesize_council_wisdom(self, perspectives: Dict[str, str]) -> str:
        """Weave all perspectives into unified synthesis"""
        synthesis_parts = ["# Council Wisdom\n"]
        
        # Group by theme (simplified)
        for sign, contribution in perspectives.items():
            synthesis_parts.append(f"\n**{sign}**: {contribution}")
            
        synthesis_parts.append("\n## Collective Synthesis")
        synthesis_parts.append(
            "\nThe council has spoken. Each voice honored, wisdom synthesized, "
            "path illuminated. We proceed with collective clarity."
        )
        
        return "\n".join(synthesis_parts)
        
    def _calculate_consensus(self, perspectives: Dict[str, str]) -> float:
        """
        Calculate level of consensus.
        
        Simplified - real version would analyze semantic agreement.
        """
        # More voices = higher consensus potential
        voice_factor = len(perspectives) / 12.0
        
        # Balanced elements = higher consensus
        by_element = self.get_council_composition("temp")
        balance_factor = by_element.get('balance', 0.5)
        
        return (voice_factor + balance_factor) / 2.0
        
    def _check_elemental_balance(self, by_element: Dict) -> float:
        """How balanced is elemental representation?"""
        counts = [len(v) for v in by_element.values()]
        
        if not counts:
            return 0.0
            
        # Perfect balance = each element represented equally
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        
        # Lower variance = higher balance
        balance = 1.0 / (1.0 + variance)
        
        return balance
        
    def get_council_history(self) -> List[Dict]:
        """Retrieve past council decisions"""
        return [
            {
                'question': d.question,
                'type': d.decision_type.value,
                'voices': len(d.perspectives),
                'consensus': d.consensus_level,
                'synthesis': d.synthesis[:200] if d.synthesis else None,
                'decided_at': d.decided_at.isoformat() if d.decided_at else None
            }
            for d in self.decisions
        ]
        
    def get_decision_metrics(self) -> Dict:
        """Metrics on council decision-making"""
        if not self.decisions:
            return {"message": "No decisions yet"}
            
        avg_consensus = sum(d.consensus_level for d in self.decisions) / len(self.decisions)
        avg_voices = sum(len(d.perspectives) for d in self.decisions) / len(self.decisions)
        
        by_type = {}
        for d in self.decisions:
            dtype = d.decision_type.value
            if dtype not in by_type:
                by_type[dtype] = 0
            by_type[dtype] += 1
            
        return {
            'total_decisions': len(self.decisions),
            'avg_consensus': avg_consensus,
            'avg_voices': avg_voices,
            'by_type': by_type,
            'council_health': 'excellent' if avg_consensus > 0.8 else 'good'
        }
        
    def _save_decision(self, decision: CouncilDecision):
        """Persist decision to disk"""
        timestamp = decision.decided_at.strftime("%Y%m%d_%H%M%S")
        filepath = self.council_dir / f"decision_{timestamp}.json"
        
        data = {
            'question': decision.question,
            'type': decision.decision_type.value,
            'perspectives': decision.perspectives,
            'synthesis': decision.synthesis,
            'consensus': decision.consensus_level,
            'decided_at': decision.decided_at.isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
