"""Tests for universal token tracking — P5."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from whitemagic.core.monitoring.token_tracker import (
    _estimate_tokens,
    _determine_locality,
    mw_token_tracker,
)
from whitemagic.tools.middleware import DispatchContext


class TestEstimateTokens(unittest.TestCase):
    """Test token estimation."""

    def test_string_estimation(self) -> None:
        self.assertEqual(_estimate_tokens("hello world"), 2)  # 11 chars // 4
        self.assertEqual(_estimate_tokens(""), 1)  # min 1
        self.assertEqual(_estimate_tokens("a"), 1)

    def test_dict_estimation(self) -> None:
        result = _estimate_tokens({"key": "value", "num": 42})
        self.assertGreater(result, 0)

    def test_list_estimation(self) -> None:
        result = _estimate_tokens(["hello", "world"])
        self.assertEqual(result, 2)

    def test_non_string(self) -> None:
        self.assertEqual(_estimate_tokens(42), 0)
        self.assertEqual(_estimate_tokens(None), 0)


class TestDetermineLocality(unittest.TestCase):
    """Test locality determination."""

    def test_resolved_locally_is_edge(self) -> None:
        ctx = DispatchContext(tool_name="test", kwargs={})
        result = {"resolved_locally": True}
        self.assertEqual(_determine_locality(ctx, result), "edge")

    def test_llama_cpp_is_local_llm(self) -> None:
        ctx = DispatchContext(tool_name="llama.chat", kwargs={})
        result = {"status": "success"}
        self.assertEqual(_determine_locality(ctx, result), "local_llm")

    def test_cloud_api_is_cloud(self) -> None:
        ctx = DispatchContext(tool_name="openai_complete", kwargs={})
        result = {"status": "success"}
        self.assertEqual(_determine_locality(ctx, result), "cloud")

    def test_meta_tier_edge(self) -> None:
        ctx = DispatchContext(tool_name="test", kwargs={})
        ctx.meta["inference_tier"] = "edge"
        result = {"status": "success"}
        self.assertEqual(_determine_locality(ctx, result), "edge")

    def test_meta_tier_cloud(self) -> None:
        ctx = DispatchContext(tool_name="test", kwargs={})
        ctx.meta["inference_tier"] = "cloud"
        result = {"status": "success"}
        self.assertEqual(_determine_locality(ctx, result), "cloud")

    def test_none_result_is_edge(self) -> None:
        ctx = DispatchContext(tool_name="test", kwargs={})
        self.assertEqual(_determine_locality(ctx, None), "edge")

    def test_default_is_edge(self) -> None:
        ctx = DispatchContext(tool_name="memory_store", kwargs={})
        result = {"status": "success"}
        self.assertEqual(_determine_locality(ctx, result), "edge")


class TestTokenTrackerMiddleware(unittest.TestCase):
    """Test the mw_token_tracker middleware."""

    @patch("whitemagic.core.monitoring.token_tracker.get_green_score")
    def test_tracks_tokens_for_tool_call(
        self,
        mock_gs_getter: MagicMock,
    ) -> None:
        mock_gs = MagicMock()
        mock_gs_getter.return_value = mock_gs

        ctx = DispatchContext(
            tool_name="memory_store",
            kwargs={"content": "This is a test memory with some content"},
        )

        def next_fn(c: DispatchContext) -> dict:
            return {"status": "success", "result": "stored successfully"}

        result = mw_token_tracker(ctx, next_fn)

        self.assertEqual(result["status"], "success")
        self.assertIn("metadata", result)
        self.assertIn("token_tracking", result["metadata"])
        tracking = result["metadata"]["token_tracking"]
        self.assertGreater(tracking["input_tokens"], 0)
        self.assertGreater(tracking["output_tokens"], 0)
        self.assertEqual(tracking["locality"], "edge")
        mock_gs.record_inference.assert_called_once()

    @patch("whitemagic.core.monitoring.token_tracker.get_green_score")
    def test_tracks_saved_tokens_for_local_resolution(
        self,
        mock_gs_getter: MagicMock,
    ) -> None:
        mock_gs = MagicMock()
        mock_gs_getter.return_value = mock_gs

        ctx = DispatchContext(
            tool_name="llama.chat",
            kwargs={"prompt": "What is the version?"},
        )

        def next_fn(c: DispatchContext) -> dict:
            return {
                "status": "success",
                "result": "Version 23.0.0",
                "resolved_locally": True,
                "tokens_saved": 50,
            }

        result = mw_token_tracker(ctx, next_fn)

        tracking = result["metadata"]["token_tracking"]
        self.assertEqual(tracking["tokens_saved"], 50)
        self.assertEqual(tracking["locality"], "edge")

    @patch("whitemagic.core.monitoring.token_tracker.get_green_score")
    def test_estimates_saved_tokens_when_not_provided(
        self,
        mock_gs_getter: MagicMock,
    ) -> None:
        mock_gs = MagicMock()
        mock_gs_getter.return_value = mock_gs

        ctx = DispatchContext(
            tool_name="reason",
            kwargs={"query": "test query"},
        )

        def next_fn(c: DispatchContext) -> dict:
            return {
                "status": "success",
                "result": "This is a long answer that would have required many tokens from an LLM",
                "resolved_locally": True,
                # No tokens_saved provided
            }

        result = mw_token_tracker(ctx, next_fn)

        tracking = result["metadata"]["token_tracking"]
        # Should estimate saved tokens from output length
        self.assertGreater(tracking["tokens_saved"], 0)

    @patch("whitemagic.core.monitoring.token_tracker.get_green_score")
    def test_handles_none_result(self, mock_gs_getter: MagicMock) -> None:
        mock_gs = MagicMock()
        mock_gs_getter.return_value = mock_gs

        ctx = DispatchContext(tool_name="test", kwargs={})

        def next_fn(c: DispatchContext) -> dict | None:
            return None

        result = mw_token_tracker(ctx, next_fn)
        self.assertIsNone(result)

    @patch("whitemagic.core.monitoring.token_tracker.get_green_score")
    def test_records_to_green_score(
        self,
        mock_gs_getter: MagicMock,
    ) -> None:
        mock_gs = MagicMock()
        mock_gs_getter.return_value = mock_gs

        ctx = DispatchContext(
            tool_name="memory_search",
            kwargs={"query": "find memories about testing"},
        )

        def next_fn(c: DispatchContext) -> dict:
            return {"status": "success", "results": ["mem1", "mem2"]}

        mw_token_tracker(ctx, next_fn)

        mock_gs.record_inference.assert_called_once()
        call_args = mock_gs.record_inference.call_args
        self.assertEqual(call_args.kwargs["tool"], "memory_search")
        self.assertGreater(call_args.kwargs["tokens_used"], 0)


if __name__ == "__main__":
    unittest.main()
