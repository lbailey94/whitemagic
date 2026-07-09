# ruff: noqa: BLE001
"""Complexity Classifier — evaluates prompt complexity for inference routing.

Inspired by Sakana Fugu's Conductor pattern and production hybrid cloud-edge
routing research (tianpan.co, CallSphere, Zylos Research 2026).

Classifies prompts along multiple dimensions to determine the minimum tier
that can handle the request:
  Tier 0: Edge rules (cache + Rust PatternEngine) — <1ms
  Tier 1: Local small model (llama.cpp 1.5B-7B quantized) — 50-500ms
  Tier 2: Local large model (BitNet/llama.cpp 8B+) — 1-10s
  Tier 3: Cloud API (frontier model) — 2-30s

Routing signals:
  1. Task type classification (extraction vs reasoning vs coding)
  2. Token budget estimation (output length proxy)
  3. Data sensitivity detection (PII, financial, health)
  4. Latency budget (interactive vs background)
  5. Tool-call requirement (does the prompt need function calling?)
  6. Context window needs (long context → higher tier)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class InferenceTier(IntEnum):
    """Inference capability tiers, ordered by cost/latency."""

    EDGE_RULES = 0  # Pattern matching, cache — sub-millisecond
    LOCAL_LLAMA_CPP = 1  # llama.cpp small model (continuous) — 10-100ms
    LOCAL_SMALL = 2  # llama.cpp 1.5B-7B quantized — 50-500ms
    LOCAL_LARGE = 3  # BitNet/llama.cpp 8B+ — 1-10s
    CLOUD = 4  # Frontier model via API — 2-30s


# Task type patterns — ordered from simplest to most complex
_TASK_PATTERNS: list[tuple[re.Pattern[str], InferenceTier, str]] = [
    # Tier 0: Edge rules can handle these
    (
        re.compile(r"^(hi|hello|hey|greetings|bye|goodbye|thanks)\b", re.I),
        InferenceTier.EDGE_RULES,
        "greeting",
    ),
    (
        re.compile(r"\b(version|what version|status|health)\b", re.I),
        InferenceTier.EDGE_RULES,
        "status_query",
    ),
    (re.compile(r"\b(yes|no|true|false)\b", re.I), InferenceTier.EDGE_RULES, "boolean"),
    # Tier 1: Local small model — classification, extraction, simple Q&A
    (
        re.compile(r"\b(classify|categor|label|tag)\b", re.I),
        InferenceTier.LOCAL_SMALL,
        "classification",
    ),
    (
        re.compile(r"\b(extract|pull out|find the|identify)\b", re.I),
        InferenceTier.LOCAL_SMALL,
        "extraction",
    ),
    (
        re.compile(r"\b(summariz|tl;?dr|brief|condense)\b", re.I),
        InferenceTier.LOCAL_SMALL,
        "summarization",
    ),
    (
        re.compile(r"\b(translat|paraphrase|rewrite|rephrase)\b", re.I),
        InferenceTier.LOCAL_SMALL,
        "reformulation",
    ),
    (
        re.compile(r"\b(format|template|structure)\b", re.I),
        InferenceTier.LOCAL_SMALL,
        "formatting",
    ),
    # Tier 2: Local large model — reasoning, analysis, code generation
    (
        re.compile(r"\b(analyz|evaluat|assess|investigat)\b", re.I),
        InferenceTier.LOCAL_LARGE,
        "analysis",
    ),
    (
        re.compile(r"\b(code|function|implement|debug|refactor)\b", re.I),
        InferenceTier.LOCAL_LARGE,
        "coding",
    ),
    (
        re.compile(r"\b(reason|deduce|infer|conclude)\b", re.I),
        InferenceTier.LOCAL_LARGE,
        "reasoning",
    ),
    (
        re.compile(r"\b(compare|contrast|versus|vs\.?)\b", re.I),
        InferenceTier.LOCAL_LARGE,
        "comparison",
    ),
    (
        re.compile(r"\b(plan|design|architect|strategy)\b", re.I),
        InferenceTier.LOCAL_LARGE,
        "planning",
    ),
    # Tier 3: Cloud — multi-step reasoning, long-form creative, complex tool chains
    (
        re.compile(r"\b(multi.?step|chain|pipeline|workflow)\b", re.I),
        InferenceTier.CLOUD,
        "multi_step",
    ),
    (
        re.compile(r"\b(creative|story|poem|novel|screenplay)\b", re.I),
        InferenceTier.CLOUD,
        "creative",
    ),
    (
        re.compile(r"\b(research|literature|survey|systematic)\b", re.I),
        InferenceTier.CLOUD,
        "research",
    ),
    (
        re.compile(r"\b(legal|medical|financial advis|compliance)\b", re.I),
        InferenceTier.CLOUD,
        "expert_domain",
    ),
]

# Sensitivity patterns — override routing to keep data local
_SENSITIVITY_PATTERNS = [
    re.compile(r"\b(ssn|social security|passport|national id)\b", re.I),
    re.compile(r"\b(credit card|bank account|routing number|iban)\b", re.I),
    re.compile(r"\b(diagnosis|prescription|medical record|patient)\b", re.I),
    re.compile(r"\b(password|api key|secret|token|credential)\b", re.I),
    re.compile(r"\b(confidential|proprietary|internal only|classified)\b", re.I),
]

# Tool-call indicators — prompts that likely need function calling
_TOOL_CALL_PATTERNS = [
    re.compile(
        r"\b(call|invoke|execute|run)\s+(the\s+)?(tool|function|api|command)\b", re.I
    ),
    re.compile(
        r"\b(search|find|lookup|query)\s+(the\s+)?(memor\w*|database|knowledge)\b", re.I
    ),
    re.compile(r"\b(use|with|via)\s+(tool|function|mcp)\b", re.I),
]

# Multi-turn indicators
_MULTI_TURN_PATTERNS = [
    re.compile(r"\b(then|after that|next|subsequently|finally)\b", re.I),
    re.compile(r"\b(step \d|phase \d|stage \d)\b", re.I),
    re.compile(r"\b(first.*second.*third|1\..*2\..*3\.)\b", re.I | re.DOTALL),
]


@dataclass
class ComplexityAssessment:
    """Result of complexity classification."""

    tier: InferenceTier
    task_type: str
    confidence: float
    estimated_output_tokens: int
    is_sensitive: bool
    needs_tool_calls: bool
    is_multi_turn: bool
    signals: dict[str, Any] = field(default_factory=dict)

    @property
    def requires_cloud(self) -> bool:
        """Whether this assessment mandates cloud tier."""
        return self.tier == InferenceTier.CLOUD and not self.is_sensitive

    @property
    def max_local_tier(self) -> InferenceTier:
        """Maximum tier allowed if cloud is unavailable."""
        if self.is_sensitive:
            return InferenceTier.LOCAL_LARGE
        return self.tier


class ComplexityClassifier:
    """Lightweight prompt complexity classifier for inference routing.

    Uses pattern matching and heuristics — no model inference needed.
    Runs in <100µs, making it suitable for the routing hot path.
    """

    def __init__(
        self,
        default_tier: InferenceTier = InferenceTier.LOCAL_SMALL,
        sensitivity_override: bool = True,
        confidence_threshold: float = 0.85,
    ) -> None:
        self._default_tier = default_tier
        self._sensitivity_override = sensitivity_override
        self._confidence_threshold = confidence_threshold

    def classify(
        self,
        prompt: str,
        max_output_tokens: int | None = None,
        latency_budget_ms: float | None = None,
        is_background: bool = False,
    ) -> ComplexityAssessment:
        """Classify a prompt to determine the appropriate inference tier.

        Args:
            prompt: The user prompt to classify.
            max_output_tokens: Expected output length (if known).
            latency_budget_ms: Maximum acceptable latency (if known).
            is_background: Whether this is a background task (not user-facing).

        Returns:
            ComplexityAssessment with routing recommendation.
        """
        signals: dict[str, Any] = {}

        # 1. Task type classification via pattern matching
        task_type = "unknown"
        best_tier = self._default_tier
        best_confidence = 0.0

        for pattern, tier, label in _TASK_PATTERNS:
            match = pattern.search(prompt)
            if match:
                # Earlier patterns have priority (ordered by simplicity)
                if tier <= best_tier or best_confidence == 0.0:
                    task_type = label
                    best_tier = tier
                    best_confidence = 0.9 if tier == InferenceTier.EDGE_RULES else 0.75
                    break  # First match wins (patterns are ordered)

        if best_confidence == 0.0:
            # No pattern matched — estimate by length and structure
            word_count = len(prompt.split())
            if word_count < 10:
                best_tier = InferenceTier.LOCAL_SMALL
                best_confidence = 0.5
                task_type = "short_query"
            elif word_count < 50:
                best_tier = InferenceTier.LOCAL_SMALL
                best_confidence = 0.4
                task_type = "medium_query"
            else:
                best_tier = InferenceTier.LOCAL_LARGE
                best_confidence = 0.4
                task_type = "long_query"

        signals["task_type"] = task_type
        signals["pattern_confidence"] = best_confidence

        # 2. Token budget estimation
        if max_output_tokens is not None:
            est_tokens = max_output_tokens
        else:
            # Heuristic: output ~ 1.5x input for generative tasks, ~0.3x for extraction
            word_count = len(prompt.split())
            if task_type in ("extraction", "classification", "boolean"):
                est_tokens = max(50, int(word_count * 0.3))
            elif task_type in ("summarization", "reformulation"):
                est_tokens = max(100, int(word_count * 0.5))
            elif task_type in ("creative", "research", "multi_step"):
                est_tokens = max(500, int(word_count * 2.0))
            else:
                est_tokens = max(128, int(word_count * 1.0))

        signals["estimated_output_tokens"] = est_tokens

        # Token budget escalation: >512 tokens → prefer higher tier
        if est_tokens > 2048 and best_tier < InferenceTier.CLOUD:
            best_tier = InferenceTier.CLOUD
            signals["escalation_reason"] = "high_token_budget"
        elif est_tokens > 512 and best_tier < InferenceTier.LOCAL_LARGE:
            best_tier = InferenceTier.LOCAL_LARGE
            signals["escalation_reason"] = "moderate_token_budget"

        # 3. Data sensitivity detection
        is_sensitive = any(p.search(prompt) for p in _SENSITIVITY_PATTERNS)
        signals["is_sensitive"] = is_sensitive

        if is_sensitive and self._sensitivity_override:
            # Sensitive data never goes to cloud unless explicitly requested
            if best_tier > InferenceTier.LOCAL_LARGE:
                best_tier = InferenceTier.LOCAL_LARGE
                signals["sensitivity_override"] = True

        # 4. Tool-call requirement detection
        needs_tool_calls = any(p.search(prompt) for p in _TOOL_CALL_PATTERNS)
        signals["needs_tool_calls"] = needs_tool_calls

        if needs_tool_calls and best_tier < InferenceTier.LOCAL_LARGE:
            # Tool-calling requires a model capable of function calling
            best_tier = InferenceTier.LOCAL_LARGE
            signals["tool_call_escalation"] = True

        # 5. Multi-turn detection
        is_multi_turn = any(p.search(prompt) for p in _MULTI_TURN_PATTERNS)
        signals["is_multi_turn"] = is_multi_turn

        if is_multi_turn and best_tier < InferenceTier.LOCAL_LARGE:
            best_tier = InferenceTier.LOCAL_LARGE
            signals["multi_turn_escalation"] = True

        # 6. Latency budget awareness
        if latency_budget_ms is not None:
            if latency_budget_ms < 100 and best_tier > InferenceTier.EDGE_RULES:
                best_tier = InferenceTier.EDGE_RULES
                signals["latency_budget_override"] = True
            elif latency_budget_ms < 500 and best_tier > InferenceTier.LOCAL_SMALL:
                best_tier = InferenceTier.LOCAL_SMALL
                signals["latency_budget_override"] = True

        # Background tasks can use higher quality (latency not critical)
        if is_background and best_tier < InferenceTier.LOCAL_LARGE:
            signals["background_quality_boost"] = True
            # Don't force escalation, but allow it

        return ComplexityAssessment(
            tier=best_tier,
            task_type=task_type,
            confidence=best_confidence,
            estimated_output_tokens=est_tokens,
            is_sensitive=is_sensitive,
            needs_tool_calls=needs_tool_calls,
            is_multi_turn=is_multi_turn,
            signals=signals,
        )


# Singleton
_classifier: ComplexityClassifier | None = None


def get_classifier() -> ComplexityClassifier:
    """Get singleton complexity classifier."""
    global _classifier
    if _classifier is None:
        _classifier = ComplexityClassifier()
    return _classifier


def classify_prompt(
    prompt: str,
    max_output_tokens: int | None = None,
    latency_budget_ms: float | None = None,
    is_background: bool = False,
) -> ComplexityAssessment:
    """Classify a prompt for inference routing."""
    return get_classifier().classify(
        prompt,
        max_output_tokens=max_output_tokens,
        latency_budget_ms=latency_budget_ms,
        is_background=is_background,
    )
