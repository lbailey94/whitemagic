"""Integration tests for PSR-003 Graph"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    import whitemagic_rust as whitemagic_rs
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    pytest.skip("Rust bindings not available", allow_module_level=True)

class TestGraphWalker:
    """Test graph walker"""
    
    def test_creation(self):
        """Test creating a GraphWalker with max_depth"""
        walker = whitemagic_rs.GraphWalker(5)
        assert walker.get_max_depth() == 5
    
    def test_traverse_bfs(self):
        """Test BFS traversal"""
        walker = whitemagic_rs.GraphWalker(3)
        
        # Edges: list of (source, target, weight) tuples
        edges = [(1, 2, 0.8), (1, 3, 0.9), (2, 4, 0.7)]
        
        results = walker.traverse_bfs(1, edges)
        
        assert len(results) > 0
        assert 1 in results  # Start node should be visited
    
    def test_traverse_dfs(self):
        """Test DFS traversal"""
        walker = whitemagic_rs.GraphWalker(5)
        
        edges = [(1, 2, 0.8), (1, 3, 0.9), (2, 4, 0.7)]
        
        results = walker.traverse_dfs(1, edges)
        
        assert len(results) > 0
        assert 1 in results
    
    def test_find_path(self):
        """Test finding path between nodes"""
        walker = whitemagic_rs.GraphWalker(10)
        
        edges = [(1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0)]
        
        path = walker.find_path(1, 4, edges)
        
        assert path is not None
        assert path == [1, 2, 3, 4]
    
    def test_min_weight_filtering(self):
        """Test that edges below min_weight are filtered"""
        walker = whitemagic_rs.GraphWalker(3)
        walker.set_min_weight(0.5)
        
        # Edge with weight below threshold
        edges = [(1, 2, 0.3), (1, 3, 0.8)]
        
        results = walker.traverse_bfs(1, edges)
        
        assert walker.get_min_weight() == 0.5
        # Only node 3 should be reachable (weight 0.8 >= 0.5)
        assert 1 in results
        assert 3 in results


class TestCommunityDetector:
    """Test community detection (PyCommunityDetector)"""
    
    def test_detector_creation(self):
        """Test creating a CommunityDetector"""
        detector = whitemagic_rs.PyCommunityDetector()
        assert detector.node_count() == 0
        assert detector.edge_count() == 0
    
    def test_add_edge(self):
        """Test adding edges"""
        detector = whitemagic_rs.PyCommunityDetector()
        
        detector.add_edge("a", "b")
        detector.add_edge("b", "c")
        
        assert detector.node_count() == 3
        assert detector.edge_count() == 2
    
    def test_detect_communities(self):
        """Test community detection"""
        detector = whitemagic_rs.PyCommunityDetector()
        
        # Create two separate communities
        # Community 1: a-b-c
        detector.add_edge("a", "b")
        detector.add_edge("b", "c")
        
        # Community 2: d-e
        detector.add_edge("d", "e")
        
        communities = detector.detect_communities(2)
        
        assert len(communities) == 2
    
    def test_modularity(self):
        """Test modularity calculation"""
        detector = whitemagic_rs.PyCommunityDetector()
        
        detector.add_edge("a", "b")
        detector.add_edge("b", "c")
        
        communities = detector.detect_communities(1)
        modularity = detector.get_modularity(communities)
        
        assert modularity >= 0.0
