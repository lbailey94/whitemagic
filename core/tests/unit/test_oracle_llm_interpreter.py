"""Tests for LLM-Powered Oracle Interpretation (Phase 6).

Tests verify:
- OracleLLMInterpreter instantiation and availability check
- Template-based fallback interpretation works
- LLM interpretation path (mocked)
- Prompt building from synthesis result
- Graceful degradation when LLM unavailable
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from whitemagic.oracle.llm_interpreter import OracleLLMInterpreter, get_oracle_interpreter


class TestOracleLLMInterpreter:
    """Test the LLM-powered oracle interpreter."""

    def test_instantiation(self):
        interpreter = OracleLLMInterpreter()
        assert interpreter is not None
        assert isinstance(interpreter.available, bool)

    def test_get_oracle_interpreter_singleton(self):
        i1 = get_oracle_interpreter()
        i2 = get_oracle_interpreter()
        assert i1 is i2

    def test_template_interpret_with_question(self):
        interpreter = OracleLLMInterpreter()
        mock_result = MagicMock()
        mock_result.unified_message = "The path is clear."
        mock_result.primary_hexagram = 32
        mock_result.elemental_harmony = "Fire and water in balance"
        mock_result.practical_guidance = "Persevere with patience"
        mock_result.cautions = ["Avoid haste"]
        mock_result.blessings = ["Good fortune awaits"]
        mock_result.hrr_resonances = [{"hexagram": 50, "similarity": 0.65}]

        result = interpreter._template_interpret(mock_result, "Should I proceed?", {})
        assert "Should I proceed?" in result
        assert "The path is clear." in result
        assert "32" in result
        assert "Persevere with patience" in result
        assert "Avoid haste" in result
        assert "Good fortune awaits" in result

    def test_template_interpret_without_question(self):
        interpreter = OracleLLMInterpreter()
        mock_result = MagicMock()
        mock_result.unified_message = "Listen to the silence."
        mock_result.primary_hexagram = 52
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = []

        result = interpreter._template_interpret(mock_result, "", {})
        assert "The oracle speaks:" in result
        assert "Listen to the silence." in result

    def test_template_interpret_empty_result(self):
        interpreter = OracleLLMInterpreter()
        mock_result = MagicMock()
        mock_result.unified_message = ""
        mock_result.primary_hexagram = None
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = []

        result = interpreter._template_interpret(mock_result, "", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_prompt_includes_question(self):
        interpreter = OracleLLMInterpreter()
        mock_result = MagicMock()
        mock_result.unified_message = "Test message"
        mock_result.primary_hexagram = 1
        mock_result.elemental_harmony = "Fire"
        mock_result.practical_guidance = "Act now"
        mock_result.cautions = ["Be careful"]
        mock_result.blessings = ["Success"]
        mock_result.hrr_resonances = [{"hexagram": 14, "similarity": 0.5}]
        mock_result.narrative = None

        prompt = interpreter._build_prompt(mock_result, "What should I do?", {})
        assert "What should I do?" in prompt
        assert "Test message" in prompt
        assert "1" in prompt

    def test_build_prompt_with_hrr_resonances(self):
        interpreter = OracleLLMInterpreter()
        mock_result = MagicMock()
        mock_result.unified_message = "Test"
        mock_result.primary_hexagram = 32
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = [
            {"hexagram": 50, "similarity": 0.7},
            {"hexagram": 35, "similarity": 0.5},
            {"hexagram": 14, "similarity": 0.4},
        ]
        mock_result.narrative = None

        prompt = interpreter._build_prompt(mock_result, "", {})
        assert "HRR resonances" in prompt
        assert "50" in prompt
        assert "35" in prompt

    def test_interpret_falls_back_to_template(self):
        """When LLM is unavailable, should use template interpretation."""
        interpreter = OracleLLMInterpreter()
        interpreter._llm_available = False

        mock_result = MagicMock()
        mock_result.unified_message = "The way is open."
        mock_result.primary_hexagram = 42
        mock_result.elemental_harmony = "Wood nourishes fire"
        mock_result.practical_guidance = "Increase your efforts"
        mock_result.cautions = []
        mock_result.blessings = ["Abundance"]
        mock_result.hrr_resonances = []

        result = interpreter.interpret(mock_result, "How to grow?")
        assert "How to grow?" in result
        assert "The way is open." in result

    def test_interpret_with_llm_mocked(self):
        """When LLM is available, should use it for interpretation."""
        interpreter = OracleLLMInterpreter()
        interpreter._llm_available = True
        interpreter._backend = MagicMock()
        interpreter._backend.chat.return_value = "The stars align for your endeavor."

        mock_result = MagicMock()
        mock_result.unified_message = "Test"
        mock_result.primary_hexagram = 14
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = []
        mock_result.narrative = None

        result = interpreter.interpret(mock_result, "What about wealth?")
        assert "The stars align" in result
        assert interpreter._backend.chat.called

    def test_interpret_llm_exception_falls_back(self):
        """If LLM call fails, should fall back to template."""
        interpreter = OracleLLMInterpreter()
        interpreter._llm_available = True
        interpreter._backend = MagicMock()
        interpreter._backend.chat.side_effect = Exception("LLM error")

        mock_result = MagicMock()
        mock_result.unified_message = "Template fallback works."
        mock_result.primary_hexagram = 1
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = []
        mock_result.narrative = None

        result = interpreter.interpret(mock_result, "Test?")
        assert "Template fallback works." in result

    def test_interpret_with_context(self):
        """Context should be passed through without errors."""
        interpreter = OracleLLMInterpreter()
        interpreter._llm_available = False

        mock_result = MagicMock()
        mock_result.unified_message = "Context received."
        mock_result.primary_hexagram = 5
        mock_result.elemental_harmony = ""
        mock_result.practical_guidance = ""
        mock_result.cautions = []
        mock_result.blessings = []
        mock_result.hrr_resonances = []
        mock_result.narrative = None

        result = interpreter.interpret(
            mock_result, "Test?",
            context={"urgency": "high", "domain": "career"},
        )
        assert isinstance(result, str)
        assert len(result) > 0
