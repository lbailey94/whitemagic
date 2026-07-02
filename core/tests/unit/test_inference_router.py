# ruff: noqa: BLE001
"""Tests for inference routing — complexity classifier, router, and metrics."""

from __future__ import annotations

from whitemagic.inference.complexity import InferenceTier, classify_prompt
from whitemagic.inference.router import InferenceRouter
from whitemagic.inference.routing_metrics import RoutingMetrics


class TestComplexityClassifier:
    """Test the complexity classifier."""

    def test_greeting_routes_to_edge(self):
        result = classify_prompt("hello there")
        assert result.tier == InferenceTier.EDGE_RULES
        assert result.task_type == "greeting"

    def test_classification_routes_to_local_small(self):
        result = classify_prompt("classify this message as urgent or normal")
        assert result.tier == InferenceTier.LOCAL_SMALL
        assert result.task_type == "classification"

    def test_coding_routes_to_local_large(self):
        result = classify_prompt("implement a binary search tree in Python")
        assert result.tier == InferenceTier.LOCAL_LARGE
        assert result.task_type == "coding"

    def test_multi_step_routes_to_cloud(self):
        result = classify_prompt("create a multi-step pipeline for data analysis")
        assert result.tier == InferenceTier.CLOUD
        assert result.task_type == "multi_step"

    def test_sensitive_data_overrides_cloud(self):
        result = classify_prompt(
            "analyze this credit card statement: 4532-XXXX-XXXX-XXXX"
        )
        assert result.is_sensitive is True
        assert result.tier <= InferenceTier.LOCAL_LARGE

    def test_tool_call_escalation(self):
        result = classify_prompt("search memory for similar patterns")
        assert result.needs_tool_calls is True
        assert result.tier >= InferenceTier.LOCAL_LARGE

    def test_token_budget_escalation(self):
        result = classify_prompt("summarize this text", max_output_tokens=3000)
        assert result.tier >= InferenceTier.CLOUD
        assert "escalation_reason" in result.signals

    def test_latency_budget_override(self):
        result = classify_prompt(
            "analyze the codebase architecture", latency_budget_ms=50
        )
        assert result.tier == InferenceTier.EDGE_RULES
        assert result.signals.get("latency_budget_override") is True

    def test_short_query_default(self):
        result = classify_prompt("what is 2+2")
        # No pattern matches — falls to word count heuristic (4 words < 10)
        assert result.tier == InferenceTier.LOCAL_SMALL
        assert result.task_type == "short_query"

    def test_long_query_escalation(self):
        long_prompt = " ".join(["word"] * 100)
        result = classify_prompt(long_prompt)
        assert result.tier >= InferenceTier.LOCAL_LARGE
        assert result.task_type == "long_query"

    def test_multi_turn_detection(self):
        result = classify_prompt("first do X, then do Y, and finally do Z")
        assert result.is_multi_turn is True
        assert result.tier >= InferenceTier.LOCAL_LARGE

    def test_estimated_output_tokens_extraction(self):
        result = classify_prompt("extract the key entities from this text")
        assert result.estimated_output_tokens > 0
        assert result.estimated_output_tokens < 500  # Extraction is concise

    def test_estimated_output_tokens_creative(self):
        result = classify_prompt(
            "write a creative story about a robot", max_output_tokens=2000
        )
        assert result.estimated_output_tokens == 2000


class TestRoutingMetrics:
    """Test routing observability metrics."""

    def test_record_routing(self):
        metrics = RoutingMetrics()
        metrics.record_routing(
            InferenceTier.LOCAL_SMALL, 150.0, 0.9, True, "classification"
        )
        summary = metrics.summary()
        assert summary["total_routed"] == 1
        assert "LOCAL_SMALL" in summary["tiers"]

    def test_record_escalation(self):
        metrics = RoutingMetrics()
        metrics.record_escalation(
            InferenceTier.LOCAL_SMALL, InferenceTier.LOCAL_LARGE, "low_confidence"
        )
        summary = metrics.summary()
        assert summary["total_escalations"] == 1

    def test_percentile_calculation(self):
        metrics = RoutingMetrics()
        for i in range(100):
            metrics.record_routing(
                InferenceTier.EDGE_RULES, float(i), 0.9, True, "test"
            )
        summary = metrics.summary()
        assert summary["tiers"]["EDGE_RULES"]["p50_ms"] > 0
        assert (
            summary["tiers"]["EDGE_RULES"]["p95_ms"]
            >= summary["tiers"]["EDGE_RULES"]["p50_ms"]
        )

    def test_drift_detection(self):
        metrics = RoutingMetrics()
        # Not enough data for drift detection
        drift = metrics.detect_drift()
        assert drift["status"] == "ok"


