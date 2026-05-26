"""Lightweight NER Engine (v16) - Fast Pattern-Based Named Entity Recognition.
===========================================================================
Provides fast, dependency-free named entity recognition using regex patterns.
No spaCy or ML models required - pure pattern matching.

Entity Types:
  - PERSON: Names (capitalized, common patterns)
  - PROJECT: Software projects, codebases
  - TECH: Technologies, languages, frameworks
  - ORG: Organizations, companies
  - CONCEPT: Abstract concepts, methodologies
  - TOOL: Tools, libraries, APIs
  - EVENT: Events, dates, milestones
  - LOCATION: Places, coordinates

Usage:
    from whitemagic.core.intelligence.lightweight_ner import LightNER

    ner = LightNER()
    entities = ner.extract("WhiteMagic uses Rust for embedding acceleration")
    # entities = [Entity("WhiteMagic", "PROJECT"), Entity("Rust", "TECH")]
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EntityMatch:
    """A matched entity from NER."""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }


# ============================================================================
# Entity Patterns
# ============================================================================

# Technology patterns - common languages, frameworks, tools
TECH_PATTERNS = [
    # Programming languages
    r"\b(Python|Rust|Zig|Mojo|Go|Golang|Elixir|Haskell|Julia|TypeScript|JavaScript|"
    r"Java|Kotlin|Swift|Rust|C\+\+|C#|Ruby|PHP|Scala|Clojure|F#|OCaml|Erlang)\b",

    # Frameworks & Libraries
    r"\b(React|Vue|Angular|Svelte|Next\.js|Nuxt|Django|Flask|FastAPI|Express|"
    r"Tauri|Electron|TensorFlow|PyTorch|Transformers|HuggingFace|LangChain|"
    r"OpenAI|Anthropic|Claude|GPT-4|Llama|Mistral)\b",

    # Infrastructure
    r"\b(Docker|Kubernetes|Redis|PostgreSQL|SQLite|MongoDB|Elasticsearch|"
    r"gRPC|WebSocket|HTTP|REST|GraphQL|OpenTelemetry|Prometheus|Grafana)\b",

    # AI/ML specific
    r"\b(BERT|GPT|LLM|RAG|HNSW|SIMD|CUDA|ROCm|TensorRT|ONNX|Whisper|"
    r"Embeddings?|Vector|Semantic|Transformer|Attention)\b",
]

# Project patterns - capitalized project names
PROJECT_PATTERNS = [
    # Known projects
    r"\b(WhiteMagic|MandalaOS|Nexus|Grimoire|Dharma|Karma|Harmony|Wu Xing|"
    r"Gan Ying|Galactic Map|Dream Cycle|BitNet|Aria|Cosmos|Orion)\b",

    # Generic project pattern: Capitalized word(s) followed by project-like suffix
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:Project|System|Engine|Platform|Framework|OS|DB))\b",
]

# Organization patterns
ORG_PATTERNS = [
    r"\b(Google|Microsoft|Apple|Amazon|Meta|OpenAI|Anthropic|DeepMind|"
    r"HuggingFace|GitHub|GitLab|Bitbucket|NVIDIA|AMD|Intel|ARM)\b",

    # Generic org pattern: Capitalized + Inc/Corp/Ltd/LLC
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|Ltd|LLC|Company|Labs))\b",
]

# Concept patterns - abstract ideas
CONCEPT_PATTERNS = [
    r"\b(memory|knowledge|graph|embedding|semantic|vector|association|"
    r"consolidation|dream|consciousness|awareness|intelligence|wisdom|"
    r"learning|reasoning|inference|training|fine-?tuning|optimization)\b",

    # Methodologies
    r"\b(TDD|BDD|CI\/CD|DevOps|MLOps|Agile|Scrum|Kanban|Microservices|"
    r"Monolith|Serverless|Event-Driven|Domain-Driven)\b",
]

# Tool patterns - specific tools and APIs
TOOL_PATTERNS = [
    r"\b(MCP|JSON-RPC|REST API|CLI|SDK|API|Webhook|OAuth|JWT|SAML)\b",

    # File types as tools
    r"\b(\.py|\.rs|\.go|\.ts|\.js|\.json|\.yaml|\.toml|\.md|\.txt)\b",
]

# Event patterns - temporal markers
EVENT_PATTERNS = [
    # Date patterns
    r"\b(\d{4}-\d{2}-\d{2})\b",  # ISO date
    r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",  # US date
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",

    # Event keywords
    r"\b((?:release|launch|deploy|update|migration|upgrade|v\d+\.\d+(?:\.\d+)?))\b",
]

# Location patterns
LOCATION_PATTERNS = [
    r"\b(US|UK|EU|USA|California|New York|London|Tokyo|Berlin|Paris|"
    r"Seattle|San Francisco|Austin|Boston|Remote|Global)\b",
]

# Person patterns - names
PERSON_PATTERNS = [
    # Common name pattern: Capitalized First Last
    r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b",

    # Single capitalized name in context
    r"\b(?:by|from|author|creator|developer|user)\s+([A-Z][a-z]+)\b",
]

# Relation patterns - extract relationships
RELATION_PATTERNS = [
    (r"(\w[\w\s]{1,30})\s+(?:uses?|utilizes?)\s+(\w[\w\s]{1,30})", "USES"),
    (r"(\w[\w\s]{1,30})\s+(?:depends?\s+on|requires?)\s+(\w[\w\s]{1,30})", "DEPENDS_ON"),
    (r"(\w[\w\s]{1,30})\s+(?:is\s+part\s+of|belongs?\s+to)\s+(\w[\w\s]{1,30})", "PART_OF"),
    (r"(\w[\w\s]{1,30})\s+(?:implements?|provides?)\s+(\w[\w\s]{1,30})", "IMPLEMENTS"),
    (r"(\w[\w\s]{1,30})\s+(?:connects?\s+to|integrates?\s+with)\s+(\w[\w\s]{1,30})", "CONNECTS_TO"),
    (r"(\w[\w\s]{1,30})\s+(?:created|built|developed)\s+(\w[\w\s]{1,30})", "CREATED"),
    (r"(\w[\w\s]{1,30})\s+(?:extends?|inherits\s+from)\s+(\w[\w\s]{1,30})", "EXTENDS"),
    (r"(\w[\w\s]{1,30})\s+(?:contains?|includes?)\s+(\w[\w\s]{1,30})", "CONTAINS"),
    (r"(\w[\w\s]{1,30})\s+(?:causes?|triggers?)\s+(\w[\w\s]{1,30})", "CAUSES"),
    (r"(\w[\w\s]{1,30})\s+(?:followed\s+by|after)\s+(\w[\w\s]{1,30})", "FOLLOWED_BY"),
]


class LightNER:
    """Lightweight Named Entity Recognition using pattern matching.

    Features:
    - No external dependencies (pure regex)
    - Fast batch processing
    - Configurable confidence thresholds
    - Overlap resolution (longest match wins)
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        max_entities: int = 50,
        max_relations: int = 20,
    ):
        self.min_confidence = min_confidence
        self.max_entities = max_entities
        self.max_relations = max_relations

        # Compile patterns for efficiency
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns."""
        pattern_groups = {
            "TECH": TECH_PATTERNS,
            "PROJECT": PROJECT_PATTERNS,
            "ORG": ORG_PATTERNS,
            "CONCEPT": CONCEPT_PATTERNS,
            "TOOL": TOOL_PATTERNS,
            "EVENT": EVENT_PATTERNS,
            "LOCATION": LOCATION_PATTERNS,
            "PERSON": PERSON_PATTERNS,
        }

        for entity_type, patterns in pattern_groups.items():
            self._compiled_patterns[entity_type] = [
                re.compile(p, re.IGNORECASE if entity_type in {"CONCEPT", "TOOL"} else 0)
                for p in patterns
            ]

        # Compile relation patterns
        self._compiled_relations = [
            (re.compile(p, re.IGNORECASE), pred)
            for p, pred in RELATION_PATTERNS
        ]

    def extract(self, text: str) -> tuple[list[EntityMatch], list[tuple[str, str, str]]]:
        """Extract entities and relations from text.

        Returns:
            Tuple of (entities, relations) where relations are (subject, predicate, object) tuples.
        """
        if not text or not text.strip():
            return [], []

        entities: list[EntityMatch] = []
        relations: list[tuple[str, str, str]] = []

        # Extract entities by type
        for entity_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity_text = match.group(0)
                    # Skip very short matches
                    if len(entity_text) < 2:
                        continue
                    # Skip common words
                    if entity_text.lower() in {"the", "a", "an", "is", "are", "was", "were", "be", "been"}:
                        continue

                    confidence = self._get_confidence(entity_type, entity_text)
                    if confidence >= self.min_confidence:
                        entities.append(EntityMatch(
                            text=entity_text,
                            entity_type=entity_type,
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                        ))

        # Resolve overlaps (keep highest confidence or longest match)
        entities = self._resolve_overlaps(entities)

        # Limit entities
        entities = sorted(entities, key=lambda e: e.confidence, reverse=True)[:self.max_entities]

        # Extract relations
        for pattern, predicate in self._compiled_relations:
            for match in pattern.finditer(text):
                subj = match.group(1).strip()
                obj = match.group(2).strip()
                if len(subj) > 2 and len(obj) > 2:
                    relations.append((subj, predicate, obj))

        # Limit relations
        relations = relations[:self.max_relations]

        return entities, relations

    def _get_confidence(self, entity_type: str, text: str) -> float:
        """Estimate confidence based on entity type and text."""
        base_confidence = {
            "TECH": 0.9,      # Tech terms are usually correct
            "PROJECT": 0.85,  # Known projects are reliable
            "ORG": 0.85,      # Organizations are usually correct
            "CONCEPT": 0.7,   # Concepts can be ambiguous
            "TOOL": 0.8,      # Tools are fairly reliable
            "EVENT": 0.75,    # Events/dates are context-dependent
            "LOCATION": 0.8,  # Locations are usually correct
            "PERSON": 0.6,    # Person names have false positives
        }.get(entity_type, 0.5)

        # Boost confidence for known terms
        known_terms = {
            "TECH": {"python", "rust", "zig", "go", "typescript", "react", "redis", "sqlite"},
            "PROJECT": {"whitemagic", "mandalaos", "nexus", "grimoire", "aria"},
            "ORG": {"google", "microsoft", "openai", "anthropic", "huggingface"},
        }

        if entity_type in known_terms and text.lower() in known_terms[entity_type]:
            base_confidence = min(1.0, base_confidence + 0.1)

        # Reduce confidence for very short or very long matches
        if len(text) < 3:
            base_confidence *= 0.7
        elif len(text) > 30:
            base_confidence *= 0.8

        return base_confidence

    def _resolve_overlaps(self, entities: list[EntityMatch]) -> list[EntityMatch]:
        """Resolve overlapping entities by keeping the best match."""
        if not entities:
            return []

        # Sort by start position
        entities = sorted(entities, key=lambda e: e.start)

        resolved: list[EntityMatch] = []
        for entity in entities:
            # Check for overlap with existing
            overlaps = False
            for i, existing in enumerate(resolved):
                # Check if ranges overlap
                if not (entity.end <= existing.start or entity.start >= existing.end):
                    overlaps = True
                    # Keep the better one (higher confidence or longer)
                    if entity.confidence > existing.confidence or (
                        entity.confidence == existing.confidence and
                        (entity.end - entity.start) > (existing.end - existing.start)
                    ):
                        resolved[i] = entity
                    break

            if not overlaps:
                resolved.append(entity)

        return resolved

    def extract_batch(self, texts: list[str]) -> list[tuple[list[EntityMatch], list[tuple[str, str, str]]]]:
        """Extract entities from multiple texts efficiently.

        Returns:
            List of (entities, relations) tuples, one per input text.
        """
        return [self.extract(text) for text in texts]

    def get_entity_counts(self, text: str) -> dict[str, int]:
        """Get counts of entities by type."""
        entities, _ = self.extract(text)
        counts: dict[str, int] = {}
        for e in entities:
            counts[e.entity_type] = counts.get(e.entity_type, 0) + 1
        return counts


# Singleton for global use
_ner: LightNER | None = None


def get_light_ner(**kwargs: Any) -> LightNER:
    """Get the global LightNER instance."""
    global _ner
    if _ner is None:
        _ner = LightNER(**kwargs)
    return _ner
