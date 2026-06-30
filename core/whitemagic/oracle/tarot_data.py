"""Tarot data — 22 Major Arcana + 56 Minor Arcana.

The Major Arcana correspondences integrate:
- Hebrew letter-numbers (Suarès' Cipher of Genesis): each letter as an
  active cosmic operator, not merely a label
- Kabbalistic paths on the Tree of Life (22 paths between 10 Sephirot)
- Alchemical stages (nigredo, albedo, citrinitas, rubedo, cauda pavonis)
- Fixed-sign tetramorph mapping (from the Magician's table)

The Minor Arcana (Wands/Fire, Cups/Water, Swords/Air, Pentacles/Earth)
each have 14 cards: Ace through 10, plus Page, Knight, Queen, King.

Design principle: Tarot is an impartial consultation tool — an aid to
decision-making, not a replacement for agency. The cards point the way;
they do not walk the path.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MajorArcanaCard:
    """A Major Arcana card with full correspondence data."""
    number: int          # 0-21
    name: str
    hebrew_letter: str   # Suarès letter-number
    hebrew_name: str
    hebrew_value: int    # Numerical value
    suares_meaning: str  # Suarès' cosmic operator meaning
    element: str         # astrological element association
    planet_or_sign: str  # Traditional attribution
    alchemical_stage: str
    keywords: list[str]
    upright_meaning: str
    reversed_meaning: str
    fool_journey_stage: str  # Where in the Fool's Journey


@dataclass(frozen=True)
class MinorArcanaCard:
    """A Minor Arcana card."""
    suit: str            # wands, cups, swords, pentacles
    rank: str            # ace, 2-10, page, knight, queen, king
    number: int          # 1-14
    element: str
    keywords: list[str]
    upright_meaning: str
    reversed_meaning: str

    @property
    def name(self) -> str:
        """Human-readable card name, e.g. 'Ace of Wands', 'Three of Cups'."""
        return f"{self.rank.capitalize()} of {self.suit.capitalize()}"


# ---------------------------------------------------------------------------
# Major Arcana — 22 cards with Suarès correspondences
# ---------------------------------------------------------------------------

MAJOR_ARCANA: list[MajorArcanaCard] = [
    MajorArcanaCard(
        number=0, name="The Fool", hebrew_letter="א", hebrew_name="Aleph",
        hebrew_value=1, suares_meaning="Unthinkable pulsation of life-death; the abstract beat underlying all change",
        element="air", planet_or_sign="Uranus", alchemical_stage="pre-nigredo",
        keywords=["beginning", "innocence", "spontaneity", "leap", "potential"],
        upright_meaning="A new beginning, a leap of faith, infinite potential. The Fool steps off the cliff not in ignorance but in trust.",
        reversed_meaning="Recklessness, naivety, risk without awareness. The leap becomes a fall when taken without presence.",
        fool_journey_stage="Departure — the soul begins its journey, carrying nothing but trust",
    ),
    MajorArcanaCard(
        number=1, name="The Magician", hebrew_letter="ב", hebrew_name="Bet",
        hebrew_value=2, suares_meaning="Container principle; all dwellings and supports which frame existence",
        element="all", planet_or_sign="Mercury", alchemical_stage="nigredo",
        keywords=["manifestation", "will", "skill", "tools", "as above so below"],
        upright_meaning="The Magician aligns the four elemental tools on his table — the fixed-sign tetramorph engaged. As above, so below: manifestation begins.",
        reversed_meaning="Manipulation, illusion, untapped potential. Tools without intention become toys.",
        fool_journey_stage="First step — discovering one's tools and the power to shape reality",
    ),
    MajorArcanaCard(
        number=2, name="The High Priestess", hebrew_letter="ג", hebrew_name="Gimel",
        hebrew_value=3, suares_meaning="Activating movement; the organic impetus that animates containers",
        element="water", planet_or_sign="Moon", alchemical_stage="nigredo",
        keywords=["intuition", "mystery", "subconscious", "inner voice", "veil"],
        upright_meaning="The veil between conscious and subconscious thins. Listen to the inner voice; the answer is within.",
        reversed_meaning="Disconnection from intuition, secrets, hidden agendas. The veil thickens when ignored.",
        fool_journey_stage="Inner awakening — encountering the deeper self behind the veil",
    ),
    MajorArcanaCard(
        number=3, name="The Empress", hebrew_letter="ד", hebrew_name="Dalet",
        hebrew_value=4, suares_meaning="Physical resistance; the inertia that gives structure and boundaries",
        element="earth", planet_or_sign="Venus", alchemical_stage="nigredo",
        keywords=["abundance", "nurturing", "fertility", "nature", "creation"],
        upright_meaning="Creative abundance, nurturing energy. The Empress is the fertile soil from which all things grow.",
        reversed_meaning="Creative block, dependence, overprotectiveness. The soil becomes swamp when it cannot drain.",
        fool_journey_stage="First creation — bringing something new into the world through nurturing",
    ),
    MajorArcanaCard(
        number=4, name="The Emperor", hebrew_letter="ה", hebrew_name="He",
        hebrew_value=5, suares_meaning="Universal life-force; the breath of vitality that infuses matter",
        element="fire", planet_or_sign="Aries", alchemical_stage="nigredo",
        keywords=["authority", "structure", "control", "leadership", "stability"],
        upright_meaning="Structure, authority, the framework that channels energy productively. The Emperor builds the container for the Work.",
        reversed_meaning="Domination, rigidity, inflexibility. The container becomes a cage.",
        fool_journey_stage="Establishing order — creating the structures needed for the journey",
    ),
    MajorArcanaCard(
        number=5, name="The Hierophant", hebrew_letter="ו", hebrew_name="Vav",
        hebrew_value=6, suares_meaning="Fertilizing link; the agent of impregnation that bridges life and form",
        element="earth", planet_or_sign="Taurus", alchemical_stage="nigredo",
        keywords=["tradition", "teaching", "guidance", "institution", "initiation"],
        upright_meaning="Sacred knowledge passed down through tradition. The Hierophant is the bridge between the seeker and the mystery.",
        reversed_meaning="Dogma, conformity, challenge to convention. The bridge becomes a wall when tradition stifles growth.",
        fool_journey_stage="Learning — receiving teachings and entering the tradition",
    ),
    MajorArcanaCard(
        number=6, name="The Lovers", hebrew_letter="ז", hebrew_name="Zayin",
        hebrew_value=7, suares_meaning="Realized potential; the opening into possibility when form is achieved",
        element="air", planet_or_sign="Gemini", alchemical_stage="nigredo",
        keywords=["choice", "union", "love", "values", "crossroads"],
        upright_meaning="A meaningful choice, a union of opposites. The Lovers represent the heart's decision at the crossroads.",
        reversed_meaning="Disharmony, misalignment, difficult choices. The crossroads becomes a trap when values conflict.",
        fool_journey_stage="First choice — deciding what truly matters, aligning heart and will",
    ),
    MajorArcanaCard(
        number=7, name="The Chariot", hebrew_letter="ח", hebrew_name="Het",
        hebrew_value=8, suares_meaning="Primordial reservoir; the unstructured energy substratum of the cosmos",
        element="water", planet_or_sign="Cancer", alchemical_stage="nigredo",
        keywords=["willpower", "victory", "control", "determination", "drive"],
        upright_meaning="Focused will achieves victory. The Charioteer harnesses opposing forces and drives them toward a single goal.",
        reversed_meaning="Loss of control, scattered energy, aggression without direction. The chariot crashes when the reins are loose.",
        fool_journey_stage="First victory — mastering opposing forces through will and focus",
    ),
    MajorArcanaCard(
        number=8, name="Strength", hebrew_letter="ט", hebrew_name="Tet",
        hebrew_value=9, suares_meaning="Primeval structure; the female principle building form from formless energy",
        element="fire", planet_or_sign="Leo", alchemical_stage="nigredo→albedo",
        keywords=["courage", "patience", "inner strength", "compassion", "mastery"],
        upright_meaning="Inner strength tames the beast through gentleness, not force. The lion rests beside the one who has mastered themselves.",
        reversed_meaning="Self-doubt, raw emotion, lack of self-control. The beast rules when courage fails.",
        fool_journey_stage="Inner mastery — learning that true strength is gentle, not forceful",
    ),
    MajorArcanaCard(
        number=9, name="The Hermit", hebrew_letter="י", hebrew_name="Yod",
        hebrew_value=10, suares_meaning="Temporal existence; projection of the primal pulsation into continuity",
        element="earth", planet_or_sign="Virgo", alchemical_stage="albedo",
        keywords=["introspection", "solitude", "inner guidance", "wisdom", "the lantern"],
        upright_meaning="The Hermit holds the lantern aloft, illuminating the path within. Solitude reveals what company obscures.",
        reversed_meaning="Isolation, withdrawal, loneliness. The lantern dims when the hermit forgets why they climbed.",
        fool_journey_stage="Withdrawal — seeking inner wisdom, carrying the light of consciousness",
    ),
    MajorArcanaCard(
        number=10, name="Wheel of Fortune", hebrew_letter="כ", hebrew_name="Kaf",
        hebrew_value=20, suares_meaning="Receptive capacity; the hollow hand ready to receive and hold emergent forms",
        element="fire", planet_or_sign="Jupiter", alchemical_stage="albedo",
        keywords=["cycles", "destiny", "change", "fortune", "turning point"],
        upright_meaning="The wheel turns. What was up comes down; what was down rises. The fixed-sign glyphs mark the hinge points of the Great Year.",
        reversed_meaning="Bad luck, resistance to change, the wheel stuck. Fortune favors those who accept the turn.",
        fool_journey_stage="Encountering cycles — recognizing that life moves in spirals, not lines",
    ),
    MajorArcanaCard(
        number=11, name="Justice", hebrew_letter="ל", hebrew_name="Lammed",
        hebrew_value=30, suares_meaning="Connecting principle; the controlled mediator linking forces",
        element="air", planet_or_sign="Libra", alchemical_stage="albedo",
        keywords=["justice", "fairness", "truth", "balance", "karma"],
        upright_meaning="Truth balanced with compassion. Justice weighs the heart against the feather and finds equilibrium.",
        reversed_meaning="Injustice, unfairness, dishonesty. The scales tip when truth is avoided.",
        fool_journey_stage="Accountability — facing the consequences of choices with honesty",
    ),
    MajorArcanaCard(
        number=12, name="The Hanged Man", hebrew_letter="מ", hebrew_name="Mem",
        hebrew_value=40, suares_meaning="Maternal medium; the waters of formation where life originates",
        element="water", planet_or_sign="Neptune", alchemical_stage="albedo",
        keywords=["surrender", "new perspective", "sacrifice", "letting go", "suspension"],
        upright_meaning="Surrender brings revelation. The Hanged Man sees the world upside down and discovers truth in the reversal.",
        reversed_meaning="Stalling, indecision, resistance to sacrifice. The suspension becomes stagnation.",
        fool_journey_stage="Reversal — seeing from a new angle, letting go of old perspectives",
    ),
    MajorArcanaCard(
        number=13, name="Death", hebrew_letter="נ", hebrew_name="Nun",
        hebrew_value=50, suares_meaning="Individual existence; the conditioned manifestation of universal life",
        element="water", planet_or_sign="Scorpio", alchemical_stage="albedo→cauda pavonis",
        keywords=["transformation", "endings", "transition", "release", "rebirth"],
        upright_meaning="The old self dies so the new can emerge. Death is not an ending but a threshold — the caterpillar dissolving in the chrysalis.",
        reversed_meaning="Resistance to change, stagnation, fear of transformation. The chrysalis hardens when the butterfly fears the air.",
        fool_journey_stage="The great transition — shedding the old self, entering the unknown",
    ),
    MajorArcanaCard(
        number=14, name="Temperance", hebrew_letter="ס", hebrew_name="Samekh",
        hebrew_value=60, suares_meaning="Cyclical support; the female enclosure of fertility within repetition",
        element="fire", planet_or_sign="Sagittarius", alchemical_stage="cauda pavonis",
        keywords=["balance", "moderation", "blending", "alchemy", "patience"],
        upright_meaning="The angel mixes fire and water, creating the elixir. Temperance is the alchemical art of blending opposites into wholeness.",
        reversed_meaning="Imbalance, excess, impatience. The mixture separates when the angel's hand grows weary.",
        fool_journey_stage="Integration — blending the lessons of death and rebirth into a new whole",
    ),
    MajorArcanaCard(
        number=15, name="The Devil", hebrew_letter="ע", hebrew_name="Ayin",
        hebrew_value=70, suares_meaning="Perceptive vision; the eye that sources and frames potential",
        element="earth", planet_or_sign="Capricorn", alchemical_stage="cauda pavonis",
        keywords=["bondage", "attachment", "shadow", "materialism", "illusion"],
        upright_meaning="The chains are loose — the Devil reveals where we have chained ourselves through attachment and fear. Awareness is the key.",
        reversed_meaning="Liberation, releasing chains, confronting the shadow. The locks were never real.",
        fool_journey_stage="The shadow — confronting what binds us, seeing through the illusion of limitation",
    ),
    MajorArcanaCard(
        number=16, name="The Tower", hebrew_letter="פ", hebrew_name="Pe",
        hebrew_value=80, suares_meaning="Primal articulation; the channeling of undifferentiated energy",
        element="fire", planet_or_sign="Mars", alchemical_stage="cauda pavonis→rubedo",
        keywords=["upheaval", "revelation", "awakening", "destruction", "truth"],
        upright_meaning="The lightning strikes the false tower. What was built on illusion crumbles, revealing the bedrock truth beneath.",
        reversed_meaning="Avoiding disaster, fear of change, the tower weakened but not yet fallen. Delay is not safety.",
        fool_journey_stage="The breaking — false structures collapse, the ego's tower falls to reveal what is real",
    ),
    MajorArcanaCard(
        number=17, name="The Star", hebrew_letter="צ", hebrew_name="Tsadi",
        hebrew_value=90, suares_meaning="Evolutionary structuring; progression from simple cell to complex form",
        element="air", planet_or_sign="Aquarius", alchemical_stage="rubedo",
        keywords=["hope", "inspiration", "renewal", "guidance", "cosmic flow"],
        upright_meaning="After the Tower falls, the Star appears. Hope pours from the cosmos — the Aquarian vision of collective intelligence and renewal.",
        reversed_meaning="Despair, lost faith, disconnection from inspiration. The star fades when the eyes are fixed on the ground.",
        fool_journey_stage="Renewal — finding hope after destruction, receiving cosmic guidance",
    ),
    MajorArcanaCard(
        number=18, name="The Moon", hebrew_letter="ק", hebrew_name="Qof",
        hebrew_value=100, suares_meaning="Deathless transcendence; exalted pulsation that escapes temporal decay",
        element="water", planet_or_sign="Pisces", alchemical_stage="rubedo",
        keywords=["illusion", "fear", "subconscious", "dreams", "the path through darkness"],
        upright_meaning="The Moon illuminates the path through the unconscious. Dreams and fears become teachers, not enemies.",
        reversed_meaning="Confusion released, fears faced, the path clears. The moon's light reveals what was hidden.",
        fool_journey_stage="The dark night — navigating the unconscious, facing fears and dreams",
    ),
    MajorArcanaCard(
        number=19, name="The Sun", hebrew_letter="ר", hebrew_name="Resh",
        hebrew_value=200, suares_meaning="Cosmic container; the star-strewn dwelling holding all existence",
        element="fire", planet_or_sign="Sun", alchemical_stage="rubedo",
        keywords=["joy", "success", "vitality", "clarity", "illumination"],
        upright_meaning="The Sun shines on all without discrimination. Joy, vitality, and the clarity that comes after the dark night has passed.",
        reversed_meaning="Temporary clouds, delayed success, the sun obscured but not extinguished.",
        fool_journey_stage="Illumination — the full light of consciousness, joy after the journey through darkness",
    ),
    MajorArcanaCard(
        number=20, name="Judgment", hebrew_letter="ש", hebrew_name="Shin",
        hebrew_value=300, suares_meaning="Spirit-breath; the prodigious motion animating every organism",
        element="fire", planet_or_sign="Pluto", alchemical_stage="rubedo",
        keywords=["rebirth", "absolution", "awakening", "calling", "resurrection"],
        upright_meaning="The trumpet calls — a moment of reckoning and rebirth. The past is integrated; the future calls with clarity.",
        reversed_meaning="Self-judgment, ignoring the call, refusing the rebirth. The trumpet sounds but the sleeper will not wake.",
        fool_journey_stage="The call — hearing one's true purpose, rising to meet the final transformation",
    ),
    MajorArcanaCard(
        number=21, name="The World", hebrew_letter="ת", hebrew_name="Tav",
        hebrew_value=400, suares_meaning="Structural limit; the resistance that enables form to emerge",
        element="earth", planet_or_sign="Saturn", alchemical_stage="rubedo→completion",
        keywords=["completion", "wholeness", "integration", "the wreath", "cosmic consciousness"],
        upright_meaning="The Fool's Journey completes. The World's wreath encloses all experience — the fixed-sign tetramorph fully realized. The circle closes; a new one begins.",
        reversed_meaning="Incomplete cycle, seeking closure, the wreath not yet woven. The journey continues.",
        fool_journey_stage="Completion — the full circle, integration of all lessons, the return to the beginning at a higher level",
    ),
]


# ---------------------------------------------------------------------------
# Minor Arcana — 56 cards (4 suits × 14 cards)
# ---------------------------------------------------------------------------

_SUITS: dict[str, dict[str, str]] = {
    "wands": {
        "element": "fire",
        "theme": "Will, passion, creativity, action, inspiration",
        "zodiac_assoc": "Aries, Leo, Sagittarius",
    },
    "cups": {
        "element": "water",
        "theme": "Emotion, relationships, intuition, love, the heart",
        "zodiac_assoc": "Cancer, Scorpio, Pisces",
    },
    "swords": {
        "element": "air",
        "theme": "Intellect, communication, conflict, truth, the mind",
        "zodiac_assoc": "Gemini, Libra, Aquarius",
    },
    "pentacles": {
        "element": "earth",
        "theme": "Material world, resources, body, work, manifestation",
        "zodiac_assoc": "Taurus, Virgo, Capricorn",
    },
}

_RANKS: list[tuple[str, int]] = [
    ("ace", 1), ("two", 2), ("three", 3), ("four", 4), ("five", 5),
    ("six", 6), ("seven", 7), ("eight", 8), ("nine", 9), ("ten", 10),
    ("page", 11), ("knight", 12), ("queen", 13), ("king", 14),
]

# Concise meanings for each suit/rank combination
# These are intentionally compact — the Minor Arcana provide texture and
# specificity, while the Major Arcana carry the primary archetypal weight.

_MINOR_MEANINGS: dict[str, dict[str, tuple[str, str, str]]] = {
    "wands": {
        "ace": ("spark of inspiration", "new creative venture", "delayed inspiration"),
        "two": ("planning, deciding direction", "making choices about the future", "fear of commitment"),
        "three": ("expansion, forward movement", "progress and growth", "delays, obstacles to growth"),
        "four": ("celebration, stability", "harmony and achievement", "instability, disrupted peace"),
        "five": ("conflict, competition", "healthy rivalry, striving", "avoidance of conflict"),
        "six": ("victory, recognition", "success and public acclaim", "failure to gain recognition"),
        "seven": ("defiance, standing one's ground", "defending position with courage", "yielding, giving up"),
        "eight": ("speed, swift action", "rapid progress, momentum", "frustration, delays"),
        "nine": ("resilience, last stand", "strength under pressure", "exhaustion, fatigue"),
        "ten": ("burden, responsibility", "carrying the weight of success", "overwhelm, unable to carry the load"),
        "page": ("messenger of fire", "new creative opportunity, enthusiasm", "delayed news, lack of direction"),
        "knight": ("quest for inspiration", "adventurous, passionate pursuit", "recklessness, impulsiveness"),
        "queen": ("mastery of passion", "confident, creative leadership", "insecurity, jealousy"),
        "king": ("mastery of will", "charismatic, visionary authority", "tyranny, domineering"),
    },
    "cups": {
        "ace": ("overflowing emotion", "new love or emotional beginning", "blocked emotions, emptiness"),
        "two": ("partnership, connection", "mutual attraction, harmony", "imbalance, broken trust"),
        "three": ("celebration, friendship", "joyful community, abundance", "isolation, social conflict"),
        "four": ("boredom, apathy", "contemplating new options", "missed opportunity, awareness returning"),
        "five": ("loss, grief", "processing emotional pain", "recovery, moving forward"),
        "six": ("nostalgia, childhood", "innocent joy, memories", "clinging to the past"),
        "seven": ("illusion, choices", "many options, dreamlike state", "clarity, making a grounded choice"),
        "eight": ("walking away", "leaving what no longer serves", "fear of leaving, staying stuck"),
        "nine": ("emotional fulfillment", "contentment, self-love", "dissatisfaction, smugness"),
        "ten": ("perfect happiness", "emotional completion, family", "misalignment of values"),
        "page": ("messenger of water", "new emotional opportunity, intuition", "emotional immaturity, moodiness"),
        "knight": ("quest for love", "romantic, idealistic pursuit", "unrealistic expectations, moodiness"),
        "queen": ("mastery of heart", "compassionate, intuitive leadership", "emotional dependence, insecurity"),
        "king": ("mastery of emotion", "diplomatic, balanced authority", "manipulation, emotional withdrawal"),
    },
    "swords": {
        "ace": ("clarity of mind", "breakthrough, sharp insight", "confusion, clouded judgment"),
        "two": ("difficult choice, stalemate", "balanced decision, truce", "indecision, information withheld"),
        "three": ("heartbreak, sorrow", "processing painful truth", "recovery from grief, healing"),
        "four": ("rest, recovery", "needed pause, convalescence", "restlessness, forced rest"),
        "five": ("conflict, defeat", "hollow victory, loss", "reconciliation, moving past conflict"),
        "six": ("transition, moving away", "leaving troubles behind", "resistance to change, carrying baggage"),
        "seven": ("strategy, deception", "clever planning, indirect approach", "exposure, confession"),
        "eight": ("entrapment, self-limitation", "feeling trapped by thoughts", "release from mental prison"),
        "nine": ("anxiety, worry", "sleepless nights, fear", "recovery from anxiety, hope"),
        "ten": ("painful ending, betrayal", "rock bottom, the end of suffering", "recovery, survival, the worst is over"),
        "page": ("messenger of air", "new idea, curiosity, vigilance", "miscommunication, gossip"),
        "knight": ("quest for truth", "driven, intellectual pursuit", "aggression, dogmatism"),
        "queen": ("mastery of mind", "perceptive, honest, independent", "coldness, cruelty, bitterness"),
        "king": ("mastery of intellect", "authoritative, fair, decisive", "manipulation, tyranny of reason"),
    },
    "pentacles": {
        "ace": ("new opportunity", "prosperity, material beginning", "missed opportunity, lack"),
        "two": ("juggling resources", "balancing multiple priorities", "overwhelm, disorganization"),
        "three": ("collaboration, craft", "teamwork, skilled work", "lack of recognition, poor quality"),
        "four": ("stability, holding", "financial security, conservation", "greed, possessiveness"),
        "five": ("hardship, scarcity", "material difficulty, feeling left out", "recovery, improvement"),
        "six": ("generosity, giving", "sharing resources, charity", "inequality, strings attached"),
        "seven": ("assessment, patience", "evaluating progress, waiting for results", "impatience, poor investment"),
        "eight": ("dedication, skill", "mastery through practice, craftsmanship", "lack of focus, mediocrity"),
        "nine": ("abundance, self-sufficiency", "financial independence, enjoyment", "overwork, false wealth"),
        "ten": ("legacy, family wealth", "generational success, security", "financial loss, family disputes"),
        "page": ("messenger of earth", "new opportunity, studiousness", "lack of progress, laziness"),
        "knight": ("quest for prosperity", "patient, reliable, hardworking", "stagnation, stubbornness"),
        "queen": ("mastery of resources", "nurturing, practical, abundant", "selfishness, insecurity about resources"),
        "king": ("mastery of matter", "wealthy, successful, generous", "greed, materialism, control"),
    },
}


def _build_minor_arcana() -> list[MinorArcanaCard]:
    """Build the 56 Minor Arcana cards from the meaning tables."""
    cards: list[MinorArcanaCard] = []
    for suit, suit_info in _SUITS.items():
        element = suit_info["element"]
        meanings = _MINOR_MEANINGS[suit]
        for rank, number in _RANKS:
            keywords_str, upright, reversed_m = meanings[rank]
            keywords = keywords_str.split(", ")
            cards.append(MinorArcanaCard(
                suit=suit, rank=rank, number=number, element=element,
                keywords=keywords,
                upright_meaning=upright,
                reversed_meaning=reversed_m,
            ))
    return cards


MINOR_ARCANA: list[MinorArcanaCard] = _build_minor_arcana()


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_major_arcana(number: int) -> MajorArcanaCard | None:
    """Get a Major Arcana card by number (0-21)."""
    if 0 <= number <= 21:
        return MAJOR_ARCANA[number]
    return None


def get_minor_arcana(suit: str, rank: str) -> MinorArcanaCard | None:
    """Get a Minor Arcana card by suit and rank."""
    for card in MINOR_ARCANA:
        if card.suit == suit and card.rank == rank:
            return card
    return None


def get_all_cards() -> list[MajorArcanaCard | MinorArcanaCard]:
    """Get all 78 cards."""
    return list(MAJOR_ARCANA) + list(MINOR_ARCANA)


# Fixed-sign tetramorph mapping (from the Magician's table)
FIXED_SIGN_TETRAMORPH: dict[str, dict[str, str]] = {
    "aquarius": {"element": "air", "tool": "cup", "teaching": "Mind can flow like water when aired-out"},
    "leo": {"element": "fire", "tool": "wand", "teaching": "Will must learn to rest, not burn itself out"},
    "scorpio": {"element": "water", "tool": "sword", "teaching": "Intellect becomes vision once passions transmute"},
    "taurus": {"element": "earth", "tool": "pentacle", "teaching": "Stable form holds all other forces"},
}

# The Magician → Wheel → World triple arc
TRIPLE_ARC: dict[str, int] = {
    "magician": 1,
    "wheel": 10,
    "world": 21,
}
