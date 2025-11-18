"""
Symbolic Reasoning Engine - Concept representation with Chinese character support.

This module provides symbolic reasoning capabilities with optional Chinese character
encoding for enhanced semantic density and token efficiency.

Philosophy:
- Concepts are nodes with both English and Chinese representations
- Chinese characters provide semantic compression (30-50% token savings)
- Toggle-able: Use Chinese internally, English for APIs
- Based on ancient wisdom: 道 (Dao), 理 (Li), 法 (Fa)

Design:
- Concept nodes with multi-lingual support
- Relationships between concepts
- Semantic density tracking
- Token efficiency measurements

Based on I Ching principle: 象 (Xiang) - Symbolic representation
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ConceptType(Enum):
    """Types of concepts in the system."""

    PRINCIPLE = "principle"  # 原則 - Core principle
    METHOD = "method"  # 方法 - Method or approach
    PATTERN = "pattern"  # 模式 - Recurring pattern
    STATE = "state"  # 狀態 - System state
    ACTION = "action"  # 行動 - Action or operation
    ENTITY = "entity"  # 實體 - Concrete entity
    QUALITY = "quality"  # 性質 - Quality or attribute


@dataclass
class ConceptNode:
    """
    A concept node with multi-lingual representation.

    Supports both English and Chinese characters for semantic compression.
    """

    id: str  # Unique identifier (e.g., "dao", "efficiency")
    english: str  # English name
    chinese: Optional[str] = None  # Chinese character(s)
    concept_type: ConceptType = ConceptType.ENTITY
    definition: str = ""  # Clear definition
    properties: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)  # Alternative names

    # Semantic information
    token_count_english: int = 0  # Tokens needed for English
    token_count_chinese: int = 0  # Tokens needed for Chinese
    compression_ratio: float = 0.0  # Chinese tokens / English tokens

    # Metadata
    created: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def __post_init__(self):
        """Calculate token counts and compression ratio."""
        if self.english:
            # Rough estimate: word count * 1.3 for English
            self.token_count_english = int(len(self.english.split()) * 1.3)

        if self.chinese:
            # Chinese: 1 character ≈ 1-2 tokens typically
            self.token_count_chinese = len(self.chinese) * 1.5

            if self.token_count_english > 0:
                self.compression_ratio = self.token_count_chinese / self.token_count_english

    def get_representation(self, use_chinese: bool = False) -> str:
        """
        Get string representation of concept.

        Args:
            use_chinese: Whether to use Chinese characters

        Returns:
            String representation
        """
        if use_chinese and self.chinese:
            return self.chinese
        return self.english

    def get_token_count(self, use_chinese: bool = False) -> int:
        """Get estimated token count for this concept."""
        if use_chinese and self.chinese:
            return self.token_count_chinese
        return self.token_count_english

    def increment_usage(self) -> None:
        """Increment usage counter."""
        self.usage_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "english": self.english,
            "chinese": self.chinese,
            "type": self.concept_type.value,
            "definition": self.definition,
            "properties": self.properties,
            "aliases": self.aliases,
            "token_count_english": self.token_count_english,
            "token_count_chinese": self.token_count_chinese,
            "compression_ratio": self.compression_ratio,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConceptNode":
        """Create ConceptNode from dictionary."""
        return cls(
            id=data["id"],
            english=data["english"],
            chinese=data.get("chinese"),
            concept_type=ConceptType(data.get("type", "entity")),
            definition=data.get("definition", ""),
            properties=data.get("properties", {}),
            aliases=data.get("aliases", []),
            token_count_english=data.get("token_count_english", 0),
            token_count_chinese=data.get("token_count_chinese", 0),
            compression_ratio=data.get("compression_ratio", 0.0),
            usage_count=data.get("usage_count", 0),
        )


class RelationshipType(Enum):
    """Types of relationships between concepts."""

    IS_A = "is_a"  # Inheritance (e.g., Dog is_a Animal)
    HAS_A = "has_a"  # Composition (e.g., Car has_a Engine)
    PART_OF = "part_of"  # Aggregation (e.g., Wheel part_of Car)
    DEPENDS_ON = "depends_on"  # Dependency
    IMPLEMENTS = "implements"  # Implementation
    RELATED_TO = "related_to"  # General relation
    CONTRADICTS = "contradicts"  # Opposition
    TRANSFORMS_TO = "transforms_to"  # State transition (Wu Xing)


@dataclass
class ConceptRelationship:
    """Relationship between two concepts."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    strength: float = 1.0  # 0.0 to 1.0
    bidirectional: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relationship_type.value,
            "strength": self.strength,
            "bidirectional": self.bidirectional,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConceptRelationship":
        """Create from dictionary."""
        return cls(
            source_id=data["source"],
            target_id=data["target"],
            relationship_type=RelationshipType(data["type"]),
            strength=data.get("strength", 1.0),
            bidirectional=data.get("bidirectional", False),
            properties=data.get("properties", {}),
        )


