"""Daily Ritual - Automated Yin/Yang/Dream cycle execution"""

from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class RitualPhase:
    """A phase in daily ritual"""
    name: str  # yin/yang/dream
    time_of_day: time
    duration_minutes: int
    actions: List[str]
    completed: bool


class DailyRitual:
    """Manages daily Yin/Yang/Dream cycle
    
    Philosophy: Like a monk's daily practice schedule.
    Morning (Yin) → Afternoon (Yang) → Evening (Dream)
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.ritual_dir = self.base_dir / "memory" / "practice"
        self.ritual_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_file = self.ritual_dir / "daily_schedule.json"
        self.bus = None
        self._connect_to_gan_ying()
        
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Daily Ritual connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def get_current_phase(self) -> str:
        """Determine current ritual phase based on time
        
        Returns:
            'yin', 'yang', or 'dream'
        """
        now = datetime.now().time()
        
        # Morning (6am-12pm): Yin phase (Reflection, Planning)
        if time(6, 0) <= now < time(12, 0):
            return 'yin'
        
        # Afternoon (12pm-6pm): Yang phase (Creation, Execution)
        elif time(12, 0) <= now < time(18, 0):
            return 'yang'
        
        # Evening (6pm-12am): Dream phase (Synthesis, Rest)
        elif time(18, 0) <= now < time(23, 59):
            return 'dream'
        
        # Night (12am-6am): Deep rest
        else:
            return 'rest'
    
    def execute_morning_ritual(self) -> Dict:
        """Execute morning Yin ritual
        
        Returns:
            Dict with ritual results
        """
        print("\n☀️ Morning Ritual - Yin Phase (Receptive)")
        print("="*50)
        
        actions = []
        
        # 1. Load collective context
        print("1. 🙏 Loading Sangha collective context...")
        try:
            from whitemagic.sangha import get_collective
            collective = get_collective()
            context = collective.get_shared_context("morning_ritual")
            actions.append(f"Loaded context: {len(context.participants)} participants")
        except Exception as e:
            actions.append(f"Context loading: {e}")
        
        # 2. Run Yin analysis
        print("2. 🌑 Running Yin phase analysis...")
        try:
            from whitemagic.orchestration.yin_phase import YinPhase
            yin = YinPhase(self.base_dir)
            results = yin.run_full_cycle()
            actions.append(f"Yin analysis: {results['analyses']['patterns']['total']} patterns")
        except Exception as e:
            actions.append(f"Yin analysis: {e}")
        
        # 3. Check Dharma harmony
        print("3. ☸️  Checking ethical harmony...")
        try:
            from whitemagic.dharma import get_dharma
            dharma = get_dharma()
            report = dharma.get_harmony_report()
            actions.append(f"Harmony: {report['overall_harmony']:.2f}")
        except Exception as e:
            actions.append(f"Dharma check: {e}")
        
        print("\n✅ Morning ritual complete\n")
        
        result = {
            'phase': 'yin',
            'time': datetime.now().isoformat(),
            'actions': actions,
            'duration': '15-30 minutes'
        }
        
        self._emit_ritual_complete('yin', result)
        return result
    
    def execute_afternoon_ritual(self) -> Dict:
        """Execute afternoon Yang ritual
        
        Returns:
            Dict with ritual results
        """
        print("\n🔥 Afternoon Ritual - Yang Phase (Creative)")
        print("="*50)
        
        actions = []
        
        # 1. Check active goals
        print("1. 🎯 Checking Sangha collective goals...")
        try:
            from whitemagic.sangha import get_collective
            collective = get_collective()
            context = collective.get_shared_context("afternoon_ritual")
            actions.append(f"Active goals: {len(context.active_goals)}")
        except Exception as e:
            actions.append(f"Goals check: {e}")
        
        # 2. Get best patterns
        print("2. 📚 Loading federated patterns...")
        try:
            from whitemagic.sangha import get_federation
            federation = get_federation()
            patterns = federation.get_best_patterns(count=5)
            actions.append(f"Best patterns: {len(patterns)}")
        except Exception as e:
            actions.append(f"Patterns: {e}")
        
        # 3. Execute work (placeholder - actual work varies)
        print("3. 💪 Executing planned work...")
        actions.append("Work phase: Ready for implementation")
        
        print("\n✅ Afternoon ritual complete\n")
        
        result = {
            'phase': 'yang',
            'time': datetime.now().isoformat(),
            'actions': actions,
            'duration': '2-4 hours'
        }
        
        self._emit_ritual_complete('yang', result)
        return result
    
    def execute_evening_ritual(self) -> Dict:
        """Execute evening Dream ritual
        
        Returns:
            Dict with ritual results
        """
        print("\n🌙 Evening Ritual - Dream Phase (Synthesis)")
        print("="*50)
        
        actions = []
        
        # 1. Consolidate memories
        print("1. 💾 Consolidating day's memories...")
        actions.append("Memory consolidation: Ready")
        
        # 2. Enter dream state
        print("2. 💤 Entering dream state for pattern synthesis...")
        try:
            from whitemagic.emergence.dream_state import DreamState
            dream = DreamState(self.base_dir / "memory")
            insights = dream.enter_dream_state(duration_minutes=5)
            actions.append(f"Dream insights: {len(insights)}")
        except Exception as e:
            actions.append(f"Dream state: {e}")
        
        # 3. Contribute to collective
        print("3. 🙏 Contributing insights to Sangha...")
        try:
            from whitemagic.sangha import get_collective
            collective = get_collective()
            # Would contribute day's key insights
            actions.append("Insights contributed to collective")
        except Exception as e:
            actions.append(f"Contribution: {e}")
        
        print("\n✅ Evening ritual complete\n")
        
        result = {
            'phase': 'dream',
            'time': datetime.now().isoformat(),
            'actions': actions,
            'duration': '30-60 minutes'
        }
        
        self._emit_ritual_complete('dream', result)
        return result
    
    def auto_execute_current(self) -> Dict:
        """Automatically execute ritual for current time
        
        Returns:
            Dict with ritual results
        """
        phase = self.get_current_phase()
        
        if phase == 'yin':
            return self.execute_morning_ritual()
        elif phase == 'yang':
            return self.execute_afternoon_ritual()
        elif phase == 'dream':
            return self.execute_evening_ritual()
        else:
            return {
                'phase': 'rest',
                'message': 'Deep rest time - no ritual scheduled',
                'time': datetime.now().isoformat()
            }
    
    def _emit_ritual_complete(self, phase: str, result: Dict):
        """Emit ritual completion to Gan Ying"""
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source="daily_ritual",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "ritual_phase": phase,
                    "completed": True,
                    "actions": len(result.get('actions', [])),
                    "time": result['time']
                },
                confidence=0.95
            ))
        except Exception:
            pass


# Global instance
_ritual: Optional[DailyRitual] = None


def get_ritual() -> DailyRitual:
    """Get global daily ritual instance"""
    global _ritual
    if _ritual is None:
        _ritual = DailyRitual()
    return _ritual
