"""
Cognitive Episode Data Model (G003)
==================================

Defines the structure for a "Thought Trace" — a unit of reasoning that can be
scored and stored in the Thought Galaxy for recursive self-improvement.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CognitiveEpisode:
    """A single episode of reasoning/thought process."""

    # Metadata
    id: str  # Unique ID (e.g. UUID)
    timestamp: datetime = field(default_factory=datetime.now)
    task_type: str = "unknown"  # e.g. "debugging", "synthesis", "coding"

    # The Thinking
    strategy: str = "default"   # e.g. "chain_of_thought", "analytical"
    thought_trace: str = ""     # The actual reasoning steps/log
    context_summary: str = ""   # Brief context of what was being solved

    # The Outcome
    outcome_score: float = 0.0  # -1.0 (fail) to +1.0 (breakthrough)
    outcome_metrics: dict[str, Any] = field(default_factory=dict) # e.g. {"tests_passed": True}

    # Associations
    related_memory_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "task_type": self.task_type,
            "strategy": self.strategy,
            "thought_trace": self.thought_trace,
            "context_summary": self.context_summary,
            "outcome_score": self.outcome_score,
            "outcome_metrics": self.outcome_metrics,
            "related_memory_ids": self.related_memory_ids,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CognitiveEpisode':
        """Deserialize from dictionary."""
        # Handle timestamp conversion
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = self.to_dict()
        # Helper for datetime serialization if needed, though to_dict handles isoformat
        return json.dumps(data, default=str)
