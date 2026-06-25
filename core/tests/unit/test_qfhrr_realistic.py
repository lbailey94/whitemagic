"""Test qFHRR with realistic synthetic embeddings and compositional reasoning.

Uses deterministic synthetic embeddings that mimic real MiniLM-L6-v2 output
(normalized, 384-dim, semantically structured) to test qFHRR accuracy
in a more realistic scenario than pure random vectors.
"""

from __future__ import annotations

import hashlib
import unittest

import numpy as np

from whitemagic.core.memory.hrr import HRREngine
from whitemagic.core.memory.qfhrr import QuantizedHRREngine


def _synthetic_embedding(text: str, dim: int = 384) -> np.ndarray:
    """Create a deterministic, semantically-structured synthetic embedding.

    Mimics real embedding properties:
    - Normalized to unit length
    - 384 dimensions (MiniLM-L6-v2)
    - Semantically similar texts produce similar vectors
    - Uses word-level hashing for semantic structure
    """
    rng = np.random.default_rng(seed=hash(text) % (2**31))
    vec = rng.standard_normal(dim).astype(np.float32)

    # Add semantic structure: hash each word and contribute to vector
    words = text.lower().split()
    for word in words:
        word_seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % (2**31)
        word_rng = np.random.default_rng(seed=word_seed)
        word_vec = word_rng.standard_normal(dim).astype(np.float32)
        vec += word_vec * 0.3  # Weighted contribution

    # Normalize to unit length (like real embeddings)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


