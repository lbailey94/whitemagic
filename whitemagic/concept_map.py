"""
Concept Mapping System - Graph-based concept relationships using NetworkX.

This module provides a graph-based system for mapping concepts and their
relationships, with visualization and analysis capabilities.

Philosophy:
- Concepts as nodes in a semantic network
- Relationships as weighted edges
- Traversal algorithms for concept discovery
- Graph analysis for pattern detection

Based on I Ching principle: 網 (Wang) - Network/Web of connections
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
import json

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

from .symbolic import (
    ConceptNode,
    ConceptRelationship,
    RelationshipType,
    SymbolicReasoning,
)


class ConceptMap:
    """
    Graph-based concept mapping system using NetworkX.
    
    Provides graph operations, traversal, and analysis on concept networks.
    """
    
    def __init__(self, symbolic_engine: Optional[SymbolicReasoning] = None):
        """
        Initialize concept map.
        
        Args:
            symbolic_engine: Optional existing symbolic reasoning engine
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError(
                "NetworkX is required for ConceptMap. "
                "Install with: pip install networkx"
            )
        
        self.symbolic_engine = symbolic_engine or SymbolicReasoning()
        self.graph = nx.DiGraph()  # Directed graph
        self._sync_from_engine()
    
    def _sync_from_engine(self) -> None:
        """Sync graph from symbolic reasoning engine."""
        # Clear existing graph
        self.graph.clear()
        
        # Add nodes
        for concept_id, concept in self.symbolic_engine.concepts.items():
            self.graph.add_node(
                concept_id,
                english=concept.english,
                chinese=concept.chinese,
                type=concept.concept_type.value,
                tokens_english=concept.token_count_english,
                tokens_chinese=concept.token_count_chinese,
            )
        
        # Add edges
        for rel in self.symbolic_engine.relationships:
            self.graph.add_edge(
                rel.source_id,
                rel.target_id,
                type=rel.relationship_type.value,
                strength=rel.strength,
                bidirectional=rel.bidirectional,
            )
            
            # Add reverse edge if bidirectional
            if rel.bidirectional:
                self.graph.add_edge(
                    rel.target_id,
                    rel.source_id,
                    type=rel.relationship_type.value,
                    strength=rel.strength,
                    bidirectional=True,
                )
    
    def _sync_to_engine(self) -> None:
        """Sync changes back to symbolic engine."""
        # This is a one-way sync for now
        # Could be extended to support bidirectional sync
        pass
    
    def get_neighbors(
        self,
        concept_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[str]:
        """
        Get neighboring concepts.
        
        Args:
            concept_id: Source concept
            relationship_type: Optional filter by type
            
        Returns:
            List of neighbor concept IDs
        """
        if concept_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(concept_id):
            if relationship_type:
                edge_data = self.graph[concept_id][neighbor]
                if edge_data.get("type") == relationship_type.value:
                    neighbors.append(neighbor)
            else:
                neighbors.append(neighbor)
        
        return neighbors
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5
    ) -> Optional[List[str]]:
        """
        Find shortest path between concepts.
        
        Args:
            source_id: Starting concept
            target_id: Target concept
            max_length: Maximum path length
            
        Returns:
            List of concept IDs forming path, or None if no path
        """
        try:
            path = nx.shortest_path(
                self.graph,
                source=source_id,
                target=target_id
            )
            
            if len(path) <= max_length + 1:  # +1 because path includes endpoints
                return path
            return None
            
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return None
    
    def find_related_concepts(
        self,
        concept_id: str,
        max_distance: int = 2,
        min_strength: float = 0.0
    ) -> Dict[str, int]:
        """
        Find concepts within N hops.
        
        Args:
            concept_id: Starting concept
            max_distance: Maximum hops away
            min_strength: Minimum edge strength
            
        Returns:
            Dictionary mapping concept_id -> distance
        """
        if concept_id not in self.graph:
            return {}
        
        # BFS to find concepts within max_distance
        distances = {concept_id: 0}
        queue = [(concept_id, 0)]
        visited = {concept_id}
        
        while queue:
            current, dist = queue.pop(0)
            
            if dist >= max_distance:
                continue
            
            for neighbor in self.graph.neighbors(current):
                if neighbor in visited:
                    continue
                
                # Check edge strength
                edge_data = self.graph[current][neighbor]
                if edge_data.get("strength", 1.0) < min_strength:
                    continue
                
                visited.add(neighbor)
                distances[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))
        
        return distances
    
    def get_central_concepts(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Get most central concepts using betweenness centrality.
        
        Args:
            top_n: Number of top concepts to return
            
        Returns:
            List of (concept_id, centrality_score) tuples
        """
        centrality = nx.betweenness_centrality(self.graph)
        sorted_concepts = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_concepts[:top_n]
    
    def detect_communities(self) -> List[Set[str]]:
        """
        Detect communities (clusters) of related concepts.
        
        Returns:
            List of sets, each containing concept IDs in a community
        """
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        # Use Louvain method (if available) or simple connected components
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = greedy_modularity_communities(undirected)
            return [set(c) for c in communities]
        except ImportError:
            # Fallback to connected components
            components = nx.connected_components(undirected)
            return [set(c) for c in components]
    
    def get_concept_importance(self, concept_id: str) -> Dict[str, float]:
        """
        Calculate various importance metrics for a concept.
        
        Args:
            concept_id: Concept to analyze
            
        Returns:
            Dictionary of importance metrics
        """
        if concept_id not in self.graph:
            return {}
        
        metrics = {}
        
        # Degree centrality (how many connections)
        metrics["degree_centrality"] = nx.degree_centrality(self.graph)[concept_id]
        
        # Betweenness centrality (how often it's on shortest paths)
        metrics["betweenness_centrality"] = nx.betweenness_centrality(self.graph)[concept_id]
        
        # PageRank (importance based on connections)
        metrics["pagerank"] = nx.pagerank(self.graph)[concept_id]
        
        # In-degree (how many concepts point to this one)
        metrics["in_degree"] = self.graph.in_degree(concept_id)
        
        # Out-degree (how many concepts this one points to)
        metrics["out_degree"] = self.graph.out_degree(concept_id)
        
        return metrics
    
    def suggest_connections(
        self,
        concept_id: str,
        max_suggestions: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Suggest potential connections for a concept.
        
        Uses graph structure to suggest concepts that might be related.
        
        Args:
            concept_id: Concept to suggest connections for
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of (concept_id, confidence_score) tuples
        """
        if concept_id not in self.graph:
            return []
        
        suggestions = []
        
        # Get 2-hop neighbors (friends of friends)
        neighbors = set(self.graph.neighbors(concept_id))
        two_hop = set()
        
        for neighbor in neighbors:
            for second_hop in self.graph.neighbors(neighbor):
                if second_hop != concept_id and second_hop not in neighbors:
                    two_hop.add(second_hop)
        
        # Calculate confidence based on common neighbors
        for candidate in two_hop:
            candidate_neighbors = set(self.graph.neighbors(candidate))
            common = neighbors.intersection(candidate_neighbors)
            confidence = len(common) / max(len(neighbors), len(candidate_neighbors))
            suggestions.append((candidate, confidence))
        
        # Sort by confidence and return top N
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:max_suggestions]
    
    def visualize_subgraph(
        self,
        concept_id: str,
        max_distance: int = 2,
        use_chinese: bool = False
    ) -> Dict[str, Any]:
        """
        Extract subgraph around a concept for visualization.
        
        Args:
            concept_id: Center concept
            max_distance: Maximum distance from center
            use_chinese: Whether to use Chinese labels
            
        Returns:
            Dictionary with nodes and edges for visualization
        """
        # Get concepts within distance
        related = self.find_related_concepts(concept_id, max_distance)
        
        # Extract subgraph
        subgraph = self.graph.subgraph(related.keys())
        
        # Format for visualization
        nodes = []
        for node_id in subgraph.nodes():
            node_data = subgraph.nodes[node_id]
            
            label = node_data.get("chinese" if use_chinese else "english", node_id)
            
            nodes.append({
                "id": node_id,
                "label": label,
                "distance": related[node_id],
                "type": node_data.get("type", "unknown"),
                "is_center": node_id == concept_id,
            })
        
        edges = []
        for source, target in subgraph.edges():
            edge_data = subgraph[source][target]
            edges.append({
                "source": source,
                "target": target,
                "type": edge_data.get("type", "unknown"),
                "strength": edge_data.get("strength", 1.0),
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "center": concept_id,
            "max_distance": max_distance,
            "use_chinese": use_chinese,
        }
    
    def export_graphml(self, path: Path) -> None:
        """
        Export graph to GraphML format for external tools.
        
        Args:
            path: Path to save GraphML file
        """
        nx.write_graphml(self.graph, str(path))
    
    def export_dot(self, path: Path) -> None:
        """
        Export graph to DOT format for Graphviz.
        
        Args:
            path: Path to save DOT file
        """
        nx.drawing.nx_pydot.write_dot(self.graph, str(path))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph),
            "num_components": nx.number_weakly_connected_components(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes()
                if self.graph.number_of_nodes() > 0 else 0,
        }


def create_concept_map(
    symbolic_engine: Optional[SymbolicReasoning] = None
) -> ConceptMap:
    """
    Convenience function to create a concept map.
    
    Args:
        symbolic_engine: Optional existing engine
        
    Returns:
        ConceptMap instance
        
    Example:
        >>> from whitemagic import create_symbolic_engine
        >>> engine = create_symbolic_engine()
        >>> engine.add_concept("dao", "The Way", "道")
        >>> engine.add_concept("de", "Virtue", "德")
        >>> engine.add_relationship("dao", "de", RelationshipType.RELATED_TO)
        >>> 
        >>> concept_map = create_concept_map(engine)
        >>> concept_map.find_path("dao", "de")
        ['dao', 'de']
    """
    return ConceptMap(symbolic_engine)
