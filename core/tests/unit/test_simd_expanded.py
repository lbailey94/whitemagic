"""Tests for expanded SIMD operations (v23.2 Phase 4).

Tests the Python bridge functions for batch_euclidean_distance,
batch_dot_product, and batch_topk_cosine. These tests use the
Python fallback paths (no Rust required).
"""

import math


class TestBatchEuclideanDistance:
    """Tests for batch_euclidean_distance Python fallback."""

    def test_basic_distances(self):
        from whitemagic.core.acceleration.simd_unified import batch_euclidean_distance

        query = [0.0, 0.0, 0.0]
        vectors = [
            [3.0, 4.0, 0.0],  # dist = 5.0
            [0.0, 0.0, 0.0],  # dist = 0.0
            [1.0, 0.0, 0.0],  # dist = 1.0
        ]
        results = batch_euclidean_distance(query, vectors)
        assert len(results) == 3
        assert abs(results[0] - 5.0) < 1e-6
        assert abs(results[1] - 0.0) < 1e-6
        assert abs(results[2] - 1.0) < 1e-6

    def test_empty_vectors(self):
        from whitemagic.core.acceleration.simd_unified import batch_euclidean_distance

        results = batch_euclidean_distance([1.0, 2.0], [])
        assert results == []

    def test_known_distance(self):
        from whitemagic.core.acceleration.simd_unified import batch_euclidean_distance

        query = [1.0, 2.0, 3.0]
        vectors = [[4.0, 5.0, 6.0]]
        results = batch_euclidean_distance(query, vectors)
        expected = math.sqrt(9 + 9 + 9)  # 3*sqrt(3)
        assert abs(results[0] - expected) < 1e-6


class TestBatchDotProduct:
    """Tests for batch_dot_product Python fallback."""

    def test_basic_dot_products(self):
        from whitemagic.core.acceleration.simd_unified import batch_dot_product

        query = [1.0, 2.0, 3.0]
        vectors = [
            [1.0, 0.0, 0.0],  # dot = 1.0
            [0.0, 1.0, 0.0],  # dot = 2.0
            [1.0, 1.0, 1.0],  # dot = 6.0
        ]
        results = batch_dot_product(query, vectors)
        assert len(results) == 3
        assert abs(results[0] - 1.0) < 1e-6
        assert abs(results[1] - 2.0) < 1e-6
        assert abs(results[2] - 6.0) < 1e-6

    def test_empty_vectors(self):
        from whitemagic.core.acceleration.simd_unified import batch_dot_product

        results = batch_dot_product([1.0, 2.0], [])
        assert results == []

    def test_orthogonal_vectors(self):
        from whitemagic.core.acceleration.simd_unified import batch_dot_product

        query = [1.0, 0.0]
        vectors = [[0.0, 1.0]]
        results = batch_dot_product(query, vectors)
        assert abs(results[0] - 0.0) < 1e-6


class TestBatchTopkCosine:
    """Tests for batch_topk_cosine Python fallback."""

    def test_top2_results(self):
        from whitemagic.core.acceleration.simd_unified import batch_topk_cosine

        query = [1.0, 0.0, 0.0]
        vectors = [
            [0.0, 1.0, 0.0],  # cosine = 0.0
            [1.0, 0.0, 0.0],  # cosine = 1.0
            [0.5, 0.5, 0.0],  # cosine = 0.5
            [0.0, 0.0, 1.0],  # cosine = 0.0
        ]
        results = batch_topk_cosine(query, vectors, k=2)
        assert len(results) == 2
        # Top result should be index 1 (cosine = 1.0)
        assert results[0][0] == 1
        assert abs(results[0][1] - 1.0) < 1e-6
        # Second result should be index 2 (cosine = 0.5/sqrt(0.5) ≈ 0.7071)
        assert results[1][0] == 2
        assert abs(results[1][1] - (0.5 / math.sqrt(0.5))) < 1e-6

    def test_k_greater_than_vectors(self):
        from whitemagic.core.acceleration.simd_unified import batch_topk_cosine

        query = [1.0, 0.0]
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        results = batch_topk_cosine(query, vectors, k=10)
        assert len(results) == 2  # Can only return as many as exist


class TestSimdStatus:
    """Tests that simd_status includes new operations."""

    def test_status_includes_new_ops(self):
        from whitemagic.core.acceleration.simd_unified import simd_status

        status = simd_status()
        ops = status["operations"]
        assert "batch_euclidean_distance" in ops
        assert "batch_dot_product" in ops
        assert "batch_topk_cosine" in ops
