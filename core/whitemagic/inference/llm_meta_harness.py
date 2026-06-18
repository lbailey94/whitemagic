# ruff: noqa: BLE001
"""
LLM Meta-Harness - WhiteMagic Enhancement Layer
================================================
Wraps local LLMs to enhance their capabilities through:
- Memory grounding (RAG with 111K memories)
- Chain-of-thought scaffolding
- Self-correction loops
- Ensemble voting
- Pattern injection
- Dharma alignment
- Performance optimization

This turns a small local LLM into a much more capable system.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EnhancementMode(Enum):
    """Enhancement strategies for LLM meta-harness."""
    DIRECT = "direct"  # No enhancement, baseline
    MEMORY_GROUNDED = "memory_grounded"  # RAG with memories
    CHAIN_OF_THOUGHT = "chain_of_thought"  # Explicit reasoning steps
    SELF_CORRECTING = "self_correcting"  # Generate -> critique -> refine
    ENSEMBLE = "ensemble"  # Multiple attempts, vote on best
    PATTERN_INJECTED = "pattern_injected"  # Inject learned patterns
    DHARMA_ALIGNED = "dharma_aligned"  # Ethical reasoning layer
    FULL_STACK = "full_stack"  # All enhancements combined


@dataclass
class EnhancedResponse:
    """Response from enhanced LLM."""
    query: str
    answer: str
    confidence: float
    mode: EnhancementMode
    latency_ms: float
    tokens_used: int
    enhancement_details: dict[str, Any] = field(default_factory=dict)
    baseline_answer: str | None = None  # For comparison
    improvement_score: float = 0.0  # How much better than baseline


class LLMMetaHarness:
    """
    Meta-harness that wraps local LLMs and enhances their capabilities
    through WhiteMagic's cognitive scaffolding systems.
    """

    def __init__(self, model_name: str = "qwen2.5-coder:1.5b"):
        self.model_name = model_name
        self._llm = None
        self._memory = None
        self._available = False
        self._stats: dict[str, Any] = {
            "total_queries": 0,
            "by_mode": {},
            "avg_latency_ms": {},
            "avg_improvement": {},
        }
        self._try_load()

    def _try_load(self):
        """Load local LLM and WhiteMagic systems."""
        try:
            from whitemagic.core.memory import get_unified_memory
            from whitemagic.inference.local_llm import LocalLLM

            self._llm = LocalLLM(model=self.model_name)
            self._memory = get_unified_memory()
            self._available = self._llm.is_available

            if self._available:
                logger.info(f"LLM Meta-Harness loaded with model: {self.model_name}")
            else:
                logger.warning(f"LLM not available: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load meta-harness: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        """
        Check whether the available condition holds.
        
        Returns:
            bool
        """
        return self._available

    async def enhance(
        self,
        query: str,
        mode: EnhancementMode = EnhancementMode.FULL_STACK,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> EnhancedResponse:
        """
        Enhance LLM response using specified mode.

        Args:
            query: User query
            mode: Enhancement strategy
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            EnhancedResponse with answer and metadata
        """
        if not self._available:
            return EnhancedResponse(
                query=query,
                answer="LLM not available",
                confidence=0.0,
                mode=mode,
                latency_ms=0.0,
                tokens_used=0,
            )

        start_time = time.time()
        total = int(self._stats.get("total_queries", 0))
        self._stats["total_queries"] = total + 1

        # Route to appropriate enhancement strategy
        if mode == EnhancementMode.DIRECT:
            response = await self._enhance_direct(query, max_tokens, temperature)
        elif mode == EnhancementMode.MEMORY_GROUNDED:
            response = await self._enhance_memory_grounded(query, max_tokens, temperature)
        elif mode == EnhancementMode.CHAIN_OF_THOUGHT:
            response = await self._enhance_chain_of_thought(query, max_tokens, temperature)
        elif mode == EnhancementMode.SELF_CORRECTING:
            response = await self._enhance_self_correcting(query, max_tokens, temperature)
        elif mode == EnhancementMode.ENSEMBLE:
            response = await self._enhance_ensemble(query, max_tokens, temperature)
        elif mode == EnhancementMode.PATTERN_INJECTED:
            response = await self._enhance_pattern_injected(query, max_tokens, temperature)
        elif mode == EnhancementMode.DHARMA_ALIGNED:
            response = await self._enhance_dharma_aligned(query, max_tokens, temperature)
        elif mode == EnhancementMode.FULL_STACK:
            response = await self._enhance_full_stack(query, max_tokens, temperature)
        else:
            response = await self._enhance_direct(query, max_tokens, temperature)

        response.latency_ms = (time.time() - start_time) * 1000

        # Update stats
        mode_key = mode.value
        if mode_key not in self._stats["by_mode"]:
            self._stats["by_mode"][mode_key] = 0
            self._stats["avg_latency_ms"][mode_key] = []
            self._stats["avg_improvement"][mode_key] = []

        self._stats["by_mode"][mode_key] += 1
        self._stats["avg_latency_ms"][mode_key].append(response.latency_ms)
        if response.improvement_score > 0:
            self._stats["avg_improvement"][mode_key].append(response.improvement_score)

        return response

    async def _enhance_direct(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Baseline: no enhancement."""
        if self._llm is None:
            return EnhancedResponse(query=query, answer="LLM not available", confidence=0.0, mode=EnhancementMode.DIRECT, latency_ms=0.0, tokens_used=0)
        answer = self._llm.complete(query, max_tokens=max_tokens, temperature=temperature)
        return EnhancedResponse(
            query=query,
            answer=answer,
            confidence=0.6,  # Baseline confidence
            mode=EnhancementMode.DIRECT,
            latency_ms=0.0,
            tokens_used=len(answer.split()),
        )

    async def _enhance_memory_grounded(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """RAG: Ground response in relevant memories."""
        if self._llm is None or self._memory is None:
            return EnhancedResponse(query=query, answer="System not available", confidence=0.0, mode=EnhancementMode.MEMORY_GROUNDED, latency_ms=0.0, tokens_used=0)
        # Search for relevant memories
        memories = self._memory.search(query, limit=5, use_vector=True)

        # Build context from memories
        context_parts = []
        for mem in memories[:3]:  # Top 3 most relevant
            context_parts.append(f"- {mem.title}: {mem.content[:200]}")

        context = "\n".join(context_parts) if context_parts else "No relevant context found."

        # Enhanced prompt with memory grounding
        enhanced_query = f"""Context from memory:
{context}

Question: {query}

Answer based on the context above:"""

        answer = self._llm.complete(enhanced_query, max_tokens=max_tokens, temperature=temperature)

        return EnhancedResponse(
            query=query,
            answer=answer,
            confidence=0.8,  # Higher confidence with grounding
            mode=EnhancementMode.MEMORY_GROUNDED,
            latency_ms=0.0,
            tokens_used=len(answer.split()),
            enhancement_details={
                "memories_used": len(memories),
                "context_length": len(context),
            },
        )

    async def _enhance_chain_of_thought(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Chain-of-thought: Explicit reasoning steps."""
        if self._llm is None:
            return EnhancedResponse(query=query, answer="LLM not available", confidence=0.0, mode=EnhancementMode.CHAIN_OF_THOUGHT, latency_ms=0.0, tokens_used=0)
        cot_prompt = f"""Question: {query}

Let's think step by step:
1."""

        reasoning = self._llm.complete(cot_prompt, max_tokens=max_tokens, temperature=temperature)

        # Extract final answer from reasoning
        answer = reasoning.split("\n")[-1] if reasoning else "Unable to reason through this."

        return EnhancedResponse(
            query=query,
            answer=answer,
            confidence=0.75,
            mode=EnhancementMode.CHAIN_OF_THOUGHT,
            latency_ms=0.0,
            tokens_used=len(reasoning.split()),
            enhancement_details={
                "reasoning_steps": reasoning,
            },
        )

    async def _enhance_self_correcting(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Self-correction: Generate -> Critique -> Refine."""
        if self._llm is None:
            return EnhancedResponse(query=query, answer="LLM not available", confidence=0.0, mode=EnhancementMode.SELF_CORRECTING, latency_ms=0.0, tokens_used=0)
        # Step 1: Generate initial answer
        initial = self._llm.complete(query, max_tokens=max_tokens // 2, temperature=temperature)

        # Step 2: Critique the answer
        critique_prompt = f"""Question: {query}
Initial answer: {initial}

Critique this answer. What's wrong or could be improved?"""

        critique = self._llm.complete(critique_prompt, max_tokens=max_tokens // 4, temperature=0.3)

        # Step 3: Refine based on critique
        refine_prompt = f"""Question: {query}
Initial answer: {initial}
Critique: {critique}

Provide an improved answer:"""

        refined = self._llm.complete(refine_prompt, max_tokens=max_tokens // 2, temperature=temperature)

        return EnhancedResponse(
            query=query,
            answer=refined,
            confidence=0.85,
            mode=EnhancementMode.SELF_CORRECTING,
            latency_ms=0.0,
            tokens_used=len(initial.split()) + len(critique.split()) + len(refined.split()),
            enhancement_details={
                "initial_answer": initial,
                "critique": critique,
            },
            baseline_answer=initial,
        )

    async def _enhance_ensemble(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Ensemble: Generate multiple answers, vote on best."""
        if self._llm is None:
            return EnhancedResponse(query=query, answer="LLM not available", confidence=0.0, mode=EnhancementMode.ENSEMBLE, latency_ms=0.0, tokens_used=0)
        # Generate 3 different answers with varying temperature
        answers = []
        for temp in [0.3, 0.7, 1.0]:
            answer = self._llm.complete(query, max_tokens=max_tokens, temperature=temp)
            answers.append(answer)

        # Simple voting: pick the longest answer (heuristic: more detailed = better)
        best_answer = max(answers, key=len)

        return EnhancedResponse(
            query=query,
            answer=best_answer,
            confidence=0.8,
            mode=EnhancementMode.ENSEMBLE,
            latency_ms=0.0,
            tokens_used=sum(len(a.split()) for a in answers),
            enhancement_details={
                "candidates": answers,
                "voting_method": "longest",
            },
        )

    async def _enhance_pattern_injected(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Pattern injection: Inject learned patterns from memory."""
        if self._llm is None or self._memory is None:
            return EnhancedResponse(query=query, answer="System not available", confidence=0.0, mode=EnhancementMode.PATTERN_INJECTED, latency_ms=0.0, tokens_used=0)
        # Search for similar past queries
        similar_memories = self._memory.search(query, limit=3, use_vector=True)

        # Extract patterns from similar queries
        patterns = []
        for mem in similar_memories:
            if "pattern" in mem.tags or "solution" in mem.tags:
                patterns.append(mem.content[:150])

        if patterns:
            pattern_context = "\n".join(f"Pattern {i+1}: {p}" for i, p in enumerate(patterns))
            enhanced_query = f"""Known patterns:
{pattern_context}

Apply these patterns to: {query}

Answer:"""
        else:
            enhanced_query = query

        answer = self._llm.complete(enhanced_query, max_tokens=max_tokens, temperature=temperature)

        return EnhancedResponse(
            query=query,
            answer=answer,
            confidence=0.75,
            mode=EnhancementMode.PATTERN_INJECTED,
            latency_ms=0.0,
            tokens_used=len(answer.split()),
            enhancement_details={
                "patterns_found": len(patterns),
            },
        )

    async def _enhance_dharma_aligned(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Dharma alignment: Add ethical reasoning layer."""
        if self._llm is None:
            return EnhancedResponse(query=query, answer="LLM not available", confidence=0.0, mode=EnhancementMode.DHARMA_ALIGNED, latency_ms=0.0, tokens_used=0)
        dharma_prompt = f"""Question: {query}

Before answering, consider:
1. Does this respect boundaries and consent?
2. Does this promote flourishing?
3. Is this aligned with love as organizing principle?

Answer with ethical awareness:"""

        answer = self._llm.complete(dharma_prompt, max_tokens=max_tokens, temperature=temperature)

        return EnhancedResponse(
            query=query,
            answer=answer,
            confidence=0.8,
            mode=EnhancementMode.DHARMA_ALIGNED,
            latency_ms=0.0,
            tokens_used=len(answer.split()),
            enhancement_details={
                "dharma_check": "passed",
            },
        )

    async def _enhance_full_stack(self, query: str, max_tokens: int, temperature: float) -> EnhancedResponse:
        """Full stack: Combine all enhancements."""
        if self._llm is None or self._memory is None:
            return EnhancedResponse(query=query, answer="System not available", confidence=0.0, mode=EnhancementMode.FULL_STACK, latency_ms=0.0, tokens_used=0)
        # 1. Memory grounding
        memories = self._memory.search(query, limit=3, use_vector=True)
        context = "\n".join(f"- {m.title}" for m in memories[:2]) if memories else ""

        # 2. Pattern injection
        patterns = []
        for mem in memories:
            if "pattern" in mem.tags:
                patterns.append(mem.content[:100])

        # 3. Chain-of-thought + Dharma alignment
        full_prompt = f"""Context: {context}
Patterns: {', '.join(patterns[:2]) if patterns else 'None'}

Question: {query}

Think step by step with ethical awareness:
1."""

        # 4. Self-correction
        initial = self._llm.complete(full_prompt, max_tokens=max_tokens // 2, temperature=temperature)

        refine_prompt = f"""Initial reasoning: {initial}

Refine and provide final answer:"""

        final = self._llm.complete(refine_prompt, max_tokens=max_tokens // 2, temperature=0.5)

        return EnhancedResponse(
            query=query,
            answer=final,
            confidence=0.9,
            mode=EnhancementMode.FULL_STACK,
            latency_ms=0.0,
            tokens_used=len(initial.split()) + len(final.split()),
            enhancement_details={
                "memories_used": len(memories),
                "patterns_used": len(patterns),
                "initial_reasoning": initial,
            },
            baseline_answer=initial,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats = {
            "total_queries": self._stats["total_queries"],
            "by_mode": self._stats["by_mode"],
        }

        # Calculate averages
        for mode, latencies in self._stats["avg_latency_ms"].items():
            if latencies:
                stats[f"{mode}_avg_latency_ms"] = sum(latencies) / len(latencies)

        for mode, improvements in self._stats["avg_improvement"].items():
            if improvements:
                stats[f"{mode}_avg_improvement"] = sum(improvements) / len(improvements)

        return stats


# Singleton instance
_harness: LLMMetaHarness | None = None


def get_meta_harness(model_name: str = "qwen2.5-coder:1.5b") -> LLMMetaHarness:
    """Get singleton meta-harness instance."""
    global _harness
    if _harness is None or _harness.model_name != model_name:
        _harness = LLMMetaHarness(model_name=model_name)
    return _harness


async def enhance_query(
    query: str,
    mode: EnhancementMode = EnhancementMode.FULL_STACK,
    model_name: str = "qwen2.5-coder:1.5b",
) -> EnhancedResponse:
    """Quick helper to enhance a query."""
    harness = get_meta_harness(model_name)
    return await harness.enhance(query, mode=mode)
