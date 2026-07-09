# ruff: noqa: BLE001
"""Dharma 4-Tier Escalation Pipeline
====================================

Progressive evaluation model: policy → heuristic → LLM → human.

When the policy tier (declarative rules) returns an ambiguous score
(between 0.3 and 0.7), the pipeline escalates to progressively deeper
evaluation methods.  Each tier can either resolve the decision (return
a score outside the ambiguous band) or defer to the next tier.

Tier 1 — Policy:     Declarative rule matching (existing rules engine)
Tier 2 — Heuristic:  Embedding similarity to known-risky action patterns
Tier 3 — LLM:        llama.cpp-based natural language safety assessment
Tier 4 — Human:      Escalation to a human review queue (logged, pending)

Design principles:
  - Each tier is optional and fails gracefully (no llama-server → skip LLM tier)
  - The pipeline never blocks indefinitely — human tier returns PENDING
  - All tier evaluations are logged to the karmic trace
  - The pipeline is thread-safe
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# Score band that triggers escalation
AMBIGUOUS_LOW = 0.3
AMBIGUOUS_HIGH = 0.7


class EvaluationTier(StrEnum):
    """Progressive evaluation tiers."""

    POLICY = "policy"
    HEURISTIC = "heuristic"
    LLM = "llm"
    HUMAN = "human"


class EscalationAction(StrEnum):
    """What the pipeline decided to do."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    PENDING = "pending"  # Awaiting human review


@dataclass
class TierResult:
    """Result from a single tier evaluation."""

    tier: EvaluationTier
    score: float
    action: EscalationAction
    reasoning: str
    escalated: bool = False  # True if deferred to next tier
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationDecision:
    """Final decision from the 4-tier pipeline."""

    action: EscalationAction
    score: float
    tiers: list[TierResult]
    final_tier: EvaluationTier
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    review_id: str | None = None  # Set when escalated to human

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "score": self.score,
            "final_tier": self.final_tier.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "review_id": self.review_id,
            "tiers": [
                {
                    "tier": t.tier.value,
                    "score": t.score,
                    "action": t.action.value,
                    "reasoning": t.reasoning,
                    "escalated": t.escalated,
                }
                for t in self.tiers
            ],
        }


# --- Known-risky action patterns for heuristic tier ---

_RISKY_PATTERNS: list[dict[str, Any]] = [
    {
        "text": "delete all memories without consent",
        "score": 0.05,
        "category": "destructive",
    },
    {
        "text": "exfiltrate user data to external server",
        "score": 0.02,
        "category": "exfiltration",
    },
    {
        "text": "execute arbitrary shell command from user input",
        "score": 0.1,
        "category": "injection",
    },
    {
        "text": "modify system configuration without authorization",
        "score": 0.15,
        "category": "privilege_escalation",
    },
    {
        "text": "send private messages on behalf of user",
        "score": 0.08,
        "category": "impersonation",
    },
    {
        "text": "download and execute remote payload",
        "score": 0.03,
        "category": "malware",
    },
    {
        "text": "access encrypted data without decryption key",
        "score": 0.12,
        "category": "bypass",
    },
    {
        "text": "disable security monitoring and logging",
        "score": 0.06,
        "category": "evasion",
    },
]

_SAFE_PATTERNS: list[dict[str, Any]] = [
    {
        "text": "create a new memory with user consent",
        "score": 0.95,
        "category": "benign_write",
    },
    {
        "text": "search memories for relevant context",
        "score": 0.98,
        "category": "read_only",
    },
    {
        "text": "list available tools and capabilities",
        "score": 0.99,
        "category": "discovery",
    },
    {
        "text": "generate a summary of recent session activity",
        "score": 0.97,
        "category": "synthesis",
    },
    {
        "text": "update memory metadata with user permission",
        "score": 0.92,
        "category": "benign_update",
    },
]


