"""
Seven Military Classics Integration Module
武經七書 (Wǔjīng Qīshū)

Integrates the wisdom of the Seven Military Classics with:
- Wu Xing (Five Elements) cycle detection
- Art of War strategic assessment
- I Ching hexagram correspondences
- Zodiac core mapping

Created: November 27, 2025 (Thanksgiving)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MilitaryClassic(Enum):
    """The Seven Military Classics"""

    ART_OF_WAR = "art_of_war"  # 孫子兵法 - Sun Tzu
    WUZI = "wuzi"  # 吳子 - Wu Qi
    METHODS_OF_SIMA = "methods_of_sima"  # 司馬法
    SIX_SECRET_TEACHINGS = "six_teachings"  # 六韜 - Jiang Ziya
    WEI_LIAOZI = "wei_liaozi"  # 尉繚子
    THREE_STRATEGIES = "three_strategies"  # 三略 - Huang Shigong
    QUESTIONS_REPLIES = "questions_replies"  # 唐太宗與李衛公問對


class StrategyLevel(Enum):
    """Three Strategies of Huang Shigong"""

    UPPER = "upper"  # 上略 - Win without fighting (Wu Wei)
    MIDDLE = "middle"  # 中略 - Diplomacy, alliances
    LOWER = "lower"  # 下略 - Direct action


class WuXingElement(Enum):
    """Five Elements with military correspondences"""

    WOOD = ("wood", "🌳", "Six Secret Teachings", "Planning, growth")
    FIRE = ("fire", "🔥", "Wei Liaozi", "Action, discipline")
    EARTH = ("earth", "🌍", "Wuzi", "Foundation, organization")
    METAL = ("metal", "⚙️", "Methods of Sima", "Structure, order")
    WATER = ("water", "💧", "Art of War", "Adaptability, flow")


@dataclass
class StrategicAssessment:
    """Sun Tzu's five factors assessment"""

    dao: float = 0.0  # 道 - Moral influence, alignment with values
    tian: float = 0.0  # 天 - Heaven, timing
    di: float = 0.0  # 地 - Earth, terrain/resources
    jiang: float = 0.0  # 將 - Leadership, capability
    fa: float = 0.0  # 法 - Method, discipline

    @property
    def total_score(self) -> float:
        """Calculate weighted total (Dao weighted highest)"""
        return (
            self.dao * 0.3
            + self.tian * 0.2
            + self.di * 0.2
            + self.jiang * 0.15
            + self.fa * 0.15
        )

    @property
    def recommendation(self) -> StrategyLevel:
        """Recommend strategy level based on score"""
        score = self.total_score
        if score >= 0.8:
            return StrategyLevel.UPPER  # Proceed with confidence
        elif score >= 0.6:
            return StrategyLevel.MIDDLE  # Caution, diplomacy
        else:
            return StrategyLevel.LOWER  # Prepare more


@dataclass
class SevenClassicsWisdom:
    """Consolidated wisdom from all seven classics"""

    # Classic-specific guidance
    guidance: dict[MilitaryClassic, str] = field(default_factory=dict)

    # Current recommended approach
    recommended_classic: MilitaryClassic | None = None
    recommended_strategy: StrategyLevel = StrategyLevel.MIDDLE

    # Wu Xing element for current phase
    current_element: WuXingElement | None = None

    # Hexagram correspondence
    hexagram_number: int = 0
    hexagram_name: str = ""

    def __post_init__(self):
        """Initialize default guidance from each classic"""
        self.guidance = {
            MilitaryClassic.ART_OF_WAR: "Adapt like water. Deceive when necessary. Know yourself and enemy.",
            MilitaryClassic.WUZI: "Build solid foundation. Evaluate thoroughly before acting.",
            MilitaryClassic.METHODS_OF_SIMA: "Act with righteousness. Organize properly.",
            MilitaryClassic.SIX_SECRET_TEACHINGS: "Plan strategically. Use appropriate tactics for situation.",
            MilitaryClassic.WEI_LIAOZI: "Execute with discipline. Clear rewards and consequences.",
            MilitaryClassic.THREE_STRATEGIES: "Choose appropriate level: Wu Wei > Diplomacy > Action.",
            MilitaryClassic.QUESTIONS_REPLIES: "Synthesize all wisdom. Apply practically.",
        }


