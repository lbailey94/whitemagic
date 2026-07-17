"""Domain-structured persona extraction (0-token).

Inspired by Synthius-Mem's 6 cognitive domains. Extracts structured facts
from conversation turns and categorizes them into domains, creating
high-density memories that are easier for FTS5 to retrieve.

Domains:
  1. biography — personal facts (age, occupation, education, location)
  2. experiences — events, activities, places visited
  3. preferences — likes, dislikes, hobbies, tastes
  4. social_circle — relationships, friends, family
  5. work — job, projects, skills
  6. psychometrics — personality traits, values, goals

Unlike Synthius-Mem (which uses LLM extraction), this uses regex patterns
for 0-token extraction. Less accurate but free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredFact:
    """A single extracted fact with domain classification."""
    domain: str
    subject: str  # person name
    predicate: str  # what kind of fact
    object: str  # the fact value
    source_text: str  # original text snippet
    confidence: float = 0.5

    def to_content(self) -> str:
        """Render as a natural-language memory content string."""
        return f"{self.subject} {self.predicate} {self.object}. (Source: {self.source_text[:100]})"

    def to_tags(self, conv_id: str = "") -> set[str]:
        """Generate tags for this fact."""
        tags = {"locomo", "real", "structured", self.domain, f"person_{self.subject.lower().replace(' ', '_')}"}
        if conv_id:
            tags.add(f"conv_{conv_id}")
        return tags


# Domain detection patterns (ordered by specificity)
_DOMAIN_PATTERNS: list[tuple[str, str, str, float]] = [
    # (domain, predicate, regex, confidence)

    # --- Preferences ---
    ("preferences", "likes", r"(?:I\s+)?(?:like|love|enjoy|adore|am\s+passionate\s+about)\s+([^.]{3,60})", 0.7),
    ("preferences", "dislikes", r"(?:I\s+)?(?:hate|dislike|can't\s+stand|don't\s+like|detest)\s+([^.]{3,60})", 0.7),
    ("preferences", "favorite", r"(?:my\s+)?favorite\s+(\w+)\s+is\s+([^.]{3,60})", 0.8),
    ("preferences", "prefers", r"(?:I\s+)?(?:prefer|would\s+rather)\s+([^.]{3,60})", 0.7),
    ("preferences", "hobby", r"(?:I\s+)?(?:enjoy|like\s+to)\s+(\w+ing[^.]{3,50})", 0.6),

    # --- Biography ---
    ("biography", "age", r"(?:I\s+am|I'm)\s+(\d{2})\s+years?\s+old", 0.9),
    ("biography", "occupation", r"(?:I\s+am|I'm|I\s+work\s+as)\s+(?:a|an)\s+([^.]{3,40})", 0.7),
    ("biography", "education", r"(?:I\s+)?(?:studied|graduated\s+from|go\s+to|went\s+to)\s+([^.]{3,60})", 0.7),
    ("biography", "location", r"(?:I\s+)?(?:live\s+in|from|moved\s+to|based\s+in)\s+([A-Z][^.]{3,50})", 0.7),
    ("biography", "born", r"(?:born\s+in|born\s+on)\s+([^.]{3,40})", 0.8),

    # --- Experiences ---
    ("experiences", "visited", r"(?:I\s+)?(?:visited|went\s+to|traveled\s+to)\s+([^.]{3,60})", 0.7),
    ("experiences", "attended", r"(?:I\s+)?(?:attended|went\s+to|joined)\s+(?:a|an|the)\s+([^.]{3,60})", 0.7),
    ("experiences", "started", r"(?:I\s+)?(?:started|began|took\s+up)\s+([^.]{3,60})", 0.6),
    ("experiences", "happened", r"(?:I\s+)?(?:happened|occurred|experienced)\s+([^.]{3,60})", 0.5),
    ("experiences", "event", r"(?:I\s+)?(?:went\s+to|participated\s+in|joined)\s+([^.]{3,60})", 0.6),

    # --- Social Circle ---
    ("social_circle", "friend", r"(?:my\s+)?friend\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", 0.6),
    ("social_circle", "family", r"(?:my\s+)?(?:sister|brother|mother|father|mom|dad|son|daughter|wife|husband|partner|cousin)\s+([A-Z][a-z]+)?", 0.7),
    ("social_circle", "met", r"(?:I\s+)?(?:met|ran\s+into|caught\s+up\s+with)\s+([A-Z][^.]{3,50})", 0.6),
    ("social_circle", "relationship", r"(?:my\s+)?(?:girlfriend|boyfriend|partner|spouse)\s+([A-Z][a-z]+)?", 0.7),

    # --- Work ---
    ("work", "project", r"(?:I'm\s+)?(?:working\s+on|building|developing|creating)\s+([^.]{3,60})", 0.7),
    ("work", "job", r"(?:I\s+)?(?:work\s+at|joined|hired\s+at|employed\s+at)\s+([^.]{3,50})", 0.7),
    ("work", "skill", r"(?:I\s+)?(?:learned|know|skilled\s+at|proficient\s+in)\s+([^.]{3,50})", 0.6),
    ("work", "promotion", r"(?:I\s+)?(?:promoted|got\s+a\s+new\s+position|advanced\s+to)\s+([^.]{3,50})", 0.7),

    # --- Psychometrics ---
    ("psychometrics", "value", r"(?:I\s+)?(?:believe|value|care\s+about|important\s+to\s+me\s+is)\s+([^.]{3,60})", 0.6),
    ("psychometrics", "goal", r"(?:I\s+)?(?:want\s+to|planning\s+to|hoping\s+to|goal\s+is\s+to)\s+([^.]{3,60})", 0.6),
    ("psychometrics", "feeling", r"(?:I\s+)?(?:feel|felt|feeling)\s+([^.]{3,40})", 0.5),
    ("psychometrics", "personality", r"(?:I'm\s+)?(?:a\s+)?(?:shy|outgoing|introverted|extroverted|creative|analytical|organized|spontaneous)\s+person", 0.6),
]


def extract_facts_from_turn(
    speaker: str,
    text: str,
    conv_id: str = "",
) -> list[StructuredFact]:
    """Extract structured facts from a single conversation turn.

    Args:
        speaker: Name of the person speaking.
        text: The turn text.
        conv_id: Conversation ID for tagging.

    Returns:
        List of extracted StructuredFact objects.
    """
    facts: list[StructuredFact] = []
    if not text or not text.strip():
        return facts

    for domain, predicate, pattern, confidence in _DOMAIN_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            obj = match.group(1) if match.groups() else match.group(0)
            if obj is None:
                continue
            obj = obj.strip().rstrip(".,;!?")
            if len(obj) < 2:
                continue

            # Avoid duplicates within same turn
            if any(f.domain == domain and f.predicate == predicate and f.object.lower() == obj.lower() for f in facts):
                continue

            facts.append(StructuredFact(
                domain=domain,
                subject=speaker,
                predicate=predicate,
                object=obj,
                source_text=text[:200],
                confidence=confidence,
            ))

    return facts


def extract_facts_from_conversation(
    turns: list[dict[str, str]],
    conv_id: str = "",
) -> list[StructuredFact]:
    """Extract all structured facts from a conversation's turns.

    Deduplicates facts across turns (same subject+predicate+object).
    """
    all_facts: list[StructuredFact] = []
    seen: set[tuple[str, str, str, str]] = set()

    for turn in turns:
        speaker = turn.get("speaker", "")
        text = turn.get("text", "")
        if not speaker or not text:
            continue

        turn_facts = extract_facts_from_turn(speaker, text, conv_id)
        for fact in turn_facts:
            key = (fact.subject.lower(), fact.domain, fact.predicate, fact.object.lower())
            if key not in seen:
                seen.add(key)
                all_facts.append(fact)

    return all_facts


def ingest_structured_facts(
    memory_store: Any,
    facts: list[StructuredFact],
    conv_id: str = "",
    galaxy: str = "locomo_real",
) -> int:
    """Ingest structured facts as high-density memories.

    Each fact becomes a separate memory with domain tags, making it
    easy for FTS5 to find the exact fact when queried.

    Returns number of facts ingested.
    """
    ingested = 0
    for fact in facts:
        content = fact.to_content()
        title = f"locomo_{conv_id}_{fact.domain}_{fact.subject}_{fact.predicate}_{hash(fact.object) % 10000}"
        tags = fact.to_tags(conv_id)
        metadata = {
            "source": "locomo_real_structured",
            "domain": fact.domain,
            "predicate": fact.predicate,
            "subject": fact.subject,
            "object": fact.object,
            "confidence": fact.confidence,
            "conversation_id": f"conv_{conv_id}",
            "is_structured_fact": True,
        }

        memory_store.store(
            content=content,
            title=title,
            tags=tags,
            galaxy=galaxy,
            metadata=metadata,
            importance=0.8,  # Structured facts are high-importance
        )
        ingested += 1

    return ingested


def get_domain_stats(facts: list[StructuredFact]) -> dict[str, int]:
    """Get statistics about extracted facts by domain."""
    stats: dict[str, int] = {}
    for fact in facts:
        stats[fact.domain] = stats.get(fact.domain, 0) + 1
    return stats
