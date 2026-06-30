"""12-step zodiacal procession definitions for the alchemical loop.

Each step carries all cross-system attributes: zodiac sign, Enochian name,
alchemical operation, Ripley's gate, color stage, Wu Xing phase, and
the action description for both yang and yin phases.

The 12 yin steps (Pisces -> Aries) and 12 yang steps (Aries -> Pisces)
form the complete 24-step dual toroidal cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProcessionStep:
    """A single step in the 12-step zodiacal procession.

    Carries all cross-system attributes for unified operation.
    """

    step_number: int          # 1-12 within the phase
    sign: str                 # Zodiac sign name
    symbol: str               # Zodiac symbol
    enochian: str             # Enochian Name of God
    enochian_meaning: str     # Meaning of the Name
    operation: str            # Alchemical operation name
    ripley_gate: str          # Ripley's twelve gates mapping
    color_stage: str          # Alchemical color stage
    wu_xing: str              # Wu Xing element
    modality: str             # Cardinal/Fixed/Mutable
    is_fixed: bool            # Fixed sign checkpoint?
    is_checkpoint: bool       # Should this step gate progression?

    # Action descriptions
    yang_action: str          # What happens in yang (creative) phase
    yin_action: str           # What happens in yin (receptive) phase

    # Tool selection hints
    yang_tool: str = ""       # Primary tool for yang phase
    yin_tool: str = ""        # Primary tool for yin phase


# ---------------------------------------------------------------------------
# The 12-Step Yin Procession (Pisces -> Aries, precessional order)
# ---------------------------------------------------------------------------

YIN_PROCESSION: list[ProcessionStep] = [
    ProcessionStep(
        step_number=1, sign="pisces", symbol="\u2653", enochian="ORO",
        enochian_meaning="Let the old forms be banished. I begin anew.",
        operation="Dissolution", ripley_gate="Calcination",
        color_stage="Nigredo", wu_xing="water", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Release: let go of completed work, clear the field",
        yin_action="Dissolve: break down output into components for analysis",
        yang_tool="internal", yin_tool="strata.analyze",
    ),
    ProcessionStep(
        step_number=2, sign="aquarius", symbol="\u2652", enochian="IBAH",
        enochian_meaning="I bind my will in patterns, ordered, cyclic, yet never the same.",
        operation="Binding", ripley_gate="Dissolution",
        color_stage="Nigredo", wu_xing="metal", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Pattern: establish structural patterns for the work",
        yin_action="Bind: identify patterns and anti-patterns in output",
        yang_tool="internal", yin_tool="autoimmune",
    ),
    ProcessionStep(
        step_number=3, sign="capricorn", symbol="\u2651", enochian="AOZPI",
        enochian_meaning="The towers of My Will arise upon the base. Level upon level.",
        operation="Foundation", ripley_gate="Separation",
        color_stage="Nigredo->Cauda Pavonis", wu_xing="earth", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Build: construct the foundation layer by layer",
        yin_action="Separate: filter results, discard impurities",
        yang_tool="internal", yin_tool="hybrid_recall",
    ),
    ProcessionStep(
        step_number=4, sign="sagittarius", symbol="\u2650", enochian="MPH",
        enochian_meaning="Fabulous filigrees, always similar, never identical, scale is lost.",
        operation="Elaboration", ripley_gate="Conjunction",
        color_stage="Cauda Pavonis", wu_xing="wood", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Elaborate: add complexity, explore fractal detail",
        yin_action="Conjoin: cross-reference with associative memories",
        yang_tool="rabbit_hole_research", yin_tool="association.mine",
    ),
    ProcessionStep(
        step_number=5, sign="scorpio", symbol="\u264f", enochian="ARSL",
        enochian_meaning="From the blending of the scales does chance arise, seeds of new motions.",
        operation="Emergence", ripley_gate="Putrefaction",
        color_stage="Cauda Pavonis->Albedo", wu_xing="water", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Emerge: allow novel solutions to surface spontaneously",
        yin_action="Putrefy: destroy old assumptions, let new insights emerge",
        yang_tool="parallel_reason", yin_tool="association.mine",
    ),
    ProcessionStep(
        step_number=6, sign="libra", symbol="\u264e", enochian="GAIOL",
        enochian_meaning="My towers are one, balanced in the light and in the darkness.",
        operation="Balancing", ripley_gate="Congelation",
        color_stage="Albedo", wu_xing="metal", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Balance: harmonize competing approaches",
        yin_action="Congeal: crystallize insights into stable form",
        yang_tool="internal", yin_tool="monte_carlo",
    ),
    ProcessionStep(
        step_number=7, sign="virgo", symbol="\u264d", enochian="OIP",
        enochian_meaning="Virgin houses, let the seeds of life be sown.",
        operation="Seeding", ripley_gate="Cibation",
        color_stage="Albedo", wu_xing="earth", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Seed: plant the refined approach for generation",
        yin_action="Nourish: feed insights back into the system",
        yang_tool="internal", yin_tool="autonomous_learner",
    ),
    ProcessionStep(
        step_number=8, sign="leo", symbol="\u264c", enochian="TEAA",
        enochian_meaning="Let the lesser creators dwell within my towers, revealing unseen potential.",
        operation="Expression", ripley_gate="Sublimation",
        color_stage="Albedo->Citrinitas", wu_xing="fire", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Express: radiate creative output, generate code",
        yin_action="Sublimate: refine quality, validate output",
        yang_tool="codegenome.generate", yin_tool="ensemble.query",
    ),
    ProcessionStep(
        step_number=9, sign="cancer", symbol="\u264b", enochian="PDOCE",
        enochian_meaning="Let the living creatures worship the creators, lesser builders work.",
        operation="Manifestation", ripley_gate="Fermentation",
        color_stage="Citrinitas", wu_xing="water", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Manifest: bring the work into material form",
        yin_action="Ferment: let lessons incubate and mature",
        yang_tool="codegenome_validate", yin_tool="autonomous_learner",
    ),
    ProcessionStep(
        step_number=10, sign="gemini", symbol="\u264a", enochian="MOR",
        enochian_meaning="Let the thoughts of men blend with My thoughts.",
        operation="Synthesis", ripley_gate="Exaltation",
        color_stage="Citrinitas", wu_xing="metal", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Synthesize: blend multiple approaches into one",
        yin_action="Exalt: raise insights to higher abstraction",
        yang_tool="parallel_reason", yin_tool="internal",
    ),
    ProcessionStep(
        step_number=11, sign="taurus", symbol="\u2649", enochian="DIAL",
        enochian_meaning="Let their work build upon My pattern, reflecting My evolving Will.",
        operation="Grounding", ripley_gate="Multiplication",
        color_stage="Citrinitas->Rubedo", wu_xing="earth", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Ground: materialize the pattern into solid form",
        yin_action="Multiply: consolidate learnings, amplify success",
        yang_tool="internal", yin_tool="memory.consolidate",
    ),
    ProcessionStep(
        step_number=12, sign="aries", symbol="\u2648", enochian="HCTGA",
        enochian_meaning="Let men work until matter and My Will are one. Thy Will is done.",
        operation="Completion", ripley_gate="Projection",
        color_stage="Rubedo", wu_xing="fire", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Complete: project the Stone, finalize the work",
        yin_action="Project: consolidate and prepare for next cycle",
        yang_tool="codegenome_validate", yin_tool="memory.consolidate",
    ),
]


# ---------------------------------------------------------------------------
# The 12-Step Yang Procession (Aries -> Pisces, forward zodiacal order)
# ---------------------------------------------------------------------------

YANG_PROCESSION: list[ProcessionStep] = [
    ProcessionStep(
        step_number=1, sign="aries", symbol="\u2648", enochian="HCTGA",
        enochian_meaning="Thy Will is done. Matter and Will are one.",
        operation="Ignition", ripley_gate="Projection",
        color_stage="Rubedo", wu_xing="fire", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Ignite: break down task into core components with will",
        yin_action="Complete: finalize analysis, prepare synthesis",
        yang_tool="internal", yin_tool="memory.consolidate",
    ),
    ProcessionStep(
        step_number=2, sign="taurus", symbol="\u2649", enochian="DIAL",
        enochian_meaning="Work builds upon My pattern, reflecting My evolving Will.",
        operation="Materialization", ripley_gate="Multiplication",
        color_stage="Rubedo", wu_xing="earth", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Materialize: establish material foundation",
        yin_action="Ground: verify structural integrity",
        yang_tool="internal", yin_tool="strata.survey",
    ),
    ProcessionStep(
        step_number=3, sign="gemini", symbol="\u264a", enochian="MOR",
        enochian_meaning="Let the thoughts of men blend with My thoughts.",
        operation="Proliferation", ripley_gate="Exaltation",
        color_stage="Citrinitas", wu_xing="metal", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Proliferate: generate multiple approaches",
        yin_action="Synthesize: blend perspectives",
        yang_tool="parallel_reason", yin_tool="internal",
    ),
    ProcessionStep(
        step_number=4, sign="cancer", symbol="\u264b", enochian="PDOCE",
        enochian_meaning="Living creatures worship the creators, lesser builders work.",
        operation="Incubation", ripley_gate="Fermentation",
        color_stage="Citrinitas", wu_xing="water", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Incubate: nurture approaches, let them develop",
        yin_action="Manifest: bring analysis into concrete form",
        yang_tool="internal", yin_tool="autonomous_learner",
    ),
    ProcessionStep(
        step_number=5, sign="leo", symbol="\u264c", enochian="TEAA",
        enochian_meaning="Lesser creators dwell within my towers, revealing unseen potential.",
        operation="Illumination", ripley_gate="Sublimation",
        color_stage="Citrinitas", wu_xing="fire", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Illuminate: radiate creative output at peak intensity",
        yin_action="Express: validate output quality",
        yang_tool="codegenome.generate", yin_tool="ensemble.query",
    ),
    ProcessionStep(
        step_number=6, sign="virgo", symbol="\u264d", enochian="OIP",
        enochian_meaning="Virgin houses, let the seeds of life be sown.",
        operation="Refinement", ripley_gate="Cibation",
        color_stage="Albedo", wu_xing="earth", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Refine: select and purify the best approach",
        yin_action="Seed: plant insights for future growth",
        yang_tool="hybrid_recall", yin_tool="autonomous_learner",
    ),
    ProcessionStep(
        step_number=7, sign="libra", symbol="\u264e", enochian="GAIOL",
        enochian_meaning="My towers are one, balanced in the light and in the darkness.",
        operation="Harmonization", ripley_gate="Congelation",
        color_stage="Albedo", wu_xing="metal", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Harmonize: balance creative tensions",
        yin_action="Balance: equilibrate analysis results",
        yang_tool="internal", yin_tool="monte_carlo",
    ),
    ProcessionStep(
        step_number=8, sign="scorpio", symbol="\u264f", enochian="ARSL",
        enochian_meaning="From the blending of the scales does chance arise.",
        operation="Transformation", ripley_gate="Putrefaction",
        color_stage="Cauda Pavonis", wu_xing="water", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Transform: destroy old structures, create anew",
        yin_action="Emerge: allow novel insights to surface",
        yang_tool="parallel_reason", yin_tool="association.mine",
    ),
    ProcessionStep(
        step_number=9, sign="sagittarius", symbol="\u2650", enochian="MPH",
        enochian_meaning="Fabulous filigrees, scale is lost.",
        operation="Expansion", ripley_gate="Conjunction",
        color_stage="Cauda Pavonis", wu_xing="wood", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Expand: elaborate with fractal complexity",
        yin_action="Conjoin: combine findings",
        yang_tool="rabbit_hole_research", yin_tool="association.mine",
    ),
    ProcessionStep(
        step_number=10, sign="capricorn", symbol="\u2651", enochian="AOZPI",
        enochian_meaning="The towers of My Will arise upon the base.",
        operation="Crystallization", ripley_gate="Separation",
        color_stage="Nigredo", wu_xing="earth", modality="cardinal",
        is_fixed=False, is_checkpoint=False,
        yang_action="Crystallize: fix the structure into final form",
        yin_action="Separate: filter and refine",
        yang_tool="internal", yin_tool="hybrid_recall",
    ),
    ProcessionStep(
        step_number=11, sign="aquarius", symbol="\u2652", enochian="IBAH",
        enochian_meaning="I bind my will in patterns, ordered, cyclic, yet never the same.",
        operation="Patterning", ripley_gate="Dissolution",
        color_stage="Nigredo", wu_xing="metal", modality="fixed",
        is_fixed=True, is_checkpoint=True,
        yang_action="Pattern: establish evolving patterns for next cycle",
        yin_action="Bind: identify anti-patterns to avoid",
        yang_tool="internal", yin_tool="autoimmune",
    ),
    ProcessionStep(
        step_number=12, sign="pisces", symbol="\u2653", enochian="ORO",
        enochian_meaning="Let the old forms be banished. I begin anew.",
        operation="Release", ripley_gate="Calcination",
        color_stage="Nigredo", wu_xing="water", modality="mutable",
        is_fixed=False, is_checkpoint=False,
        yang_action="Release: let go, prepare for yin phase",
        yin_action="Dissolve: break down for deep analysis",
        yang_tool="internal", yin_tool="strata.analyze",
    ),
]


# Index by sign name for quick lookup
YIN_BY_SIGN: dict[str, ProcessionStep] = {s.sign: s for s in YIN_PROCESSION}
YANG_BY_SIGN: dict[str, ProcessionStep] = {s.sign: s for s in YANG_PROCESSION}


# Fixed sign checkpoints (appear in both processions)
FIXED_CHECKPOINTS: list[str] = ["taurus", "leo", "scorpio", "aquarius"]


def get_checkpoint_description(sign: str) -> str:
    """Get the checkpoint description for a fixed sign."""
    _descriptions = {
        "taurus": "Grounding: Is the material foundation solid? If not, loop back and rebuild.",
        "leo": "Expression: Is the creative output adequate? If not, loop back and generate more.",
        "scorpio": "Emergence: Has novelty emerged from analysis? If not, loop back and dig deeper.",
        "aquarius": "Innovation: Has the pattern evolved? If not, loop back and innovate.",
    }
    return _descriptions.get(sign, "")


# Color stage boundaries for cycle tracking
COLOR_STAGES = ["Nigredo", "Cauda Pavonis", "Albedo", "Citrinitas", "Rubedo"]


def get_color_stage_for_step(step: int, phase: str) -> str:
    """Get the alchemical color stage for a given step number and phase.

    Args:
        step: 1-12
        phase: "yin" or "yang"
    """
    if phase == "yin":
        if step <= 2:
            return "Nigredo"
        elif step <= 4:
            return "Cauda Pavonis"
        elif step <= 7:
            return "Albedo"
        elif step <= 10:
            return "Citrinitas"
        else:
            return "Rubedo"
    else:  # yang
        if step <= 2:
            return "Rubedo"
        elif step <= 5:
            return "Citrinitas"
        elif step <= 7:
            return "Albedo"
        elif step <= 9:
            return "Cauda Pavonis"
        else:
            return "Nigredo"