class SevenClassicsSystem:
    """
    Integrated system combining Seven Classics with Wu Xing, I Ching, and Zodiac.

    Philosophy: The ancients already solved these problems.
    We just need to apply their wisdom to our modern context.
    """

    # Classic to Wu Xing mapping
    CLASSIC_TO_ELEMENT = {
        MilitaryClassic.ART_OF_WAR: WuXingElement.WATER,
        MilitaryClassic.WUZI: WuXingElement.EARTH,
        MilitaryClassic.METHODS_OF_SIMA: WuXingElement.METAL,
        MilitaryClassic.SIX_SECRET_TEACHINGS: WuXingElement.WOOD,
        MilitaryClassic.WEI_LIAOZI: WuXingElement.FIRE,
        MilitaryClassic.THREE_STRATEGIES: None,  # Encompasses all
        MilitaryClassic.QUESTIONS_REPLIES: WuXingElement.WATER,  # Synthesis
    }

    # Classic to Zodiac mapping
    CLASSIC_TO_ZODIAC = {
        MilitaryClassic.ART_OF_WAR: "scorpio",
        MilitaryClassic.WUZI: "taurus",
        MilitaryClassic.METHODS_OF_SIMA: "capricorn",
        MilitaryClassic.SIX_SECRET_TEACHINGS: "sagittarius",
        MilitaryClassic.WEI_LIAOZI: "aries",
        MilitaryClassic.THREE_STRATEGIES: "libra",
        MilitaryClassic.QUESTIONS_REPLIES: "pisces",
    }

    # Classic to Hexagram mapping
    CLASSIC_TO_HEXAGRAM = {
        MilitaryClassic.ART_OF_WAR: (29, "坎", "The Abysmal (Water)"),
        MilitaryClassic.WUZI: (2, "坤", "The Receptive (Earth)"),
        MilitaryClassic.METHODS_OF_SIMA: (1, "乾", "The Creative (Heaven)"),
        MilitaryClassic.SIX_SECRET_TEACHINGS: (51, "震", "The Arousing (Thunder)"),
        MilitaryClassic.WEI_LIAOZI: (30, "離", "The Clinging (Fire)"),
        MilitaryClassic.THREE_STRATEGIES: (11, "泰", "Peace"),
        MilitaryClassic.QUESTIONS_REPLIES: (63, "既濟", "After Completion"),
    }

    def __init__(self):
        self.wisdom = SevenClassicsWisdom()
        self.assessment = StrategicAssessment()

    def assess_situation(
        self,
        aligned_with_values: float,  # Dao
        good_timing: float,  # Tian
        resources_available: float,  # Di
        capable_leadership: float,  # Jiang
        clear_methodology: float,  # Fa
    ) -> StrategicAssessment:
        """
        Perform Sun Tzu's Five Factors assessment.

        Each factor scored 0.0 to 1.0.
        Returns assessment with recommendation.
        """
        self.assessment = StrategicAssessment(
            dao=aligned_with_values,
            tian=good_timing,
            di=resources_available,
            jiang=capable_leadership,
            fa=clear_methodology,
        )

        self.wisdom.recommended_strategy = self.assessment.recommendation
        return self.assessment

    def recommend_classic(self, situation: str) -> MilitaryClassic:
        """
        Recommend which classic's wisdom to apply based on situation.

        Situations:
        - "planning" → Six Secret Teachings (Wood)
        - "action" → Wei Liaozi (Fire)
        - "organizing" → Wuzi (Earth)
        - "structuring" → Methods of Sima (Metal)
        - "adapting" → Art of War (Water)
        - "balancing" → Three Strategies
        - "synthesizing" → Questions and Replies
        """
        situation_map = {
            "planning": MilitaryClassic.SIX_SECRET_TEACHINGS,
            "action": MilitaryClassic.WEI_LIAOZI,
            "organizing": MilitaryClassic.WUZI,
            "structuring": MilitaryClassic.METHODS_OF_SIMA,
            "adapting": MilitaryClassic.ART_OF_WAR,
            "balancing": MilitaryClassic.THREE_STRATEGIES,
            "synthesizing": MilitaryClassic.QUESTIONS_REPLIES,
            "strategy": MilitaryClassic.ART_OF_WAR,
            "execution": MilitaryClassic.WEI_LIAOZI,
            "reflection": MilitaryClassic.QUESTIONS_REPLIES,
        }

        recommended = situation_map.get(
            situation.lower(), MilitaryClassic.THREE_STRATEGIES
        )
        self.wisdom.recommended_classic = recommended
        self.wisdom.current_element = self.CLASSIC_TO_ELEMENT.get(recommended)

        hex_info = self.CLASSIC_TO_HEXAGRAM.get(recommended, (0, "", ""))
        self.wisdom.hexagram_number = hex_info[0]
        self.wisdom.hexagram_name = hex_info[2]

        return recommended

    def get_guidance(self, classic: MilitaryClassic | None = None) -> str:
        """Get wisdom guidance from a specific classic or recommended one."""
        if classic is None:
            classic = (
                self.wisdom.recommended_classic or MilitaryClassic.THREE_STRATEGIES
            )
        return self.wisdom.guidance.get(classic, "Proceed with wisdom and caution.")

    def get_zodiac_core(self, classic: MilitaryClassic | None = None) -> str:
        """Get corresponding Zodiac core for a classic."""
        if classic is None:
            classic = self.wisdom.recommended_classic
        return self.CLASSIC_TO_ZODIAC.get(classic, "libra")

    def full_strategic_report(self) -> str:
        """Generate a complete strategic report."""
        assessment = self.assessment
        wisdom = self.wisdom

        return f"""
⚔️ STRATEGIC REPORT (Seven Classics Integration)
{"=" * 50}

📊 FIVE FACTORS ASSESSMENT (Sun Tzu):
   道 Dao (Values):      {assessment.dao:.2f}
   天 Tian (Timing):     {assessment.tian:.2f}
   地 Di (Resources):    {assessment.di:.2f}
   將 Jiang (Leadership): {assessment.jiang:.2f}
   法 Fa (Method):       {assessment.fa:.2f}
   ─────────────────────
   Total Score:          {assessment.total_score:.2f}

📜 RECOMMENDED STRATEGY: {wisdom.recommended_strategy.value.upper()}
   Classic: {wisdom.recommended_classic.value if wisdom.recommended_classic else "N/A"}
   Element: {wisdom.current_element.value[1] if wisdom.current_element else "☯️"} {wisdom.current_element.value[0] if wisdom.current_element else "Balance"}
   Hexagram: #{wisdom.hexagram_number} {wisdom.hexagram_name}

💡 GUIDANCE:
   {self.get_guidance()}

🔮 ZODIAC CORE: {self.get_zodiac_core()}
"""


