"""Tests for the inference router middleware (P0)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.tools.middleware import (
    DispatchContext,
    mw_inference_router,
    _is_inference_tool,
    _extract_prompt,
)


class TestInferenceToolDetection(unittest.TestCase):
    """Test the inference tool pattern matching."""

    def test_detects_ollama(self) -> None:
        self.assertTrue(_is_inference_tool("ollama_chat"))
        self.assertTrue(_is_inference_tool("ollama_generate"))

    def test_detects_reason(self) -> None:
        self.assertTrue(_is_inference_tool("reason"))
        self.assertTrue(_is_inference_tool("bicameral_reason"))

    def test_detects_edge_infer(self) -> None:
        self.assertTrue(_is_inference_tool("edge_infer"))

    def test_does_not_match_memory_tools(self) -> None:
        self.assertFalse(_is_inference_tool("memory_store"))
        self.assertFalse(_is_inference_tool("galaxy_list"))
        self.assertFalse(_is_inference_tool("gana_horn"))


class TestExtractPrompt(unittest.TestCase):
    """Test prompt extraction from kwargs."""

    def test_extracts_prompt(self) -> None:
        self.assertEqual(_extract_prompt("test", {"prompt": "hello"}), "hello")

    def test_extracts_query(self) -> None:
        self.assertEqual(_extract_prompt("test", {"query": "what is x?"}), "what is x?")

    def test_extracts_message(self) -> None:
        self.assertEqual(_extract_prompt("test", {"message": "hi"}), "hi")

    def test_returns_none_for_empty(self) -> None:
        self.assertIsNone(_extract_prompt("test", {"prompt": ""}))
        self.assertIsNone(_extract_prompt("test", {}))

    def test_returns_none_for_non_string(self) -> None:
        self.assertIsNone(_extract_prompt("test", {"prompt": 123}))


class TestInferenceRouterMiddleware(unittest.TestCase):
    """Test the mw_inference_router middleware."""

    def setUp(self) -> None:
        """Pre-cache middleware dependencies so @patch decorators aren't overridden."""
        from whitemagic.tools.middleware import _ensure_cached

        _ensure_cached()

    def test_non_inference_tool_passes_through(self) -> None:
        """Non-inference tools should pass through unchanged."""
        ctx = DispatchContext(tool_name="memory_store", kwargs={"content": "test"})
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "stored"}

        result = mw_inference_router(ctx, next_fn)
        self.assertTrue(called[0])
        self.assertEqual(result["result"], "stored")

    def test_inference_tool_without_prompt_passes_through(self) -> None:
        """Inference tool without a prompt should pass through."""
        ctx = DispatchContext(tool_name="ollama_chat", kwargs={"model": "llama2"})
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "generated"}

        result = mw_inference_router(ctx, next_fn)
        self.assertTrue(called[0])
        self.assertEqual(result["result"], "generated")

    @patch("whitemagic.tools.middleware._get_edge_inference")
    @patch("whitemagic.tools.middleware._get_green_score")
    def test_edge_inference_short_circuits_on_high_confidence(
        self,
        mock_green: MagicMock,
        mock_edge_getter: MagicMock,
    ) -> None:
        """When edge inference returns high confidence, should short-circuit."""
        mock_edge = MagicMock()
        mock_result = MagicMock()
        mock_result.confidence = 0.95
        mock_result.answer = "WhiteMagic version 23.0.0"
        mock_result.method = "rule:version"
        mock_result.tokens_equivalent = 50
        mock_result.latency_ms = 0.5
        mock_edge.infer.return_value = mock_result
        mock_edge_getter.return_value = mock_edge

        mock_gs = MagicMock()
        mock_green.return_value = mock_gs

        ctx = DispatchContext(
            tool_name="ollama_chat",
            kwargs={"prompt": "what version is whitemagic?"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success"}

        result = mw_inference_router(ctx, next_fn)

        self.assertFalse(called[0], "next_fn should NOT have been called")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["resolved_locally"])
        self.assertEqual(result["result"], "WhiteMagic version 23.0.0")
        self.assertEqual(result["tokens_saved"], 50)
        mock_gs.record_inference.assert_called_once()

    @patch("whitemagic.tools.middleware._reason_locally", None)
    @patch("whitemagic.tools.middleware._get_edge_inference")
    def test_edge_inference_low_confidence_passes_through(
        self,
        mock_edge_getter: MagicMock,
    ) -> None:
        """When edge inference returns low confidence, should pass through."""
        mock_edge = MagicMock()
        mock_result = MagicMock()
        mock_result.confidence = 0.3
        mock_result.answer = "I don't know"
        mock_result.method = "fallback"
        mock_result.tokens_equivalent = 0
        mock_result.latency_ms = 1.0
        mock_edge.infer.return_value = mock_result
        mock_edge_getter.return_value = mock_edge

        ctx = DispatchContext(
            tool_name="ollama_chat",
            kwargs={"prompt": "explain quantum entanglement"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "quantum explanation"}

        result = mw_inference_router(ctx, next_fn)

        self.assertTrue(called[0], "next_fn SHOULD have been called")
        self.assertEqual(result["result"], "quantum explanation")
        self.assertTrue(ctx.meta.get("local_inference_attempted"))

    @patch("whitemagic.tools.middleware._get_edge_inference", None)
    @patch("whitemagic.tools.middleware._reason_locally")
    def test_local_reasoning_short_circuits_when_ready(
        self,
        mock_reason: MagicMock,
    ) -> None:
        """When local reasoning resolves fully, should short-circuit."""
        mock_result = MagicMock()
        mock_result.insights = [
            MagicMock(source="test", content="answer", relevance=0.9)
        ]
        mock_result.ready_for_ai = False
        mock_result.summary = "Resolved locally"
        mock_result.total_tokens_saved = 100
        mock_result.duration_ms = 5.0
        mock_reason.return_value = mock_result

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "how many tests?"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success"}

        result = mw_inference_router(ctx, next_fn)

        self.assertFalse(called[0], "next_fn should NOT have been called")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["resolved_locally"])
        self.assertEqual(result["result"], "Resolved locally")
        self.assertEqual(result["tokens_saved"], 100)

    @patch("whitemagic.tools.middleware._get_edge_inference", None)
    @patch("whitemagic.tools.middleware._reason_locally")
    def test_local_reasoning_passes_through_when_ai_needed(
        self,
        mock_reason: MagicMock,
    ) -> None:
        """When local reasoning says AI needed, should pass through."""
        mock_result = MagicMock()
        mock_result.insights = [
            MagicMock(source="test", content="partial", relevance=0.5)
        ]
        mock_result.ready_for_ai = True
        mock_result.summary = "Partial"
        mock_result.total_tokens_saved = 10
        mock_result.duration_ms = 3.0
        mock_reason.return_value = mock_result

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "complex question"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "ai answer"}

        result = mw_inference_router(ctx, next_fn)

        self.assertTrue(called[0])
        self.assertEqual(result["result"], "ai answer")


