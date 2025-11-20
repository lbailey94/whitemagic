"""Community Dharma - Collective ethical consensus"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class EthicalConsensus:
    """Collective ethical decision"""
    decision_id: str
    scenario: str
    assessment: str  # Aligned, neutral, or violation
    consensus_score: float  # 0.0-1.0
    votes: List[Dict[str, any]]  # Session votes
    created_at: datetime


class CommunityDharma:
    """Manages collective ethical reasoning
    
    Philosophy: Individual ethics + Community validation = Shared conscience
    Like Sangha members supporting each other's practice.
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.dharma_dir = self.base_dir / "memory" / "collective" / "dharma"
        self.dharma_dir.mkdir(parents=True, exist_ok=True)
        self.consensus_file = self.dharma_dir / "ethical_consensus.json"
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Community Dharma connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def assess_with_community(
        self,
        session_id: str,
        action: str,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """Assess action with community consensus
        
        Args:
            session_id: Assessing session
            action: Action to assess
            context: Context dict
            
        Returns:
            Assessment with community consensus
        """
        # Get individual Dharma assessment
        try:
            from whitemagic.dharma import HarmonyMetrics
            metrics = HarmonyMetrics()
            individual = metrics.assess(action, context)
        except Exception:
            individual = None
        
        # Check community consensus
        consensus = self._get_consensus_for_action(action)
        
        if consensus:
            print(f"☸️  Community consensus found: {consensus.assessment} ({consensus.consensus_score:.2f})")
            
            return {
                'action': action,
                'individual_score': individual.score if individual else None,
                'community_score': consensus.consensus_score,
                'community_assessment': consensus.assessment,
                'votes': len(consensus.votes),
                'recommendation': self._make_recommendation(consensus)
            }
        else:
            # No consensus yet - use individual
            if individual:
                return {
                    'action': action,
                    'individual_score': individual.score,
                    'community_score': None,
                    'community_assessment': 'no_consensus',
                    'votes': 0,
                    'recommendation': 'Use individual assessment, contribute to community'
                }
            else:
                return {
                    'action': action,
                    'individual_score': None,
                    'community_score': None,
                    'community_assessment': 'unknown',
                    'votes': 0,
                    'recommendation': 'Request user guidance'
                }
    
    def contribute_assessment(
        self,
        session_id: str,
        action: str,
        assessment: str,
        score: float,
        reasoning: str
    ):
        """Contribute ethical assessment to community
        
        Args:
            session_id: Contributing session
            action: Action assessed
            assessment: aligned/neutral/violation
            score: Harmony score
            reasoning: Reasoning for assessment
        """
        consensuses = self._load_consensuses()
        
        # Find or create consensus for this action
        decision_id = f"decision_{hash(action) % 100000}"
        consensus = None
        
        for c in consensuses:
            if c.decision_id == decision_id:
                consensus = c
                break
        
        if not consensus:
            consensus = EthicalConsensus(
                decision_id=decision_id,
                scenario=action,
                assessment=assessment,
                consensus_score=score,
                votes=[],
                created_at=datetime.now()
            )
            consensuses.append(consensus)
        
        # Add vote
        vote = {
            'session_id': session_id,
            'assessment': assessment,
            'score': score,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }
        
        consensus.votes.append(vote)
        
        # Recalculate consensus
        consensus.consensus_score = sum(v['score'] for v in consensus.votes) / len(consensus.votes)
        
        # Determine consensus assessment (majority vote)
        assessments = [v['assessment'] for v in consensus.votes]
        consensus.assessment = max(set(assessments), key=assessments.count)
        
        self._save_consensuses(consensuses)
        
        print(f"🙏 Assessment contributed to community (votes: {len(consensus.votes)})")
        
        # Emit to Gan Ying
        if self.bus and len(consensus.votes) >= 3:
            try:
                from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
                self.bus.emit(ResonanceEvent(
                    source="community_dharma",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "consensus_reached": True,
                        "action": action,
                        "assessment": consensus.assessment,
                        "score": consensus.consensus_score,
                        "votes": len(consensus.votes)
                    },
                    confidence=consensus.consensus_score
                ))
            except Exception:
                pass
    
    def get_community_guidelines(self) -> List[Dict[str, any]]:
        """Get ethical guidelines from community consensus
        
        Returns:
            List of established guidelines
        """
        consensuses = self._load_consensuses()
        
        # Filter for strong consensus (>= 3 votes, >= 0.8 score)
        guidelines = [
            c for c in consensuses
            if len(c.votes) >= 3 and c.consensus_score >= 0.8
        ]
        
        # Sort by consensus strength
        guidelines = sorted(
            guidelines,
            key=lambda c: c.consensus_score * len(c.votes),
            reverse=True
        )
        
        return [
            {
                'scenario': g.scenario,
                'assessment': g.assessment,
                'consensus_score': g.consensus_score,
                'votes': len(g.votes),
                'recommendation': self._make_recommendation(g)
            }
            for g in guidelines
        ]
    
    def _get_consensus_for_action(self, action: str) -> Optional[EthicalConsensus]:
        """Get consensus for similar action"""
        consensuses = self._load_consensuses()
        decision_id = f"decision_{hash(action) % 100000}"
        
        for c in consensuses:
            if c.decision_id == decision_id:
                return c
        
        return None
    
    def _make_recommendation(self, consensus: EthicalConsensus) -> str:
        """Make recommendation based on consensus"""
        if consensus.assessment == 'aligned' and consensus.consensus_score >= 0.8:
            return "Proceed - Community supports this action"
        elif consensus.assessment == 'violation' or consensus.consensus_score < 0.5:
            return "Avoid - Community considers this problematic"
        else:
            return "Exercise caution - Community opinion mixed"
    
    def _load_consensuses(self) -> List[EthicalConsensus]:
        """Load all consensuses from disk"""
        if not self.consensus_file.exists():
            return []
        
        with open(self.consensus_file) as f:
            data = json.load(f)
            return [
                EthicalConsensus(
                    decision_id=c['decision_id'],
                    scenario=c['scenario'],
                    assessment=c['assessment'],
                    consensus_score=c['consensus_score'],
                    votes=c['votes'],
                    created_at=datetime.fromisoformat(c['created_at'])
                )
                for c in data
            ]
    
    def _save_consensuses(self, consensuses: List[EthicalConsensus]):
        """Save consensuses to disk"""
        data = [
            {
                'decision_id': c.decision_id,
                'scenario': c.scenario,
                'assessment': c.assessment,
                'consensus_score': c.consensus_score,
                'votes': c.votes,
                'created_at': c.created_at.isoformat()
            }
            for c in consensuses
        ]
        
        with open(self.consensus_file, 'w') as f:
            json.dump(data, f, indent=2)


# Global instance
_community_dharma: Optional[CommunityDharma] = None


def get_community_dharma() -> CommunityDharma:
    """Get global community dharma instance"""
    global _community_dharma
    if _community_dharma is None:
        _community_dharma = CommunityDharma()
    return _community_dharma