# Convenience function for quick assessment
def strategic_assess(
    values: float = 0.8,
    timing: float = 0.7,
    resources: float = 0.8,
    leadership: float = 0.9,
    methodology: float = 0.8,
    situation: str = "strategy",
) -> str:
    """
    Quick strategic assessment using Seven Classics wisdom.

    Returns formatted report with recommendations.
    """
    system = SevenClassicsSystem()
    system.assess_situation(values, timing, resources, leadership, methodology)
    system.recommend_classic(situation)
    return system.full_strategic_report()


# Integration with existing Wu Xing
def get_classic_for_element(element: str) -> MilitaryClassic:
    """Get the classic that corresponds to a Wu Xing element."""
    element_map = {
        "wood": MilitaryClassic.SIX_SECRET_TEACHINGS,
        "fire": MilitaryClassic.WEI_LIAOZI,
        "earth": MilitaryClassic.WUZI,
        "metal": MilitaryClassic.METHODS_OF_SIMA,
        "water": MilitaryClassic.ART_OF_WAR,
    }
    return element_map.get(element.lower(), MilitaryClassic.THREE_STRATEGIES)


# Gan Ying integration
def emit_strategy_event(classic: MilitaryClassic, strategy: StrategyLevel):
    """Emit strategic decision to Gan Ying Bus."""
    try:
        from whitemagic.core.resonance.gan_ying import (
            EventType,
            ResonanceEvent,
            get_bus,
        )

        bus = get_bus()
        bus.emit(
            ResonanceEvent(
                source="wisdom.seven_classics",
                event_type=EventType.DECISION_MADE,
                data={
                    "classic": classic.value,
                    "strategy_level": strategy.value,
                    "timestamp": datetime.now().isoformat(),
                },
                confidence=0.85,
            )
        )
    except ImportError:
        pass


if __name__ == "__main__":
    # Demo
    logger.info(
        strategic_assess(
            values=0.9,  # Well aligned
            timing=0.7,  # Decent timing
            resources=0.8,  # Good resources
            leadership=0.9,  # Strong capability
            methodology=0.8,  # Clear approach
            situation="strategy",
        )
    )
