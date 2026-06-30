"""Tests for Corpus Callosum Bus."""

from unittest.mock import MagicMock, patch

from whitemagic.core.intelligence.corpus_callosum import (
    CorpusCallosumBus,
    DebateResult,
    DebateRound,
    SynthesisArbiter,
)
from whitemagic.core.intelligence.hemisphere_agents import (
    LeftHemisphereAgent,
    RightHemisphereAgent,
)


def _mock_bicameral_result(tension: float = 0.5):
    """Create a mock BicameralResult for fast testing."""
    result = MagicMock()
    result.left_analysis.content = f"Left analysis with tension {tension}"
    result.right_analysis.content = f"Right analysis with tension {tension}"
    left_crit = MagicMock()
    left_crit.challenges = ["Left challenges right's assumptions"]
    right_crit = MagicMock()
    right_crit.challenges = ["Right challenges left's constraints"]
    result.cross_critique = [left_crit, right_crit]
    result.tension_score = tension
    return result


class TestDebateRound:
    def test_to_dict(self):
        r = DebateRound(
            round_number=1,
            left_position="left",
            right_position="right",
            left_critique="lc",
            right_critique="rc",
            tension=0.5,
        )
        d = r.to_dict()
        assert d["round_number"] == 1
        assert d["tension"] == 0.5


class TestSynthesisArbiter:
    def test_should_escalate(self):
        assert SynthesisArbiter.should_escalate(0.95) is True
        assert SynthesisArbiter.should_escalate(0.89) is False

    def test_synthesize_consensus(self):
        rounds = [DebateRound(1, "l", "r", "lc", "rc", 0.1)]
        text, tension, dominant = SynthesisArbiter.synthesize("topic", rounds)
        assert "CONSENSUS" in text
        assert dominant == "balanced"

    def test_synthesize_tension(self):
        rounds = [
            DebateRound(1, "l", "r", "lc", "rc", 0.8),
            DebateRound(2, "l", "r", "lc", "rc", 0.95),
        ]
        text, tension, dominant = SynthesisArbiter.synthesize("topic", rounds)
        assert "TENSION" in text or "ESCALATED" in text
        assert tension == 0.95

    def test_synthesize_empty(self):
        text, tension, dominant = SynthesisArbiter.synthesize("topic", [])
        assert "No debate occurred" in text


class TestCorpusCallosumBus:
    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_debate_produces_result(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.3)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Should we refactor memory tiers?")
        assert isinstance(result, DebateResult)
        assert result.topic == "Should we refactor memory tiers?"
        assert len(result.rounds) >= 1
        assert result.debate_id.startswith("debate_")
        assert result.timestamp is not None

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_debate_low_tension_consensus(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.2)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Should we add comments to code?")
        assert result.final_tension < 0.9
        assert result.escalated is False
        assert "CONSENSUS" in result.synthesis or "SYNTHESIS" in result.synthesis

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_get_debate(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.3)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Topic A")
        fetched = bus.get_debate(result.debate_id)
        assert fetched is not None
        assert fetched.debate_id == result.debate_id

    def test_get_missing_debate(self):
        bus = CorpusCallosumBus()
        assert bus.get_debate("nonexistent") is None

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_status(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.3)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        bus.debate("Topic B")
        status = bus.status()
        assert status["total_debates"] >= 1
        assert "recent_avg_tension" in status

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_max_three_rounds(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.3)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Topic C")
        assert len(result.rounds) <= CorpusCallosumBus.MAX_ROUNDS

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_karma_logged(self, mock_br_cls, mock_get_br, mock_run):
        mock_run.return_value = _mock_bicameral_result(0.3)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Topic D")
        assert result.karma_logged is True

    @patch("whitemagic.core.intelligence.corpus_callosum.asyncio.run")
    @patch("whitemagic.core.intelligence.bicameral.get_bicameral_reasoner")
    @patch("whitemagic.core.intelligence.bicameral.BicameralReasoner")
    def test_followup_rounds_receive_context(self, mock_br_cls, mock_get_br, mock_run):
        """Rounds 2+3 should use real BicameralReasoner with prior round context."""
        mock_run.return_value = _mock_bicameral_result(0.4)
        mock_get_br.return_value = MagicMock()
        mock_br_cls.return_value = MagicMock()
        bus = CorpusCallosumBus()
        result = bus.debate("Topic E")
        # All 3 rounds should call asyncio.run (real reasoner path)
        assert mock_run.call_count == 3


class TestHemisphereAgents:
    def test_left_propose(self):
        agent = LeftHemisphereAgent()
        text = agent.propose("test")
        assert "LEFT" in text
        assert "rigorous" in text.lower()

    def test_right_propose(self):
        agent = RightHemisphereAgent()
        text = agent.propose("test")
        assert "RIGHT" in text
        assert "creative" in text.lower() or "emergent" in text.lower()

    def test_left_critique(self):
        agent = LeftHemisphereAgent()
        text = agent.critique("be creative")
        assert "LEFT→RIGHT" in text

    def test_right_critique(self):
        agent = RightHemisphereAgent()
        text = agent.critique("be safe")
        assert "RIGHT→LEFT" in text
