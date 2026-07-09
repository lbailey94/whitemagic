"""Unit tests for llama.cpp agent loop — tool call parsing, completion detection, system prompt."""

from unittest.mock import patch

from whitemagic.tools.handlers.llama_agent import (
    _build_system_prompt,
    _check_completion,
    _parse_tool_calls,
    handle_llama_agent,
)


class TestParseToolCalls:
    """Test tool-call parsing from model responses."""

    def test_parse_json_code_block(self):
        response = 'I will search for that.\n```json\n{"tool": "memory_search", "args": {"query": "test"}}\n```\nLet me check.'
        calls = _parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0]["tool"] == "memory_search"
        assert calls[0]["args"]["query"] == "test"

    def test_parse_inline_marker(self):
        response = 'Working on it.\n[TOOL_CALL]{"tool": "kg_query", "args": {"node": "ai"}}[/TOOL_CALL]\nDone.'
        calls = _parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0]["tool"] == "kg_query"

    def test_parse_multiple_code_blocks(self):
        response = (
            '```json\n{"tool": "memory_search", "args": {"query": "a"}}\n```\n'
            'Now let me check another.\n```json\n{"tool": "kg_query", "args": {"node": "b"}}\n```'
        )
        calls = _parse_tool_calls(response)
        assert len(calls) == 2
        assert calls[0]["tool"] == "memory_search"
        assert calls[1]["tool"] == "kg_query"

    def test_parse_no_tool_calls(self):
        response = "I don't need any tools for this. The answer is 42."
        calls = _parse_tool_calls(response)
        assert len(calls) == 0

    def test_parse_invalid_json_ignored(self):
        response = '```json\n{"tool": "broken", "args":}\n```\nOops.'
        calls = _parse_tool_calls(response)
        assert len(calls) == 0

    def test_parse_parameters_alias(self):
        response = '```json\n{"tool": "search", "parameters": {"q": "test"}}\n```'
        calls = _parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0]["args"]["q"] == "test"

    def test_parse_missing_tool_key_ignored(self):
        response = '```json\n{"action": "search", "args": {"q": "test"}}\n```'
        calls = _parse_tool_calls(response)
        assert len(calls) == 0


class TestCheckCompletion:
    """Test completion detection."""

    def test_done_marker(self):
        assert _check_completion("DONE\nThe answer is 42.", []) is True

    def test_task_complete_marker(self):
        assert _check_completion("TASK_COMPLETE: All done.", []) is True

    def test_complete_marker_case_insensitive(self):
        assert _check_completion("complete - finished processing", []) is True

    def test_finished_marker(self):
        assert _check_completion("FINISHED", []) is True

    def test_no_marker_no_calls_long_response(self):
        # Long response with no tool calls = completion
        assert (
            _check_completion(
                "This is a long response that has no tool calls in it.", []
            )
            is True
        )

    def test_no_marker_with_calls_not_complete(self):
        calls = [{"tool": "search", "args": {}}]
        assert _check_completion("Let me search for that.", calls) is False

    def test_short_response_no_calls_not_complete(self):
        # Short response (<50 chars) without marker = not complete
        assert _check_completion("Working...", []) is False

    def test_done_with_tool_calls(self):
        # DONE marker takes precedence
        calls = [{"tool": "search", "args": {}}]
        assert _check_completion("DONE - all tools used.", calls) is True


class TestBuildSystemPrompt:
    """Test system prompt construction."""

    def test_default_prompt_has_tool_instructions(self):
        prompt = _build_system_prompt(None)
        assert "WhiteMagic" in prompt
        assert "tool" in prompt.lower()
        assert "```json" in prompt

    def test_prompt_with_specific_tools(self):
        tools = ["memory_search", "kg_query", "analysis"]
        prompt = _build_system_prompt(tools)
        assert "memory_search" in prompt
        assert "kg_query" in prompt
        assert "analysis" in prompt

    def test_prompt_mentions_done(self):
        prompt = _build_system_prompt(None)
        assert "DONE" in prompt


class TestHandleLlamaAgent:
    """Test the main handler function."""

    def test_missing_task(self):
        result = handle_llama_agent(model="llama3.2", task="")
        assert result["status"] == "error"
        assert result["error_code"] == "invalid_params"

    def test_no_task_key(self):
        result = handle_llama_agent(model="llama3.2")
        assert result["status"] == "error"
        assert result["error_code"] == "invalid_params"

    def test_llama_cpp_unavailable(self):
        """When llama-server is not running, should return service_unavailable."""
        from unittest.mock import MagicMock

        mock_backend = MagicMock()
        mock_backend.is_available = False
        with (
            patch(
                "whitemagic.inference.llama_cpp.get_llama_cpp_backend",
                return_value=mock_backend,
            ),
        ):
            result = handle_llama_agent(
                model="llama-server",
                task="test task",
            )
        assert result["status"] == "error"
        assert result["error_code"] == "service_unavailable"
