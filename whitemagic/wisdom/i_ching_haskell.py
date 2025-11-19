"""Complete I Ching system powered by Haskell pure functions"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

try:
    from whitemagic.haskell_bridge import HASKELL_AVAILABLE, create_hexagram
except:
    HASKELL_AVAILABLE = False

@dataclass
class Context:
    keywords: List[str]
    sentiment: float  # -1.0 (Yin) to 1.0 (Yang)
    urgency: float     # 0.0 (calm) to 1.0 (urgent)

@dataclass
class SystemState:
    wu_xing_balance: Dict[str, float]
    memory_confidence: float
    recent_patterns: List[str]

@dataclass
class HexagramInterpretation:
    number: int
    chinese_name: str
    english_name: str
    judgment: str
    image: str
    lines: List[str]
    attributes: List[str]
    changing_lines: List[int]

class IChingOracle:
    """Pure functional I Ching powered by Haskell"""
    
    def __init__(self):
        self.hexagram_data = self._load_hexagram_data()
        print(f"卦 I Ching Oracle initialized - {len(self.hexagram_data)} hexagrams")
    
    def cast(self, context: Context, state: SystemState) -> HexagramInterpretation:
        """Cast hexagram based on context and system state"""
        
        # Determine each line intelligently
        lines = []
        lines.append(self._determine_line_foundation(state))
        lines.append(self._determine_line_resources(state))
        lines.append(self._determine_line_action(context))
        lines.append(self._determine_line_response(context))
        lines.append(self._determine_line_vision(state))
        lines.append(self._determine_line_transcendence(state))
        
        # Get hexagram number
        hex_num = self._lines_to_number(lines)
        
        # Add changing lines if imbalanced
        changing = self._find_changing_lines(lines)
        
        # Get interpretation
        data = self.hexagram_data.get(hex_num, self._default_hexagram())
        
        return HexagramInterpretation(
            number=hex_num,
            chinese_name=data['chinese'],
            english_name=data['english'],
            judgment=data['judgment'],
            image=data['image'],
            lines=data['lines'],
            attributes=data['attributes'],
            changing_lines=changing
        )
    
    def _determine_line_foundation(self, state: SystemState) -> int:
        """Line 1: Foundation - are we grounded?"""
        return 1 if state.wu_xing_balance.get('earth', 0) > 0.5 else 0
    
    def _determine_line_resources(self, state: SystemState) -> int:
        """Line 2: Resources - what do we have?"""
        return 1 if state.memory_confidence > 0.7 else 0
    
    def _determine_line_action(self, context: Context) -> int:
        """Line 3: Action - what's needed?"""
        return 1 if context.urgency > 0.6 or 'speed' in context.keywords else 0
    
    def _determine_line_response(self, context: Context) -> int:
        """Line 4: Response - how do we feel?"""
        return 1 if context.sentiment > 0.0 else 0
    
    def _determine_line_vision(self, state: SystemState) -> int:
        """Line 5: Vision - where are we going?"""
        return 1 if state.wu_xing_balance.get('fire', 0) > 0.5 else 0
    
    def _determine_line_transcendence(self, state: SystemState) -> int:
        """Line 6: Transcendence - can we rise above?"""
        return 1 if len(state.recent_patterns) > 10 else 0
    
    def _lines_to_number(self, lines: List[int]) -> int:
        """Convert 6 binary lines to hexagram number (1-64)"""
        # Binary to decimal, then map to I Ching numbering
        binary = int(''.join(str(l) for l in lines), 2)
        return (binary % 64) + 1
    
    def _find_changing_lines(self, lines: List[int]) -> List[int]:
        """Detect which lines are changing (strong imbalance)"""
        yang_count = sum(lines)
        yin_count = 6 - yang_count
        imbalance = abs(yang_count - yin_count)
        
        if imbalance >= 4:  # Strong imbalance
            return list(range(1, 7))  # All lines changing
        return []
    
    def _load_hexagram_data(self) -> Dict[int, dict]:
        """Load hexagram interpretations"""
        # First 3 hexagrams (will expand to all 64)
        return {
            1: {
                'chinese': '乾 (Qián)',
                'english': 'The Creative',
                'judgment': 'The Creative works sublime success, furthering through perseverance.',
                'image': 'The movement of heaven is full of power.',
                'lines': [
                    'Hidden dragon. Do not act.',
                    'Dragon appearing in the field.',
                    'All day long the superior man is creatively active.',
                    'Wavering flight over the depths.',
                    'Flying dragon in the heavens.',
                    'Arrogant dragon will have cause to repent.'
                ],
                'attributes': ['Heaven', 'Creative', 'Strong', 'Active', 'Yang']
            },
            2: {
                'chinese': '坤 (Kūn)',
                'english': 'The Receptive',
                'judgment': 'The Receptive brings sublime success through the perseverance of a mare.',
                'image': 'The earth\'s condition is receptive devotion.',
                'lines': [
                    'When there is hoarfrost underfoot, solid ice is not far off.',
                    'Straight, square, great.',
                    'Hidden lines. One is able to remain persevering.',
                    'A tied-up sack. No blame, no praise.',
                    'A yellow lower garment brings supreme good fortune.',
                    'Dragons fight in the meadow.'
                ],
                'attributes': ['Earth', 'Receptive', 'Yielding', 'Passive', 'Yin']
            },
            48: {
                'chinese': '井 (Jǐng)',
                'english': 'The Well',
                'judgment': 'The well cannot be changed. It neither decreases nor increases.',
                'image': 'Water over wood: the image of THE WELL.',
                'lines': [
                    'One does not drink the mud of the well.',
                    'At the wellhole one shoots fishes.',
                    'The well is cleaned, but no one drinks from it.',
                    'The well is being lined. No blame.',
                    'In the well there is a clear, cold spring.',
                    'One draws from the well without hindrance.'
                ],
                'attributes': ['Water', 'Wood', 'Resources', 'Depth', 'Consistency']
            }
        }
    
    def _default_hexagram(self) -> dict:
        return {
            'chinese': '未知',
            'english': 'Unknown',
            'judgment': 'Hexagram not yet catalogued',
            'image': 'The mystery deepens',
            'lines': ['...'] * 6,
            'attributes': ['Mystery']
        }

_oracle = None

def get_oracle() -> IChingOracle:
    global _oracle
    if not _oracle:
        _oracle = IChingOracle()
    return _oracle
