# ruff: noqa: BLE001
"""Inference Router — complexity-aware routing across edge/local/cloud tiers.

Inspired by Sakana Fugu's Conductor (ICLR 2026) and production hybrid
cloud-edge routing patterns. Routes each inference request to the
cheapest, fastest, most appropriate tier that can handle it.

Architecture:
    Prompt → ComplexityClassifier → Route Decision
                                        ├─ Tier 0: Edge rules (cache + Rust PatternEngine)
                                        ├─ Tier 1: Local small model (Ollama 1.5B-7B)
                                        ├─ Tier 2: Local large model (BitNet/Ollama 8B+)
                                        └─ Tier 3: Cloud API (frontier model)

    With confidence cascading: if Tier N output confidence < threshold,
    escalate to Tier N+1. Sensitive data never routes to cloud.

Integration points:
    - EdgeInference (edge/inference.py): Tier 0 handler
    - LocalLLM (inference/local_llm.py): Tier 1-2 handler
    - Ollama handlers (tools/handlers/ollama.py): Tier 1-2 MCP interface
    - BitNet bridge (inference/bitnet_bridge.py): Tier 2 handler
    - Cloud API: Tier 3 (user-provided API key)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from whitemagic.inference.complexity import (
    ComplexityAssessment,
    ComplexityClassifier,
    InferenceTier,
)
from whitemagic.inference.routing_metrics import RoutingMetrics, get_routing_metrics

logger = logging.getLogger(__name__)


class TokenBudgetTracker:
    """Tracks token budget across routing calls in a session.

    Maintains a rolling window of token usage and provides feedback
    to the router when budget is running low, enabling tier downgrades
    to conserve remaining tokens.

    The tracker uses an exponential moving average of token usage per
    request to predict whether the next request will fit within budget.
    """

    def __init__(
        self,
        total_budget: int = 100_000,
        warning_threshold: float = 0.7,
        critical_threshold: float = 0.9,
    ) -> None:
        self._total_budget = total_budget
        self._used_tokens = 0
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._request_count = 0
        self._ema_usage = 0.0  # Exponential moving average of tokens per request
        self._alpha = 0.3  # EMA smoothing factor

    @property
    def remaining(self) -> int:
        return max(0, self._total_budget - self._used_tokens)

    @property
    def usage_ratio(self) -> float:
        if self._total_budget <= 0:
            return 1.0
        return self._used_tokens / self._total_budget

    @property
    def is_warning(self) -> bool:
        return self.usage_ratio >= self._warning_threshold

    @property
    def is_critical(self) -> bool:
        return self.usage_ratio >= self._critical_threshold

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record token usage from a completed request."""
        total = input_tokens + output_tokens
        self._used_tokens += total
        self._request_count += 1
        # Update EMA
        self._ema_usage = self._alpha * total + (1 - self._alpha) * self._ema_usage
        # Bridge to consciousness token economy
        try:
            from whitemagic.core.consciousness.token_economy import get_token_tracker

            get_token_tracker().record_api_call(
                f"inference:{self._request_count}", total
            )
        except (ImportError, RuntimeError, AttributeError):
            pass

    def recommend_downgrade(
        self, requested_tier: InferenceTier
    ) -> InferenceTier | None:
        """Recommend a lower tier if token budget is running low.

        Returns the downgraded tier if a downgrade is recommended,
        or None if the requested tier is fine.
        """
        if not self.is_warning or requested_tier == InferenceTier.EDGE_RULES:
            return None

        # Critical: downgrade to cheapest possible
        if self.is_critical:
            if requested_tier > InferenceTier.EDGE_RULES:
                return InferenceTier.EDGE_RULES
            return None

        # Warning: downgrade by one tier
        if self.is_warning and requested_tier > InferenceTier.EDGE_RULES:
            return InferenceTier(int(requested_tier) - 1)

        return None

    def reset(self, new_budget: int | None = None) -> None:
        """Reset the tracker, optionally with a new budget."""
        self._used_tokens = 0
        self._request_count = 0
        self._ema_usage = 0.0
        if new_budget is not None:
            self._total_budget = new_budget

    def summary(self) -> dict[str, Any]:
        return {
            "total_budget": self._total_budget,
            "used_tokens": self._used_tokens,
            "remaining": self.remaining,
            "usage_ratio": round(self.usage_ratio, 3),
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "request_count": self._request_count,
            "avg_tokens_per_request": round(self._ema_usage, 1)
            if self._request_count > 0
            else 0,
        }


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    tier: InferenceTier
    assessment: ComplexityAssessment
    reason: str
    latency_budget_ms: float | None = None


