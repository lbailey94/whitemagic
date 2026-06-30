"""Tests for token budget feedback loop in InferenceRouter."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.inference.complexity import InferenceTier
from whitemagic.inference.router import InferenceRouter, TokenBudgetTracker


class TestTokenBudgetTracker(unittest.TestCase):
    """Test TokenBudgetTracker in isolation."""

    def test_initial_state(self) -> None:
        tracker = TokenBudgetTracker(total_budget=10_000)
        self.assertEqual(tracker.remaining, 10_000)
        self.assertAlmostEqual(tracker.usage_ratio, 0.0)
        self.assertFalse(tracker.is_warning)
        self.assertFalse(tracker.is_critical)

    def test_record_usage(self) -> None:
        tracker = TokenBudgetTracker(total_budget=10_000)
        tracker.record_usage(500, 1500)
        self.assertEqual(tracker.remaining, 8_000)
        self.assertAlmostEqual(tracker.usage_ratio, 0.2)
        self.assertEqual(tracker._request_count, 1)

    def test_warning_threshold(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000, warning_threshold=0.7)
        tracker.record_usage(600, 200)  # 80% used
        self.assertTrue(tracker.is_warning)
        self.assertFalse(tracker.is_critical)

    def test_critical_threshold(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000, critical_threshold=0.9)
        tracker.record_usage(800, 200)  # 100% used
        self.assertTrue(tracker.is_critical)
        self.assertTrue(tracker.is_warning)

    def test_recommend_downgrade_none_when_healthy(self) -> None:
        tracker = TokenBudgetTracker(total_budget=10_000)
        self.assertIsNone(tracker.recommend_downgrade(InferenceTier.CLOUD))

    def test_recommend_downgrade_warning(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000, warning_threshold=0.7)
        tracker.record_usage(600, 200)  # 80%
        result = tracker.recommend_downgrade(InferenceTier.LOCAL_LARGE)
        self.assertEqual(result, InferenceTier.LOCAL_SMALL)

    def test_recommend_downgrade_critical(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000, critical_threshold=0.9)
        tracker.record_usage(800, 200)  # 100%
        result = tracker.recommend_downgrade(InferenceTier.CLOUD)
        self.assertEqual(result, InferenceTier.EDGE_RULES)

    def test_no_downgrade_at_edge_rules(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000, critical_threshold=0.9)
        tracker.record_usage(800, 200)
        self.assertIsNone(tracker.recommend_downgrade(InferenceTier.EDGE_RULES))

    def test_reset(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000)
        tracker.record_usage(500, 500)
        tracker.reset()
        self.assertEqual(tracker.remaining, 1_000)
        self.assertEqual(tracker._request_count, 0)

    def test_reset_with_new_budget(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000)
        tracker.record_usage(500, 500)
        tracker.reset(new_budget=5_000)
        self.assertEqual(tracker.remaining, 5_000)

    def test_summary(self) -> None:
        tracker = TokenBudgetTracker(total_budget=1_000)
        tracker.record_usage(300, 200)
        s = tracker.summary()
        self.assertEqual(s["total_budget"], 1_000)
        self.assertEqual(s["used_tokens"], 500)
        self.assertEqual(s["remaining"], 500)
        self.assertAlmostEqual(s["usage_ratio"], 0.5)
        self.assertFalse(s["is_warning"])
        self.assertFalse(s["is_critical"])
        self.assertEqual(s["request_count"], 1)


class TestRouterBudgetFeedback(unittest.TestCase):
    """Test token budget feedback integration in InferenceRouter."""

    def test_router_has_budget_tracker(self) -> None:
        router = InferenceRouter(token_budget=5_000)
        self.assertIsNotNone(router.budget_tracker)
        self.assertEqual(router.budget_tracker.remaining, 5_000)

    def test_budget_downgrade_in_route(self) -> None:
        """Router should downgrade tier when budget is low."""
        router = InferenceRouter(token_budget=1_000, confidence_threshold=0.0)

        # Register a mock handler for LOCAL_SMALL
        mock_handler = MagicMock(
            return_value={
                "answer": "test answer",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)
        router.register_handler(InferenceTier.LOCAL_LARGE, mock_handler)
        router.register_handler(InferenceTier.EDGE_RULES, mock_handler)

        # Use most of the budget
        router.budget_tracker.record_usage(800, 100)  # 90% used → critical

        # Route a prompt that would normally go to LOCAL_SMALL
        response = router.route("What is 2+2?")

        # Should be downgraded to EDGE_RULES due to critical budget
        self.assertEqual(response.tier, InferenceTier.EDGE_RULES)
        self.assertIn("budget_downgrade", response.metadata.get("assessment", {}))

    def test_budget_recorded_after_routing(self) -> None:
        """Router should record token usage after each successful route."""
        router = InferenceRouter(token_budget=10_000)

        mock_handler = MagicMock(
            return_value={
                "answer": "The answer is forty two",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)

        initial_used = router.budget_tracker._used_tokens
        router.route("What is the meaning of life?")
        self.assertGreater(router.budget_tracker._used_tokens, initial_used)

    def test_budget_summary_in_metadata(self) -> None:
        """Response metadata should include token budget summary."""
        router = InferenceRouter(token_budget=10_000)

        mock_handler = MagicMock(
            return_value={
                "answer": "yes",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.EDGE_RULES, mock_handler)
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)
        router.register_handler(InferenceTier.LOCAL_LARGE, mock_handler)

        response = router.route("Is the sky blue?")
        self.assertIn("token_budget", response.metadata)
        self.assertIn("remaining", response.metadata["token_budget"])

    def test_no_downgrade_when_budget_healthy(self) -> None:
        """Router should not downgrade when budget is healthy."""
        router = InferenceRouter(token_budget=100_000)

        mock_handler = MagicMock(
            return_value={
                "answer": "test",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)

        response = router.route("What is 2+2?")
        self.assertEqual(response.tier, InferenceTier.LOCAL_SMALL)
        self.assertNotIn("budget_downgrade", response.metadata.get("assessment", {}))


class TestSelfModelRouterFeedback(unittest.TestCase):
    """Test SelfModel forecast integration in InferenceRouter."""

    def test_no_upgrade_when_no_alerts(self) -> None:
        """Router should not upgrade when self-model has no alerts."""
        router = InferenceRouter()
        mock_handler = MagicMock(
            return_value={
                "answer": "test",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)

        # SelfModel singleton may have alerts from other tests — mock it
        with patch("whitemagic.core.intelligence.self_model.get_self_model") as mock_sm:
            mock_model = MagicMock()
            mock_model.get_alerts.return_value = []
            mock_sm.return_value = mock_model

            response = router.route("What is 2+2?")
            self.assertNotIn(
                "self_model_upgrade", response.metadata.get("assessment", {})
            )

    def test_upgrade_on_critical_error_rate_forecast(self) -> None:
        """Router should upgrade tier when error_rate is forecast critical."""
        from whitemagic.core.intelligence.self_model import Forecast

        router = InferenceRouter()

        mock_handler = MagicMock(
            return_value={
                "answer": "test",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)
        router.register_handler(InferenceTier.LOCAL_LARGE, mock_handler)

        critical_forecast = Forecast(
            metric="error_rate",
            current=0.25,
            predicted=0.35,
            trend="rising",
            slope=0.01,
            confidence=0.8,
            steps_ahead=10,
            alert="error_rate predicted to hit critical high (0.3) in ~3 steps",
            threshold_eta=3,
        )

        with patch("whitemagic.core.intelligence.self_model.get_self_model") as mock_sm:
            mock_model = MagicMock()
            mock_model.get_alerts.return_value = [critical_forecast]
            mock_sm.return_value = mock_model

            response = router.route("What is 2+2?")
            self.assertIn("self_model_upgrade", response.metadata.get("assessment", {}))
            upgrade_info = response.metadata["assessment"]["self_model_upgrade"]
            self.assertEqual(upgrade_info["from"], "LOCAL_SMALL")
            self.assertEqual(upgrade_info["to"], "LOCAL_LARGE")

    def test_no_upgrade_at_cloud_tier(self) -> None:
        """Router should not upgrade beyond CLOUD."""
        from whitemagic.core.intelligence.self_model import Forecast

        router = InferenceRouter(cloud_available=True)

        mock_handler = MagicMock(
            return_value={
                "answer": "test",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.CLOUD, mock_handler)

        critical_forecast = Forecast(
            metric="error_rate",
            current=0.25,
            predicted=0.35,
            trend="rising",
            slope=0.01,
            confidence=0.8,
            steps_ahead=10,
            alert="error_rate critical",
            threshold_eta=2,
        )

        with patch("whitemagic.core.intelligence.self_model.get_self_model") as mock_sm:
            mock_model = MagicMock()
            mock_model.get_alerts.return_value = [critical_forecast]
            mock_sm.return_value = mock_model

            # Force cloud tier
            response = router.route(
                "Write a comprehensive research paper on quantum computing",
                force_tier=InferenceTier.CLOUD,
            )
            self.assertNotIn(
                "self_model_upgrade", response.metadata.get("assessment", {})
            )

    def test_no_upgrade_when_eta_too_far(self) -> None:
        """Router should not upgrade when threshold_eta > 5 steps."""
        from whitemagic.core.intelligence.self_model import Forecast

        router = InferenceRouter()

        mock_handler = MagicMock(
            return_value={
                "answer": "test",
                "confidence": 0.95,
                "metadata": {},
            }
        )
        router.register_handler(InferenceTier.LOCAL_SMALL, mock_handler)

        far_forecast = Forecast(
            metric="error_rate",
            current=0.15,
            predicted=0.25,
            trend="rising",
            slope=0.005,
            confidence=0.6,
            steps_ahead=10,
            alert="error_rate trending toward warning high",
            threshold_eta=10,
        )

        with patch("whitemagic.core.intelligence.self_model.get_self_model") as mock_sm:
            mock_model = MagicMock()
            mock_model.get_alerts.return_value = [far_forecast]
            mock_sm.return_value = mock_model

            response = router.route("What is 2+2?")
            self.assertNotIn(
                "self_model_upgrade", response.metadata.get("assessment", {})
            )


if __name__ == "__main__":
    unittest.main()
