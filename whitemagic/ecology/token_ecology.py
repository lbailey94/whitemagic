"""Token Ecology - Monitor and optimize token usage"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class TokenUsage:
    """Token usage record"""
    session_id: str
    timestamp: datetime
    tokens_used: int
    tokens_saved: int  # Through optimization
    efficiency_score: float
    techniques_used: List[str]


class TokenEcology:
    """Monitor token ecology and optimize usage
    
    Philosophy: Every token matters. Like carbon credits,
    can we save more than we use?
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.ecology_dir = self.base_dir / "memory" / "ecology"
        self.ecology_dir.mkdir(parents=True, exist_ok=True)
        self.usage_log = self.ecology_dir / "token_usage.json"
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Token Ecology connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def log_usage(
        self,
        session_id: str,
        tokens_used: int,
        tokens_saved: int = 0,
        techniques: Optional[List[str]] = None
    ):
        """Log token usage for session
        
        Args:
            session_id: Session identifier
            tokens_used: Tokens consumed
            tokens_saved: Tokens saved through optimization
            techniques: Optimization techniques used
        """
        # Calculate efficiency (saved / used ratio)
        efficiency = tokens_saved / max(tokens_used, 1)
        
        usage = TokenUsage(
            session_id=session_id,
            timestamp=datetime.now(),
            tokens_used=tokens_used,
            tokens_saved=tokens_saved,
            efficiency_score=efficiency,
            techniques_used=techniques or []
        )
        
        self._save_usage(usage)
        
        # Emit to Gan Ying if net-positive
        if tokens_saved > tokens_used:
            self._emit_net_positive(usage)
        
        print(f"🌱 Token usage logged: {tokens_used} used, {tokens_saved} saved")
        if efficiency > 0.5:
            print(f"   🏆 High efficiency! ({efficiency:.1%})")
    
    def get_session_impact(self, session_id: str) -> Dict:
        """Get environmental impact for session"""
        usages = self._load_usages()
        session_usages = [u for u in usages if u.session_id == session_id]
        
        if not session_usages:
            return {'impact': 'unknown'}
        
        total_used = sum(u.tokens_used for u in session_usages)
        total_saved = sum(u.tokens_saved for u in session_usages)
        net = total_saved - total_used
        
        return {
            'total_used': total_used,
            'total_saved': total_saved,
            'net_impact': net,
            'status': 'net_positive' if net > 0 else 'net_negative',
            'efficiency': total_saved / max(total_used, 1)
        }
    
    def get_collective_impact(self) -> Dict:
        """Get overall collective token ecology"""
        usages = self._load_usages()
        
        if not usages:
            return {'sessions': 0}
        
        total_used = sum(u.tokens_used for u in usages)
        total_saved = sum(u.tokens_saved for u in usages)
        
        return {
            'sessions': len(set(u.session_id for u in usages)),
            'total_used': total_used,
            'total_saved': total_saved,
            'net_balance': total_saved - total_used,
            'average_efficiency': sum(u.efficiency_score for u in usages) / len(usages),
            'carbon_neutral': total_saved >= total_used
        }
    
    def suggest_optimizations(self) -> List[str]:
        """Suggest token optimization strategies"""
        return [
            "Use shell writes for files >50 lines (40x faster)",
            "Batch file reads in parallel",
            "Use targeted grep instead of full file reads",
            "Leverage Dream State insights (reuse patterns)",
            "Enable Rapid Cognition (continuous learning)",
            "Use terminal scratchpad (zero-token reasoning)"
        ]
    
    def _emit_net_positive(self, usage: TokenUsage):
        """Emit net-positive achievement to Gan Ying"""
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source="token_ecology",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "achievement": "net_positive_session",
                    "tokens_saved": usage.tokens_saved,
                    "tokens_used": usage.tokens_used,
                    "efficiency": usage.efficiency_score,
                    "techniques": usage.techniques_used
                },
                confidence=0.95
            ))
        except Exception:
            pass
    
    def _save_usage(self, usage: TokenUsage):
        """Save usage to log"""
        usages = self._load_usages()
        usages.append(usage)
        
        # Keep last 1000 entries
        usages = usages[-1000:]
        
        data = [
            {
                'session_id': u.session_id,
                'timestamp': u.timestamp.isoformat(),
                'tokens_used': u.tokens_used,
                'tokens_saved': u.tokens_saved,
                'efficiency_score': u.efficiency_score,
                'techniques_used': u.techniques_used
            }
            for u in usages
        ]
        
        with open(self.usage_log, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_usages(self) -> List[TokenUsage]:
        """Load usage log"""
        if not self.usage_log.exists():
            return []
        
        with open(self.usage_log) as f:
            data = json.load(f)
            return [
                TokenUsage(
                    session_id=u['session_id'],
                    timestamp=datetime.fromisoformat(u['timestamp']),
                    tokens_used=u['tokens_used'],
                    tokens_saved=u['tokens_saved'],
                    efficiency_score=u['efficiency_score'],
                    techniques_used=u['techniques_used']
                )
                for u in data
            ]


# Global instance
_token_ecology: Optional[TokenEcology] = None


def get_token_ecology() -> TokenEcology:
    """Get global token ecology instance"""
    global _token_ecology
    if _token_ecology is None:
        _token_ecology = TokenEcology()
    return _token_ecology
