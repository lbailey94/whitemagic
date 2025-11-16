"""
Symbolic Memory Integration - Connect symbolic reasoning with memory system.

This module integrates the symbolic reasoning engine with WhiteMagic's memory
system, allowing concepts to be linked to memories and vice versa.

Philosophy:
- Memories can be tagged with concepts
- Concepts can reference memories
- Bidirectional discovery: memory -> concepts, concepts -> memories
- Automatic concept extraction from memory content

Based on principle: 記憶與符號 (Memory and Symbol united)
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
from datetime import datetime

from .symbolic import SymbolicReasoning, ConceptNode, ConceptType
from .concept_map import ConceptMap
from .core import MemoryManager
from .models import Memory


class SymbolicMemoryIntegration:
    """
    Integration layer between symbolic reasoning and memory system.
    
    Provides bidirectional linking and concept extraction.
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        symbolic_engine: Optional[SymbolicReasoning] = None
    ):
        """
        Initialize integration.
        
        Args:
            memory_manager: WhiteMagic memory manager
            symbolic_engine: Optional existing symbolic engine
        """
        self.memory_manager = memory_manager
        self.symbolic_engine = symbolic_engine or SymbolicReasoning()
        self.concept_map = ConceptMap(self.symbolic_engine)
        
        # Mappings
        self._memory_to_concepts: Dict[str, Set[str]] = {}  # filename -> concept_ids
        self._concept_to_memories: Dict[str, Set[str]] = {}  # concept_id -> filenames
    
    def link_memory_to_concept(
        self,
        memory_filename: str,
        concept_id: str
    ) -> None:
        """
        Link a memory to a concept.
        
        Args:
            memory_filename: Memory filename
            concept_id: Concept ID
        """
        # Verify concept exists
        if concept_id not in self.symbolic_engine.concepts:
            raise ValueError(f"Concept '{concept_id}' not found")
        
        # Add to mappings
        if memory_filename not in self._memory_to_concepts:
            self._memory_to_concepts[memory_filename] = set()
        self._memory_to_concepts[memory_filename].add(concept_id)
        
        if concept_id not in self._concept_to_memories:
            self._concept_to_memories[concept_id] = set()
        self._concept_to_memories[concept_id].add(memory_filename)
    
    def get_concepts_for_memory(self, memory_filename: str) -> List[ConceptNode]:
        """
        Get concepts linked to a memory.
        
        Args:
            memory_filename: Memory filename
            
        Returns:
            List of ConceptNode objects
        """
        concept_ids = self._memory_to_concepts.get(memory_filename, set())
        return [
            self.symbolic_engine.concepts[cid]
            for cid in concept_ids
            if cid in self.symbolic_engine.concepts
        ]
    
    def get_memories_for_concept(self, concept_id: str) -> List[Memory]:
        """
        Get memories linked to a concept.
        
        Args:
            concept_id: Concept ID
            
        Returns:
            List of Memory objects
        """
        filenames = self._concept_to_memories.get(concept_id, set())
        memories = []
        
        for filename in filenames:
            try:
                memory = self.memory_manager.get_memory(filename)
                if memory:
                    memories.append(memory)
            except Exception:
                continue
        
        return memories
    
    def extract_concepts_from_memory(
        self,
        memory_filename: str,
        auto_link: bool = True
    ) -> List[str]:
        """
        Extract concepts mentioned in a memory.
        
        Searches memory content for known concept names (English or Chinese).
        
        Args:
            memory_filename: Memory to analyze
            auto_link: Whether to automatically link found concepts
            
        Returns:
            List of concept IDs found
        """
        # Get memory content
        memory = self.memory_manager.get_memory(memory_filename)
        if not memory:
            return []
        
        # Read content
        memory_path = self.memory_manager.base_dir / memory.path
        if not memory_path.exists():
            return []
        
        content = memory_path.read_text(encoding="utf-8").lower()
        
        # Find concepts
        found_concepts = []
        
        for concept_id, concept in self.symbolic_engine.concepts.items():
            # Check English name
            if concept.english.lower() in content:
                found_concepts.append(concept_id)
                if auto_link:
                    self.link_memory_to_concept(memory_filename, concept_id)
                continue
            
            # Check Chinese
            if concept.chinese and concept.chinese in content:
                found_concepts.append(concept_id)
                if auto_link:
                    self.link_memory_to_concept(memory_filename, concept_id)
                continue
            
            # Check aliases
            for alias in concept.aliases:
                if alias.lower() in content:
                    found_concepts.append(concept_id)
                    if auto_link:
                        self.link_memory_to_concept(memory_filename, concept_id)
                    break
        
        return found_concepts
    
    def tag_memory_with_concepts(
        self,
        memory_filename: str,
        tag_prefix: str = "concept:"
    ) -> None:
        """
        Add concept tags to a memory's tags.
        
        Args:
            memory_filename: Memory to tag
            tag_prefix: Prefix for concept tags
        """
        concepts = self.get_concepts_for_memory(memory_filename)
        
        if not concepts:
            return
        
        # Get current memory
        memory = self.memory_manager.get_memory(memory_filename)
        if not memory:
            return
        
        # Add concept tags
        new_tags = set(memory.tags)
        for concept in concepts:
            tag = f"{tag_prefix}{concept.id}"
            new_tags.add(tag)
        
        # Update memory
        self.memory_manager.update_memory(
            memory_filename,
            tags=list(new_tags)
        )
    
    def search_by_concept(
        self,
        concept_id: str,
        include_related: bool = False,
        max_distance: int = 2
    ) -> List[Memory]:
        """
        Search memories by concept.
        
        Args:
            concept_id: Concept to search for
            include_related: Whether to include related concepts
            max_distance: Max distance for related concepts
            
        Returns:
            List of Memory objects
        """
        concept_ids = {concept_id}
        
        if include_related:
            # Get related concepts
            related = self.concept_map.find_related_concepts(
                concept_id,
                max_distance=max_distance
            )
            concept_ids.update(related.keys())
        
        # Get memories for all concepts
        all_memories = []
        seen = set()
        
        for cid in concept_ids:
            memories = self.get_memories_for_concept(cid)
            for memory in memories:
                if memory.filename not in seen:
                    seen.add(memory.filename)
                    all_memories.append(memory)
        
        return all_memories
    
    def create_concept_from_memory_pattern(
        self,
        pattern_name: str,
        memory_filenames: List[str],
        concept_type: ConceptType = ConceptType.PATTERN,
        chinese: Optional[str] = None
    ) -> ConceptNode:
        """
        Create a concept representing a pattern across memories.
        
        Args:
            pattern_name: Name for the pattern
            memory_filenames: Memories exhibiting this pattern
            concept_type: Type of concept
            chinese: Optional Chinese character
            
        Returns:
            Created ConceptNode
        """
        # Create concept
        concept_id = pattern_name.lower().replace(" ", "_")
        
        concept = self.symbolic_engine.add_concept(
            concept_id=concept_id,
            english=pattern_name,
            chinese=chinese,
            concept_type=concept_type,
            definition=f"Pattern identified across {len(memory_filenames)} memories",
        )
        
        # Link to memories
        for filename in memory_filenames:
            self.link_memory_to_concept(filename, concept_id)
        
        return concept
    
    def analyze_memory_concepts(
        self,
        memory_filename: str
    ) -> Dict[str, Any]:
        """
        Analyze concept usage in a memory.
        
        Args:
            memory_filename: Memory to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Get concepts
        concepts = self.get_concepts_for_memory(memory_filename)
        
        if not concepts:
            return {
                "memory": memory_filename,
                "num_concepts": 0,
                "concepts": [],
            }
        
        # Analyze
        analysis = {
            "memory": memory_filename,
            "num_concepts": len(concepts),
            "concepts": [],
        }
        
        for concept in concepts:
            # Get related concepts
            related = self.concept_map.get_neighbors(concept.id)
            
            # Get importance metrics
            importance = self.concept_map.get_concept_importance(concept.id)
            
            analysis["concepts"].append({
                "id": concept.id,
                "english": concept.english,
                "chinese": concept.chinese,
                "type": concept.concept_type.value,
                "num_related": len(related),
                "importance": importance,
            })
        
        return analysis
    
    def suggest_related_memories(
        self,
        memory_filename: str,
        max_suggestions: int = 5
    ) -> List[Tuple[Memory, float]]:
        """
        Suggest related memories based on shared concepts.
        
        Args:
            memory_filename: Source memory
            max_suggestions: Maximum suggestions
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        # Get concepts for this memory
        source_concepts = set(
            c.id for c in self.get_concepts_for_memory(memory_filename)
        )
        
        if not source_concepts:
            return []
        
        # Find memories with overlapping concepts
        candidates: Dict[str, float] = {}
        
        for concept_id in source_concepts:
            memories = self.get_memories_for_concept(concept_id)
            
            for memory in memories:
                if memory.filename == memory_filename:
                    continue
                
                # Get concepts for candidate
                candidate_concepts = set(
                    c.id for c in self.get_concepts_for_memory(memory.filename)
                )
                
                # Calculate Jaccard similarity
                intersection = source_concepts.intersection(candidate_concepts)
                union = source_concepts.union(candidate_concepts)
                
                similarity = len(intersection) / len(union) if union else 0
                
                candidates[memory.filename] = max(
                    candidates.get(memory.filename, 0),
                    similarity
                )
        
        # Sort and return top N
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_suggestions]
        
        results = []
        for filename, score in sorted_candidates:
            memory = self.memory_manager.get_memory(filename)
            if memory:
                results.append((memory, score))
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "num_memories_with_concepts": len(self._memory_to_concepts),
            "num_concepts_with_memories": len(self._concept_to_memories),
            "total_links": sum(
                len(concepts) for concepts in self._memory_to_concepts.values()
            ),
            "avg_concepts_per_memory": (
                sum(len(c) for c in self._memory_to_concepts.values()) / len(self._memory_to_concepts)
                if self._memory_to_concepts else 0
            ),
            "avg_memories_per_concept": (
                sum(len(m) for m in self._concept_to_memories.values()) / len(self._concept_to_memories)
                if self._concept_to_memories else 0
            ),
        }


def create_symbolic_memory_integration(
    memory_manager: MemoryManager,
    symbolic_engine: Optional[SymbolicReasoning] = None
) -> SymbolicMemoryIntegration:
    """
    Convenience function to create symbolic-memory integration.
    
    Args:
        memory_manager: Memory manager instance
        symbolic_engine: Optional symbolic engine
        
    Returns:
        SymbolicMemoryIntegration instance
        
    Example:
        >>> from whitemagic import MemoryManager
        >>> manager = MemoryManager()
        >>> integration = create_symbolic_memory_integration(manager)
        >>> integration.extract_concepts_from_memory("my_memory.md")
    """
    return SymbolicMemoryIntegration(memory_manager, symbolic_engine)
