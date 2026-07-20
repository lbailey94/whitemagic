"""LLM-Powered Oracle Interpretation.

Uses local LLM (via LlamaCppBackend) to generate natural-language interpretations
of oracle readings. Falls back to template-based interpretation when LLM is
unavailable.

The interpreter takes a SynthesisResult and produces a rich, contextual
narrative that weaves together the symbolic layers with the question asked.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OracleLLMInterpreter:
    """Generates LLM-powered interpretations of oracle readings.

    Uses LlamaCppBackend when available for rich narrative generation.
    Falls back to structured template interpretation otherwise.
    """

    def __init__(self) -> None:
        self._llm_available = False
        try:
            from whitemagic.inference.llama_cpp import get_llama_cpp_backend
            backend = get_llama_cpp_backend()
            self._llm_available = backend is not None
            self._backend = backend
        except Exception:  # noqa: BLE001
            self._llm_available = False
            self._backend = None

    @property
    def available(self) -> bool:
        """True if LLM interpretation is available."""
        return self._llm_available

    def interpret(
        self,
        synthesis_result: Any,
        question: str = "",
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate a natural-language interpretation of an oracle reading.

        Args:
            synthesis_result: A SynthesisResult from OracleSynthesizer.synthesize().
            question: The original question asked (if any).
            context: Additional context for interpretation.

        Returns:
            A rich interpretation string.
        """
        if self._llm_available:
            try:
                return self._llm_interpret(synthesis_result, question, context or {})
            except Exception as exc:  # noqa: BLE001
                logger.debug("LLM interpretation failed, falling back to template: %s", exc)

        return self._template_interpret(synthesis_result, question, context or {})

    def _llm_interpret(
        self,
        result: Any,
        question: str,
        context: dict[str, Any],
    ) -> str:
        """Use LLM to generate interpretation."""
        prompt = self._build_prompt(result, question, context)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a wise oracle interpreter. You read divination symbols "
                    "(I Ching, Tarot, Ifá, astrology) and weave them into a single "
                    "coherent, insightful message. Be poetic but practical. "
                    "Keep interpretations under 300 words."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = self._backend.chat(messages, max_tokens=400, temperature=0.7)
        if isinstance(response, str):
            return response.strip()
        if isinstance(response, dict):
            return response.get("content", response.get("response", "")).strip()
        return str(response).strip()

    def _build_prompt(self, result: Any, question: str, context: dict[str, Any]) -> str:
        """Build the LLM prompt from synthesis result."""
        parts = []

        if question:
            parts.append(f"Question asked: {question}")

        if hasattr(result, "primary_hexagram") and result.primary_hexagram:
            parts.append(f"Primary hexagram: #{result.primary_hexagram}")

        if hasattr(result, "unified_message"):
            parts.append(f"Core message: {result.unified_message}")

        if hasattr(result, "elemental_harmony"):
            parts.append(f"Elemental harmony: {result.elemental_harmony}")

        if hasattr(result, "practical_guidance"):
            parts.append(f"Practical guidance: {result.practical_guidance}")

        if hasattr(result, "cautions") and result.cautions:
            parts.append(f"Cautions: {', '.join(result.cautions)}")

        if hasattr(result, "blessings") and result.blessings:
            parts.append(f"Blessings: {', '.join(result.blessings)}")

        if hasattr(result, "hrr_resonances") and result.hrr_resonances:
            top_res = result.hrr_resonances[:3]
            res_str = ", ".join(
                f"#{r['hexagram']} ({r['similarity']:.2f})" for r in top_res
            )
            parts.append(f"HRR resonances: {res_str}")

        if hasattr(result, "narrative") and result.narrative:
            parts.append(f"Narrative arc: {result.narrative}")

        parts.append("\nPlease provide a unified interpretation that weaves these elements together.")

        return "\n".join(parts)

    def _template_interpret(
        self,
        result: Any,
        question: str,
        context: dict[str, Any],
    ) -> str:
        """Generate a structured template interpretation (fallback)."""
        sections: list[str] = []

        # Opening
        if question:
            sections.append(f"In response to your question about '{question}':")
        else:
            sections.append("The oracle speaks:")

        # Core message
        if hasattr(result, "unified_message") and result.unified_message:
            sections.append(f"\n{result.unified_message}")

        # Hexagram
        if hasattr(result, "primary_hexagram") and result.primary_hexagram:
            sections.append(f"\nHexagram #{result.primary_hexagram} stands as the primary pattern.")

        # HRR resonances
        if hasattr(result, "hrr_resonances") and result.hrr_resonances:
            top = result.hrr_resonances[:3]
            res_list = ", ".join(f"#{r['hexagram']}" for r in top)
            sections.append(f"This hexagram resonates with: {res_list}.")

        # Elemental harmony
        if hasattr(result, "elemental_harmony") and result.elemental_harmony:
            sections.append(f"\n{result.elemental_harmony}")

        # Practical guidance
        if hasattr(result, "practical_guidance") and result.practical_guidance:
            sections.append(f"\nGuidance: {result.practical_guidance}")

        # Cautions
        if hasattr(result, "cautions") and result.cautions:
            sections.append(f"\nCaution: {'; '.join(result.cautions)}")

        # Blessings
        if hasattr(result, "blessings") and result.blessings:
            sections.append(f"\nBlessing: {'; '.join(result.blessings)}")

        return "\n".join(sections) if sections else "The oracle is silent."


_interpreter: OracleLLMInterpreter | None = None


def get_oracle_interpreter() -> OracleLLMInterpreter:
    """Get the singleton OracleLLMInterpreter instance."""
    global _interpreter
    if _interpreter is None:
        _interpreter = OracleLLMInterpreter()
    return _interpreter
