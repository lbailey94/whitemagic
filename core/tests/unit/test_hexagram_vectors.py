"""Tests for hexagram HRR vectorization."""

from __future__ import annotations

import numpy as np
import pytest

from whitemagic.core.intelligence.hexagram_vectors import (
    HexagramVectors,
    get_hexagram_vectors,
)


@pytest.fixture
def hv() -> HexagramVectors:
    return HexagramVectors()


class TestHexagramVectors:
    def test_vector_dimension(self, hv: HexagramVectors) -> None:
        v = hv.get_vector(1)
        assert len(v) == 64

    def test_vector_unit_norm(self, hv: HexagramVectors) -> None:
        for kw in range(1, 65):
            v = hv.get_vector(kw)
            norm = sum(x * x for x in v) ** 0.5
            assert abs(norm - 1.0) < 1e-6, f"Hexagram {kw} norm = {norm}"

    def test_vector_deterministic(self, hv: HexagramVectors) -> None:
        v1 = hv.get_vector(15)
        v2 = hv.get_vector(15)
        assert v1 == v2

    def test_different_hexagrams_different_vectors(self, hv: HexagramVectors) -> None:
        v1 = hv.get_vector(1)
        v2 = hv.get_vector(2)
        assert v1 != v2

    def test_invalid_hexagram_raises(self, hv: HexagramVectors) -> None:
        with pytest.raises(ValueError):
            hv.get_vector(0)
        with pytest.raises(ValueError):
            hv.get_vector(65)

    def test_interaction_score_self_is_one(self, hv: HexagramVectors) -> None:
        for kw in [1, 15, 30, 64]:
            score = hv.interaction_score(kw, kw)
            assert abs(score - 1.0) < 1e-6, f"Self-similarity for {kw} = {score}"

    def test_interaction_score_range(self, hv: HexagramVectors) -> None:
        for a in [1, 10, 30, 50, 64]:
            for b in [1, 10, 30, 50, 64]:
                score = hv.interaction_score(a, b)
                assert -1.01 <= score <= 1.01

    def test_interaction_score_symmetric(self, hv: HexagramVectors) -> None:
        for a in [1, 15, 30, 45, 64]:
            for b in [2, 20, 40, 60]:
                s1 = hv.interaction_score(a, b)
                s2 = hv.interaction_score(b, a)
                assert abs(s1 - s2) < 1e-6

    def test_top_synergies_count(self, hv: HexagramVectors) -> None:
        top = hv.top_synergies(10)
        assert len(top) == 10

    def test_top_synergies_sorted(self, hv: HexagramVectors) -> None:
        top = hv.top_synergies(20)
        for i in range(1, len(top)):
            assert top[i]["similarity"] <= top[i - 1]["similarity"]

    def test_top_synergies_format(self, hv: HexagramVectors) -> None:
        top = hv.top_synergies(5)
        for p in top:
            assert "hexagram_a" in p
            assert "hexagram_b" in p
            assert "similarity" in p
            assert 1 <= p["hexagram_a"] <= 64
            assert 1 <= p["hexagram_b"] <= 64
            assert p["hexagram_a"] < p["hexagram_b"]  # No self-pairs

    def test_detect_synergies_threshold(self, hv: HexagramVectors) -> None:
        high = hv.detect_synergies(0.99)
        for p in high:
            assert p["similarity"] > 0.99

        low = hv.detect_synergies(-1.0)
        assert len(low) == 64 * 63 // 2  # All pairs

    def test_detect_synergies_sorted(self, hv: HexagramVectors) -> None:
        syn = hv.detect_synergies(0.0)
        for i in range(1, len(syn)):
            assert syn[i]["similarity"] <= syn[i - 1]["similarity"]

    def test_superpose_unit_norm(self, hv: HexagramVectors) -> None:
        result = hv.superpose(1, 2)
        norm = sum(x * x for x in result) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    def test_superpose_dimension(self, hv: HexagramVectors) -> None:
        result = hv.superpose(1, 2)
        assert len(result) == 64

    def test_interaction_matrix_shape(self, hv: HexagramVectors) -> None:
        matrix = hv.interaction_matrix()
        assert len(matrix) == 64
        for row in matrix:
            assert len(row) == 64

    def test_interaction_matrix_diagonal_one(self, hv: HexagramVectors) -> None:
        matrix = hv.interaction_matrix()
        for i in range(64):
            assert abs(matrix[i][i] - 1.0) < 1e-6

    def test_interaction_matrix_symmetric(self, hv: HexagramVectors) -> None:
        matrix = hv.interaction_matrix()
        for i in range(64):
            for j in range(64):
                assert abs(matrix[i][j] - matrix[j][i]) < 1e-6

    def test_nearest_hexagrams(self, hv: HexagramVectors) -> None:
        v = hv.get_vector(1)
        nearest = hv.nearest_hexagrams(v, k=5)
        assert len(nearest) == 5
        # Hexagram 1 should be nearest to itself
        assert nearest[0]["hexagram"] == 1
        assert abs(nearest[0]["similarity"] - 1.0) < 1e-6

    def test_nearest_hexagrams_sorted(self, hv: HexagramVectors) -> None:
        v = hv.get_vector(15)
        nearest = hv.nearest_hexagrams(v, k=10)
        for i in range(1, len(nearest)):
            assert nearest[i]["similarity"] <= nearest[i - 1]["similarity"]

    def test_nearest_hexagrams_padded_vector(self, hv: HexagramVectors) -> None:
        # Short vector should be padded
        nearest = hv.nearest_hexagrams([0.1, 0.2, 0.3], k=3)
        assert len(nearest) == 3

    def test_singleton(self) -> None:
        hv1 = get_hexagram_vectors()
        hv2 = get_hexagram_vectors()
        assert hv1 is hv2


class TestHexagramHandlers:
    """Test MCP tool handlers."""

    def test_interaction_score_handler(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_interaction_score

        r = handle_hexagram_interaction_score(hexagram_a=1, hexagram_b=2)
        assert r["status"] == "success"
        assert "similarity" in r
        assert -1.0 <= r["similarity"] <= 1.0

    def test_interaction_score_handler_invalid(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_interaction_score

        r = handle_hexagram_interaction_score(hexagram_a=0, hexagram_b=99)
        assert r["status"] == "error"

    def test_synergies_handler_top_k(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_synergies

        r = handle_hexagram_synergies(top_k=5)
        assert r["status"] == "success"
        assert r["count"] == 5

    def test_synergies_handler_threshold(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_synergies

        r = handle_hexagram_synergies(threshold=0.5)
        assert r["status"] == "success"
        for p in r["pairs"]:
            assert p["similarity"] > 0.5

    def test_superpose_handler(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_superpose

        r = handle_hexagram_superpose(hexagram_a=1, hexagram_b=2)
        assert r["status"] == "success"
        assert r["dimension"] == 64

    def test_vector_handler(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_vector

        r = handle_hexagram_vector(hexagram_num=1)
        assert r["status"] == "success"
        assert r["dimension"] == 64
        assert len(r["vector"]) == 64

    def test_vector_handler_invalid(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_vector

        r = handle_hexagram_vector(hexagram_num=0)
        assert r["status"] == "error"

    def test_nearest_handler(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_nearest

        r = handle_hexagram_nearest(vector=[0.1] * 64, top_k=3)
        assert r["status"] == "success"
        assert r["count"] == 3

    def test_nearest_handler_no_vector(self) -> None:
        from whitemagic.tools.handlers.simd import handle_hexagram_nearest

        r = handle_hexagram_nearest()
        assert r["status"] == "error"