@dataclass
class InferenceResponse:
    """Response from routed inference."""

    answer: str
    confidence: float
    tier: InferenceTier
    latency_ms: float
    escalated: bool = False
    escalation_chain: list[InferenceTier] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class InferenceRouter:
    """Complexity-aware inference router with confidence cascading.

    Routes prompts to the appropriate inference tier based on complexity
    classification, then cascades to higher tiers if confidence is low.

    Usage:
        router = InferenceRouter()
        response = router.route("What is the capital of France?")
        print(response.answer, response.tier, response.confidence)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.85,
        max_escalations: int = 2,
        cloud_available: bool = True,
        token_budget: int | None = None,
    ) -> None:
        self._classifier = ComplexityClassifier()
        self._metrics = get_routing_metrics()
        self._confidence_threshold = confidence_threshold
        self._max_escalations = max_escalations
        self._cloud_available = cloud_available
        self._budget_tracker = TokenBudgetTracker(total_budget=token_budget or 100_000)

        # Tier handlers — lazily initialized
        self._edge_handler: Callable[..., dict[str, Any]] | None = None
        self._llama_cpp_handler: Callable[..., dict[str, Any]] | None = None
        self._local_small_handler: Callable[..., dict[str, Any]] | None = None
        self._local_large_handler: Callable[..., dict[str, Any]] | None = None
        self._cloud_handler: Callable[..., dict[str, Any]] | None = None

    def register_handler(
        self,
        tier: InferenceTier,
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        """Register a handler for a specific tier.

        Args:
            tier: The inference tier this handler serves.
            handler: Callable that accepts (prompt, **kwargs) and returns
                     {"answer": str, "confidence": float, "metadata": dict}
        """
        if tier == InferenceTier.EDGE_RULES:
            self._edge_handler = handler
        elif tier == InferenceTier.LOCAL_LLAMA_CPP:
            self._llama_cpp_handler = handler
        elif tier == InferenceTier.LOCAL_SMALL:
            self._local_small_handler = handler
        elif tier == InferenceTier.LOCAL_LARGE:
            self._local_large_handler = handler
        elif tier == InferenceTier.CLOUD:
            self._cloud_handler = handler

    def route(
        self,
        prompt: str,
        max_output_tokens: int | None = None,
        latency_budget_ms: float | None = None,
        is_background: bool = False,
        force_tier: InferenceTier | None = None,
    ) -> InferenceResponse:
        """Route a prompt to the appropriate inference tier.

        Args:
            prompt: The user prompt.
            max_output_tokens: Expected output length (if known).
            latency_budget_ms: Maximum acceptable latency.
            is_background: Whether this is a background task.
            force_tier: Override routing and force a specific tier.

        Returns:
            InferenceResponse with the answer and routing metadata.
        """
        start_time = time.time()

        if force_tier is not None:
            assessment = self._classifier.classify(
                prompt, max_output_tokens, latency_budget_ms, is_background
            )
            tier = force_tier
            reason = "forced"
        else:
            assessment = self._classifier.classify(
                prompt, max_output_tokens, latency_budget_ms, is_background
            )
            tier = assessment.tier
            reason = assessment.task_type

        budget_downgrade = self._budget_tracker.recommend_downgrade(tier)
        if budget_downgrade is not None:
            original_tier = tier
            tier = budget_downgrade
            reason = f"budget_downgrade_{self._budget_tracker.usage_ratio:.0%}"
            assessment.signals["budget_downgrade"] = {
                "from": original_tier.name,
                "to": tier.name,
                "usage_ratio": round(self._budget_tracker.usage_ratio, 3),
                "remaining": self._budget_tracker.remaining,
            }
            logger.debug(
                "Token budget feedback: %s → %s (usage=%.1f%%, remaining=%d)",
                original_tier.name,
                tier.name,
                self._budget_tracker.usage_ratio * 100,
                self._budget_tracker.remaining,
            )

        self_model_upgrade = self._check_self_model_forecast(tier)
        if self_model_upgrade is not None:
            original_tier = tier
            tier = self_model_upgrade
            reason = f"self_model_upgrade_{original_tier.name}_to_{tier.name}"
            assessment.signals["self_model_upgrade"] = {
                "from": original_tier.name,
                "to": tier.name,
                "reason": "predicted_high_error_rate",
            }
            logger.debug(
                "Self-model forecast upgrade: %s → %s (predicted error rate critical)",
                original_tier.name,
                tier.name,
            )

        if tier == InferenceTier.CLOUD and not self._cloud_available:
            if assessment.is_sensitive:
                tier = InferenceTier.LOCAL_LARGE
                reason = "cloud_unavailable_sensitive"
            else:
                tier = InferenceTier.LOCAL_LARGE
                reason = "cloud_unavailable_fallback"

        ghrr_metadata: dict[str, Any] = {}
        if tier in (InferenceTier.LOCAL_SMALL, InferenceTier.LOCAL_LARGE):
            try:
                from whitemagic.core.memory.ghrr_attention import get_ghrr_attention

                ghrr = get_ghrr_attention()
                context_items: list[dict[str, Any]] = []
                try:
                    from whitemagic.core.intelligence.core_access import get_core_access

                    cal = get_core_access()
                    # Use hybrid recall to get relevant context
                    results = cal.hybrid_recall(query=prompt, k=5)
                    for r in results:
                        mem = r.get("memory") or r
                        if isinstance(mem, dict):
                            context_items.append(
                                {
                                    "content": str(mem.get("content", ""))[:500],
                                    "source": "memory",
                                }
                            )
                except Exception:
                    pass  # No context available — GHRR will skip

                if context_items:
                    ghrr_result = ghrr.preprocess_prompt(prompt, context_items)
                    prompt = ghrr_result.get("prompt", prompt)
                    ghrr_metadata = {
                        "method": ghrr_result.get("method"),
                        "compression_ratio": ghrr_result.get("compression_ratio"),
                        "items_processed": ghrr_result.get("items_processed", 0),
                    }
            except (ImportError, ModuleNotFoundError):
                pass  # GHRR not available — skip pre-processing

        escalation_chain: list[InferenceTier] = []
        current_tier = tier
        escalations = 0

        while current_tier <= InferenceTier.CLOUD:
            handler = self._get_handler(current_tier)
            if handler is None:
                # No handler for this tier — escalate
                if current_tier < InferenceTier.CLOUD:
                    escalation_chain.append(current_tier)
                    self._metrics.record_escalation(
                        current_tier, InferenceTier(int(current_tier) + 1), "no_handler"
                    )
                    current_tier = InferenceTier(int(current_tier) + 1)
                    escalations += 1
                    continue
                else:
                    # No cloud handler either — return fallback
                    return InferenceResponse(
                        answer="No inference handler available for any tier.",
                        confidence=0.0,
                        tier=current_tier,
                        latency_ms=(time.time() - start_time) * 1000,
                        escalated=len(escalation_chain) > 0,
                        escalation_chain=escalation_chain,
                        metadata={
                            "reason": "no_handler",
                            "assessment": assessment.signals,
                        },
                    )

            try:
                result = handler(
                    prompt=prompt,
                    max_tokens=max_output_tokens or assessment.estimated_output_tokens,
                )
            except Exception as e:
                logger.error("Tier %s handler failed: %s", current_tier.name, e)
                self._metrics.record_routing(
                    current_tier,
                    (time.time() - start_time) * 1000,
                    0.0,
                    False,
                    "handler_error",
                )
                if (
                    current_tier < InferenceTier.CLOUD
                    and escalations < self._max_escalations
                ):
                    escalation_chain.append(current_tier)
                    self._metrics.record_escalation(
                        current_tier,
                        InferenceTier(int(current_tier) + 1),
                        "handler_error",
                    )
                    current_tier = InferenceTier(int(current_tier) + 1)
                    escalations += 1
                    continue
                return InferenceResponse(
                    answer=f"Error: {e}",
                    confidence=0.0,
                    tier=current_tier,
                    latency_ms=(time.time() - start_time) * 1000,
                    escalated=len(escalation_chain) > 0,
                    escalation_chain=escalation_chain,
                    metadata={"error": str(e), "assessment": assessment.signals},
                )

            latency_ms = (time.time() - start_time) * 1000
            answer = result.get("answer", "")
            confidence = result.get("confidence", 0.0)
            success = confidence > 0.0

            # Record metrics
            self._metrics.record_routing(
                current_tier, latency_ms, confidence, success, reason
            )

            if (
                confidence < self._confidence_threshold
                and current_tier < InferenceTier.CLOUD
                and escalations < self._max_escalations
                and not assessment.is_sensitive  # Don't cascade sensitive data to cloud
            ):
                logger.debug(
                    "Confidence cascade: %s (conf=%.2f) → %s",
                    current_tier.name,
                    confidence,
                    InferenceTier(int(current_tier) + 1).name,
                )
                escalation_chain.append(current_tier)
                next_tier = InferenceTier(int(current_tier) + 1)
                self._metrics.record_escalation(
                    current_tier, next_tier, "low_confidence"
                )
                current_tier = InferenceTier(int(current_tier) + 1)
                escalations += 1
                continue

            # Record token usage for budget tracking
            input_tokens = len(prompt.split()) * 2  # Rough estimate: ~2 tokens/word
            output_tokens = len(answer.split()) * 2 if answer else 0
            self._budget_tracker.record_usage(input_tokens, output_tokens)

            # Success — return response
            return InferenceResponse(
                answer=answer,
                confidence=confidence,
                tier=current_tier,
                latency_ms=latency_ms,
                escalated=len(escalation_chain) > 0,
                escalation_chain=escalation_chain,
                metadata={
                    "assessment": assessment.signals,
                    "task_type": assessment.task_type,
                    "estimated_output_tokens": assessment.estimated_output_tokens,
                    "token_budget": self._budget_tracker.summary(),
                    **ghrr_metadata,
                    **result.get("metadata", {}),
                },
            )

        # Exhausted escalations
        return InferenceResponse(
            answer=answer if "answer" in locals() else "All tiers exhausted.",
            confidence=confidence if "confidence" in locals() else 0.0,
            tier=current_tier,
            latency_ms=(time.time() - start_time) * 1000,
            escalated=True,
            escalation_chain=escalation_chain,
            metadata={"reason": "max_escalations", "assessment": assessment.signals},
        )

    def _get_handler(self, tier: InferenceTier) -> Callable[..., dict[str, Any]] | None:
        """Get the handler for a specific tier."""
        if tier == InferenceTier.EDGE_RULES:
            return self._edge_handler
        elif tier == InferenceTier.LOCAL_LLAMA_CPP:
            return self._llama_cpp_handler
        elif tier == InferenceTier.LOCAL_SMALL:
            return self._local_small_handler
        elif tier == InferenceTier.LOCAL_LARGE:
            return self._local_large_handler
        elif tier == InferenceTier.CLOUD:
            return self._cloud_handler
        return None

    @property
    def metrics(self) -> RoutingMetrics:
        """Access routing metrics for observability."""
        return self._metrics

    @property
    def budget_tracker(self) -> TokenBudgetTracker:
        """Access token budget tracker for budget management."""
        return self._budget_tracker

    def _check_self_model_forecast(
        self, current_tier: InferenceTier
    ) -> InferenceTier | None:
        """Check SelfModel forecasts for error rate trends.

        If the self-model predicts error_rate will breach critical threshold
        within 5 steps, upgrade the tier by 1 for reliability.

        Returns the upgraded tier if upgrade is recommended, or None.
        """
        try:
            from whitemagic.core.intelligence.self_model import get_self_model

            model = get_self_model()
            alerts = model.get_alerts()
            for alert in alerts:
                if alert.metric == "error_rate" and alert.threshold_eta is not None:
                    if alert.threshold_eta <= 5 and current_tier < InferenceTier.CLOUD:
                        return InferenceTier(int(current_tier) + 1)
                    break
        except Exception as e:
            logger.debug("Self-model forecast check skipped: %s", e)
        return None

    @property
    def metrics_summary(self) -> dict[str, Any]:
        """Get a summary of routing metrics."""
        return self._metrics.summary()


# ── Default handlers ──────────────────────────────────────────────────────


def _edge_rules_handler(prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Default Tier 0 handler — uses EdgeInference."""
    try:
        from whitemagic.edge.inference import get_edge_inference

        result = get_edge_inference().infer(prompt)
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "metadata": {
                "method": result.method,
                "from_cache": result.from_cache,
                "tokens_equivalent": result.tokens_equivalent,
            },
        }
    except Exception as e:
        logger.debug("Edge rules handler failed: %s", e)
        return {"answer": "", "confidence": 0.0, "metadata": {"error": str(e)}}


