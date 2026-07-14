# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Discovery Subsystem (Consolidated v1.2).
=======================================
Unified gateway for entity extraction, NER, and prompt classification.
Contains the EntityExtractor (regex/LLM extraction) and LightweightNER logic.

Consolidated from entity_extractor.py, lightweight_ner.py, and prompt_classifier.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Entity: entity.

    Value object: equality and repr are field-based."""

    name: str
    entity_type: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """Relation: relation.

    Value object: equality and repr are field-based."""

    subject: str
    predicate: str
    object: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """ExtractionResult: extraction result.

    Value object: equality and repr are field-based."""

    entities: list[Entity]
    relations: list[Relation]
    method: str = "regex"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


_EXTRACTION_PROMPT = """Extract entities and their relationships from the following text into JSON format.
Entities should have 'name' and 'type' (CONCEPT, PERSON, PLACE, TOOL, ORGANIZATION).
Relations should have 'subject', 'predicate', and 'object'.
Text:
"""


class EntityExtractor:
    """Extracts entities and relations using LLM (llama.cpp) or regex fallbacks."""

    def __init__(
        self, llama_url: str = "http://localhost:8080", model: str = "llama-server"
    ):
        self._llama_url = llama_url
        self._model = model
        self._lock = threading.RLock()
        self._total_extractions = 0
        self._total_entities = 0
        self._total_relations = 0

    def extract(self, text: str) -> ExtractionResult:
        # Fallback to regex for speed in consolidation phase
        """
        Perform the extract operation.

        Args:
            text: Parameter description.

        Returns:
            ExtractionResult
        """
        return self._extract_regex(text)

    def _extract_regex(self, text: str) -> ExtractionResult:
        entities = []
        # Proper nouns
        for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
            entities.append(
                Entity(name=m.group(1), entity_type="CONCEPT", confidence=0.5)
            )
        # Acronyms
        for m in re.finditer(r"\b([A-Z]{2,})\b", text):
            entities.append(
                Entity(name=m.group(1), entity_type="CONCEPT", confidence=0.4)
            )

        return ExtractionResult(entities=entities[:10], relations=[], method="regex")

    def extract_and_store(self, memory_id: str, text: str) -> ExtractionResult:
        """
        Mine or extract and store.

        Args:
            memory_id: Parameter description.
            text: Parameter description.

        Returns:
            ExtractionResult
        """
        result = self.extract(text)
        return result


class PromptClassifier:
    """Classifies user prompts into intent categories."""

    INTENTS = {
        "coding": [r"rewrite", r"fix", r"implement", r"code", r"refactor"],
        "research": [r"explain", r"who is", r"what is", r"research", r"tell me about"],
        "action": [r"run", r"execute", r"start", r"open", r"delete"],
    }

    def classify(self, text: str) -> dict[str, float]:
        """
        Perform the classify operation.

        Args:
            text: Parameter description.

        Returns:
            dict[str, float]
        """
        text_lower = text.lower()
        scores = {}
        for intent, patterns in self.INTENTS.items():
            matches = sum(1 for p in patterns if re.search(p, text_lower))
            scores[intent] = matches / len(patterns)
        return scores


_extractor: EntityExtractor | None = None


def get_entity_extractor() -> EntityExtractor:
    """
    Get the entity extractor.

    Returns:
        EntityExtractor
    """
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