class TestInferenceRouter:
    """Test the inference router with mock handlers."""

    def _make_mock_handler(self, answer: str, confidence: float):
        def handler(prompt: str, **kwargs):
            return {
                "answer": answer,
                "confidence": confidence,
                "metadata": {"mock": True},
            }

        return handler

    def test_edge_rules_success(self):
        router = InferenceRouter()
        router.register_handler(
            InferenceTier.EDGE_RULES, self._make_mock_handler("Hi!", 1.0)
        )
        response = router.route("hello")
        assert response.tier == InferenceTier.EDGE_RULES
        assert response.answer == "Hi!"
        assert response.confidence == 1.0
        assert response.escalated is False

    def test_confidence_cascade(self):
        router = InferenceRouter(confidence_threshold=0.9)
        router.register_handler(
            InferenceTier.EDGE_RULES, self._make_mock_handler("maybe", 0.5)
        )
        router.register_handler(
            InferenceTier.LOCAL_SMALL, self._make_mock_handler("better answer", 0.95)
        )
        response = router.route("hello")
        assert response.escalated is True
        assert response.tier == InferenceTier.LOCAL_SMALL
        assert response.answer == "better answer"
        assert InferenceTier.EDGE_RULES in response.escalation_chain

    def test_max_escalations_limit(self):
        router = InferenceRouter(confidence_threshold=0.99, max_escalations=1)
        router.register_handler(
            InferenceTier.EDGE_RULES, self._make_mock_handler("low", 0.3)
        )
        router.register_handler(
            InferenceTier.LOCAL_LLAMA_CPP, self._make_mock_handler("low2", 0.3)
        )
        router.register_handler(
            InferenceTier.LOCAL_SMALL, self._make_mock_handler("medium", 0.5)
        )
        router.register_handler(
            InferenceTier.LOCAL_LARGE, self._make_mock_handler("high", 0.95)
        )
        response = router.route("hello")
        # Should only escalate once from EDGE to next tier
        assert len(response.escalation_chain) <= 1

    def test_sensitive_data_no_cloud(self):
        router = InferenceRouter()
        cloud_called = []

        def cloud_handler(prompt: str, **kwargs):
            cloud_called.append(True)
            return {"answer": "cloud", "confidence": 1.0}

        router.register_handler(
            InferenceTier.EDGE_RULES, self._make_mock_handler("", 0.0)
        )
        router.register_handler(
            InferenceTier.LOCAL_SMALL, self._make_mock_handler("", 0.0)
        )
        router.register_handler(
            InferenceTier.LOCAL_LARGE, self._make_mock_handler("local answer", 0.9)
        )
        router.register_handler(InferenceTier.CLOUD, cloud_handler)

        response = router.route("analyze this credit card number: 4532-1234-5678-9012")
        assert cloud_called == []  # Cloud should never be called for sensitive data
        assert response.tier <= InferenceTier.LOCAL_LARGE

    def test_force_tier(self):
        router = InferenceRouter()
        router.register_handler(
            InferenceTier.CLOUD, self._make_mock_handler("cloud answer", 1.0)
        )
        response = router.route("hello", force_tier=InferenceTier.CLOUD)
        assert response.tier == InferenceTier.CLOUD
        assert response.answer == "cloud answer"

    def test_no_handler_escalation(self):
        router = InferenceRouter()
        # No edge handler registered
        router.register_handler(
            InferenceTier.LOCAL_SMALL, self._make_mock_handler("local", 0.9)
        )
        response = router.route("hello")
        assert response.tier == InferenceTier.LOCAL_SMALL
        assert response.escalated is True

    def test_handler_error_escalation(self):
        router = InferenceRouter()

        def error_handler(prompt: str, **kwargs):
            raise RuntimeError("handler crashed")

        router.register_handler(InferenceTier.EDGE_RULES, error_handler)
        router.register_handler(
            InferenceTier.LOCAL_SMALL, self._make_mock_handler("fallback", 0.9)
        )
        response = router.route("hello")
        assert response.tier == InferenceTier.LOCAL_SMALL
        assert response.escalated is True

    def test_metrics_tracked(self):
        router = InferenceRouter()
        router.register_handler(
            InferenceTier.EDGE_RULES, self._make_mock_handler("hi", 1.0)
        )
        router.route("hello")
        summary = router.metrics_summary
        assert summary["total_routed"] >= 1

    def test_all_tiers_exhausted(self):
        router = InferenceRouter(max_escalations=0)
        # No handlers registered at all
        response = router.route("hello")
        assert response.confidence == 0.0
        assert (
            "No inference handler" in response.answer
            or "exhausted" in response.answer.lower()
        )

    def test_adaptive_thresholds(self):
        from whitemagic.inference.routing_metrics import get_routing_metrics

        metrics = get_routing_metrics()
        # Record enough samples for EDGE_RULES to get adaptive recommendation
        for _ in range(25):
            metrics.record_routing(InferenceTier.EDGE_RULES, 0.5, 0.95, True, "test")
        thresholds = metrics.adaptive_thresholds()
        assert "EDGE_RULES" in thresholds
        assert 0.5 <= thresholds["EDGE_RULES"] <= 0.99

    def test_export_dashboard(self):
        from whitemagic.inference.routing_metrics import get_routing_metrics

        metrics = get_routing_metrics()
        metrics.record_routing(InferenceTier.EDGE_RULES, 1.0, 0.9, True, "test")
        dashboard = metrics.export_dashboard()
        assert "routing" in dashboard
        assert "drift" in dashboard
        assert "adaptive_thresholds" in dashboard
        assert "exported_at" in dashboard

    def test_mound_metrics_export(self):
        from whitemagic.inference.routing_metrics import get_routing_metrics

        metrics = get_routing_metrics()
        metrics.record_routing(InferenceTier.LOCAL_SMALL, 50.0, 0.88, True, "test")
        mound = metrics.to_mound_metrics()
        assert "routing.total_routed" in mound
        assert "routing.local_small.requests" in mound
        assert "routing.local_small.p50_ms" in mound
        assert isinstance(mound["routing.total_routed"], float)