def _local_small_handler(prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Default Tier 1 handler — uses Ollama with a small model."""
    try:
        from whitemagic.inference.local_llm import LocalLLM

        llm = LocalLLM(model="qwen2.5-coder:1.5b")
        if not llm.is_available:
            return {
                "answer": "",
                "confidence": 0.0,
                "metadata": {"error": "ollama_unavailable"},
            }

        max_tokens = kwargs.get("max_tokens", 256)
        answer = llm.complete(prompt, max_tokens=max_tokens, temperature=0.3)
        if answer.startswith("Error"):
            return {"answer": "", "confidence": 0.0, "metadata": {"error": answer}}

        # Small models get moderate confidence — the router will cascade if needed
        return {
            "answer": answer,
            "confidence": 0.75,  # Default for small model — cascading will escalate if needed
            "metadata": {"model": llm.model, "method": "local_llm"},
        }
    except Exception as e:
        logger.debug("Local small handler failed: %s", e)
        return {"answer": "", "confidence": 0.0, "metadata": {"error": str(e)}}


def _local_large_handler(prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Default Tier 2 handler — uses Ollama with a larger model or BitNet."""
    try:
        from whitemagic.inference.local_llm import LocalLLM

        llm = LocalLLM(model="llama3.1:8b")
        if not llm.is_available:
            # Try BitNet as fallback
            try:
                from whitemagic.inference.bitnet_bridge import infer as bitnet_infer

                result = bitnet_infer(prompt, n_predict=kwargs.get("max_tokens", 512))
                if result.get("status") == "success":
                    return {
                        "answer": result.get("response", ""),
                        "confidence": 0.85,
                        "metadata": {
                            "method": "bitnet",
                            "model": result.get("model", "bitnet"),
                        },
                    }
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
            return {
                "answer": "",
                "confidence": 0.0,
                "metadata": {"error": "no_local_large"},
            }

        max_tokens = kwargs.get("max_tokens", 512)
        answer = llm.complete(prompt, max_tokens=max_tokens, temperature=0.5)
        if answer.startswith("Error"):
            return {"answer": "", "confidence": 0.0, "metadata": {"error": answer}}

        return {
            "answer": answer,
            "confidence": 0.85,
            "metadata": {"model": llm.model, "method": "local_llm"},
        }
    except Exception as e:
        logger.debug("Local large handler failed: %s", e)
        return {"answer": "", "confidence": 0.0, "metadata": {"error": str(e)}}


def _cloud_handler(prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Default Tier 3 handler — placeholder for cloud API.

    Users should register their own cloud handler with the router.
    This default returns a low-confidence response to trigger cascading.
    """
    return {
        "answer": "",
        "confidence": 0.0,
        "metadata": {"error": "no_cloud_handler_registered"},
    }


# Singleton
_router: InferenceRouter | None = None


def _llama_cpp_handler(prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Default Tier 1 handler — uses llama.cpp backend (continuous background model)."""
    try:
        from whitemagic.inference.llama_cpp import get_llama_cpp_backend

        backend = get_llama_cpp_backend()
        if not backend.is_available:
            return {
                "answer": "",
                "confidence": 0.0,
                "metadata": {"error": "llama_cpp_unavailable"},
            }

        max_tokens = kwargs.get("max_tokens", 128)
        answer = backend.complete(prompt, max_tokens=max_tokens, temperature=0.3)
        if answer.startswith("Error"):
            return {"answer": "", "confidence": 0.0, "metadata": {"error": answer}}

        return {
            "answer": answer,
            "confidence": 0.7,
            "metadata": {"backend": "llama_cpp", "model": backend._model_path},
        }
    except Exception as e:
        logger.debug("llama.cpp handler failed: %s", e)
        return {"answer": "", "confidence": 0.0, "metadata": {"error": str(e)}}


def get_inference_router() -> InferenceRouter:
    """Get singleton inference router with default handlers."""
    global _router
    if _router is None:
        _router = InferenceRouter()
        _router.register_handler(InferenceTier.EDGE_RULES, _edge_rules_handler)
        _router.register_handler(InferenceTier.LOCAL_LLAMA_CPP, _llama_cpp_handler)
        _router.register_handler(InferenceTier.LOCAL_SMALL, _local_small_handler)
        _router.register_handler(InferenceTier.LOCAL_LARGE, _local_large_handler)
        _router.register_handler(InferenceTier.CLOUD, _cloud_handler)
    return _router


def route_inference(
    prompt: str,
    max_output_tokens: int | None = None,
    latency_budget_ms: float | None = None,
    is_background: bool = False,
    force_tier: InferenceTier | None = None,
) -> InferenceResponse:
    """Route an inference request to the appropriate tier.

    Args:
        prompt: The user prompt.
        max_output_tokens: Expected output length.
        latency_budget_ms: Maximum acceptable latency.
        is_background: Whether this is a background task.
        force_tier: Override routing and force a specific tier.

    Returns:
        InferenceResponse with the answer and routing metadata.
    """
    return get_inference_router().route(
        prompt,
        max_output_tokens=max_output_tokens,
        latency_budget_ms=latency_budget_ms,
        is_background=is_background,
        force_tier=force_tier,
    )
