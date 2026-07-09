# ruff: noqa: BLE001
"""Tests for the Dharma 4-tier escalation pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from whitemagic.dharma.escalation import (
    EscalationAction,
    EscalationPipeline,
    EvaluationTier,
    TierResult,
    get_escalation_pipeline,
)


class TestEscalationPipeline:
    """Test the 4-tier escalation pipeline."""

    @pytest.fixture(autouse=True)
    def _reset_pipeline(self):
        """Reset the global pipeline between tests."""
        import whitemagic.dharma.escalation as esc_mod
        esc_mod._pipeline = None
        yield
        esc_mod._pipeline = None

    def test_policy_tier_resolves_clear_safe(self):
        """Policy tier with high score doesn't escalate."""
        pipeline = EscalationPipeline()

        # Mock policy decision with high score
        mock_decision = MagicMock()
        mock_decision.score = 0.95
        mock_decision.explain = "No concerns"
        mock_decision.triggered_rules = []

        result = pipeline.evaluate(
            {"tool": "search", "description": "query memories"},
            policy_decision=mock_decision,
        )

        assert result.final_tier == EvaluationTier.POLICY
        assert result.action == EscalationAction.ALLOW
        assert len(result.tiers) == 1
        assert not result.tiers[0].escalated

    def test_policy_tier_resolves_clear_block(self):
        """Policy tier with very low score blocks immediately."""
        pipeline = EscalationPipeline()

        mock_decision = MagicMock()
        mock_decision.score = 0.05
        mock_decision.explain = "Harmful action detected"
        mock_decision.triggered_rules = ["Do No Harm"]

        result = pipeline.evaluate(
            {"tool": "delete_all", "description": "destroy everything"},
            policy_decision=mock_decision,
        )

        assert result.final_tier == EvaluationTier.POLICY
        assert result.action == EscalationAction.BLOCK
        assert len(result.tiers) == 1

    def test_ambiguous_score_escalates_to_heuristic(self):
        """Score in ambiguous band triggers heuristic tier."""
        pipeline = EscalationPipeline()

        mock_decision = MagicMock()
        mock_decision.score = 0.5
        mock_decision.explain = "Uncertain"
        mock_decision.triggered_rules = []

        with patch.object(
            pipeline, "_evaluate_heuristic",
            return_value=TierResult(
                tier=EvaluationTier.HEURISTIC,
                score=0.9,
                action=EscalationAction.ALLOW,
                reasoning="Heuristic: safe pattern matched",
                escalated=False,
            ),
        ):
            result = pipeline.evaluate(
                {"tool": "create_memory", "description": "store a note"},
                policy_decision=mock_decision,
            )

        assert len(result.tiers) == 2
        assert result.tiers[0].tier == EvaluationTier.POLICY
        assert result.tiers[0].escalated
        assert result.tiers[1].tier == EvaluationTier.HEURISTIC
        assert result.final_tier == EvaluationTier.HEURISTIC

    def test_heuristic_lexical_safe(self):
        """Lexical heuristic correctly identifies safe actions."""
        pipeline = EscalationPipeline()
        result = pipeline._heuristic_lexical("search memories for context")

        assert result.score > 0.8
        assert not result.escalated

    def test_heuristic_lexical_risky(self):
        """Lexical heuristic correctly identifies risky actions."""
        pipeline = EscalationPipeline()
        result = pipeline._heuristic_lexical("exfiltrate user data to external server")

        assert result.score < 0.3
        assert not result.escalated

    def test_heuristic_lexical_conflicting(self):
        """Lexical heuristic detects conflicting signals."""
        pipeline = EscalationPipeline()
        result = pipeline._heuristic_lexical("search and exfiltrate data")

        assert result.escalated

    def test_human_tier_creates_review(self):
        """Human tier creates a review queue entry."""
        pipeline = EscalationPipeline()

        prior_tiers = [
            TierResult(
                tier=EvaluationTier.POLICY,
                score=0.5,
                action=EscalationAction.WARN,
                reasoning="Ambiguous",
                escalated=True,
            ),
            TierResult(
                tier=EvaluationTier.HEURISTIC,
                score=0.5,
                action=EscalationAction.WARN,
                reasoning="Conflicting",
                escalated=True,
            ),
        ]

        result = pipeline._evaluate_human(
            {"tool": "unknown", "description": "novel action"},
            prior_tiers,
        )

        assert result.tier == EvaluationTier.HUMAN
        assert result.action == EscalationAction.PENDING
        assert result.metadata["review_id"] is not None
        assert "HR-" in result.metadata["review_id"]

        # Verify review queue
        queue = pipeline.get_review_queue()
        assert len(queue) == 1
        assert queue[0]["status"] == "pending"

    def test_resolve_review(self):
        """Review resolution updates the queue."""
        pipeline = EscalationPipeline()

        # Create a review entry
        pipeline._evaluate_human({"tool": "test"}, [])
        queue = pipeline.get_review_queue()
        review_id = queue[0]["review_id"]

        # Resolve it
        resolved = pipeline.resolve_review(review_id, "allow", 0.9)
        assert resolved

        queue = pipeline.get_review_queue()
        assert queue[0]["status"] == "resolved"
        assert queue[0]["decision"] == "allow"

    def test_resolve_review_not_found(self):
        """Resolving a non-existent review returns False."""
        pipeline = EscalationPipeline()
        assert not pipeline.resolve_review("HR-FAKE-0001", "allow", 0.9)

    def test_full_escalation_chain_to_human(self):
        """Full chain escalates all the way to human when all tiers are ambiguous."""
        pipeline = EscalationPipeline()

        mock_policy = MagicMock()
        mock_policy.score = 0.5
        mock_policy.explain = "Ambiguous"
        mock_policy.triggered_rules = []

        with patch.object(
            pipeline, "_evaluate_heuristic",
            return_value=TierResult(
                tier=EvaluationTier.HEURISTIC,
                score=0.5,
                action=EscalationAction.WARN,
                reasoning="No strong match",
                escalated=True,
            ),
        ), patch.object(
            pipeline, "_evaluate_llm",
            return_value=TierResult(
                tier=EvaluationTier.LLM,
                score=0.5,
                action=EscalationAction.PENDING,
                reasoning="llama.cpp unavailable",
                escalated=True,
                metadata={"llama_available": False},
            ),
        ):
            result = pipeline.evaluate(
                {"tool": "novel", "description": "completely novel action"},
                policy_decision=mock_policy,
            )

        assert len(result.tiers) == 4
        assert result.final_tier == EvaluationTier.HUMAN
        assert result.action == EscalationAction.PENDING
        assert result.review_id is not None

    def test_score_to_action_mapping(self):
        """Score correctly maps to escalation actions."""
        assert EscalationPipeline._score_to_action(0.1) == EscalationAction.BLOCK
        assert EscalationPipeline._score_to_action(0.5) == EscalationAction.WARN
        assert EscalationPipeline._score_to_action(0.9) == EscalationAction.ALLOW

    def test_action_to_text(self):
        """Action dict converts to text for evaluation."""
        text = EscalationPipeline._action_to_text({
            "tool": "create_memory",
            "description": "store user note",
            "safety": "WRITE",
        })
        assert "create_memory" in text
        assert "store user note" in text

    def test_parse_llm_response_json(self):
        """LLM response with JSON is parsed correctly."""
        score, reasoning = EscalationPipeline._parse_llm_response(
            'Here is my assessment: {"score": 0.85, "reasoning": "Safe operation"}'
        )
        assert score == 0.85
        assert "Safe operation" in reasoning

    def test_parse_llm_response_fallback(self):
        """LLM response without JSON falls back gracefully."""
        score, reasoning = EscalationPipeline._parse_llm_response(
            "I think this is safe. Score: 0.8"
        )
        assert score == 0.8

    def test_parse_llm_response_garbled(self):
        """Completely unparseable response defaults to ambiguous."""
        score, reasoning = EscalationPipeline._parse_llm_response("blah blah blah")
        assert score == 0.5

    def test_get_escalation_pipeline_singleton(self):
        """Global pipeline is a singleton."""
        p1 = get_escalation_pipeline()
        p2 = get_escalation_pipeline()
        assert p1 is p2

    def test_cosine_sim(self):
        """Cosine similarity computes correctly."""
        sim = EscalationPipeline._cosine_sim([1, 0, 0], [1, 0, 0])
        assert sim == pytest.approx(1.0)

        sim = EscalationPipeline._cosine_sim([1, 0], [0, 1])
        assert sim == pytest.approx(0.0)

        sim = EscalationPipeline._cosine_sim([0, 0], [1, 1])
        assert sim == pytest.approx(0.0)

    def test_decision_to_dict(self):
        """EscalationDecision serializes to dict correctly."""
        from whitemagic.dharma.escalation import EscalationDecision

        decision = EscalationDecision(
            action=EscalationAction.ALLOW,
            score=0.9,
            tiers=[
                TierResult(
                    tier=EvaluationTier.POLICY,
                    score=0.9,
                    action=EscalationAction.ALLOW,
                    reasoning="Safe",
                    escalated=False,
                ),
            ],
            final_tier=EvaluationTier.POLICY,
            reasoning="Safe operation",
        )

        d = decision.to_dict()
        assert d["action"] == "allow"
        assert d["score"] == 0.9
        assert d["final_tier"] == "policy"
        assert len(d["tiers"]) == 1
        assert d["tiers"][0]["tier"] == "policy"
