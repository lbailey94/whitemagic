# ruff: noqa: BLE001
"""Bicameral Reasoning - Dual-Hemisphere Processing with Cross-Critique.
====================================================================
Inspired by CyberBrains' bicameral mind architecture and Jaynes' theory:

  Left Hemisphere:  Sequential, symbolic, causal, low-temperature.
                    Aims for precision, logical consistency, fewer hallucinations.

  Right Hemisphere: Holistic, pattern-matching, stochastic, high-temperature.
                    Aims for creativity, novel connections, anomaly detection.

  Corpus Callosum:  High-bandwidth message bus connecting both hemispheres.
                    Left queries Right for intuition; Right queries Left for
                    logic checks. Neither hemisphere dominates — creativity
                    emerges from the *tension* between precision and freedom.

This module extends the existing ThoughtClone / MultiSpectral infrastructure
by adding a structured dual-mode reasoning pass with cross-validation.

Usage:
    from whitemagic.core.intelligence.bicameral import (
        get_bicameral_reasoner, BicameralReasoner
    )

    reasoner = get_bicameral_reasoner()
    result = await reasoner.reason("How should we restructure the memory tier?")
    print(result.synthesis)
    print(result.left_analysis)
    print(result.right_analysis)
    print(result.cross_critique)
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HemisphereResult:
    """Output from a single hemisphere."""

    hemisphere: str  # "left" or "right"
    content: str
    confidence: float
    strategy: str
    reasoning_chain: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossCritique:
    """Result of one hemisphere critiquing the other."""

    critic: str  # Which hemisphere is critiquing
    target: str  # Which hemisphere is being critiqued
    agreements: list[str]  # Points of agreement
    challenges: list[str]  # Points of disagreement / concern
    suggestions: list[str]  # Constructive modifications
    confidence_adjustment: float  # How much the critique adjusts confidence (-1 to +1)


@dataclass
class BicameralResult:
    """Full bicameral reasoning output."""

    query: str
    left_analysis: HemisphereResult
    right_analysis: HemisphereResult
    cross_critique: list[CrossCritique]
    synthesis: str
    final_confidence: float
    dominant_hemisphere: str  # Which hemisphere "won" this round
    tension_score: float  # 0=agreement, 1=maximum disagreement
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "query": self.query,
            "left": {
                "content": self.left_analysis.content,
                "confidence": self.left_analysis.confidence,
                "strategy": self.left_analysis.strategy,
            },
            "right": {
                "content": self.right_analysis.content,
                "confidence": self.right_analysis.confidence,
                "strategy": self.right_analysis.strategy,
            },
            "synthesis": self.synthesis,
            "final_confidence": round(self.final_confidence, 4),
            "dominant_hemisphere": self.dominant_hemisphere,
            "tension_score": round(self.tension_score, 4),
            "cross_critique_count": len(self.cross_critique),
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


# Left hemisphere: precise, analytical strategies
LEFT_STRATEGIES = [
    "analytical",
    "systematic",
    "factual",
    "cautious",
    "logical",
    "sequential",
    "deductive",
]

# Right hemisphere: creative, holistic strategies
RIGHT_STRATEGIES = [
    "creative",
    "intuitive",
    "optimistic",
    "theoretical",
    "holistic",
    "associative",
    "divergent",
]


class BicameralReasoner:
    """Dual-hemisphere reasoning engine.

    Runs two independent thought-clone armies (left=precise, right=creative),
    then performs cross-critique through the "corpus callosum" before
    synthesizing a final answer.
    """

    def __init__(
        self,
        left_clones: int = 50,
        right_clones: int = 50,
        cross_critique_enabled: bool = True,
        max_debate_rounds: int = 1,
    ):
        self._left_clones = left_clones
        self._right_clones = right_clones
        self._cross_critique_enabled = cross_critique_enabled
        self._max_debate_rounds = max_debate_rounds

        # Stats
        self._total_reasonings: int = 0
        self._left_wins: int = 0
        self._right_wins: int = 0
        self._ties: int = 0
        self._avg_tension: float = 0.0

    async def reason(
        self, query: str, context: dict[str, Any] | None = None
    ) -> BicameralResult:
        """Run bicameral reasoning on a query.

        1. Left hemisphere explores with precision strategies
        2. Right hemisphere explores with creative strategies
        3. Corpus callosum performs cross-critique
        4. Synthesis integrates both perspectives
        """
        start = time.perf_counter()
        context = context or {}

        left_result, right_result = await asyncio.gather(
            self._explore_hemisphere("left", query, LEFT_STRATEGIES, self._left_clones),
            self._explore_hemisphere(
                "right", query, RIGHT_STRATEGIES, self._right_clones
            ),
        )

        all_critiques: list[CrossCritique] = []
        if self._cross_critique_enabled:
            for round_num in range(self._max_debate_rounds):
                round_critiques = self._cross_critique(left_result, right_result)
                all_critiques.extend(round_critiques)

                # On subsequent rounds, refine hemisphere results based on critiques
                if round_num < self._max_debate_rounds - 1 and all_critiques:
                    left_result, right_result = await self._refine_hemispheres(
                        query,
                        left_result,
                        right_result,
                        round_critiques,
                    )

        synthesis, final_conf, dominant, tension = self._synthesize(
            left_result,
            right_result,
            all_critiques,
        )

        # Stats
        self._total_reasonings += 1
        if dominant == "left":
            self._left_wins += 1
        elif dominant == "right":
            self._right_wins += 1
        else:
            self._ties += 1
        # Running average tension
        self._avg_tension = (
            self._avg_tension * (self._total_reasonings - 1) + tension
        ) / self._total_reasonings

        elapsed_ms = (time.perf_counter() - start) * 1000

        result = BicameralResult(
            query=query,
            left_analysis=left_result,
            right_analysis=right_result,
            cross_critique=all_critiques,
            synthesis=synthesis,
            final_confidence=final_conf,
            dominant_hemisphere=dominant,
            tension_score=tension,
            duration_ms=elapsed_ms,
        )

        # Emit events
        self._emit_event(result)
        if result.final_confidence < 0.5:
            self._emit_low_confidence_event(result)

        return result

    async def _refine_hemispheres(
        self,
        query: str,
        left: HemisphereResult,
        right: HemisphereResult,
        critiques: list[CrossCritique],
    ) -> tuple[HemisphereResult, HemisphereResult]:
        """Refine hemisphere outputs using critique feedback from the previous round.

        Uses LLM to incorporate critique points into each hemisphere's reasoning.
        Falls back to returning original results if LLM unavailable.
        """
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return left, right

            critique_summary = []
            for c in critiques:
                if c.target == "left" and c.challenges:
                    critique_summary.append(
                        f"Left challenged on: {'; '.join(c.challenges[:2])}"
                    )
                if c.target == "right" and c.challenges:
                    critique_summary.append(
                        f"Right challenged on: {'; '.join(c.challenges[:2])}"
                    )
            critique_text = (
                "\n".join(critique_summary) if critique_summary else "(no challenges)"
            )

            def _refine(hemisphere: HemisphereResult, side: str) -> HemisphereResult:
                prompt = (
                    f"Refine this {side} perspective on: {query}\n\n"
                    f"Current view: {hemisphere.content[:300]}\n\n"
                    f"Critique feedback:\n{critique_text}\n\n"
                    f"Produce a refined, concise response addressing the critiques."
                )
                response = llm.complete(prompt, max_tokens=256, temperature=0.4)
                if response and response.strip():
                    return HemisphereResult(
                        hemisphere=hemisphere.hemisphere,
                        content=response.strip(),
                        confidence=min(0.98, hemisphere.confidence + 0.02),
                        strategy=f"{hemisphere.strategy}_refined",
                        reasoning_chain=hemisphere.reasoning_chain + [response.strip()],
                        duration_ms=hemisphere.duration_ms,
                        metadata=hemisphere.metadata,
                    )
                return hemisphere

            new_left = _refine(left, "analytical")
            new_right = _refine(right, "creative")
            return new_left, new_right
        except Exception as e:
            logger.debug("Hemisphere refinement unavailable: %s", e)
            return left, right

    async def _explore_hemisphere(
        self,
        hemisphere: str,
        query: str,
        strategies: list[str],
        num_clones: int,
    ) -> HemisphereResult:
        """Run a thought clone army biased toward a hemisphere's strategies."""
        from whitemagic.edge.thought_clones_async import (
            AsyncThoughtCloneArmy,
            CloneConfig,
        )

        config = CloneConfig(max_clones=num_clones, max_concurrent_api_calls=50)
        army = AsyncThoughtCloneArmy(config=config)

        # Override strategy generation to bias toward this hemisphere

        def biased_strategies(count: int) -> list[str]:
            """
            Perform the biased strategies operation.

            Args:
                count: Parameter description.

            Returns:
                list[str]
            """
            result = []
            for i in range(count):
                result.append(strategies[i % len(strategies)])
            return result

        army._generate_strategies = biased_strategies  # type: ignore[assignment]

        start = time.perf_counter()
        # Force the Python path here so the hemisphere-specific strategy bias
        # is respected; the Rust/Tokio fast-path generates its own generic
        # strategies and collapses left/right exploration into the same shape.
        best_path = await army.parallel_explore(query, num_clones, use_tokio=False)
        elapsed = (time.perf_counter() - start) * 1000

        return HemisphereResult(
            hemisphere=hemisphere,
            content=best_path.content,
            confidence=best_path.confidence,
            strategy=best_path.strategy,
            reasoning_chain=[best_path.content],
            duration_ms=elapsed,
            metadata={
                "clone_id": best_path.clone_id,
                "tokens": best_path.tokens,
            },
        )

    def _compute_semantic_similarity(self, text_a: str, text_b: str) -> float | None:
        """Compute cosine similarity between embeddings of two texts.

        Returns None if embedding engine is unavailable, so callers
        can fall back to word-overlap heuristics.
        """
        try:
            import numpy as np

            from whitemagic.core.memory.embeddings import get_embedding_engine

            engine = get_embedding_engine()
            emb_a = engine.encode(text_a)
            emb_b = engine.encode(text_b)
            if emb_a is None or emb_b is None:
                return None
            a = np.asarray(emb_a, dtype=np.float32)
            b = np.asarray(emb_b, dtype=np.float32)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a < 1e-8 or norm_b < 1e-8:
                return None
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception:
            return None

    def _cross_critique(
        self,
        left: HemisphereResult,
        right: HemisphereResult,
    ) -> list[CrossCritique]:
        """Each hemisphere critiques the other.

        Uses LLM-driven critique when Ollama is available.
        Falls back to heuristic analysis of content characteristics.
        """
        # Try LLM-driven cross-critique
        llm_critiques = self._llm_cross_critique(left, right)
        if llm_critiques is not None:
            return llm_critiques

        # Heuristic fallback
        critiques = []
        left_on_right = self._left_critiques_right(left, right)
        critiques.append(left_on_right)
        right_on_left = self._right_critiques_left(left, right)
        critiques.append(right_on_left)
        return critiques

    def _llm_cross_critique(
        self,
        left: HemisphereResult,
        right: HemisphereResult,
    ) -> list[CrossCritique] | None:
        """Use LLM to generate cross-critiques between hemispheres.

        Returns None if LLM unavailable, falling back to heuristic.
        """
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return None

            prompt = (
                f"Analyze two perspectives on the same topic.\n\n"
                f"Analytical (conf={left.confidence:.2f}): {left.content[:300]}\n\n"
                f"Creative (conf={right.confidence:.2f}): {right.content[:300]}\n\n"
                f"For each perspective, identify:\n"
                f"1. One agreement point\n"
                f"2. One challenge (weakness or gap)\n"
                f"3. One suggestion for improvement\n"
                f"Format: LEFT_CRITIQUE_RIGHT: agree=X | challenge=Y | suggest=Z\n"
                f"RIGHT_CRITIQUE_LEFT: agree=X | challenge=Y | suggest=Z"
            )
            response = llm.complete(prompt, max_tokens=256, temperature=0.4)
            if not response or not response.strip():
                return None

            critiques = []
            for section in response.split("LEFT_CRITIQUE_RIGHT"):
                if "RIGHT_CRITIQUE_LEFT" in section:
                    left_part, right_part = section.split("RIGHT_CRITIQUE_LEFT")
                else:
                    left_part = section
                    right_part = ""

                lc = self._parse_llm_critique("left", "right", left_part)
                if lc:
                    critiques.append(lc)
                rc = self._parse_llm_critique("right", "left", right_part)
                if rc:
                    critiques.append(rc)

            if not critiques:
                return None
            logger.debug("LLM cross-critique generated %d critiques", len(critiques))
            return critiques
        except Exception as e:
            logger.debug("LLM cross-critique unavailable: %s", e)
            return None

    @staticmethod
    def _parse_llm_critique(
        critic: str, target: str, text: str
    ) -> CrossCritique | None:
        """Parse LLM critique response into CrossCritique."""
        agreements = []
        challenges = []
        suggestions = []
        conf_adj = 0.0

        for part in text.split("|"):
            part = part.strip()
            if part.startswith("agree="):
                val = part[6:].strip()
                if val:
                    agreements.append(val)
                    conf_adj += 0.03
            elif part.startswith("challenge="):
                val = part[10:].strip()
                if val:
                    challenges.append(val)
                    conf_adj -= 0.04
            elif part.startswith("suggest="):
                val = part[8:].strip()
                if val:
                    suggestions.append(val)

        if not agreements and not challenges and not suggestions:
            return None

        return CrossCritique(
            critic=critic,
            target=target,
            agreements=agreements,
            challenges=challenges,
            suggestions=suggestions,
            confidence_adjustment=conf_adj,
        )

    def _left_critiques_right(
        self, left: HemisphereResult, right: HemisphereResult
    ) -> CrossCritique:
        """Left hemisphere checks Right for logical consistency."""
        agreements = []
        challenges = []
        suggestions = []
        conf_adj = 0.0

        # Agreement: use embedding cosine similarity if available, else word-overlap
        sim_score = self._compute_semantic_similarity(left.content, right.content)
        if sim_score is not None:
            if sim_score > 0.5:
                agreements.append(f"Strong semantic alignment (cosine={sim_score:.3f})")
                conf_adj += 0.05
            elif sim_score > 0.3:
                agreements.append(f"Moderate semantic overlap (cosine={sim_score:.3f})")
                conf_adj += 0.02
        else:
            # Fallback: word-overlap
            left_words = set(left.content.lower().split())
            right_words = set(right.content.lower().split())
            overlap = left_words & right_words
            stopwords = {
                "the",
                "a",
                "an",
                "is",
                "are",
                "was",
                "were",
                "to",
                "of",
                "and",
                "in",
                "for",
                "on",
                "with",
                "that",
                "this",
                "it",
            }
            meaningful_overlap = overlap - stopwords
            if len(meaningful_overlap) > 3:
                agreements.append(
                    f"Shared focus on: {', '.join(list(meaningful_overlap)[:5])}"
                )
                conf_adj += 0.05

        # Challenge: right hemisphere may be too speculative
        right_words = set(right.content.lower().split())
        speculative_markers = {
            "maybe",
            "perhaps",
            "possibly",
            "could",
            "might",
            "imagine",
            "creative",
            "unconventional",
            "novel",
        }
        right_speculation = right_words & speculative_markers
        if len(right_speculation) > 1:
            challenges.append(
                f"High speculation detected: {', '.join(right_speculation)}"
            )
            conf_adj -= 0.05

        # Suggestion: ground creative ideas in specifics
        if right.confidence < left.confidence:
            suggestions.append(
                "Consider grounding creative insights with concrete evidence or examples"
            )

        return CrossCritique(
            critic="left",
            target="right",
            agreements=agreements,
            challenges=challenges,
            suggestions=suggestions,
            confidence_adjustment=conf_adj,
        )

    def _right_critiques_left(
        self, left: HemisphereResult, right: HemisphereResult
    ) -> CrossCritique:
        """Right hemisphere checks Left for creative breadth."""
        agreements = []
        challenges = []
        suggestions = []
        conf_adj = 0.0

        # Agreement: use embedding cosine similarity if available, else word-overlap
        sim_score = self._compute_semantic_similarity(left.content, right.content)
        if sim_score is not None:
            if sim_score > 0.5:
                agreements.append(f"Strong semantic alignment (cosine={sim_score:.3f})")
                conf_adj += 0.05
            elif sim_score > 0.3:
                agreements.append(f"Moderate semantic overlap (cosine={sim_score:.3f})")
                conf_adj += 0.02
        else:
            # Fallback: word-overlap
            left_words = set(left.content.lower().split())
            right_words = set(right.content.lower().split())
            overlap = left_words & right_words
            stopwords = {
                "the",
                "a",
                "an",
                "is",
                "are",
                "was",
                "were",
                "to",
                "of",
                "and",
                "in",
                "for",
                "on",
                "with",
                "that",
                "this",
                "it",
            }
            meaningful_overlap = overlap - stopwords
            if len(meaningful_overlap) > 3:
                agreements.append(
                    f"Common ground on: {', '.join(list(meaningful_overlap)[:5])}"
                )
                conf_adj += 0.05

        # Challenge: left hemisphere may be too narrow
        left_words = set(left.content.lower().split())
        narrow_markers = {
            "only",
            "must",
            "always",
            "never",
            "precisely",
            "exactly",
            "systematic",
        }
        left_narrowness = left_words & narrow_markers
        if len(left_narrowness) > 1:
            challenges.append(
                f"Potentially over-constrained thinking: {', '.join(left_narrowness)}"
            )
            conf_adj -= 0.03

        # Suggestion: explore adjacent possibilities
        if left.confidence > right.confidence + 0.2:
            suggestions.append(
                "High precision may miss novel approaches — consider exploring adjacent solution spaces"
            )

        return CrossCritique(
            critic="right",
            target="left",
            agreements=agreements,
            challenges=challenges,
            suggestions=suggestions,
            confidence_adjustment=conf_adj,
        )

    def _synthesize(
        self,
        left: HemisphereResult,
        right: HemisphereResult,
        critiques: list[CrossCritique],
    ) -> tuple:
        """Synthesize both hemispheres + cross-critiques into a final answer.

        Uses LLM for synthesis when Ollama is available.
        Falls back to heuristic weighted synthesis when not.

        Returns: (synthesis_text, final_confidence, dominant_hemisphere, tension_score)
        """
        # Calculate tension (disagreement between hemispheres)
        conf_diff = abs(left.confidence - right.confidence)
        content_overlap = self._content_similarity(left.content, right.content)
        tension = (conf_diff + (1.0 - content_overlap)) / 2.0
        tension = max(0.0, min(1.0, tension))

        # Apply critique adjustments
        left_adj = 0.0
        right_adj = 0.0
        for c in critiques:
            if c.target == "left":
                left_adj += c.confidence_adjustment
            elif c.target == "right":
                right_adj += c.confidence_adjustment

        adj_left_conf = max(0.0, min(1.0, left.confidence + left_adj))
        adj_right_conf = max(0.0, min(1.0, right.confidence + right_adj))

        # Determine dominance
        if abs(adj_left_conf - adj_right_conf) < 0.05:
            dominant = "balanced"
        elif adj_left_conf > adj_right_conf:
            dominant = "left"
        else:
            dominant = "right"

        # Weighted synthesis
        total_conf = adj_left_conf + adj_right_conf
        if total_conf == 0:
            left_weight = 0.5
            right_weight = 0.5
        else:
            left_weight = adj_left_conf / total_conf
            right_weight = adj_right_conf / total_conf

        final_confidence = left_weight * adj_left_conf + right_weight * adj_right_conf

        # Try LLM-enhanced synthesis
        llm_synthesis = self._llm_synthesize(left, right, critiques, dominant, tension)
        if llm_synthesis is not None:
            return llm_synthesis, final_confidence, dominant, tension

        # Heuristic fallback: build synthesis text
        parts = []
        parts.append(
            f"[LEFT ({left.strategy}, conf={adj_left_conf:.2f})] {left.content}"
        )
        parts.append(
            f"[RIGHT ({right.strategy}, conf={adj_right_conf:.2f})] {right.content}"
        )

        if critiques:
            critique_notes = []
            for c in critiques:
                if c.challenges:
                    critique_notes.append(
                        f"{c.critic}→{c.target}: {'; '.join(c.challenges)}"
                    )
                if c.suggestions:
                    critique_notes.append(
                        f"{c.critic} suggests: {'; '.join(c.suggestions)}"
                    )
            if critique_notes:
                parts.append(f"[CORPUS CALLOSUM] {' | '.join(critique_notes)}")

        parts.append(
            f"[SYNTHESIS] Dominant={dominant}, tension={tension:.2f}, "
            f"confidence={final_confidence:.2f}",
        )

        synthesis = "\n".join(parts)
        return synthesis, final_confidence, dominant, tension

    def _llm_synthesize(
        self,
        left: HemisphereResult,
        right: HemisphereResult,
        critiques: list[CrossCritique],
        dominant: str,
        tension: float,
    ) -> str | None:
        """Use LLM to synthesize bicameral output. Returns None if unavailable."""
        try:
            from whitemagic.inference.local_llm import LocalLLM

            llm = LocalLLM()
            if not llm.is_available:
                return None

            critique_text = ""
            for c in critiques:
                if c.challenges:
                    critique_text += (
                        f"\n{c.critic}→{c.target} challenges: {'; '.join(c.challenges)}"
                    )
                if c.suggestions:
                    critique_text += (
                        f"\n{c.critic} suggests: {'; '.join(c.suggestions)}"
                    )

            prompt = (
                f"Synthesize two perspectives into one concise answer.\n\n"
                f"Analytical (conf={left.confidence:.2f}): {left.content[:200]}\n\n"
                f"Creative (conf={right.confidence:.2f}): {right.content[:200]}\n\n"
                f"Key insight from their tension:"
            )
            response = llm.complete(prompt, max_tokens=256, temperature=0.5)
            if response and response.strip():
                return f"[LLM SYNTHESIS] {response.strip()}\n[dominant={dominant}, tension={tension:.2f}]"
            return None
        except Exception as e:
            logger.debug("LLM synthesis unavailable: %s", e)
            return None

    def _content_similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity."""
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    def _emit_event(self, result: BicameralResult) -> None:
        """Emit reasoning result to the Gan Ying bus."""
        try:
            from whitemagic.core.resonance.gan_ying import emit_event
            from whitemagic.core.resonance.gan_ying_enhanced import EventType

            emit_event(
                "bicameral_reasoner",
                EventType.REASONING_COMPLETE,
                {
                    "query": result.query[:100],
                    "dominant": result.dominant_hemisphere,
                    "tension": result.tension_score,
                    "confidence": result.final_confidence,
                    "duration_ms": result.duration_ms,
                },
            )
        except Exception as e:
            logger.debug("Bicameral non-critical execution error: %s", e, exc_info=True)

    def _emit_low_confidence_event(self, result: BicameralResult) -> None:
        """Emit CREATIVE_BRIDGE_LOW_CONFIDENCE when synthesis is uncertain."""
        try:
            from whitemagic.core.resonance.gan_ying import emit_event
            from whitemagic.core.resonance.gan_ying_enhanced import EventType

            emit_event(
                "bicameral_reasoner",
                EventType.CREATIVE_BRIDGE_LOW_CONFIDENCE,
                {
                    "query": result.query[:200],
                    "left": result.left_analysis.content[:500],
                    "right": result.right_analysis.content[:500],
                    "synthesis": result.synthesis[:500],
                    "confidence": result.final_confidence,
                    "tension": result.tension_score,
                    "dominant": result.dominant_hemisphere,
                },
            )
        except Exception as e:
            logger.debug(
                "Bicameral low-confidence emission error: %s", e, exc_info=True
            )

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return {
            "total_reasonings": self._total_reasonings,
            "left_wins": self._left_wins,
            "right_wins": self._right_wins,
            "ties": self._ties,
            "avg_tension": round(self._avg_tension, 4),
            "left_clones": self._left_clones,
            "right_clones": self._right_clones,
            "cross_critique_enabled": self._cross_critique_enabled,
        }


_reasoner_instance: BicameralReasoner | None = None
_reasoner_lock = threading.Lock()


def get_bicameral_reasoner(
    left_clones: int = 50,
    right_clones: int = 50,
    max_debate_rounds: int = 1,
) -> BicameralReasoner:
    """Get or create the global BicameralReasoner singleton."""
    global _reasoner_instance
    with _reasoner_lock:
        if _reasoner_instance is None:
            _reasoner_instance = BicameralReasoner(
                left_clones=left_clones,
                right_clones=right_clones,
                max_debate_rounds=max_debate_rounds,
            )
        return _reasoner_instance
