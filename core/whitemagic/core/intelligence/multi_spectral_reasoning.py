# ruff: noqa: BLE001
"""Multi-Spectral Reasoning Engine - Unified Wisdom System.

Philosophy:
-----------
Like biological organisms, intelligent reasoning requires multiple perspectives:
- I Ching: What is CHANGING? (64 archetypal transformations)
- Wu Xing: What needs BALANCE? (5 elemental cycles)
- Art of War: What is the STRATEGY? (timing, positioning, resources)
- Zodiac: What is the PHASE? (12 specialized modes of consciousness)
- Sequential-Thinking: How do I REASON through this? (structured multi-step)

Together, these form a "Multi-Spectral Scientific Method":
1. Observe from multiple lenses (multi-spectral)
2. Detect patterns from memory (biological learning)
3. Reason step-by-step (scientific method)
4. Synthesize into coherent decision (integration)
"""

from __future__ import annotations

import importlib
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class ReasoningLens(Enum):
    """Available reasoning lenses."""

    I_CHING = "i_ching"
    WU_XING = "wu_xing"
    ART_OF_WAR = "art_of_war"
    ZODIAC = "zodiac"
    SEQUENTIAL = "sequential"
    ALL = "all"

@dataclass
class ReasoningContext:
    """Context for reasoning operation."""

    question: str
    task_type: str = "analysis"
    urgency: str = "normal"
    complexity: str = "medium"
    stakes: str = "medium"
    available_resources: dict[str, bool] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    past_patterns: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class LensPerspective:
    """Perspective from a single reasoning lens."""

    lens: ReasoningLens
    analysis: str
    confidence: float
    guidance: str
    details: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ReasoningThought:
    """Single thought in sequential reasoning chain."""

    number: int
    content: str
    lens_used: ReasoningLens | None = None
    revises: int | None = None
    branch_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ReasoningResult:
    """Final result of multi-spectral reasoning."""

    question: str
    perspectives: list[LensPerspective]
    thoughts: list[ReasoningThought]
    synthesis: str
    recommendation: str
    confidence: float
    reasoning_chain: list[str]
    patterns_matched: list[dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)

