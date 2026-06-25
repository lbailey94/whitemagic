"""Tests for PyO3 ternary kernel bindings.

These tests verify the Python-facing API of the Rust ternary SIMD kernels.
They skip gracefully if the Rust extension isn't built.
"""
import pytest

try:
    import whitemagic_rust
    rust_inference = whitemagic_rust.inference
    _HAS_RUST = True
except (ImportError, AttributeError):
    _HAS_RUST = False

pytestmark = pytest.mark.skipif(not _HAS_RUST, reason="whitemagic_rust not built")


class TestPyPackTernary:
    def test_pack_basic(self):
        values = [1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1]
        packed = rust_inference.py_pack_ternary(values)
        assert len(packed) == 1  # 16 values → 1 word

    def test_pack_empty(self):
        packed = rust_inference.py_pack_ternary([])
        assert len(packed) == 0

    def test_pack_invalid_value(self):
        with pytest.raises(ValueError):
            rust_inference.py_pack_ternary([1, 0, 2])


class TestPyPackTernaryMatrix:
    def test_pack_matrix(self):
        # 2x16 matrix = 32 values
        values = [1, -1, 0] * 10 + [0, 1]  # 32 values
        packed = rust_inference.py_pack_ternary_matrix(values, 2, 16)
        assert len(packed) == 2  # 2 rows × 1 word each

    def test_pack_matrix_non_multiple_16(self):
        # 2x8 matrix = 16 values, but k=8 → 1 word per row
        values = [1, -1, 0, 1, -1, 0, 1, -1] * 2
        packed = rust_inference.py_pack_ternary_matrix(values, 2, 8)
        assert len(packed) == 2


class TestPyUnpackTernary:
    def test_roundtrip(self):
        original = [1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1, -1, 0, 1]
        packed = rust_inference.py_pack_ternary(original)
        unpacked = rust_inference.py_unpack_ternary(packed, len(original))
        assert unpacked == original


class TestPyTernaryGemv:
    def test_gemv_basic(self):
        # 1x16 matrix, all +1
        weights = [1] * 16
        packed = rust_inference.py_pack_ternary_matrix(weights, 1, 16)
        activations = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
                       9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
        result = rust_inference.py_ternary_gemv(packed, activations, 1, 16)
        assert len(result) == 1
        expected = sum(activations)
        assert abs(result[0] - expected) < 0.01

    def test_gemv_all_zero(self):
        weights = [0] * 16
        packed = rust_inference.py_pack_ternary_matrix(weights, 1, 16)
        activations = [1.0] * 16
        result = rust_inference.py_ternary_gemv(packed, activations, 1, 16)
        assert abs(result[0]) < 0.001

    def test_gemv_all_negative(self):
        weights = [-1] * 16
        packed = rust_inference.py_pack_ternary_matrix(weights, 1, 16)
        activations = [1.0] * 16
        result = rust_inference.py_ternary_gemv(packed, activations, 1, 16)
        assert abs(result[0] - (-16.0)) < 0.01


class TestPyTernaryDot:
    def test_dot_basic(self):
        weights = [1, -1, 1, -1]
        activations = [1.0, 2.0, 3.0, 4.0]
        result = rust_inference.py_ternary_dot(weights, activations)
        assert abs(result - (1.0 - 2.0 + 3.0 - 4.0)) < 0.01

    def test_dot_length_mismatch(self):
        with pytest.raises(ValueError):
            rust_inference.py_ternary_dot([1, 0, 1], [1.0, 2.0])


class TestPyTernaryBackend:
    def test_backend_returns_string(self):
        backend = rust_inference.py_ternary_backend()
        assert backend in ("avx2", "scalar")
