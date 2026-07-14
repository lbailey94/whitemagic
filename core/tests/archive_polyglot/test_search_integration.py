"""Integration tests for PSR-002 Search"""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    import whitemagic_rust as whitemagic_rs
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    pytest.skip("Rust bindings not available", allow_module_level=True)

class TestVectorSearch:
    """Test vector search"""

    def test_add_and_search(self):
        """Test adding vectors and searching"""
        vs = whitemagic_rs.PyVectorIndex("cosine")

        # Add vectors (returns index)
        idx1 = vs.add([1.0, 2.0, 3.0])
        vs.add([1.1, 2.1, 3.1])
        vs.add([5.0, 6.0, 7.0])

        # Search returns (index, distance) pairs
        results = vs.search([1.0, 2.0, 3.0], 2)

        assert len(results) == 2
        assert results[0][0] == idx1  # Closest match is the first vector added

    def test_index_len(self):
        """Test vector index length"""
        vs = whitemagic_rs.PyVectorIndex("cosine")

        # Initially empty
        assert len(vs) == 0

        # Add vectors
        vs.add([1.0, 2.0, 3.0])
        vs.add([1.1, 2.1, 3.1])

        assert len(vs) == 2

class TestHybridRecall:
    """Test hybrid recall - skipped (HybridRecall not exported)"""

    @pytest.mark.skip(reason="HybridRecall not yet implemented")
    def test_hybrid_search(self):
        """Test hybrid search combining methods"""
        recall = whitemagic_rs.HybridRecall()

        results = recall.search("test query", use_fts=True, use_vector=True, limit=5)

        assert isinstance(results, list)
        assert len(results) <= 5
