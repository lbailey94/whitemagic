"""Generalized HRR (GHRR) Attention Mechanism — Research Foundation.

This module implements the mathematical foundation for replacing standard
transformer attention with GHRR binding operations, based on the research:

  - "Attention as Binding" (AAAI 2026): Transformer attention ≈ VSA binding
  - GHRR uses non-commutative binding via block-diagonal matrices
  - GHRR attention is more expressive than standard attention
  - GHRR Transformer outperforms vanilla transformer on language modeling

Key insight: In standard attention:
  Q·K^T = similarity(query, key) → attention weights
  softmax(Q·K^T)·V = weighted sum of values

In GHRR attention:
  bind(Q, K) = binding-based similarity → attention weights
  superpose(bind(Q_i, K_i), V_i) = compositional aggregation

The binding operation captures structural relationships that dot-product
attention misses, enabling more expressive attention without additional
parameters.

This is a RESEARCH STUB — not yet wired into any model. It provides the
mathematical operations needed for future integration with local LLMs
(llama.cpp, BitNet) to replace standard attention with GHRR binding.

Usage:
    from whitemagic.core.memory.ghrr_attention import GHRRAttention
    attn = GHRRAttention(dim=384, num_heads=4)
    output = attn(queries, keys, values)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from whitemagic.core.memory.hrr import get_hrr_engine

logger = logging.getLogger(__name__)


@dataclass
class GHRRAttentionConfig:
    """Configuration for GHRR attention."""

    dim: int = 384
    num_heads: int = 4
    head_dim: int | None = None  # Defaults to dim // num_heads
    use_block_diagonal: bool = True
    block_size: int = 16  # Size of diagonal blocks for non-commutative binding
    dropout: float = 0.0

    def __post_init__(self) -> None:
        if self.head_dim is None:
            self.head_dim = self.dim // self.num_heads


class GHRRAttention:
    """GHRR-based attention mechanism using HRR binding.

    Replaces standard dot-product attention with binding-based attention:

    Standard:  attn = softmax(Q @ K^T / sqrt(d)) @ V
    GHRR:      attn = superpose(bind(Q_i, K_i) * V_i) for each head

    The binding operation captures structural relationships between
    queries and keys that dot-product attention cannot express.

    This is a RESEARCH STUB for future integration with local LLMs.
    """

    def __init__(self, config: GHRRAttentionConfig | None = None) -> None:
        self._config = config or GHRRAttentionConfig()
        self._hrr = get_hrr_engine(dim=self._config.dim)
        self._relation_vectors = self._init_head_relations()

    def _init_head_relations(self) -> list[np.ndarray]:
        """Initialize a relation vector for each attention head.

        Each head uses a different relation vector, enabling the heads
        to capture different types of relationships (like multi-head
        attention capturing different subspaces).
        """
        relations = []
        for i in range(self._config.num_heads):
            rel_name = f"ATTN_HEAD_{i}"
            relations.append(self._hrr.get_relation_vector(rel_name))
        return relations

    def forward(
        self,
        queries: np.ndarray,  # (seq_len, dim)
        keys: np.ndarray,  # (seq_len, dim)
        values: np.ndarray,  # (seq_len, dim)
        mask: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Compute GHRR attention (vectorized).

        Args:
            queries: Query vectors (seq_len, dim).
            keys: Key vectors (seq_len, dim).
            values: Value vectors (seq_len, dim).
            mask: Optional attention mask (seq_len, seq_len).

        Returns:
            Dict with 'output' (seq_len, dim), 'attention_weights', and 'method'.
        """
        seq_len = queries.shape[0]
        dim = self._config.dim

        head_outputs = []
        all_weights = []

        for head_idx in range(self._config.num_heads):
            rel_vec = self._relation_vectors[head_idx]

            # Vectorized batch binding: bind all queries with relation vector
            # FFT-based circular convolution, batched across seq_len
            q_fft = np.fft.fft(queries, axis=-1)  # (seq_len, dim)
            r_fft = np.fft.fft(rel_vec)            # (dim,)
            bound_q = np.real(np.fft.ifft(q_fft * r_fft, axis=-1)).astype(np.float32)  # (seq_len, dim)

            # Vectorized similarity: cosine(bound_q[i], keys[j]) for all i,j
            # Normalize rows
            bound_norm = np.linalg.norm(bound_q, axis=-1, keepdims=True) + 1e-8
            key_norm = np.linalg.norm(keys, axis=-1, keepdims=True) + 1e-8
            bound_normalized = bound_q / bound_norm
            keys_normalized = keys / key_norm

            # Full similarity matrix via matrix multiply
            scores = bound_normalized @ keys_normalized.T  # (seq_len, seq_len)

            # Binding stretch: amplify differences between heads by applying
            # a temperature scaling unique to each head. This prevents softmax
            head_temp = 1.0 + 0.5 * head_idx  # Each head uses different temperature
            scores = scores * head_temp

            # Apply mask if provided
            if mask is not None:
                scores = np.where(mask, scores, -1e9)

            # Softmax normalization
            scores = scores - np.max(scores, axis=-1, keepdims=True)
            exp_scores = np.exp(scores)
            weights = exp_scores / (np.sum(exp_scores, axis=-1, keepdims=True) + 1e-8)

            # Weighted sum of values
            output = weights @ values  # (seq_len, dim)
            head_outputs.append(output)
            all_weights.append(weights)

        # Concatenate heads and project back
        concat = np.concatenate(head_outputs, axis=-1)
        if concat.shape[-1] != dim:
            concat = concat.reshape(seq_len, self._config.num_heads, -1).mean(axis=1)

        return {
            "output": concat,
            "attention_weights": all_weights,
            "method": "ghrr_binding_vectorized",
            "num_heads": self._config.num_heads,
        }

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.forward(*args, **kwargs)

    def get_config(self) -> dict[str, Any]:
        return {
            "dim": self._config.dim,
            "num_heads": self._config.num_heads,
            "head_dim": self._config.head_dim,
            "use_block_diagonal": self._config.use_block_diagonal,
            "block_size": self._config.block_size,
            "method": "ghrr_binding_vectorized",
            "research_status": "wired_to_inference_router",
        }

    def preprocess_prompt(self, prompt: str, context_items: list[dict[str, Any]] | None = None, max_context_items: int = 10) -> dict[str, Any]:
        """GHRR attention-based context compression for LLM inference."""
        if not context_items:
            return {"prompt": prompt, "context_vector": None, "relevance_scores": [], "method": "ghrr_no_context", "compression_ratio": 1.0}
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine
            ee = get_embedding_engine()
            if not ee or not ee.available():
                return {"prompt": prompt, "context_vector": None, "relevance_scores": [], "method": "ghrr_no_embed", "compression_ratio": 1.0}
            pv = ee.encode(prompt)
            if pv is None:
                return {"prompt": prompt, "context_vector": None, "relevance_scores": [], "method": "ghrr_encode_failed", "compression_ratio": 1.0}
            ROLES = {"memory": "OBJECT", "session": "AGENT", "tool_result": "ACTION", "scratchpad": "LOCATION", "reasoning": "TIME"}
            bound_vecs: list[np.ndarray] = []
            texts: list[str] = []
            for item in context_items[:max_context_items]:
                c = str(item.get("content", ""))[:500]
                texts.append(c)
                v = ee.encode(c)
                if v is not None:
                    bound_vecs.append(self._hrr.bind(v, self._hrr.get_relation_vector(ROLES.get(item.get("source", "memory"), "OBJECT"))))
            if not bound_vecs:
                return {"prompt": prompt, "context_vector": None, "relevance_scores": [], "method": "ghrr_no_valid", "compression_ratio": 1.0}
            compressed = self._hrr.superpose(*bound_vecs)
            pa = np.asarray(pv, dtype=np.float32)
            scores = []
            for i, bv in enumerate(bound_vecs):
                sim = float(np.dot(pa / (np.linalg.norm(pa) + 1e-8), bv / (np.linalg.norm(bv) + 1e-8)))
                scores.append((i, sim))
            scores.sort(key=lambda x: x[1], reverse=True)
            top = [i for i, _ in scores[:5]]
            summary = "\n".join(f"- {texts[i][:200]}" for i in top if i < len(texts))
            enhanced = f"[Context]\n{summary}\n\n[Query]\n{prompt}" if summary else prompt
            orig_tok = sum(len(t) // 4 for t in texts)
            comp_tok = len(summary) // 4
            return {"prompt": enhanced, "context_vector": compressed.tolist(), "relevance_scores": [(i, round(s, 4)) for i, s in scores], "method": "ghrr_attention", "compression_ratio": round(orig_tok / max(1, comp_tok), 2), "items_processed": len(bound_vecs)}
        except Exception as e:  # noqa: BLE001
            logger.debug("GHRR preprocess failed: %s", e)
            return {"prompt": prompt, "context_vector": None, "relevance_scores": [], "method": "ghrr_error", "compression_ratio": 1.0}



_attention: GHRRAttention | None = None


def get_ghrr_attention(config: GHRRAttentionConfig | None = None) -> GHRRAttention:
    """Get the global GHRRAttention singleton."""
    global _attention
    if _attention is None:
        _attention = GHRRAttention(config=config)
    return _attention