class MultiSpectralReasoner:
    """Unified reasoning engine combining all wisdom systems."""

    def __init__(self, base_dir: Path = Path(".")) -> None:
        self.base_dir = base_dir
        self.memory_dir = self.base_dir / "memory" / "reasoning"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.i_ching: Any | None = None
        self.wu_xing: Any | None = None
        self.zodiac_cores: Any | None = None
        self.art_of_war: Callable[[str], Any] | None = None
        self.holographic: Any | None = None
        self.unified_memory: Any | None = None
        self.reasoning_history: list[ReasoningResult] = []
        self.bus: Any | None = None

        self._init_systems()
        # Only print if not silent to avoid CLI spam
        import os
        if not os.getenv("WM_SILENT_INIT"):
            logger.info("🌈 Multi-Spectral Reasoning Engine initialized (Materialized Core)")

    def _init_systems(self) -> None:
        """Initialize all wisdom systems."""
        try:
            from whitemagic.gardens.wisdom.i_ching import get_i_ching
            self.i_ching = get_i_ching()
        except Exception as e:
            logger.debug("I Ching system not available: %s", e, exc_info=True)

        try:
            # Use new path for Wu Xing
            from whitemagic.core.intelligence.wisdom.wu_xing import get_wu_xing
            self.wu_xing = get_wu_xing()
        except Exception as e:
            logger.debug("Wu Xing system not available: %s", e, exc_info=True)

        try:
            from whitemagic.zodiac.zodiac_cores import get_zodiac_cores
            self.zodiac_cores = get_zodiac_cores()
        except Exception as e:
            logger.debug("Zodiac cores matching not available: %s", e, exc_info=True)

        try:
            try:
                art_mod = importlib.import_module("whitemagic.core.intelligence.wisdom.art_of_war")
            except ImportError:
                art_mod = importlib.import_module("whitemagic.gardens.wisdom.art_of_war")
            get_war_wisdom = getattr(art_mod, "get_war_wisdom", None)
            if callable(get_war_wisdom):
                self.art_of_war = get_war_wisdom
        except Exception as e:
            logger.debug("Art of War wisdom not available: %s", e, exc_info=True)

        try:
            from whitemagic.core.resonance._consolidated import get_bus
            self.bus = get_bus()
        except Exception as e:
            logger.debug("Gan Ying resonance bus not available: %s", e, exc_info=True)

        try:
            from whitemagic.core.memory.holographic import get_holographic_memory
            from whitemagic.core.memory.unified import get_unified_memory
            self.holographic = get_holographic_memory()
            self.unified_memory = get_unified_memory()
        except Exception as e:
            logger.debug("Memory systems not available: %s", e, exc_info=True)

    def reason(self, question: str, lenses: Sequence[ReasoningLens] | None = None,
               context: ReasoningContext | None = None,
               use_sequential_thinking: bool = True) -> ReasoningResult:
        """Main reasoning entry point."""
        if context is None:
            context = ReasoningContext(question=question)

        lenses_list = [ReasoningLens.I_CHING, ReasoningLens.WU_XING,
                       ReasoningLens.ART_OF_WAR, ReasoningLens.ZODIAC] if not lenses or ReasoningLens.ALL in lenses else list(lenses)

        perspectives: list[LensPerspective] = []
        thoughts: list[ReasoningThought] = []

        # 1. I Ching Lens
        if ReasoningLens.I_CHING in lenses_list and self.i_ching:
            try:
                hexagram = self.i_ching.cast_hexagram(question)
                perspectives.append(LensPerspective(
                    lens=ReasoningLens.I_CHING,
                    analysis=hexagram.judgment,
                    confidence=0.9,
                    guidance=hexagram.guidance,
                    details={"hexagram": hexagram.number, "name": hexagram.name, "image": hexagram.image},
                ))
            except Exception as e:
                logger.info("⚠️ I Ching reasoning failed: %s", e, exc_info=True)

        # 2. Wu Xing Lens
        if ReasoningLens.WU_XING in lenses_list and self.wu_xing:
            try:
                element = self.wu_xing.identify_element(context.task_type)
                suggestion = self.wu_xing.suggest_optimization(element)
                perspectives.append(LensPerspective(
                    lens=ReasoningLens.WU_XING,
                    analysis=f"Current phase is {element.value}",
                    confidence=0.85,
                    guidance=suggestion,
                    details={"element": element.value},
                ))
            except Exception as e:
                logger.info("⚠️ Wu Xing reasoning failed: %s", e, exc_info=True)

        # 3. Art of War Lens
        if ReasoningLens.ART_OF_WAR in lenses_list and self.art_of_war:
            try:
                # self.art_of_war is the function get_war_wisdom directly
                wisdom = self.art_of_war(context.task_type)
                perspectives.append(LensPerspective(
                    lens=ReasoningLens.ART_OF_WAR,
                    analysis=wisdom.principle,
                    confidence=0.8,
                    guidance=wisdom.application,
                    details={"chapter": wisdom.chapter},
                ))
            except Exception as e:
                logger.info("⚠️ Art of War reasoning failed: %s", e, exc_info=True)

        # 4. Zodiac Lens
        if ReasoningLens.ZODIAC in lenses_list and self.zodiac_cores:
            try:
                ctx = {
                    "operation": context.task_type,
                    "intention": context.question[:50],
                    "urgency": context.urgency,
                }
                all_cores = self.zodiac_cores.get_all_cores()
                best_core = max(all_cores.values(), key=lambda c: c.can_handle(ctx)) if all_cores else None
                if best_core and best_core.can_handle(ctx) > 0.4:
                    resp = best_core.activate(ctx)
                    perspectives.append(LensPerspective(
                        lens=ReasoningLens.ZODIAC,
                        analysis=f"Zodiac core {best_core.name} resonates ({best_core.element}/{best_core.mode})",
                        confidence=0.75,
                        guidance=resp.wisdom,
                        details={"core": best_core.name, "element": best_core.element,
                                 "mode": best_core.mode, "resonance": resp.resonance},
                    ))
            except Exception as e:
                logger.info("\u26a0\ufe0f Zodiac reasoning failed: %s", e, exc_info=True)

        # 5. Pattern Matching (Memory Lens)
        patterns_matched = self._match_patterns(context, perspectives)

        # 5b. Sequential Thinking (v23.2: structured multi-step reasoning)
        if use_sequential_thinking:
            thoughts = self._sequential_think(question, context, perspectives, patterns_matched)

        # 5. Synthesis
        synthesis = self._synthesize_perspectives(perspectives, patterns_matched)
        recommendation = self._generate_recommendation(context, perspectives, synthesis, patterns_matched)
        confidence = self._calculate_confidence(perspectives, patterns_matched)

        result = ReasoningResult(
            question=question,
            perspectives=perspectives,
            thoughts=thoughts,
            synthesis=synthesis,
            recommendation=recommendation,
            confidence=confidence,
            reasoning_chain=[t.content for t in thoughts],
            patterns_matched=patterns_matched,
        )

        self.reasoning_history.append(result)

        # Emit reasoning result to bus
        if self.bus:
            try:
                from whitemagic.core.resonance._consolidated import EventType, ResonanceEvent
                self.bus.emit(ResonanceEvent(
                    source="multi_spectral_reasoner",
                    event_type=EventType.WISDOM_INTEGRATED,
                    data={
                        "question": question,
                        "synthesis": synthesis,
                        "recommendation": recommendation,
                        "lens_count": len(perspectives),
                    },
                    timestamp=datetime.now(),
                    confidence=confidence,
                ))
            except Exception as e:
                logger.warning("Failed to emit reasoning event: %s", e, exc_info=True)

        return result

    def _sequential_think(
        self,
        question: str,
        context: ReasoningContext,
        perspectives: list[LensPerspective],
        patterns: list[dict[str, Any]],
    ) -> list[ReasoningThought]:
        """Build a structured sequential reasoning chain.

        Produces a series of ReasoningThought objects that walk through:
        1. Observation — what is the question and context?
        2. Multi-lens analysis — what do the perspectives say?
        3. Pattern matching — what does past experience suggest?
        4. Synthesis — how do the perspectives converge or conflict?
        5. Conclusion — what is the recommended action?
        """
        thoughts: list[ReasoningThought] = []
        step = 1

        # Thought 1: Observation
        thoughts.append(ReasoningThought(
            number=step,
            content=(
                f"Observing: '{question[:120]}' — "
                f"task_type={context.task_type}, urgency={context.urgency}, "
                f"complexity={context.complexity}, stakes={context.stakes}"
            ),
            lens_used=None,
        ))
        step += 1

        # Thought 2: Multi-lens analysis
        if perspectives:
            lens_summaries = []
            for p in perspectives:
                lens_name = p.lens.value.replace("_", " ").title()
                lens_summaries.append(
                    f"{lens_name} (conf={p.confidence:.2f}): {p.guidance[:80]}"
                )
            thoughts.append(ReasoningThought(
                number=step,
                content=(
                    f"Multi-lens analysis ({len(perspectives)} perspectives):\n"
                    + "\n".join(lens_summaries)
                ),
                lens_used=perspectives[0].lens if perspectives else None,
            ))
            step += 1

            # Thought 3: Consensus/tension detection
            consensus = self._detect_consensus(perspectives)
            if consensus["strong"]:
                thoughts.append(ReasoningThought(
                    number=step,
                    content=(
                        f"Consensus detected across: {', '.join(consensus['strong'])}. "
                        f"Multiple lenses converge — higher confidence warranted."
                    ),
                    lens_used=None,
                ))
                step += 1
            if consensus["tension"]:
                thoughts.append(ReasoningThought(
                    number=step,
                    content=(
                        f"Creative tension between: {', '.join(consensus['tension'])}. "
                        f"Conflicting signals — consider both angles before deciding."
                    ),
                    lens_used=None,
                ))
                step += 1

        # Thought 4: Pattern matching
        if patterns:
            pat_summaries = []
            for pat in patterns[:2]:
                pat_summaries.append(
                    f"Past: '{pat['past_question'][:60]}' (sim={pat['similarity']:.2f}) → {pat['outcome'][:60]}"
                )
            thoughts.append(ReasoningThought(
                number=step,
                content=(
                    f"Pattern resonance: {len(patterns)} similar past situations.\n"
                    + "\n".join(pat_summaries)
                ),
                lens_used=None,
            ))
            step += 1
        elif not perspectives:
            thoughts.append(ReasoningThought(
                number=step,
                content=(
                    "No wisdom perspectives or pattern matches available. "
                    "Falling back to objective analysis with default confidence (0.5)."
                ),
                lens_used=None,
            ))
            step += 1

        # Thought 5: Themes
        if perspectives:
            themes = self._extract_themes(perspectives)
            if themes:
                top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
                theme_str = ", ".join(f"{t} ({w:.1f})" for t, w in top_themes)
                thoughts.append(ReasoningThought(
                    number=step,
                    content=f"Dominant themes identified: {theme_str}",
                    lens_used=None,
                ))
                step += 1

        # Thought 6: Conclusion
        if perspectives:
            top_p = max(perspectives, key=lambda p: p.confidence)
            lens_name = top_p.lens.value.replace("_", " ").title()
            thoughts.append(ReasoningThought(
                number=step,
                content=(
                    f"Conclusion: {len(perspectives)} lenses examined. "
                    f"Leading guidance from {lens_name}. "
                    f"Recommended action: proceed with {top_p.guidance[:80]}"
                ),
                lens_used=top_p.lens,
            ))
        else:
            thoughts.append(ReasoningThought(
                number=step,
                content=(
                    "Conclusion: No lens perspectives available. "
                    "Recommend proceeding with standard operating procedures."
                ),
                lens_used=None,
            ))

        return thoughts

    def _calculate_similarity(self, q1: str, q2: str) -> float:
        """Calculate semantic similarity using Rust acceleration (Materialized)."""
        try:
            from whitemagic.core.memory.neural.rust_bridge import fast_similarity
            return float(fast_similarity(q1, q2))
        except (ImportError, Exception):
            # Fallback to keyword overlap
            words1, words2 = set(q1.lower().split()), set(q2.lower().split())
            if not words1 or not words2:
                return 0.0
            overlap = len(words1 & words2)
            total = len(words1 | words2)
            return overlap / total if total > 0 else 0.0

    def _match_patterns(self, context: ReasoningContext, perspectives: list[LensPerspective]) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        for past in self.reasoning_history[-50:]:  # Check last 50
            similarity = self._calculate_similarity(context.question, past.question)
            if similarity > 0.6:
                patterns.append({
                    "past_question": past.question,
                    "similarity": similarity,
                    "lessons": past.synthesis[:100],
                    "outcome": past.recommendation,
                })
        return sorted(patterns, key=lambda x: float(x["similarity"]), reverse=True)[:3]

    def _synthesize_perspectives(self, perspectives: list[LensPerspective], patterns: list[dict[str, Any]]) -> str:
        """Synthesize multiple lens perspectives into a coherent analysis.

        v23.1: Real cross-lens synthesis with consensus detection, conflict
        resolution, and weighted integration. Replaces trivial string joining.
        """
        if not perspectives:
            return "No wisdom perspectives available. Relying on objective analysis."

        # Detect consensus: do multiple lenses point in the same direction?
        consensus_clusters = self._detect_consensus(perspectives)

        synthesis_parts = [f"Multi-Spectral Analysis: {len(perspectives)} lenses examined."]

        # Report consensus clusters
        if consensus_clusters["strong"]:
            lens_names = ", ".join(consensus_clusters["strong"])
            synthesis_parts.append(f"Strong consensus detected across: {lens_names}.")

        if consensus_clusters["tension"]:
            lens_names = ", ".join(consensus_clusters["tension"])
            synthesis_parts.append(f"Creative tension between: {lens_names} — explore both angles.")

        # Weighted perspective summaries (sorted by confidence)
        sorted_perspectives = sorted(perspectives, key=lambda p: p.confidence, reverse=True)
        for p in sorted_perspectives:
            lens_name = p.lens.value.replace('_', ' ').title()
            synthesis_parts.append(f"{lens_name} (confidence={p.confidence:.2f}): {p.guidance}")

        # Integrate pattern matches
        if patterns:
            synthesis_parts.append(f"Pattern resonance: {len(patterns)} similar past situations found.")
            for pat in patterns[:2]:
                synthesis_parts.append(f"  Past: {pat['past_question'][:80]} → {pat['outcome'][:80]}")

        # Cross-lens insight: identify complementary themes
        themes = self._extract_themes(perspectives)
        if themes:
            top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
            theme_str = ", ".join(f"{t} ({w:.1f})" for t, w in top_themes)
            synthesis_parts.append(f"Dominant themes: {theme_str}")

        return "\n".join(synthesis_parts)

    def _generate_recommendation(self, context: ReasoningContext, perspectives: list[LensPerspective],
                                 synthesis: str, patterns: list[dict[str, Any]]) -> str:
        """Generate actionable recommendation from synthesized perspectives.

        v23.1: Context-aware recommendation engine that weights lenses by
        relevance to the situation, integrates pattern matches, and produces
        structured guidance instead of simple priority selection.
        """
        if not perspectives:
            return "Proceed with standard operating procedures."

        # Weight lenses by context relevance
        lens_weights = self._compute_lens_weights(context, perspectives)

        # Score each perspective by confidence * context_weight
        scored = [
            (p, p.confidence * lens_weights.get(p.lens, 0.5))
            for p in perspectives
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Build recommendation from top perspectives
        rec_parts = []
        top_p, top_score = scored[0]
        lens_name = top_p.lens.value.replace('_', ' ').title()
        rec_parts.append(f"Primary guidance ({lens_name}, score={top_score:.2f}): {top_p.guidance}")

        # Add secondary perspective if it adds new information
        if len(scored) > 1:
            second_p, second_score = scored[1]
            if second_score > top_score * 0.5:  # Meaningful contribution
                lens_name2 = second_p.lens.value.replace('_', ' ').title()
                rec_parts.append(f"Supporting angle ({lens_name2}): {second_p.guidance}")

        # Integrate pattern-based advice
        if patterns:
            best_pattern = patterns[0]
            rec_parts.append(f"Past precedent (similarity={best_pattern['similarity']:.2f}): {best_pattern['outcome'][:100]}")

        # Context-specific override for high stakes
        if context.stakes == "high":
            for p, _ in scored:
                if p.lens == ReasoningLens.ART_OF_WAR:
                    rec_parts.insert(0, f"⚠ High stakes — Strategic priority: {p.guidance}")
                    break

        return "\n".join(rec_parts)

    def _calculate_confidence(self, perspectives: list[LensPerspective], patterns: list[dict[str, Any]]) -> float:
        """Calculate overall confidence from perspective agreement and pattern support."""
        if not perspectives:
            return 0.5

        # Base: average confidence across lenses
        base_conf = sum(p.confidence for p in perspectives) / len(perspectives)

        # Consensus boost: multiple lenses agreeing increases confidence
        consensus = self._detect_consensus(perspectives)
        if consensus["strong"]:
            base_conf += 0.08 * len(consensus["strong"])

        # Pattern match boost
        if patterns:
            base_conf += 0.05 * len(patterns)

        # Tension penalty: conflicting lenses reduce confidence
        if consensus["tension"]:
            base_conf -= 0.05 * len(consensus["tension"])

        return max(0.1, min(1.0, base_conf))

    def _detect_consensus(self, perspectives: list[LensPerspective]) -> dict[str, list[str]]:
        """Detect consensus and tension between lens perspectives.

        Uses keyword overlap between guidance texts to determine if lenses
        are pointing in the same direction (consensus) or offering
        contradictory advice (tension).
        """
        if len(perspectives) < 2:
            return {"strong": [], "tension": []}

        # Extract keyword sets from each perspective's guidance
        keyword_sets = []
        for p in perspectives:
            words = set(p.guidance.lower().split())
            # Filter common words
            words -= {"the", "a", "an", "is", "to", "and", "or", "in", "for", "of", "with", "it", "this", "that"}
            keyword_sets.append((p.lens.value, words))

        strong_pairs: list[str] = []
        tension_pairs: list[str] = []

        for i, (lens_a, words_a) in enumerate(keyword_sets):
            for j, (lens_b, words_b) in enumerate(keyword_sets[i+1:], i+1):
                overlap = len(words_a & words_b)
                union = len(words_a | words_b)
                jaccard = overlap / union if union > 0 else 0

                pair_label = f"{lens_a}↔{lens_b}"
                if jaccard > 0.25:
                    strong_pairs.append(pair_label)
                elif jaccard < 0.05 and len(words_a) > 3 and len(words_b) > 3:
                    tension_pairs.append(pair_label)

        return {"strong": strong_pairs, "tension": tension_pairs}

    def _extract_themes(self, perspectives: list[LensPerspective]) -> dict[str, float]:
        """Extract dominant themes from perspective guidance texts."""
        theme_keywords = {
            "action": ["act", "execute", "do", "implement", "move", "strike", "advance"],
            "caution": ["wait", "observe", "careful", "slow", "patience", "defend", "protect"],
            "transformation": ["change", "transform", "shift", "evolve", "transition", "become"],
            "balance": ["balance", "harmony", "align", "stabilize", "center", "equilibrium"],
            "strategy": ["plan", "strategy", "position", "timing", "resource", "advantage"],
            "intuition": ["feel", "sense", "intuit", "know", "wisdom", "insight", "pattern"],
        }

        theme_scores: dict[str, float] = defaultdict(float)
        for p in perspectives:
            text = (p.guidance + " " + p.analysis).lower()
            for theme, keywords in theme_keywords.items():
                matches = sum(1 for kw in keywords if kw in text)
                if matches > 0:
                    theme_scores[theme] += matches * p.confidence

        return dict(theme_scores)

    def _compute_lens_weights(self, context: ReasoningContext, perspectives: list[LensPerspective]) -> dict[ReasoningLens, float]:
        """Compute context-aware weights for each lens."""
        weights: dict[ReasoningLens, float] = {}

        for p in perspectives:
            w = 0.5  # Base weight

            # Art of War weighted higher for high stakes and strategic tasks
            if p.lens == ReasoningLens.ART_OF_WAR:
                if context.stakes == "high":
                    w = 0.9
                elif context.task_type in ("strategy", "planning", "competition"):
                    w = 0.8

            # Wu Xing weighted higher for complex, multi-faceted tasks
            elif p.lens == ReasoningLens.WU_XING:
                if context.complexity == "high":
                    w = 0.8
                elif context.task_type in ("balance", "optimization", "tuning"):
                    w = 0.85

            # I Ching weighted higher for transformation/decision questions
            elif p.lens == ReasoningLens.I_CHING:
                if context.task_type in ("decision", "transformation", "change"):
                    w = 0.85
                elif context.urgency == "low":
                    w = 0.7  # Good for contemplative analysis

            # Zodiac weighted higher for phase-related work
            elif p.lens == ReasoningLens.ZODIAC:
                if context.task_type in ("coordination", "timing", "phase"):
                    w = 0.8

            weights[p.lens] = w

        return weights

_reasoner: MultiSpectralReasoner | None = None


def get_reasoner() -> MultiSpectralReasoner:
    """
    Get the reasoner.

    Returns:
        MultiSpectralReasoner
    """
    global _reasoner
    if _reasoner is None:
        _reasoner = MultiSpectralReasoner()
    return _reasoner