class SymbolicReasoning:
    """
    Symbolic reasoning engine with Chinese character support.

    Manages concepts and their relationships, with toggle-able Chinese
    character encoding for semantic compression.
    """

    def __init__(self, use_chinese: bool = False):
        """
        Initialize symbolic reasoning engine.

        Args:
            use_chinese: Whether to use Chinese characters by default
        """
        self.use_chinese = use_chinese
        self.concepts: Dict[str, ConceptNode] = {}
        self.relationships: List[ConceptRelationship] = []

        # Statistics
        self.total_queries = 0
        self.chinese_queries = 0
        self.token_savings = 0

    def add_concept(
        self,
        concept_id: str,
        english: str,
        chinese: Optional[str] = None,
        concept_type: ConceptType = ConceptType.ENTITY,
        definition: str = "",
        properties: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None,
    ) -> ConceptNode:
        """
        Add a new concept to the system.

        Args:
            concept_id: Unique identifier
            english: English name
            chinese: Optional Chinese character(s)
            concept_type: Type of concept
            definition: Clear definition
            properties: Additional properties
            aliases: Alternative names

        Returns:
            Created ConceptNode
        """
        if concept_id in self.concepts:
            raise ValueError(f"Concept '{concept_id}' already exists")

        concept = ConceptNode(
            id=concept_id,
            english=english,
            chinese=chinese,
            concept_type=concept_type,
            definition=definition,
            properties=properties or {},
            aliases=aliases or [],
        )

        self.concepts[concept_id] = concept
        return concept

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Get a concept by ID."""
        return self.concepts.get(concept_id)

    def find_concept(self, query: str) -> Optional[ConceptNode]:
        """
        Find a concept by English name, Chinese, or alias.

        Args:
            query: Search query

        Returns:
            Found ConceptNode or None
        """
        query_lower = query.lower()

        for concept in self.concepts.values():
            # Check English name
            if concept.english.lower() == query_lower:
                return concept

            # Check Chinese
            if concept.chinese and concept.chinese == query:
                return concept

            # Check aliases
            if any(alias.lower() == query_lower for alias in concept.aliases):
                return concept

        return None

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        strength: float = 1.0,
        bidirectional: bool = False,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ConceptRelationship:
        """
        Add a relationship between concepts.

        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            relationship_type: Type of relationship
            strength: Relationship strength (0.0 to 1.0)
            bidirectional: Whether relationship goes both ways
            properties: Additional properties

        Returns:
            Created ConceptRelationship
        """
        if source_id not in self.concepts:
            raise ValueError(f"Source concept '{source_id}' not found")
        if target_id not in self.concepts:
            raise ValueError(f"Target concept '{target_id}' not found")

        relationship = ConceptRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=strength,
            bidirectional=bidirectional,
            properties=properties or {},
        )

        self.relationships.append(relationship)
        return relationship

    def get_related_concepts(
        self,
        concept_id: str,
        relationship_type: Optional[RelationshipType] = None,
        min_strength: float = 0.0,
    ) -> List[Tuple[ConceptNode, ConceptRelationship]]:
        """
        Get concepts related to a given concept.

        Args:
            concept_id: Concept to find relations for
            relationship_type: Optional filter by relationship type
            min_strength: Minimum relationship strength

        Returns:
            List of (related_concept, relationship) tuples
        """
        related = []

        for rel in self.relationships:
            # Check if this relationship involves our concept
            target_id = None

            if rel.source_id == concept_id:
                target_id = rel.target_id
            elif rel.bidirectional and rel.target_id == concept_id:
                target_id = rel.source_id

            if target_id is None:
                continue

            # Apply filters
            if relationship_type and rel.relationship_type != relationship_type:
                continue

            if rel.strength < min_strength:
                continue

            # Get target concept
            target_concept = self.concepts.get(target_id)
            if target_concept:
                related.append((target_concept, rel))

        return related

    def calculate_token_savings(self) -> Dict[str, Any]:
        """
        Calculate potential token savings using Chinese characters.

        Returns:
            Dictionary with token savings statistics
        """
        total_english = sum(c.token_count_english for c in self.concepts.values())
        total_chinese = sum(
            c.token_count_chinese if c.chinese else c.token_count_english
            for c in self.concepts.values()
        )

        savings = total_english - total_chinese
        savings_pct = (savings / total_english * 100) if total_english > 0 else 0

        chinese_available = sum(1 for c in self.concepts.values() if c.chinese)
        total_concepts = len(self.concepts)
        coverage = (chinese_available / total_concepts * 100) if total_concepts > 0 else 0

        return {
            "total_concepts": total_concepts,
            "concepts_with_chinese": chinese_available,
            "chinese_coverage_pct": coverage,
            "english_tokens": total_english,
            "chinese_tokens": total_chinese,
            "token_savings": savings,
            "savings_pct": savings_pct,
            "avg_compression_ratio": total_chinese / total_english if total_english > 0 else 1.0,
        }

    def query_concept(self, concept_id: str, use_chinese: Optional[bool] = None) -> str:
        """
        Query a concept and get its representation.

        Tracks usage statistics for token savings analysis.

        Args:
            concept_id: Concept to query
            use_chinese: Override default Chinese setting

        Returns:
            String representation of concept
        """
        concept = self.get_concept(concept_id)
        if not concept:
            return concept_id

        use_cn = use_chinese if use_chinese is not None else self.use_chinese

        # Update statistics
        self.total_queries += 1
        if use_cn:
            self.chinese_queries += 1

        concept.increment_usage()

        # Calculate token savings
        if use_cn and concept.chinese:
            saved = concept.token_count_english - concept.token_count_chinese
            self.token_savings += saved

        return concept.get_representation(use_cn)

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        savings_info = self.calculate_token_savings()

        return {
            **savings_info,
            "total_queries": self.total_queries,
            "chinese_queries": self.chinese_queries,
            "chinese_usage_pct": (
                self.chinese_queries / self.total_queries * 100 if self.total_queries > 0 else 0
            ),
            "actual_token_savings": self.token_savings,
        }

    def export_graph(self) -> Dict[str, Any]:
        """
        Export concept graph for visualization.

        Returns:
            Dictionary with nodes and edges
        """
        nodes = [
            {
                "id": c.id,
                "label": c.get_representation(self.use_chinese),
                "type": c.concept_type.value,
                "tokens": c.get_token_count(self.use_chinese),
            }
            for c in self.concepts.values()
        ]

        edges = [
            {
                "source": r.source_id,
                "target": r.target_id,
                "type": r.relationship_type.value,
                "strength": r.strength,
            }
            for r in self.relationships
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "use_chinese": self.use_chinese,
            "statistics": self.get_statistics(),
        }

    def save(self, path: Path) -> None:
        """
        Save symbolic reasoning state to file.

        Args:
            path: Path to save JSON file
        """
        data = {
            "use_chinese": self.use_chinese,
            "concepts": [c.to_dict() for c in self.concepts.values()],
            "relationships": [r.to_dict() for r in self.relationships],
            "statistics": self.get_statistics(),
        }

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: Path) -> "SymbolicReasoning":
        """
        Load symbolic reasoning state from file.

        Args:
            path: Path to JSON file

        Returns:
            Loaded SymbolicReasoning instance
        """
        data = json.loads(path.read_text())

        engine = cls(use_chinese=data.get("use_chinese", False))

        # Load concepts
        for concept_data in data.get("concepts", []):
            concept = ConceptNode.from_dict(concept_data)
            engine.concepts[concept.id] = concept

        # Load relationships
        for rel_data in data.get("relationships", []):
            rel = ConceptRelationship.from_dict(rel_data)
            engine.relationships.append(rel)

        return engine


def create_symbolic_engine(use_chinese: bool = False) -> SymbolicReasoning:
    """
    Convenience function to create a symbolic reasoning engine.

    Args:
        use_chinese: Whether to use Chinese characters

    Returns:
        SymbolicReasoning instance

    Example:
        >>> engine = create_symbolic_engine(use_chinese=True)
        >>> engine.add_concept("dao", "The Way", "道", ConceptType.PRINCIPLE)
        >>> engine.query_concept("dao")  # Returns: "道"
    """
    return SymbolicReasoning(use_chinese=use_chinese)