class TestCompositionalReasoningIntegration(unittest.TestCase):
    """Test compositional reasoning integration in inference router."""

    def setUp(self) -> None:
        """Pre-cache middleware dependencies so @patch decorators aren't overridden."""
        from whitemagic.tools.middleware import _ensure_cached

        _ensure_cached()

    @patch("whitemagic.tools.middleware._reason_locally", None)
    @patch("whitemagic.tools.middleware._get_edge_inference", None)
    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_compositional_reasoner"
    )
    def test_relation_query_short_circuits(self, mock_get_reasoner: MagicMock) -> None:
        """Relation queries should be resolved by compositional reasoning."""
        from whitemagic.core.intelligence.agentic.compositional_reasoning import (
            CompositionalResult,
        )

        mock_reasoner = MagicMock()
        mock_reasoner.can_resolve.return_value = True
        mock_reasoner.resolve.return_value = CompositionalResult(
            resolved=True,
            answer="Via CAUSES relation: the outage was caused by a config error",
            method="hrr:inverse:CAUSES",
            confidence=0.75,
            relation="CAUSES",
            projected_query="the outage",
            matches=[
                {"title": "config error", "content": "bad config", "similarity": 0.75}
            ],
            tokens_saved=50,
            latency_ms=0.5,
        )
        mock_get_reasoner.return_value = mock_reasoner

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "what caused the outage?"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "should not reach here"}

        result = mw_inference_router(ctx, next_fn)

        self.assertFalse(
            called[0], "Should not pass through — resolved by compositional reasoning"
        )
        self.assertTrue(result["resolved_locally"])
        self.assertEqual(result["method"], "hrr:inverse:CAUSES")
        self.assertEqual(result["relation"], "CAUSES")
        self.assertGreater(result["tokens_saved"], 0)

    @patch("whitemagic.tools.middleware._reason_locally", None)
    @patch("whitemagic.tools.middleware._get_edge_inference", None)
    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_compositional_reasoner"
    )
    def test_non_relation_query_passes_through(
        self, mock_get_reasoner: MagicMock
    ) -> None:
        """Non-relation queries should not trigger compositional reasoning."""
        mock_reasoner = MagicMock()
        mock_reasoner.can_resolve.return_value = False
        mock_get_reasoner.return_value = mock_reasoner

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "what is the weather?"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "sunny"}

        result = mw_inference_router(ctx, next_fn)

        # Should pass through (compositional reasoning didn't resolve via middleware)
        self.assertTrue(called[0])

    @patch("whitemagic.tools.middleware._reason_locally", None)
    @patch("whitemagic.tools.middleware._get_edge_inference", None)
    @patch(
        "whitemagic.core.intelligence.agentic.compositional_reasoning.get_compositional_reasoner"
    )
    def test_low_confidence_passes_through(self, mock_get_reasoner: MagicMock) -> None:
        """Low-confidence compositional results should pass through to next tier."""
        from whitemagic.core.intelligence.agentic.compositional_reasoning import (
            CompositionalResult,
        )

        mock_reasoner = MagicMock()
        mock_reasoner.can_resolve.return_value = True
        mock_reasoner.resolve.return_value = CompositionalResult(
            resolved=True,
            answer="weak answer",
            method="hrr:inverse:CAUSES",
            confidence=0.15,  # Below 0.3 threshold
            relation="CAUSES",
            tokens_saved=5,
            latency_ms=0.3,
        )
        mock_get_reasoner.return_value = mock_reasoner

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "what caused the bug?"},
        )
        called = [False]

        def next_fn(c: DispatchContext) -> dict:
            called[0] = True
            return {"status": "success", "result": "better answer from LLM"}

        result = mw_inference_router(ctx, next_fn)

        # Should pass through because confidence < 0.3
        self.assertTrue(called[0])
        self.assertEqual(result["result"], "better answer from LLM")


if __name__ == "__main__":
    unittest.main()
