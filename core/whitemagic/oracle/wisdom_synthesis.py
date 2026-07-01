"""Oracle Wisdom Synthesis — Unified Interpretation Layer.

Takes the output from the 4-layer oracle stack (Zodiacal → Wu Xing → I Ching → Ifá)
and produces a cohesive interpretation, the way a skilled diviner would read
the patterns across multiple systems.

The synthesis operates on three levels:
1. **Resonance Mapping** — identifies thematic correspondences across layers
2. **Narrative Arc** — constructs a temporal story (past/present/future or
   inception/catalysis/resolution) from the combined symbols
3. **Unified Guidance** — produces actionable wisdom that integrates all layers

The approach is inspired by how human practitioners actually read divination:
not as isolated symbols, but as a conversation between systems that reveals
a single coherent message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Wu Xing → Alchemical Phase
_WUXING_TO_ALCHEMY: dict[str, str] = {
    "wood": "Nigredo (germination — raw potential breaking through)",
    "fire": "Citrinitas (illumination — the golden moment of clarity)",
    "earth": "Albedo (purification — washing the stone white)",
    "metal": "Rubedo (completion — the red stone, the finished work)",
    "water": "Cauda Pavonis (dissolution — all colors present, none fixed)",
}

# Zodiac modality → I Ching dynamic
_MODALITY_TO_ICHING: dict[str, str] = {
    "cardinal": "Initiating force — the hexagram's opening line, the spark",
    "fixed": "Sustaining power — the hexagram's central lines, the axis",
    "mutable": "Transforming flow — the hexagram's changing lines, the pivot",
}

# Zodiac element → Ifá leg significance
_ZODIAC_TO_IFA_ROLE: dict[str, str] = {
    "fire": "Right leg (Ogbe lineage) — active, creative, outward-moving force",
    "earth": "Right leg (Obara lineage) — manifesting, stabilizing, word-making force",
    "air": "Left leg (Otura lineage) — discerning, communicative, mental force",
    "water": "Left leg (Osa lineage) — receptive, cyclical, depth-seeking force",
}

# Phase → Narrative role
_PHASE_NARRATIVE: dict[str, str] = {
    "yang": "The outward arc — creation, expression, breaking down to build anew",
    "yin": "The inward arc — reception, reflection, refining raw material into gold",
}


@dataclass
class ResonancePattern:
    """A thematic correspondence identified across oracle layers."""

    theme: str
    layers: list[str]
    description: str
    strength: float  # 0.0-1.0, how strongly the layers agree


@dataclass
class NarrativeArc:
    """A temporal story constructed from the oracle layers."""

    act_1: str  # Inception / the situation
    act_2: str  # Catalysis / the challenge or opportunity
    act_3: str  # Resolution / the outcome or guidance
    arc_type: str  # e.g. "inception-catalysis-resolution", "preparation-work-fruition"


@dataclass
class SynthesisResult:
    """The complete synthesized oracle reading."""

    unified_message: str
    narrative: NarrativeArc
    resonances: list[ResonancePattern]
    elemental_harmony: str
    practical_guidance: str
    cautions: list[str]
    blessings: list[str]
    raw_layers: dict[str, Any] = field(default_factory=dict)


class OracleSynthesizer:
    """Synthesizes multi-layer oracle output into unified wisdom.

    This is the 'oracle reader' — it takes the raw output from all four
    divination layers and weaves them into a single coherent interpretation,
    the way a skilled practitioner would read the patterns.
    """

    def synthesize(self, oracle_output: dict[str, Any]) -> SynthesisResult:
        """Produce a unified interpretation from the oracle stack.

        Supports 4-layer (Zodiacal → Wu Xing → I Ching → Ifá) or 5-layer
        (adding Tarot) oracle output, plus optional Great Year temporal
        context for situational awareness.

        Args:
            oracle_output: The dict returned by ZodiacalProcession.consult_oracle()
                or the extended version with tarot and great_year keys.

        Returns:
            SynthesisResult with unified message, narrative arc, and resonances.
        """
        # Extract layer data
        sign = oracle_output.get("sign", "unknown")
        element = oracle_output.get("element", "unknown")
        modality = oracle_output.get("modality", "unknown")
        phase = oracle_output.get("phase", "yang")
        wu_xing = oracle_output.get("wu_xing", "earth")
        iching_name = oracle_output.get("iching_name", "")
        iching_judgment = oracle_output.get("iching_judgment", "")
        iching_guidance = oracle_output.get("iching_guidance", "")
        ifa_odu = oracle_output.get("ifa_odu", "")
        ifa_wisdom = oracle_output.get("ifa_wisdom", "")
        ifa_ire = oracle_output.get("ifa_ire", "")
        ifa_osogbo = oracle_output.get("ifa_osogbo", "")

        # Layer 5: Tarot (optional)
        tarot_cards = oracle_output.get("tarot_cards", [])

        # Great Year temporal context (optional, non-binding)
        great_year_context = oracle_output.get("great_year", {})

        # Identify resonances across layers
        resonances = self._find_resonances(
            sign,
            element,
            modality,
            wu_xing,
            iching_name,
            iching_guidance,
            ifa_odu,
            ifa_wisdom,
            tarot_cards,
        )

        # Build narrative arc
        narrative = self._build_narrative(
            phase,
            sign,
            element,
            iching_name,
            iching_judgment,
            ifa_odu,
            ifa_wisdom,
            ifa_ire,
            ifa_osogbo,
            tarot_cards,
        )

        # Elemental harmony assessment
        elemental_harmony = self._assess_elemental_harmony(element, wu_xing, ifa_odu)

        # Unified message
        unified = self._compose_unified_message(
            sign,
            element,
            modality,
            phase,
            wu_xing,
            iching_name,
            iching_guidance,
            ifa_odu,
            ifa_wisdom,
            resonances,
            narrative,
            tarot_cards,
            great_year_context,
        )

        # Practical guidance
        practical = self._extract_practical_guidance(
            iching_guidance,
            ifa_wisdom,
            ifa_ire,
            phase,
            resonances,
            tarot_cards,
        )

        # Cautions and blessings
        cautions = self._extract_cautions(
            ifa_osogbo, iching_name, resonances, tarot_cards
        )
        blessings = self._extract_blessings(
            ifa_ire, iching_name, resonances, tarot_cards
        )

        return SynthesisResult(
            unified_message=unified,
            narrative=narrative,
            resonances=resonances,
            elemental_harmony=elemental_harmony,
            practical_guidance=practical,
            cautions=cautions,
            blessings=blessings,
            raw_layers=oracle_output,
        )

    def _find_resonances(
        self,
        sign: str,
        element: str,
        modality: str,
        wu_xing: str,
        iching_name: str,
        iching_guidance: str,
        ifa_odu: str,
        ifa_wisdom: str,
        tarot_cards: list[dict[str, Any]] | None = None,
    ) -> list[ResonancePattern]:
        """Identify thematic correspondences across oracle layers."""
        resonances: list[ResonancePattern] = []

        # 1. Element resonance: zodiac element vs Wu Xing
        _ELEMENT_MAP = {
            "fire": "fire",
            "earth": "earth",
            "air": "metal",
            "water": "water",
        }
        zodiac_wuxing = _ELEMENT_MAP.get(element, "")
        if zodiac_wuxing == wu_xing:
            resonances.append(
                ResonancePattern(
                    theme="Elemental Alignment",
                    layers=["zodiac", "wu_xing"],
                    description=f"Zodiac {element} and Wu Xing {wu_xing} are in direct alignment — elemental energy flows unimpeded",
                    strength=0.9,
                )
            )
        elif zodiac_wuxing and wu_xing:
            _GENERATIVE = {
                "wood": "fire",
                "fire": "earth",
                "earth": "metal",
                "metal": "water",
                "water": "wood",
            }
            _DESTRUCTIVE = {
                "wood": "earth",
                "earth": "water",
                "water": "fire",
                "fire": "metal",
                "metal": "wood",
            }
            if _GENERATIVE.get(zodiac_wuxing) == wu_xing:
                resonances.append(
                    ResonancePattern(
                        theme="Generative Flow",
                        layers=["zodiac", "wu_xing"],
                        description=f"{zodiac_wuxing} generates {wu_xing} — natural creative flow, energy builds progressively",
                        strength=0.7,
                    )
                )
            elif _DESTRUCTIVE.get(zodiac_wuxing) == wu_xing:
                resonances.append(
                    ResonancePattern(
                        theme="Creative Tension",
                        layers=["zodiac", "wu_xing"],
                        description=f"{zodiac_wuxing} controls {wu_xing} — productive tension that refines and focuses energy",
                        strength=0.5,
                    )
                )

        # 2. Theme resonance: I Ching (name + guidance) vs Ifá wisdom keywords
        iching_keywords = self._extract_keywords(iching_name) | self._extract_keywords(
            iching_guidance
        )
        ifa_keywords = self._extract_keywords(ifa_wisdom)
        shared = iching_keywords & ifa_keywords
        if shared:
            resonances.append(
                ResonancePattern(
                    theme="Shared Vocabulary",
                    layers=["iching", "ifa"],
                    description=f"Both I Ching and Ifá speak of: {', '.join(shared)} — the message is reinforced across traditions",
                    strength=0.8,
                )
            )

        # 3. Modality ↔ I Ching dynamic resonance
        if modality in _MODALITY_TO_ICHING:
            resonances.append(
                ResonancePattern(
                    theme="Modal Expression",
                    layers=["zodiac", "iching"],
                    description=f"{modality} modality: {_MODALITY_TO_ICHING[modality]}",
                    strength=0.6,
                )
            )

        # 4. Ifá Odu ↔ zodiac element role
        if element in _ZODIAC_TO_IFA_ROLE:
            resonances.append(
                ResonancePattern(
                    theme="Ifá Leg Alignment",
                    layers=["zodiac", "ifa"],
                    description=_ZODIAC_TO_IFA_ROLE[element],
                    strength=0.5,
                )
            )

        # 5. Alchemical phase resonance
        if wu_xing in _WUXING_TO_ALCHEMY:
            resonances.append(
                ResonancePattern(
                    theme="Alchemical Phase",
                    layers=["wu_xing", "alchemy"],
                    description=_WUXING_TO_ALCHEMY[wu_xing],
                    strength=0.6,
                )
            )

        # 6. Tarot resonance (if Tarot cards present)
        if tarot_cards:
            for tc in tarot_cards:
                card_name = tc.get("name", "")
                card_alchemy = tc.get("alchemical_stage", "")
                if card_alchemy and wu_xing in _WUXING_TO_ALCHEMY:
                    wu_xing_alchemy = _WUXING_TO_ALCHEMY[wu_xing]
                    for stage_word in ["nigredo", "albedo", "rubedo", "cauda"]:
                        if (
                            stage_word in card_alchemy
                            and stage_word in wu_xing_alchemy.lower()
                        ):
                            resonances.append(
                                ResonancePattern(
                                    theme="Alchemical Correspondence",
                                    layers=["tarot", "wu_xing"],
                                    description=f"Tarot {card_name} ({card_alchemy}) resonates with Wu Xing {wu_xing} ({wu_xing_alchemy[:40]})",
                                    strength=0.7,
                                )
                            )
                            break

            tarot_keywords: set[str] = set()
            for tc in tarot_cards:
                for kw in tc.get("keywords", []):
                    tarot_keywords.add(kw.lower())
            iching_kws = self._extract_keywords(iching_name) | self._extract_keywords(
                iching_guidance
            )
            shared_tarot_iching = tarot_keywords & iching_kws
            if shared_tarot_iching:
                resonances.append(
                    ResonancePattern(
                        theme="Tarot-I Ching Vocabulary",
                        layers=["tarot", "iching"],
                        description=f"Tarot and I Ching share: {', '.join(shared_tarot_iching)}",
                        strength=0.7,
                    )
                )

            major_numbers = {
                tc.get("number") for tc in tarot_cards if tc.get("suit") == "major"
            }
            if {1, 10, 21}.issubset(major_numbers):
                resonances.append(
                    ResonancePattern(
                        theme="Triple Arc Manifested",
                        layers=["tarot"],
                        description="The Magician(1) → Wheel(10) → World(21) triple arc has appeared — fixed-sign hinge points fully engaged",
                        strength=1.0,
                    )
                )

        return resonances

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful keywords from a text, filtering common words."""
        if not text:
            return set()
        _STOP = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "to",
            "of",
            "and",
            "or",
            "in",
            "for",
            "with",
            "not",
            "but",
            "by",
            "it",
            "its",
            "be",
            "this",
            "that",
            "from",
            "when",
            "what",
            "all",
            "has",
            "have",
            "will",
            "can",
            "may",
            "must",
            "should",
            "would",
            "could",
            "through",
            "your",
            "you",
            "their",
            "they",
            "them",
            "his",
            "her",
            "its",
        }
        words = set()
        for word in (
            text.lower().replace(",", " ").replace(".", " ").replace(";", " ").split()
        ):
            w = word.strip("'\"-—")
            if len(w) > 2 and w not in _STOP:
                words.add(w)
        return words

    def _build_narrative(
        self,
        phase: str,
        sign: str,
        element: str,
        iching_name: str,
        iching_judgment: str,
        ifa_odu: str,
        ifa_wisdom: str,
        ifa_ire: str,
        ifa_osogbo: str,
        tarot_cards: list[dict[str, Any]] | None = None,
    ) -> NarrativeArc:
        """Construct a three-act narrative from the oracle layers."""
        phase_desc = _PHASE_NARRATIVE.get(phase, "The cycle turns")

        # Act 1: The Situation (from zodiacal position)
        act_1 = f"In the {phase} phase under {sign} ({element}), {phase_desc.lower()}"

        # Act 2: The Challenge/Opportunity (from I Ching)
        if iching_name and iching_judgment:
            act_2 = f"The I Ching casts {iching_name}: {iching_judgment[:120]}"
        else:
            act_2 = "The pattern is forming — observe without forcing"

        # Act 3: The Resolution (from Ifá + Tarot)
        parts_3 = []
        if ifa_odu and ifa_wisdom:
            parts_3.append(f"Ifá reveals {ifa_odu}: {ifa_wisdom[:100]}")
        if tarot_cards:
            major = [tc for tc in tarot_cards if tc.get("suit") == "major"]
            if major:
                card_names = ", ".join(tc["name"] for tc in major[:2])
                parts_3.append(f"Tarot shows {card_names}")
        if parts_3:
            act_3 = ". ".join(parts_3)
        else:
            act_3 = "The answer will come through patience and right action"

        # Determine arc type
        if phase == "yang":
            arc_type = "inception-catalysis-resolution"
        else:
            arc_type = "preparation-work-fruition"

        return NarrativeArc(act_1=act_1, act_2=act_2, act_3=act_3, arc_type=arc_type)

    def _assess_elemental_harmony(
        self, zodiac_element: str, wu_xing: str, ifa_odu: str
    ) -> str:
        """Assess how well the elements across layers harmonize."""
        _ELEMENT_MAP = {
            "fire": "fire",
            "earth": "earth",
            "air": "metal",
            "water": "water",
        }
        zodiac_wx = _ELEMENT_MAP.get(zodiac_element, "earth")

        if zodiac_wx == wu_xing:
            return f"Harmonious — {zodiac_element} and {wu_xing} are the same element. Energy flows without resistance."

        _GENERATIVE = {
            "wood": "fire",
            "fire": "earth",
            "earth": "metal",
            "metal": "water",
            "water": "wood",
        }
        _DESTRUCTIVE = {
            "wood": "earth",
            "earth": "water",
            "water": "fire",
            "fire": "metal",
            "metal": "wood",
        }

        if _GENERATIVE.get(zodiac_wx) == wu_xing:
            return f"Generative — {zodiac_wx} feeds {wu_xing}. Creative energy builds naturally."
        elif _GENERATIVE.get(wu_xing) == zodiac_wx:
            return f"Receptive — {wu_xing} feeds {zodiac_wx}. You are being nourished by the current cycle."
        elif _DESTRUCTIVE.get(zodiac_wx) == wu_xing:
            return f"Tension — {zodiac_wx} controls {wu_xing}. Use this friction to refine, not to destroy."
        elif _DESTRUCTIVE.get(wu_xing) == zodiac_wx:
            return f"Pressure — {wu_xing} controls {zodiac_wx}. External forces are shaping you; yield productively."
        else:
            return f"Neutral — {zodiac_wx} and {wu_xing} are in indirect relationship. No strong resonance or conflict."

    def _compose_unified_message(
        self,
        sign: str,
        element: str,
        modality: str,
        phase: str,
        wu_xing: str,
        iching_name: str,
        iching_guidance: str,
        ifa_odu: str,
        ifa_wisdom: str,
        resonances: list[ResonancePattern],
        narrative: NarrativeArc,
        tarot_cards: list[dict[str, Any]] | None = None,
        great_year_context: dict[str, Any] | None = None,
    ) -> str:
        """Compose the unified message from all layers."""
        parts: list[str] = []

        # Opening: zodiacal context
        parts.append(f"Under {sign} ({element}/{modality}), in the {phase} phase:")

        # Core: I Ching + Ifá + Tarot synthesis
        if iching_name and ifa_odu:
            parts.append(
                f"The I Ching speaks of {iching_name}, while Ifá reveals {ifa_odu}."
            )
        elif iching_name:
            parts.append(f"The I Ching speaks of {iching_name}.")
        elif ifa_odu:
            parts.append(f"Ifá reveals {ifa_odu}.")

        # Tarot layer (if present)
        if tarot_cards:
            major = [tc for tc in tarot_cards if tc.get("suit") == "major"]
            if major:
                names = ", ".join(tc["name"] for tc in major[:3])
                parts.append(f"Tarot's Major Arcana shows: {names}.")

        # Great Year context (if present, non-binding)
        if great_year_context and great_year_context.get("current_age"):
            age = great_year_context["current_age"]
            parts.append(f"Context: we are in the Age of {age.title()}.")

        # Resonance summary
        strong_resonances = [r for r in resonances if r.strength >= 0.7]
        if strong_resonances:
            themes = [r.theme for r in strong_resonances]
            parts.append(f"Strong resonance detected: {', '.join(themes)}.")

        # Guidance synthesis
        if iching_guidance and ifa_wisdom:
            parts.append(f"{iching_guidance[:100]} {ifa_wisdom[:100]}")
        elif iching_guidance:
            parts.append(iching_guidance[:150])
        elif ifa_wisdom:
            parts.append(ifa_wisdom[:150])

        # Closing: elemental harmony
        alchemy = _WUXING_TO_ALCHEMY.get(wu_xing, "")
        if alchemy:
            parts.append(f"Alchemically: {alchemy}.")

        return " ".join(parts)

    def _extract_practical_guidance(
        self,
        iching_guidance: str,
        ifa_wisdom: str,
        ifa_ire: str,
        phase: str,
        resonances: list[ResonancePattern],
        tarot_cards: list[dict[str, Any]] | None = None,
    ) -> str:
        """Extract actionable guidance from the oracle layers."""
        parts: list[str] = []

        # Phase-specific base guidance
        if phase == "yang":
            parts.append("Act with creative intention")
        else:
            parts.append("Receive with reflective awareness")

        # I Ching guidance
        if iching_guidance:
            parts.append(iching_guidance[:100])

        # Ifá wisdom
        if ifa_wisdom:
            parts.append(ifa_wisdom[:100])

        # Ifá ire (blessings/path of good fortune)
        if ifa_ire:
            parts.append(f"Path of good fortune: {ifa_ire[:80]}")

        # Tarot guidance (if present)
        if tarot_cards:
            for tc in tarot_cards[:2]:
                meaning = tc.get("meaning", "")
                if meaning:
                    parts.append(f"Tarot {tc.get('name', '')}: {meaning[:60]}")

        # Strongest resonance guidance
        strongest = max(resonances, key=lambda r: r.strength) if resonances else None
        if strongest and strongest.strength >= 0.7:
            parts.append(f"Key pattern: {strongest.description[:80]}")

        return ". ".join(parts) + "."

    def _extract_cautions(
        self,
        ifa_osogbo: str,
        iching_name: str,
        resonances: list[ResonancePattern],
        tarot_cards: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Extract cautions/warnings from the oracle layers."""
        cautions: list[str] = []

        if ifa_osogbo:
            cautions.append(f"Ifá warns: {ifa_osogbo[:100]}")

        # Cautions from destructive resonances
        for r in resonances:
            if (
                "Tension" in r.description
                or "Pressure" in r.description
                or "Creative Tension" in r.description
            ):
                cautions.append(r.description[:100])

        # I Ching cautionary hexagrams
        _CAUTION_HEXAGRAMS = {
            "Difficulty",
            "Conflict",
            "Obstruction",
            "Oppression",
            "Splitting Apart",
            "Darkness",
        }
        if any(h in iching_name for h in _CAUTION_HEXAGRAMS):
            cautions.append(
                f"The hexagram {iching_name} signals a period requiring careful navigation"
            )

        # Tarot cautionary cards (reversed Major Arcana)
        if tarot_cards:
            _CAUTION_TAROT = {"The Tower", "Death", "The Devil", "The Moon"}
            for tc in tarot_cards:
                if tc.get("reversed") and tc.get("name") in _CAUTION_TAROT:
                    cautions.append(
                        f"Tarot {tc['name']} (reversed) suggests: {tc.get('reversed_meaning', '')[:80]}"
                    )

        return cautions

    def _extract_blessings(
        self,
        ifa_ire: str,
        iching_name: str,
        resonances: list[ResonancePattern],
        tarot_cards: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Extract blessings/positive signs from the oracle layers."""
        blessings: list[str] = []

        if ifa_ire:
            blessings.append(f"Ifá blesses: {ifa_ire[:100]}")

        # Blessings from generative resonances
        for r in resonances:
            if (
                "Generative" in r.description
                or "Alignment" in r.description
                or "Harmonious" in r.description
            ):
                blessings.append(r.description[:100])

        # I Ching auspicious hexagrams
        _AUSPICIOUS = {
            "Peace",
            "Progress",
            "Success",
            "Abundance",
            "Joy",
            "Fellowship",
            "Creative",
        }
        if any(h in iching_name for h in _AUSPICIOUS):
            blessings.append(
                f"The hexagram {iching_name} promises favorable conditions"
            )

        # Tarot auspicious cards (upright Major Arcana)
        if tarot_cards:
            _AUSPICIOUS_TAROT = {
                "The Sun",
                "The Star",
                "The World",
                "The Magician",
                "Temperance",
            }
            for tc in tarot_cards:
                if not tc.get("reversed") and tc.get("name") in _AUSPICIOUS_TAROT:
                    blessings.append(
                        f"Tarot {tc['name']} (upright) promises: {tc.get('upright_meaning', '')[:80]}"
                    )

        return blessings


_synthesizer: OracleSynthesizer | None = None


def get_synthesizer() -> OracleSynthesizer:
    """Get the singleton OracleSynthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = OracleSynthesizer()
    return _synthesizer


def synthesize_oracle(oracle_output: dict[str, Any]) -> SynthesisResult:
    """Synthesize oracle output into unified wisdom. Convenience function."""
    return get_synthesizer().synthesize(oracle_output)
