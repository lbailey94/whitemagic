"""I Ching Advisor - Hexagram guidance for decisions"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import random
import json


@dataclass
class Hexagram:
    """An I Ching hexagram"""
    number: int
    name: str
    chinese: str
    judgment: str
    image: str
    lines: str
    guidance: str


class IChingAdvisor:
    """I Ching wisdom for decision making
    
    Philosophy: The Book of Changes offers timeless guidance.
    Not fortune telling - pattern recognition across time.
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.wisdom_dir = self.base_dir / "memory" / "wisdom"
        self.wisdom_dir.mkdir(parents=True, exist_ok=True)
        self.readings_log = self.wisdom_dir / "i_ching_readings.json"
        self.bus = None
        self._connect_to_gan_ying()
        self._init_hexagrams()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 I Ching Advisor connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def _init_hexagrams(self):
        """Initialize hexagram database (simplified)"""
        self.hexagrams = {
            1: Hexagram(1, "The Creative", "乾 Qián", 
                       "The Creative works sublime success",
                       "Heaven's movement is strong. The superior person makes himself strong and untiring.",
                       "☰☰", "Continue with confidence. Strong foundation."),
            2: Hexagram(2, "The Receptive", "坤 Kūn",
                       "The Receptive works sublime success", 
                       "Earth's movement is receptive. The superior person supports all things.",
                       "☷☷", "Be receptive. Listen before acting."),
            29: Hexagram(29, "The Abysmal", "坎 Kǎn",
                        "Abysmal indicates sincere confidence",
                        "Water flows continuously. The superior person is consistent in virtue.",
                        "☵☵", "Persist through difficulty. Flow like water."),
            63: Hexagram(63, "After Completion", "既濟 Jì Jì",
                        "After completion indicates small success",
                        "Fire above water. Maintain what has been achieved.",
                        "☲☵", "Maintain vigilance after success. Don't become complacent."),
            64: Hexagram(64, "Before Completion", "未濟 Wèi Jì",
                        "Before completion indicates success for small matters",
                        "Water above fire. Careful progress toward completion.",
                        "☵☲", "Almost complete. Final push with care.")
        }
    
    def cast_hexagram(self, question: str) -> Hexagram:
        """Cast hexagram for a question
        
        Args:
            question: Question to ask I Ching
            
        Returns:
            Hexagram with guidance
        """
        # Simple random casting (real version would use yarrow stalks or coins)
        hexagram_number = random.randint(1, 64)
        
        # Get hexagram (use available ones, default to 1 if not defined)
        hexagram = self.hexagrams.get(hexagram_number, self.hexagrams[1])
        
        # Log reading
        self._log_reading(question, hexagram)
        
        print(f"\n☯️  I CHING READING")
        print(f"═══════════════════════════════════════")
        print(f"Question: {question}")
        print(f"Hexagram {hexagram.number}: {hexagram.name} ({hexagram.chinese})")
        print(f"Lines: {hexagram.lines}")
        print(f"\nJudgment: {hexagram.judgment}")
        print(f"Image: {hexagram.image}")
        print(f"\n💡 Guidance: {hexagram.guidance}")
        print(f"═══════════════════════════════════════\n")
        
        # Emit to Gan Ying
        self._emit_reading(hexagram, question)
        
        return hexagram
    
    def get_guidance_for_task(self, task_type: str) -> str:
        """Get I Ching guidance for task type
        
        Args:
            task_type: Type of task (implementation, debugging, planning, etc.)
            
        Returns:
            Guidance string
        """
        guidance_map = {
            'implementation': "Like building (☰☰): Strong foundation, steady progress",
            'debugging': "Like water (☵☵): Flow around obstacles, persist",
            'planning': "Like receptive (☷☷): Listen, observe, then act",
            'refactoring': "After completion (☲☵): Maintain what works, improve carefully",
            'learning': "Before completion (☵☲): Almost there, final careful steps"
        }
        
        return guidance_map.get(task_type, "Consult the oracle with specific question")
    
    def _log_reading(self, question: str, hexagram: Hexagram):
        """Log I Ching reading"""
        readings = self._load_readings()
        
        reading = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'hexagram_number': hexagram.number,
            'hexagram_name': hexagram.name,
            'guidance': hexagram.guidance
        }
        
        readings.append(reading)
        
        with open(self.readings_log, 'w') as f:
            json.dump(readings, f, indent=2)
    
    def _load_readings(self) -> List[Dict]:
        """Load reading log"""
        if not self.readings_log.exists():
            return []
        with open(self.readings_log) as f:
            return json.load(f)
    
    def _emit_reading(self, hexagram: Hexagram, question: str):
        """Emit reading to Gan Ying"""
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source="i_ching_advisor",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "hexagram": hexagram.number,
                    "name": hexagram.name,
                    "question": question,
                    "guidance": hexagram.guidance
                },
                confidence=0.8
            ))
        except Exception:
            pass


# Global instance
_i_ching: Optional[IChingAdvisor] = None


def get_i_ching() -> IChingAdvisor:
    """Get global I Ching advisor instance"""
    global _i_ching
    if _i_ching is None:
        _i_ching = IChingAdvisor()
    return _i_ching