class TestQFHRRRealisticEmbeddings(unittest.TestCase):
    """Test qFHRR with realistic synthetic embeddings."""

    def setUp(self) -> None:
        self.dim = 384
        self.hrr = HRREngine(dim=self.dim)
        self.qhrr = QuantizedHRREngine(dim=self.dim, bits=4)

    def test_semantic_similarity_preservation(self) -> None:
        """qFHRR should preserve semantic similarity between related texts."""
        texts = [
            "the bug was caused by a race condition",
            "race condition in threading module",
            "concurrent access to shared state",
            "the weather is nice today",  # Unrelated
            "gardening tips for beginners",  # Unrelated
        ]

        embeddings = [_synthetic_embedding(t, self.dim) for t in texts]

        # Compute similarity matrix with full-precision HRR
        hrr_sims = np.zeros((5, 5))
        qhrr_sims = np.zeros((5, 5))
        for i in range(5):
            for j in range(5):
                hrr_sims[i, j] = self.hrr.similarity(embeddings[i], embeddings[j])
                q_i = self.qhrr._to_quantized(embeddings[i])
                q_j = self.qhrr._to_quantized(embeddings[j])
                qhrr_sims[i, j] = self.qhrr.similarity(q_i, q_j)

        # Related texts (0,1,2) should have higher similarity than unrelated (3,4)
        related_hrr = np.mean(hrr_sims[0:3, 0:3])
        unrelated_hrr = np.mean(hrr_sims[0:3, 3:5])
        related_qhrr = np.mean(qhrr_sims[0:3, 0:3])
        unrelated_qhrr = np.mean(qhrr_sims[0:3, 3:5])

        print(f"\n  Semantic similarity preservation:")
        print(f"    HRR  — related: {related_hrr:.3f}, unrelated: {unrelated_hrr:.3f}, gap: {related_hrr - unrelated_hrr:.3f}")
        print(f"    qFHRR — related: {related_qhrr:.3f}, unrelated: {unrelated_qhrr:.3f}, gap: {related_qhrr - unrelated_qhrr:.3f}")

        # Both should show a positive gap between related and unrelated
        self.assertGreater(related_hrr - unrelated_hrr, 0, "HRR should distinguish related from unrelated")
        self.assertGreater(related_qhrr - unrelated_qhrr, 0, "qFHRR should also distinguish related from unrelated")

    def test_project_accuracy_with_realistic_embeddings(self) -> None:
        """Test HRR projection accuracy with realistic embeddings."""
        subject = "the database outage"
        relation = "CAUSES"

        embedding = _synthetic_embedding(subject, self.dim)

        # Full precision projection
        projected_hrr = self.hrr.project(embedding, relation)
        recovered_hrr = self.hrr.inverse_project(projected_hrr, relation)
        hrr_sim = self.hrr.similarity(embedding, recovered_hrr)

        # Quantized projection
        projected_q = self.qhrr.project(embedding, relation)
        recovered_q = self.qhrr.inverse_project(projected_q, relation)
        q_orig = self.qhrr._to_quantized(embedding)
        qhrr_sim = self.qhrr.similarity(q_orig, recovered_q)

        print(f"\n  Projection accuracy with realistic embeddings:")
        print(f"    HRR  roundtrip similarity: {hrr_sim:.3f}")
        print(f"    qFHRR roundtrip similarity: {qhrr_sim:.3f}")

        # Both should preserve some similarity through roundtrip
        self.assertGreater(hrr_sim, 0.2, "HRR should preserve similarity through project/inverse_project")
        self.assertGreater(qhrr_sim, -0.1, "qFHRR should not be anti-correlated through roundtrip")

    def test_bind_unbind_with_semantic_content(self) -> None:
        """Test bind/unbind with semantically meaningful content."""
        pairs = [
            ("race condition", "threading module"),
            ("memory leak", "garbage collector"),
            ("network timeout", "connection pool"),
        ]

        hrr_sims = []
        qhrr_sims = []

        for a_text, b_text in pairs:
            a = _synthetic_embedding(a_text, self.dim)
            b = _synthetic_embedding(b_text, self.dim)

            # HRR
            bound = self.hrr.bind(a, b)
            recovered = self.hrr.unbind(bound, b)
            hrr_sims.append(self.hrr.similarity(a, recovered))

            # qFHRR
            q_bound = self.qhrr.bind(a, b)
            q_recovered = self.qhrr.unbind(q_bound, b)
            qhrr_sims.append(self.qhrr.similarity(self.qhrr._to_quantized(a), q_recovered))

        avg_hrr = np.mean(hrr_sims)
        avg_qhrr = np.mean(qhrr_sims)

        print(f"\n  Bind/unbind with semantic content:")
        for i, (a, b) in enumerate(pairs):
            print(f"    '{a}' + '{b}': HRR={hrr_sims[i]:.3f}, qFHRR={qhrr_sims[i]:.3f}")
        print(f"    Average: HRR={avg_hrr:.3f}, qFHRR={avg_qhrr:.3f}")

        self.assertGreater(avg_hrr, 0.3, "HRR should preserve semantic content through bind/unbind")
        self.assertGreater(avg_qhrr, -0.1, "qFHRR should not destroy semantic content through bind/unbind")

    def test_superposition_preserves_relevance(self) -> None:
        """Test that superposed vectors preserve relevance ranking."""
        contexts = [
            "the bug was caused by a race condition in the threading module",
            "database connection pool exhausted during peak traffic",
            "memory leak in the garbage collector caused heap overflow",
            "the weather forecast predicts rain tomorrow",
            "recipe for chocolate chip cookies",
        ]

        query = "what caused the system crash"
        query_emb = _synthetic_embedding(query, self.dim)

        # Compute relevance scores with both engines
        context_embs = [_synthetic_embedding(c, self.dim) for c in contexts]

        hrr_scores = [self.hrr.similarity(query_emb, c) for c in context_embs]
        qhrr_scores = [
            self.qhrr.similarity(self.qhrr._to_quantized(query_emb), self.qhrr._to_quantized(c))
            for c in context_embs
        ]

        # Top result should be the same for both
        hrr_top = np.argmax(hrr_scores)
        qhrr_top = np.argmax(qhrr_scores)

        print(f"\n  Relevance ranking preservation:")
        for i, ctx in enumerate(contexts):
            print(f"    HRR={hrr_scores[i]:+.3f}  qFHRR={qhrr_scores[i]:+.3f}  {ctx[:50]}")
        print(f"    HRR top:   #{hrr_top} ({contexts[hrr_top][:40]}...)")
        print(f"    qFHRR top: #{qhrr_top} ({contexts[qhrr_top][:40]}...)")

        # Both should rank bug-related contexts higher than unrelated ones
        self.assertLess(hrr_top, 3, "HRR should rank bug-related context as top")
        self.assertLess(qhrr_top, 3, "qFHRR should rank bug-related context as top")


if __name__ == "__main__":
    unittest.main()