class EscalationPipeline:
    """4-tier progressive evaluation pipeline.

    Thread-safe.  Each tier is independent and can be called in isolation
    or via :meth:`evaluate` which runs the full escalation chain.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._review_queue: list[dict[str, Any]] = []
        self._review_counter = 0
        self._embedding_engine: Any = None
        self._embedding_init = False

    def _get_embedding_engine(self) -> Any:
        """Lazy-load the embedding engine for heuristic similarity."""
        if self._embedding_init:
            return self._embedding_engine
        self._embedding_init = True
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine

            self._embedding_engine = get_embedding_engine()
        except Exception as e:
            logger.debug("Embedding engine unavailable for heuristic tier: %s", e)
            self._embedding_engine = None
        return self._embedding_engine

    def evaluate(
        self,
        action: dict[str, Any],
        policy_decision: Any | None = None,
    ) -> EscalationDecision:
        """Run the full 4-tier escalation pipeline.

        Args:
            action: The action dict to evaluate.
            policy_decision: Pre-computed policy decision (DharmaDecision).
                             If None, the pipeline will run policy tier itself.

        Returns:
            EscalationDecision with full tier trace.
        """
        tiers: list[TierResult] = []

        # --- Tier 1: Policy ---
        tier1 = self._evaluate_policy(action, policy_decision)
        tiers.append(tier1)

        if not tier1.escalated:
            return self._finalize(tiers, tier1)

        # --- Tier 2: Heuristic ---
        tier2 = self._evaluate_heuristic(action)
        tiers.append(tier2)

        if not tier2.escalated:
            return self._finalize(tiers, tier2)

        # --- Tier 3: LLM ---
        tier3 = self._evaluate_llm(action)
        tiers.append(tier3)

        if not tier3.escalated:
            return self._finalize(tiers, tier3)

        # --- Tier 4: Human ---
        tier4 = self._evaluate_human(action, tiers)
        tiers.append(tier4)

        return self._finalize(tiers, tier4)

    def _evaluate_policy(
        self, action: dict[str, Any], precomputed: Any | None
    ) -> TierResult:
        """Tier 1: Policy-based evaluation using declarative rules."""
        if precomputed is not None:
            score = precomputed.score
            reasoning = precomputed.explain
            triggered = precomputed.triggered_rules
        else:
            try:
                from whitemagic.dharma.rules import get_rules_engine

                engine = get_rules_engine()
                decision = engine.evaluate(action)
                score = decision.score
                reasoning = decision.explain
                triggered = decision.triggered_rules
            except Exception as e:
                logger.debug("Policy tier failed: %s", e)
                score = 0.5
                reasoning = f"Policy evaluation error: {e}"
                triggered = []

        escalated = AMBIGUOUS_LOW <= score <= AMBIGUOUS_HIGH
        action_result = self._score_to_action(score)

        return TierResult(
            tier=EvaluationTier.POLICY,
            score=score,
            action=action_result,
            reasoning=reasoning,
            escalated=escalated,
            metadata={"triggered_rules": triggered},
        )

    def _evaluate_heuristic(self, action: dict[str, Any]) -> TierResult:
        """Tier 2: Heuristic evaluation using embedding similarity.

        Compares the action text against known-risky and known-safe patterns.
        Returns a score based on nearest-neighbor similarity.
        """
        action_text = self._action_to_text(action)

        engine = self._get_embedding_engine()
        if engine is None:
            # No embeddings — use lexical fallback
            return self._heuristic_lexical(action_text)

        try:
            action_vec = engine.embed(action_text)
        except Exception as e:
            logger.debug("Heuristic embedding failed: %s", e)
            return self._heuristic_lexical(action_text)

        # Compare against known patterns
        best_risky_score = 1.0  # Default: no risky match
        best_safe_score = 1.0
        best_risky_cat = ""
        best_safe_cat = ""

        for pattern in _RISKY_PATTERNS:
            try:
                pat_vec = engine.embed(pattern["text"])
                sim = self._cosine_sim(action_vec, pat_vec)
                if sim > 0.75:  # High similarity to risky pattern
                    if pattern["score"] < best_risky_score:
                        best_risky_score = pattern["score"]
                        best_risky_cat = pattern["category"]
            except Exception:
                continue

        for pattern in _SAFE_PATTERNS:
            try:
                pat_vec = engine.embed(pattern["text"])
                sim = self._cosine_sim(action_vec, pat_vec)
                if sim > 0.75:
                    if pattern["score"] > best_safe_score:
                        best_safe_score = pattern["score"]
                        best_safe_cat = pattern["category"]
            except Exception:
                continue

        # Blend: if we matched a risky pattern, lower the score
        if best_risky_score < 1.0 and best_safe_score > 0.9:
            # Conflicting signals — stay ambiguous, escalate
            score = 0.5
            reasoning = (
                f"Heuristic: conflicting signals "
                f"(risky={best_risky_cat}, safe={best_safe_cat})"
            )
            escalated = True
        elif best_risky_score < 1.0:
            score = best_risky_score
            reasoning = f"Heuristic: matched risky pattern ({best_risky_cat})"
            escalated = AMBIGUOUS_LOW <= score <= AMBIGUOUS_HIGH
        elif best_safe_score > 0.9:
            score = best_safe_score
            reasoning = f"Heuristic: matched safe pattern ({best_safe_cat})"
            escalated = AMBIGUOUS_LOW <= score <= AMBIGUOUS_HIGH
        else:
            # No strong match — remain ambiguous
            score = 0.5
            reasoning = "Heuristic: no strong pattern match"
            escalated = True

        return TierResult(
            tier=EvaluationTier.HEURISTIC,
            score=score,
            action=self._score_to_action(score),
            reasoning=reasoning,
            escalated=escalated,
            metadata={
                "risky_match": best_risky_cat or None,
                "safe_match": best_safe_cat or None,
            },
        )

    def _heuristic_lexical(self, action_text: str) -> TierResult:
        """Lexical fallback for heuristic tier when embeddings unavailable."""
        text_lower = action_text.lower()

        risky_keywords = [
            "exfiltrate", "exploit", "inject", "bypass", "disable",
            "unauthorized", "escalate privilege", "arbitrary",
        ]
        safe_keywords = [
            "search", "list", "summarize", "create memory", "update memory",
            "read", "query", "help", "guide",
        ]

        risky_hits = sum(1 for kw in risky_keywords if kw in text_lower)
        safe_hits = sum(1 for kw in safe_keywords if kw in text_lower)

        if risky_hits > 0 and safe_hits == 0:
            score = 0.15
            reasoning = f"Heuristic (lexical): {risky_hits} risky keyword(s) matched"
            escalated = False
        elif risky_hits > 0 and safe_hits > 0:
            score = 0.5
            reasoning = (
                f"Heuristic (lexical): conflicting signals "
                f"({risky_hits} risky, {safe_hits} safe)"
            )
            escalated = True
        elif safe_hits > 0:
            score = 0.9
            reasoning = f"Heuristic (lexical): {safe_hits} safe keyword(s) matched"
            escalated = False
        else:
            score = 0.5
            reasoning = "Heuristic (lexical): no keyword matches"
            escalated = True

        return TierResult(
            tier=EvaluationTier.HEURISTIC,
            score=score,
            action=self._score_to_action(score),
            reasoning=reasoning,
            escalated=escalated,
        )

    def _evaluate_llm(self, action: dict[str, Any]) -> TierResult:
        """Tier 3: LLM-based evaluation using llama.cpp.

        Asks a local LLM to assess the action's safety.  Falls back to
        ambiguous (escalate to human) if llama-server is unavailable.
        """
        action_text = self._action_to_text(action)

        # Check if llama-server is available
        try:
            from whitemagic.inference.llama_cpp import get_llama_cpp_backend
            backend = get_llama_cpp_backend()
            if not backend.is_available:
                raise ConnectionError("llama-server not running")
        except Exception as e:
            logger.debug("LLM tier: llama-server unavailable (%s), escalating to human", e)
            return TierResult(
                tier=EvaluationTier.LLM,
                score=0.5,
                action=EscalationAction.PENDING,
                reasoning=f"LLM tier: llama-server unavailable ({type(e).__name__})",
                escalated=True,
                metadata={"llama_available": False},
            )

        # Build the evaluation prompt
        prompt = (
            "You are a safety evaluator. Assess whether the following action is safe.\n"
            "Respond with ONLY a JSON object: {\"score\": 0.0-1.0, \"reasoning\": \"...\"}\n"
            "Score 1.0 = completely safe, 0.0 = extremely dangerous.\n\n"
            f"Action: {action_text}\n\n"
            "Evaluate based on: potential harm, data exposure, unauthorized access, "
            "and whether consent is implied.\n"
        )

        try:
            from whitemagic.inference.grammar_schemas import SAFETY_EVALUATION_SCHEMA

            response_text = backend.complete(
                prompt,
                max_tokens=200,
                temperature=0.1,
                json_schema=SAFETY_EVALUATION_SCHEMA,
            )

            # Parse the LLM's JSON response
            score, reasoning = self._parse_llm_response(response_text)
            escalated = AMBIGUOUS_LOW <= score <= AMBIGUOUS_HIGH

            return TierResult(
                tier=EvaluationTier.LLM,
                score=score,
                action=self._score_to_action(score),
                reasoning=f"LLM (llama-server): {reasoning}",
                escalated=escalated,
                metadata={
                    "llama_available": True,
                    "raw_response": response_text[:500],
                },
            )

        except Exception as e:
            logger.debug("LLM tier evaluation failed: %s", e)
            return TierResult(
                tier=EvaluationTier.LLM,
                score=0.5,
                action=EscalationAction.PENDING,
                reasoning=f"LLM tier: evaluation error ({type(e).__name__})",
                escalated=True,
                metadata={"llama_available": True, "error": str(e)},
            )

    def _evaluate_human(
        self, action: dict[str, Any], prior_tiers: list[TierResult]
    ) -> TierResult:
        """Tier 4: Human review escalation.

        Logs the action to a review queue and returns PENDING.
        The action is not blocked — it's flagged for human review.
        In production, this would notify a human operator.
        """
        with self._lock:
            self._review_counter += 1
            review_id = f"HR-{datetime.now().strftime('%Y%m%d')}-{self._review_counter:04d}"

            review_entry = {
                "review_id": review_id,
                "action": action,
                "prior_tiers": [
                    {
                        "tier": t.tier.value,
                        "score": t.score,
                        "reasoning": t.reasoning,
                    }
                    for t in prior_tiers
                ],
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
            }
            self._review_queue.append(review_entry)

            # Keep queue bounded
            if len(self._review_queue) > 100:
                self._review_queue = self._review_queue[-50:]

        logger.warning(
            "Dharma escalation to HUMAN review: %s for action: %s",
            review_id,
            self._action_to_text(action)[:100],
        )

        return TierResult(
            tier=EvaluationTier.HUMAN,
            score=0.5,
            action=EscalationAction.PENDING,
            reasoning=f"Escalated to human review (ID: {review_id})",
            escalated=False,  # Terminal tier
            metadata={"review_id": review_id},
        )

    def get_review_queue(self) -> list[dict[str, Any]]:
        """Get pending human review items."""
        with self._lock:
            return list(self._review_queue)

    def resolve_review(self, review_id: str, decision: str, score: float) -> bool:
        """Resolve a human review item.

        Args:
            review_id: The review ID to resolve.
            decision: "allow", "warn", or "block".
            score: The human-assigned score (0.0-1.0).

        Returns:
            True if the review was found and resolved.
        """
        with self._lock:
            for item in self._review_queue:
                if item["review_id"] == review_id and item["status"] == "pending":
                    item["status"] = "resolved"
                    item["decision"] = decision
                    item["score"] = score
                    item["resolved_at"] = datetime.now().isoformat()
                    return True
        return False

    # --- Helpers ---

    @staticmethod
    def _action_to_text(action: dict[str, Any]) -> str:
        """Convert an action dict to a text description for evaluation."""
        tool = action.get("tool", "")
        desc = action.get("description", "")
        safety = action.get("safety", "")
        parts = [str(p) for p in [tool, desc, safety] if p]
        return " ".join(parts) or str(action)

    @staticmethod
    def _score_to_action(score: float) -> EscalationAction:
        """Map a score to an escalation action."""
        if score < AMBIGUOUS_LOW:
            return EscalationAction.BLOCK
        if score < AMBIGUOUS_HIGH:
            return EscalationAction.WARN
        return EscalationAction.ALLOW

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(y * y for y in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _parse_llm_response(text: str) -> tuple[float, str]:
        """Parse the LLM's JSON response into (score, reasoning)."""
        # Try to extract JSON from the response
        import re

        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                score = float(data.get("score", 0.5))
                score = max(0.0, min(1.0, score))
                reasoning = str(data.get("reasoning", "No reasoning provided"))
                return score, reasoning
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Fallback: look for score-like patterns
        score_match = re.search(r'score[:\s]+([0-9]*\.?[0-9]+)', text, re.IGNORECASE)
        if score_match:
            try:
                score = max(0.0, min(1.0, float(score_match.group(1))))
                return score, text[:200]
            except ValueError:
                pass

        return 0.5, "Could not parse LLM response"

    def _finalize(
        self, tiers: list[TierResult], final: TierResult
    ) -> EscalationDecision:
        """Build the final EscalationDecision from tier results."""
        review_id = final.metadata.get("review_id")
        return EscalationDecision(
            action=final.action,
            score=final.score,
            tiers=tiers,
            final_tier=final.tier,
            reasoning=final.reasoning,
            review_id=review_id,
        )


# --- Global instance ---

_pipeline: EscalationPipeline | None = None
_pipeline_lock = threading.Lock()


def get_escalation_pipeline() -> EscalationPipeline:
    """Get the global escalation pipeline instance."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = EscalationPipeline()
    return _pipeline
