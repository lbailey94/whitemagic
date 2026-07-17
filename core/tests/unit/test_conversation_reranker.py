"""Unit tests for conversation_reranker.py."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from dataclasses import dataclass, field
from typing import Any

from whitemagic.core.memory.conversation_reranker import (
    detect_answer_type,
    conversation_rerank,
    _extract_conv_id,
    _extract_turn_idx,
    _marker_score,
    _OPINION_MARKERS,
)


@dataclass
class FakeMem:
    id: str = "m1"
    content: str = "test content"
    title: str | None = None
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


class TestDetectAnswerType:
    def test_opinion(self):
        assert detect_answer_type("What did Alice think about machine learning?") == "opinion"

    def test_opinion_say(self):
        assert detect_answer_type("What did Bob say about the deadline?") == "opinion"

    def test_preference(self):
        assert detect_answer_type("What is Alice's favorite food?") == "preference"

    def test_fact(self):
        assert detect_answer_type("What is the deadline for the project?") == "fact"

    def test_general(self):
        assert detect_answer_type("Tell me about machine learning") == "general"

    def test_how_many(self):
        assert detect_answer_type("How many people are on the team?") == "fact"


class TestExtractConvId:
    def test_from_tags(self):
        m = FakeMem(tags={"user", "conv_0001"})
        assert _extract_conv_id(m) == "conv_0001"

    def test_from_title(self):
        m = FakeMem(title="conv_0002_turn_15")
        assert _extract_conv_id(m) == "conv_0002"

    def test_from_metadata(self):
        m = FakeMem(metadata={"conversation_id": "conv_0003"})
        assert _extract_conv_id(m) == "conv_0003"

    def test_none(self):
        m = FakeMem()
        assert _extract_conv_id(m) is None


class TestExtractTurnIdx:
    def test_from_title(self):
        m = FakeMem(title="conv_0000_turn_15")
        assert _extract_turn_idx(m) == 15

    def test_none(self):
        m = FakeMem()
        assert _extract_turn_idx(m) is None


class TestMarkerScore:
    def test_full_match(self):
        content = "I think we should recommend this. In my opinion it's great."
        score = _marker_score(content, _OPINION_MARKERS)
        assert score == 1.0

    def test_no_match(self):
        score = _marker_score("The project uses Python", _OPINION_MARKERS)
        assert score == 0.0


class TestConversationRerank:
    def test_empty(self):
        assert conversation_rerank("test", [], limit=10) == []

    def test_single(self):
        m = FakeMem(content="hello")
        assert conversation_rerank("test", [m], limit=10) == [m]

    def test_opinion_boost(self):
        """Opinion content should be boosted for opinion queries."""
        m_factual = FakeMem(
            id="m1", content="The project uses Python and Rust. The budget is $50,000.",
            title="conv_0000_turn_1", tags={"conv_0000"},
            metadata={"blended_score": 0.5},
        )
        m_opinion = FakeMem(
            id="m2", content="I think we should use Python. I'd recommend it personally.",
            title="conv_0000_turn_5", tags={"conv_0000"},
            metadata={"blended_score": 0.5},
        )
        results = conversation_rerank(
            "What did Alice think about the project?",
            [m_factual, m_opinion], limit=10,
        )
        assert results[0].id == "m_opinion" or results[0].id == "m2"

    def test_conversation_grouping(self):
        """Results from the dominant conversation should be boosted."""
        m_other = FakeMem(
            id="m1", content="Some random content about topics",
            title="conv_0001_turn_1", tags={"conv_0001"},
            metadata={"blended_score": 0.6},
        )
        m_same = FakeMem(
            id="m2", content="Related content about the same topic",
            title="conv_0000_turn_3", tags={"conv_0000"},
            metadata={"blended_score": 0.55},
        )
        m_top = FakeMem(
            id="m3", content="Best matching content about the topic",
            title="conv_0000_turn_1", tags={"conv_0000"},
            metadata={"blended_score": 0.9},
        )
        results = conversation_rerank("What is the topic?", [m_other, m_same, m_top], limit=10)
        # m_top should be first (highest base + conv group)
        assert results[0].id == "m3"
        # m_same should be boosted above m_other due to conv grouping
        assert results[1].id == "m2"

    def test_turn_position(self):
        """Later turns should get a slight boost."""
        m_early = FakeMem(
            id="m1", content="Talking about project deadlines",
            title="conv_0000_turn_1", tags={"conv_0000"},
            metadata={"blended_score": 0.5},
        )
        m_late = FakeMem(
            id="m2", content="The deadline is next Friday for the project",
            title="conv_0000_turn_29", tags={"conv_0000"},
            metadata={"blended_score": 0.5},
        )
        results = conversation_rerank(
            "What is the deadline for the project?",
            [m_early, m_late], limit=10,
        )
        # m_late should be boosted by turn position
        assert results[0].id == "m2"

    def test_metadata_annotated(self):
        """Results should have conv_rerank_score and answer_type in metadata."""
        m = FakeMem(content="test", title="conv_0000_turn_1", tags={"conv_0000"},
                     metadata={"blended_score": 0.5})
        results = conversation_rerank("What did Alice think?", [m], limit=10)
        assert "conv_rerank_score" in results[0].metadata
        assert results[0].metadata["answer_type"] == "opinion"
