"""Ifa Divination System - 256 Odu corpus.

The 16 principal Odu (Meji) are the base alphabet of the Ifa oracular system.
Each corresponds to a 4-bit binary figure. When cast, two legs (right + left)
produce an 8-bit Odu -- one of 256 possible combinations.

Binary encoding: 0 = open mouth (single mark |), 1 = closed mouth (double mark ||)
Reading order: bottom-to-top within each leg (leg 1 = bottom, leg 4 = top)

The 16 Meji (doubled) Odus are the "parents". The 240 Amulu (combined) Odus
are their "children", formed by pairing two different Meji figures.

Ifa's 256 = 4 x I Ching's 64. Each I Ching hexagram corresponds to 4 Ifa Odus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OduMeji:
    """A principal (Meji) Odu -- one of the 16 fundamental figures."""

    number: int  # 1-16, traditional ordering
    name: str  # Yoruba name (e.g., "Eji Ogbe")
    short_name: str  # Short form (e.g., "ogbe")
    binary: str  # 4-bit string, read bottom-to-top (e.g., "0000")
    decimal: int  # Integer value of binary
    element: str  # Wu Xing element association
    polarity: str  # "yang" or "yin" dominant
    meaning: str  # Core meaning
    wisdom: str  # Guidance for this Odu
    ire: str  # Blessing (positive outcome)
    osogbo: str  # Warning (negative outcome)
    prescriptions: list[str] = field(default_factory=list)
    prohibitions: list[str] = field(default_factory=list)

    @property
    def marks(self) -> str:
        """Visual representation: | = open (0), || = closed (1)."""
        return " ".join("||" if b == "1" else "|" for b in self.binary)


PRINCIPAL_ODU: list[OduMeji] = [
    OduMeji(
        number=1,
        name="Eji Ogbe",
        short_name="ogbe",
        binary="0000",
        decimal=0,
        element="wood",
        polarity="yang",
        meaning="Light, beginnings, expansion, truth, kingship",
        wisdom="Honesty and gentle character open the way. Begin with clarity and let light guide expansion.",
        ire="Abundance, long life, success through integrity",
        osogbo="Arrogance, overconfidence, neglect of foundations",
        prescriptions=[
            "Be truthful in all dealings",
            "Start new ventures with clean intention",
        ],
        prohibitions=[
            "Do not lie or deceive",
            "Do not rush expansion without foundation",
        ],
    ),
    OduMeji(
        number=2,
        name="Oyeku Meji",
        short_name="oyeku",
        binary="1111",
        decimal=15,
        element="water",
        polarity="yin",
        meaning="Endings, transformation, death and rebirth, ancestral realm",
        wisdom="Every ending births a new beginning. Honor what passes; transformation is not destruction.",
        ire="Spiritual awakening, ancestral guidance, successful transition",
        osogbo="Untimely loss, stagnation, fear of change",
        prescriptions=["Honor ancestors and transitions", "Embrace necessary endings"],
        prohibitions=[
            "Do not cling to what must pass",
            "Do not ignore ancestral wisdom",
        ],
    ),
    OduMeji(
        number=3,
        name="Iwori Meji",
        short_name="iwori",
        binary="1001",
        decimal=9,
        element="water",
        polarity="yin",
        meaning="Self-reflection, inner vision, intuition, patience",
        wisdom="Look inward for answers. Patience reveals what impulse conceals.",
        ire="Insight, discovery, spiritual vision, patience rewarded",
        osogbo="Confusion, deception, impulsive decisions",
        prescriptions=[
            "Meditate and reflect before acting",
            "Trust intuition over appearances",
        ],
        prohibitions=["Do not act impulsively", "Do not ignore inner warnings"],
    ),
    OduMeji(
        number=4,
        name="Odi Meji",
        short_name="odi",
        binary="0110",
        decimal=6,
        element="earth",
        polarity="yin",
        meaning="Barriers, restriction, containment, the hidden womb",
        wisdom="Obstacles are discipline's teachers. Timing is everything; wait for the gate to open.",
        ire="Protection, strategic advantage, hidden potential realized",
        osogbo="Isolation, blockage, missed opportunities through delay",
        prescriptions=["Use obstacles as training", "Wait for proper timing"],
        prohibitions=["Do not force through barriers", "Do not isolate unnecessarily"],
    ),
    OduMeji(
        number=5,
        name="Irosun Meji",
        short_name="irosun",
        binary="0011",
        decimal=3,
        element="earth",
        polarity="yin",
        meaning="Ancestry, bloodlines, spiritual inheritance, healing",
        wisdom="You are shaped by those who came before. Honor lineage; heal generational patterns.",
        ire="Healing, family harmony, generational blessings",
        osogbo="Family conflict, inherited illness, neglect of roots",
        prescriptions=["Honor ancestors and lineage", "Address inherited patterns"],
        prohibitions=["Do not forget your roots", "Do not repeat ancestral mistakes"],
    ),
    OduMeji(
        number=6,
        name="Owonrin Meji",
        short_name="owonrin",
        binary="1100",
        decimal=12,
        element="metal",
        polarity="yang",
        meaning="Change, movement, instability, transformation",
        wisdom="Life is constant motion. Adaptability is the supreme survival skill.",
        ire="Successful transition, favorable movement, new opportunities",
        osogbo="Instability, restlessness, destructive change",
        prescriptions=["Embrace change adaptively", "Stay grounded during transitions"],
        prohibitions=[
            "Do not resist necessary change",
            "Do not create instability through restlessness",
        ],
    ),
    OduMeji(
        number=7,
        name="Obara Meji",
        short_name="obara",
        binary="0111",
        decimal=7,
        element="earth",
        polarity="yang",
        meaning="Speech, communication, leadership, social order",
        wisdom="Words create reality. Speak truth with clarity; lead through communication.",
        ire="Leadership, influence, successful negotiation, harmony through speech",
        osogbo="Gossip, lies, miscommunication, abuse of power",
        prescriptions=["Speak truthfully and clearly", "Use words to build harmony"],
        prohibitions=["Do not gossip or lie", "Do not misuse influence"],
    ),
    OduMeji(
        number=8,
        name="Okanran Meji",
        short_name="okanran",
        binary="1110",
        decimal=14,
        element="metal",
        polarity="yin",
        meaning="Conflict, struggle, testing of character, resilience",
        wisdom="Challenges forge strength. Meet conflict with patience; character is the ultimate victory.",
        ire="Growth through adversity, character proven, conflict resolved",
        osogbo="Destructive conflict, impulsive reactions, character failure",
        prescriptions=[
            "Meet challenges with patience",
            "Let adversity build character",
        ],
        prohibitions=[
            "Do not react impulsively to provocation",
            "Do not avoid necessary conflict",
        ],
    ),
    OduMeji(
        number=9,
        name="Ogunda Meji",
        short_name="ogunda",
        binary="0001",
        decimal=1,
        element="metal",
        polarity="yang",
        meaning="Iron, labor, breakthrough through struggle, technology",
        wisdom="Progress requires effort and the right tools. Break through obstacles with disciplined action.",
        ire="Breakthrough, technological success, victory through effort",
        osogbo="Injury, conflict, destruction through force",
        prescriptions=[
            "Use the right tools for the job",
            "Persist through obstacles with discipline",
        ],
        prohibitions=["Do not use force carelessly", "Do not neglect proper tools"],
    ),
    OduMeji(
        number=10,
        name="Osa Meji",
        short_name="osa",
        binary="1000",
        decimal=8,
        element="water",
        polarity="yin",
        meaning="Secrets, hidden forces, spiritual power, transformation",
        wisdom="What is hidden shapes what is visible. Seek to understand the unseen forces at work.",
        ire="Spiritual power, hidden knowledge revealed, protection",
        osogbo="Deception, betrayal, overwhelming hidden forces",
        prescriptions=["Investigate the hidden", "Develop spiritual awareness"],
        prohibitions=["Do not ignore hidden influences", "Do not deceive others"],
    ),
    OduMeji(
        number=11,
        name="Ika Meji",
        short_name="ika",
        binary="1011",
        decimal=11,
        element="fire",
        polarity="yang",
        meaning="Struggle, discipline, lessons through hardship, morality",
        wisdom="Hardship tests character. Discipline transforms suffering into wisdom.",
        ire="Character strengthened, discipline rewarded, moral victory",
        osogbo="Arrogance, recklessness, misuse of power, prolonged hardship",
        prescriptions=[
            "Embrace discipline as a path to growth",
            "Maintain morality under pressure",
        ],
        prohibitions=["Do not become arrogant through hardship", "Do not misuse power"],
    ),
    OduMeji(
        number=12,
        name="Oturupon Meji",
        short_name="oturupon",
        binary="1101",
        decimal=13,
        element="earth",
        polarity="yin",
        meaning="Abundance and renewal, expansion and contraction cycles",
        wisdom="Life moves in cycles of fullness and emptiness. Humility in prosperity; patience in hardship.",
        ire="Abundance, renewal, cyclical success, sustainable growth",
        osogbo="Excess, waste, failure to prepare for contraction",
        prescriptions=["Practice humility in prosperity", "Prepare for natural cycles"],
        prohibitions=["Do not waste abundance", "Do not resist necessary contraction"],
    ),
    OduMeji(
        number=13,
        name="Otura Meji",
        short_name="otura",
        binary="0100",
        decimal=4,
        element="metal",
        polarity="yang",
        meaning="Wisdom, guidance, orientation, discernment",
        wisdom="Seek counsel when uncertain. Divine guidance provides direction; discernment reveals the path.",
        ire="Clear direction, wise counsel, good decisions, spiritual guidance",
        osogbo="Poor judgment, ignoring advice, disorientation",
        prescriptions=["Seek wise counsel", "Practice discernment in all things"],
        prohibitions=["Do not ignore good advice", "Do not act without reflection"],
    ),
    OduMeji(
        number=14,
        name="Irete Meji",
        short_name="irete",
        binary="0010",
        decimal=2,
        element="fire",
        polarity="yang",
        meaning="Prosperity, abundance, responsibility, stewardship",
        wisdom="Wealth demands responsibility. Ethical stewardship ensures that prosperity endures.",
        ire="Prosperity, success, opportunities, wealth well-managed",
        osogbo="Greed, irresponsibility, prosperity without ethics",
        prescriptions=["Practice ethical stewardship", "Be grateful for abundance"],
        prohibitions=["Do not hoard wealth", "Do not neglect responsibility"],
    ),
    OduMeji(
        number=15,
        name="Ose Meji",
        short_name="ose",
        binary="0101",
        decimal=5,
        element="water",
        polarity="yin",
        meaning="Sweetness, fertility, feminine energy, nurturing",
        wisdom="Kindness and generosity open the way for blessings. Nurture what you wish to see grow.",
        ire="Love, fertility, prosperity, vitality, harmonious relationships",
        osogbo="Bitterness, infertility, broken relationships, neglect",
        prescriptions=[
            "Practice kindness and generosity",
            "Nurture relationships and projects",
        ],
        prohibitions=["Do not become bitter", "Do not neglect those who depend on you"],
    ),
    OduMeji(
        number=16,
        name="Ofun Meji",
        short_name="ofun",
        binary="1010",
        decimal=10,
        element="metal",
        polarity="yin",
        meaning="Purity, completion, authority, fulfillment of destiny",
        wisdom="Cycles reach completion. Truth is revealed; destiny fulfilled through moral integrity.",
        ire="Destiny fulfilled, legacy established, completion, spiritual maturity",
        osogbo="Impurity, incomplete cycles, moral failure, destiny blocked",
        prescriptions=["Maintain moral integrity", "See cycles through to completion"],
        prohibitions=[
            "Do not abandon projects before completion",
            "Do not compromise ethics",
        ],
    ),
]


# Index by number, short_name, binary, and decimal for fast lookup
ODU_BY_NUMBER: dict[int, OduMeji] = {odu.number: odu for odu in PRINCIPAL_ODU}
ODU_BY_SHORT_NAME: dict[str, OduMeji] = {odu.short_name: odu for odu in PRINCIPAL_ODU}
ODU_BY_BINARY: dict[str, OduMeji] = {odu.binary: odu for odu in PRINCIPAL_ODU}
ODU_BY_DECIMAL: dict[int, OduMeji] = {odu.decimal: odu for odu in PRINCIPAL_ODU}


def get_meji_by_binary(binary: str) -> OduMeji | None:
    """Look up a principal Odu by its 4-bit binary string."""
    return ODU_BY_BINARY.get(binary)


def get_meji_by_number(number: int) -> OduMeji | None:
    """Look up a principal Odu by its traditional number (1-16)."""
    return ODU_BY_NUMBER.get(number)


def get_meji_by_short_name(name: str) -> OduMeji | None:
    """Look up a principal Odu by its short name (e.g., 'ogbe')."""
    return ODU_BY_SHORT_NAME.get(name.lower())


def ifa_to_iching(right_binary: str, left_binary: str) -> int:
    """Map an Ifa Odu (two 4-bit legs) to an I Ching hexagram number (1-64).

    The I Ching hexagram is derived from the trigram elements of both legs.
    Returns the King Wen sequence number.
    """
    # Extract lower trigram from right leg (bottom 3 bits of the 4-bit leg)
    # and upper trigram from left leg (bottom 3 bits of the 4-bit leg)
    lower_tri = int(right_binary[1:], 2)  # bits 1-3 of right leg
    upper_tri = int(left_binary[1:], 2)  # bits 1-3 of left leg

    # Build 6-bit hexagram: lower trigram (3 bits) + upper trigram (3 bits)
    hex_binary = f"{lower_tri:03b}{upper_tri:03b}"
    hex_decimal = int(hex_binary, 2)

    # Convert from Fu Xi sequence to King Wen sequence
    # Fu Xi 0-63 -> King Wen 1-64
    _FUXI_TO_KINGWEN = [
        2,
        23,
        8,
        20,
        16,
        35,
        45,
        12,  # 000-007
        15,
        52,
        39,
        53,
        62,
        56,
        31,
        33,  # 008-015
        7,
        4,
        29,
        59,
        40,
        64,
        47,
        6,  # 016-023
        46,
        18,
        48,
        57,
        32,
        50,
        28,
        44,  # 024-031
        24,
        27,
        3,
        42,
        51,
        21,
        17,
        25,  # 032-039
        36,
        22,
        63,
        37,
        55,
        30,
        49,
        13,  # 040-047
        19,
        41,
        60,
        61,
        54,
        38,
        58,
        10,  # 048-055
        11,
        26,
        5,
        34,
        43,
        9,
        14,
        1,  # 056-063
    ]

    if 0 <= hex_decimal < 64:
        return _FUXI_TO_KINGWEN[hex_decimal]
    return 1  # fallback


def iching_to_ifa(hexagram_number: int) -> list[tuple[str, str]]:
    """Map an I Ching hexagram to its 4 corresponding Ifa Odu leg pairs.

    Returns a list of (right_leg, left_leg) 4-bit binary strings.
    """
    # King Wen to Fu Xi
    _KINGWEN_TO_FUXI = {
        2: 0,
        23: 1,
        8: 2,
        20: 3,
        16: 4,
        35: 5,
        45: 6,
        12: 7,
        15: 8,
        52: 9,
        39: 10,
        53: 11,
        62: 12,
        56: 13,
        31: 14,
        33: 15,
        7: 16,
        4: 17,
        29: 18,
        59: 19,
        40: 20,
        64: 21,
        47: 22,
        6: 23,
        46: 24,
        18: 25,
        48: 26,
        57: 27,
        32: 28,
        50: 29,
        28: 30,
        44: 31,
        24: 32,
        27: 33,
        3: 34,
        42: 35,
        51: 36,
        21: 37,
        17: 38,
        25: 39,
        36: 40,
        22: 41,
        63: 42,
        37: 43,
        55: 44,
        30: 45,
        49: 46,
        13: 47,
        19: 48,
        41: 49,
        60: 50,
        61: 51,
        54: 52,
        38: 53,
        58: 54,
        10: 55,
        11: 56,
        26: 57,
        5: 58,
        34: 59,
        43: 60,
        9: 61,
        14: 62,
        1: 63,
    }

    fuxi_num = _KINGWEN_TO_FUXI.get(hexagram_number, 0)
    hex_binary = f"{fuxi_num:06b}"

    # Lower trigram = first 3 bits, upper trigram = last 3 bits
    lower_tri = hex_binary[0:3]
    upper_tri = hex_binary[3:6]

    # 4 variants: the 4th bit of each leg varies (2 bits = 4 combinations)
    variants = ["0", "1"]
    result = []
    for v_right in variants:
        for v_left in variants:
            right_leg = v_right + lower_tri  # 4-bit right leg
            left_leg = v_left + upper_tri  # 4-bit left leg
            result.append((right_leg, left_leg))

    return result


@dataclass(frozen=True)
class OduAmulu:
    """A combined (Amulu) Odu -- two different Meji figures paired."""

    right_leg: OduMeji  # Right leg (cast first, active/yang)
    left_leg: OduMeji  # Left leg (cast second, receptive/yin)
    number: int  # Position in the 256 (17-256)

    @property
    def name(self) -> str:
        """Naming convention: right-leg short name + left-leg short name."""
        return f"{self.right_leg.short_name.title()}-{self.left_leg.short_name.title()}"

    @property
    def binary(self) -> str:
        """8-bit binary: right leg (4 bits) + left leg (4 bits)."""
        return self.right_leg.binary + self.left_leg.binary

    @property
    def decimal(self) -> int:
        """Decimal value of the 8-bit binary."""
        return int(self.binary, 2)

    @property
    def is_meji(self) -> bool:
        """True if both legs are the same (should not happen for Amulu, but checked)."""
        return self.right_leg.number == self.left_leg.number

    @property
    def iching_hexagram(self) -> int:
        """Corresponding I Ching hexagram number (King Wen sequence)."""
        return ifa_to_iching(self.right_leg.binary, self.left_leg.binary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "number": self.number,
            "binary": self.binary,
            "decimal": self.decimal,
            "right_leg": self.right_leg.short_name,
            "left_leg": self.left_leg.short_name,
            "iching_hexagram": self.iching_hexagram,
            "right_wisdom": self.right_leg.wisdom,
            "left_wisdom": self.left_leg.wisdom,
            "combined_wisdom": f"{self.right_leg.wisdom} {self.left_leg.wisdom}",
        }


def generate_all_amulu() -> list[OduAmulu]:
    """Generate all 240 Amulu (combined) Odu.

    These are ordered pairs of different Meji figures.
    The traditional ordering follows the principal Odu sequence.
    """
    amulu = []
    number = 17  # After the 16 Meji

    for right in PRINCIPAL_ODU:
        for left in PRINCIPAL_ODU:
            if right.number != left.number:
                amulu.append(
                    OduAmulu(
                        right_leg=right,
                        left_leg=left,
                        number=number,
                    )
                )
                number += 1

    return amulu


# Build the complete 256 Odu index lazily
_ALL_ODU: dict[str, OduMeji | OduAmulu] | None = None


def get_all_odu() -> dict[str, OduMeji | OduAmulu]:
    """Get the complete 256 Odu index, keyed by 8-bit binary string."""
    global _ALL_ODU
    if _ALL_ODU is None:
        _ALL_ODU = {}
        # Add 16 Meji (doubled)
        for odu in PRINCIPAL_ODU:
            key = odu.binary + odu.binary  # right + left = same
            _ALL_ODU[key] = odu
        # Add 240 Amulu
        for amulu in generate_all_amulu():
            _ALL_ODU[amulu.binary] = amulu
    return _ALL_ODU


def get_odu_by_binary(binary: str) -> OduMeji | OduAmulu | None:
    """Look up any of the 256 Odu by its 8-bit binary string."""
    return get_all_odu().get(binary)


def get_odu_by_decimal(decimal: int) -> OduMeji | OduAmulu | None:
    """Look up any of the 256 Odu by its decimal value (0-255)."""
    binary = f"{decimal:08b}"
    return get_odu_by_binary(binary)
