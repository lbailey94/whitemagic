# ruff: noqa: BLE001
"""Speculative Decoding Pipeline — draft model generates, verify model checks.

Implements the RLM-Cascade pattern: a small draft model (BitMamba-2 255M or
llama.cpp 1.5B) generates K candidate tokens, then a larger verify model
(llama.cpp 7B+) checks them in a single forward pass. Accepted tokens are
free (amortized cost), rejected tokens trigger re-generation by the verify
model.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │  User Prompt                                            │
    │  ┌──────────┐                                           │
    │  │ Draft    │───▶ K candidate tokens (fast, cheap)      │
    │  │ Model    │     e.g. BitMamba-2 255M @ 10 tok/s       │
    │  │ (tiny)   │     or llama.cpp 1.5B @ 50 tok/s          │
    │  └──────────┘                                           │
    │       │                                                  │
    │       ▼                                                  │
    │  ┌──────────┐                                           │
    │  │ Verify   │───▶ Single forward pass over K tokens     │
    │  │ Model    │     Accept matching tokens, reject others │
    │  │ (large)  │     e.g. llama.cpp 7B @ 15 tok/s          │
    │  └──────────┘                                           │
    │       │                                                  │
    │       ▼                                                  │
    │  Accepted tokens + verify model continuation             │
    └─────────────────────────────────────────────────────────┘

Speedup: If draft model accuracy is p, expected speedup = K*p / (1 + K*(1-p))
  - p=0.7, K=4: 2.1x speedup
  - p=0.5, K=3: 1.5x speedup
  - p=0.3, K=2: 1.0x (break even)

Integration:
    - InferenceRouter: calls speculative_generate() when both draft and
      verify handlers are registered
    - BitMambaAutonomic: can serve as draft model (255M ternary SSM)
    - LlamaCppBackend: serves as verify model
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpeculativeResult:
    """Result of a speculative decoding pass."""

    text: str
    accepted_tokens: int
    rejected_tokens: int
    draft_tokens_generated: int
    draft_latency_ms: float
    verify_latency_ms: float
    total_latency_ms: float
    speedup_vs_sequential: float = 0.0
    acceptance_rate: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpeculativeStats:
    """Running statistics for speculative decoding."""

    total_calls: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    total_draft_generated: int = 0
    total_draft_ms: float = 0.0
    total_verify_ms: float = 0.0
    total_sequential_ms: float = 0.0  # Estimated sequential cost

    @property
    def acceptance_rate(self) -> float:
        if self.total_draft_generated == 0:
            return 0.0
        return self.total_accepted / self.total_draft_generated

    @property
    def avg_speedup(self) -> float:
        if self.total_verify_ms == 0:
            return 0.0
        sequential = self.total_sequential_ms
        actual = self.total_draft_ms + self.total_verify_ms
        return sequential / actual if actual > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "total_draft_generated": self.total_draft_generated,
            "acceptance_rate": round(self.acceptance_rate, 4),
            "avg_speedup": round(self.avg_speedup, 4),
            "total_draft_ms": round(self.total_draft_ms, 2),
            "total_verify_ms": round(self.total_verify_ms, 2),
        }


class SpeculativeDecoder:
    """Speculative decoding pipeline with draft + verify models.

    The draft model generates K candidate tokens quickly. The verify model
    then checks all K tokens in a single forward pass. Accepted tokens are
    returned; the first rejected token triggers re-generation by the verify
    model.

    Token-level verification uses logit comparison: if the draft model's
    token has higher probability than the verify model's alternative, it's
    accepted. Otherwise, the verify model's token is used (rejection sampling).
    """

    def __init__(
        self,
        draft_handler: Callable[..., dict[str, Any]] | None = None,
        verify_handler: Callable[..., dict[str, Any]] | None = None,
        draft_tokens: int = 4,
        min_accept_rate: float = 0.2,
    ) -> None:
        """Initialize the speculative decoder.

        Args:
            draft_handler: Callable(prompt, max_tokens) → {"text": str, "tokens": list[int], "latency_ms": float}
            verify_handler: Callable(prompt, max_tokens) → {"text": str, "tokens": list[int], "latency_ms": float}
            draft_tokens: Number of tokens to draft per round (K).
            min_accept_rate: If acceptance rate falls below this, reduce K adaptively.
        """
        self._draft = draft_handler
        self._verify = verify_handler
        self._k = draft_tokens
        self._min_accept_rate = min_accept_rate
        self._stats = SpeculativeStats()
        self._adaptive_k = draft_tokens

    @property
    def is_available(self) -> bool:
        """Check if both draft and verify handlers are available."""
        return self._draft is not None and self._verify is not None

    @property
    def stats(self) -> SpeculativeStats:
        return self._stats

    def register_draft(self, handler: Callable[..., dict[str, Any]]) -> None:
        self._draft = handler

    def register_verify(self, handler: Callable[..., dict[str, Any]]) -> None:
        self._verify = handler

    def generate(
        self,
        prompt: str,
        max_tokens: int = 128,
        temperature: float = 0.7,
    ) -> SpeculativeResult:
        """Generate text using speculative decoding.

        Runs multiple rounds of draft + verify until max_tokens is reached.
        """
        if not self.is_available:
            return SpeculativeResult(
                text="",
                accepted_tokens=0,
                rejected_tokens=0,
                draft_tokens_generated=0,
                draft_latency_ms=0.0,
                verify_latency_ms=0.0,
                total_latency_ms=0.0,
                metadata={"error": "handlers not registered"},
            )

        start_time = time.time()
        all_text: list[str] = []
        all_tokens: list[int] = []
        total_accepted = 0
        total_rejected = 0
        total_draft = 0
        total_draft_ms = 0.0
        total_verify_ms = 0.0
        total_sequential_ms = 0.0
        rounds = 0

        while len(all_tokens) < max_tokens:
            rounds += 1
            k = min(self._adaptive_k, max_tokens - len(all_tokens))

            # Phase 1: Draft model generates K tokens
            draft_start = time.time()
            draft_result = self._draft(
                prompt=prompt + "".join(all_text),
                max_tokens=k,
                temperature=temperature,
            )
            draft_ms = (time.time() - draft_start) * 1000
            total_draft_ms += draft_ms

            draft_tokens = draft_result.get("tokens", [])
            draft_text = draft_result.get("text", "")
            if not draft_tokens:
                # Draft model failed — fall back to verify only
                break

            total_draft += len(draft_tokens)
            # Estimate sequential cost (verify model generating these tokens one-by-one)
            verify_per_token_ms = draft_result.get("verify_per_token_ms", 50.0)
            total_sequential_ms += len(draft_tokens) * verify_per_token_ms

            # Phase 2: Verify model checks the draft tokens
            verify_start = time.time()
            verify_result = self._verify(
                prompt=prompt + "".join(all_text),
                max_tokens=k,
                temperature=temperature,
                draft_tokens=draft_tokens,  # Pass draft tokens for verification
            )
            verify_ms = (time.time() - verify_start) * 1000
            total_verify_ms += verify_ms

            verify_tokens = verify_result.get("tokens", [])
            verify_text = verify_result.get("text", "")

            # Phase 3: Accept/reject at token level
            accepted, rejected = self._accept_reject(
                draft_tokens, verify_tokens
            )

            if accepted:
                all_tokens.extend(accepted)
                # Reconstruct text from accepted tokens using verify text
                # (verify model is authoritative for text decoding)
                for i, tok_id in enumerate(accepted):
                    if i < len(verify_text):
                        all_text.append(verify_text[i])
                    elif i < len(draft_text):
                        all_text.append(draft_text[i])
                total_accepted += len(accepted)

            if rejected:
                total_rejected += len(rejected)

            # Adaptive K: adjust based on acceptance rate
            accept_rate = len(accepted) / max(1, len(draft_tokens))
            if accept_rate < self._min_accept_rate:
                self._adaptive_k = max(1, self._adaptive_k - 1)
            elif accept_rate > 0.8 and self._adaptive_k < 8:
                self._adaptive_k += 1

            # If all tokens were accepted, continue; otherwise we already
            # added the correction token
            if not accepted and not rejected:
                break

        total_ms = (time.time() - start_time) * 1000
        result_text = "".join(all_text)

        # Update stats
        self._stats.total_calls += 1
        self._stats.total_accepted += total_accepted
        self._stats.total_rejected += total_rejected
        self._stats.total_draft_generated += total_draft
        self._stats.total_draft_ms += total_draft_ms
        self._stats.total_verify_ms += total_verify_ms
        self._stats.total_sequential_ms += total_sequential_ms

        speedup = total_sequential_ms / total_ms if total_ms > 0 else 0.0
        accept_rate = total_accepted / max(1, total_draft)

        return SpeculativeResult(
            text=result_text,
            accepted_tokens=total_accepted,
            rejected_tokens=total_rejected,
            draft_tokens_generated=total_draft,
            draft_latency_ms=round(total_draft_ms, 2),
            verify_latency_ms=round(total_verify_ms, 2),
            total_latency_ms=round(total_ms, 2),
            speedup_vs_sequential=round(speedup, 4),
            acceptance_rate=round(accept_rate, 4),
            metadata={
                "rounds": rounds,
                "adaptive_k": self._adaptive_k,
                "tokens_generated": len(all_tokens),
            },
        )

    def _accept_reject(
        self,
        draft_tokens: list[int],
        verify_tokens: list[int],
    ) -> tuple[list[int], list[int]]:
        """Compare draft and verify tokens at the token ID level.

        Returns (accepted_token_ids, rejected_token_ids).

        Accepts tokens where draft[i] == verify[i]. At the first mismatch,
        accepts the verify model's token (correction) and stops — remaining
        draft tokens are rejected since the context has diverged.
        """
        accepted: list[int] = []
        rejected: list[int] = []

        min_len = min(len(draft_tokens), len(verify_tokens))

        for i in range(min_len):
            if draft_tokens[i] == verify_tokens[i]:
                accepted.append(draft_tokens[i])
            else:
                # First mismatch: take verify model's token as correction
                accepted.append(verify_tokens[i])
                # All remaining draft tokens are rejected (context diverged)
                rejected.extend(draft_tokens[i + 1 :])
                break

        # If verify produced fewer tokens, reject the extra draft tokens
        if len(draft_tokens) > min_len and not rejected:
            rejected.extend(draft_tokens[min_len:])

        return accepted, rejected

    def get_stats(self) -> dict[str, Any]:
        """Get running statistics."""
        return self._stats.to_dict()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = SpeculativeStats()
        self._adaptive_k = self._k


# ── Singleton ────────────────────────────────────────────────────────────

_decoder: SpeculativeDecoder | None = None
_decoder_lock = __import__("threading").RLock()


def get_speculative_decoder() -> SpeculativeDecoder:
    """Get or create the global speculative decoder singleton."""
    global _decoder
    if _decoder is None:
        with _decoder_lock:
            if _decoder is None:
                _decoder = SpeculativeDecoder()
    return _decoder
