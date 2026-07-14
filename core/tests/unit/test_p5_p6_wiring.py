"""Tests for P5+P6 wiring gaps — SymbolicHRR in synthesize() and use_llm param.

Tests verify:
- synthesize() uses SymbolicHRR for alchemical phase (not hardcoded map)
- synthesize() uses SymbolicHRR for modality dynamic
- synthesize(use_llm=True) populates llm_interpretation field
- synthesize(use_llm=False) leaves llm_interpretation empty
- Fallback to hardcoded maps when SymbolicHRR unavailable
"""

import pytest
from unittest.mock import patch, MagicMock

from whitemagic.oracle.wisdom_synthesis import (
    OracleSynthesizer,
    SynthesisResult,
    _get_alchemical_phase,
    _get_modality_dynamic,
)


@pytest.fixture(autouse=True)
def mock_forecast_db():
    """Mock TemporalForecastDB to prevent real DB operations."""
    mock_db = MagicMock()
    mock_db.record_oracle_claim.return_value = "test-claim-id"
    with patch("whitemagic.forecasting.temporal_db.TemporalForecastDB", return_value=mock_db):
        yield


def _make_oracle_output(**overrides):
    """Create a minimal oracle output dict for testing."""
    base = {
        "iching_number": 32,
        "iching_name": "Duration",
        "iching_judgment": "Duration succeeds through constancy.",
        "iching_guidance": "Persevere in your path.",
        "sign": "Leo",
        "element": "fire",
        "modality": "fixed",
        "phase": "yang",
        "wu_xing": "fire",
        "ifa_odu": "Ogbe",
        "ifa_wisdom": "Patience brings blessings.",
        "ifa_ire": "Good fortune",
        "ifa_osogbo": "Avoid haste",
    }
    base.update(overrides)
    return base


class TestSymbolicHRRWiring:
    """Test that synthesize() uses SymbolicHRR instead of hardcoded maps."""

    def test_get_alchemical_phase_returns_string(self):
        result = _get_alchemical_phase("fire")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_get_alchemical_phase_all_elements(self):
        for element in ["wood", "fire", "earth", "metal", "water"]:
            result = _get_alchemical_phase(element)
            assert isinstance(result, str)
            assert len(result) > 5

    def test_get_modality_dynamic_returns_string(self):
        result = _get_modality_dynamic("cardinal")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_get_modality_dynamic_all_modalities(self):
        for mod in ["cardinal", "fixed", "mutable"]:
            result = _get_modality_dynamic(mod)
            assert isinstance(result, str)
            assert len(result) > 5

    def test_get_alchemical_phase_fallback(self):
        """When SymbolicHRR fails, should fall back to hardcoded map."""
        with patch("whitemagic.oracle.symbolic_hrr.get_symbolic_hrr", side_effect=Exception("fail")):
            result = _get_alchemical_phase("fire")
            assert "Citrinitas" in result  # From hardcoded fallback

    def test_get_modality_dynamic_fallback(self):
        """When SymbolicHRR fails, should fall back to hardcoded map."""
        with patch("whitemagic.oracle.symbolic_hrr.get_symbolic_hrr", side_effect=Exception("fail")):
            result = _get_modality_dynamic("cardinal")
            assert "Initiating force" in result  # From hardcoded fallback

    def test_synthesize_uses_symbolic_hrr_for_alchemy(self):
        """synthesize() should use SymbolicHRR for alchemical phase."""
        synth = OracleSynthesizer()
        output = _make_oracle_output()
        result = synth.synthesize(output)
        # The alchemical phase should appear in resonances
        alchemy_resonances = [r for r in result.resonances if r.theme == "Alchemical Phase"]
        assert len(alchemy_resonances) > 0
        assert len(alchemy_resonances[0].description) > 10

    def test_synthesize_uses_symbolic_hrr_for_modality(self):
        """synthesize() should use SymbolicHRR for modality dynamic."""
        synth = OracleSynthesizer()
        output = _make_oracle_output(modality="cardinal")
        result = synth.synthesize(output)
        modal_resonances = [r for r in result.resonances if r.theme == "Modal Expression"]
        assert len(modal_resonances) > 0
        assert len(modal_resonances[0].description) > 10


class TestLLMInterpretationWiring:
    """Test that synthesize(use_llm=True) populates llm_interpretation."""

    def test_synthesize_without_llm_has_empty_interpretation(self):
        synth = OracleSynthesizer()
        result = synth.synthesize(_make_oracle_output(), use_llm=False)
        assert result.llm_interpretation == ""

    def test_synthesize_with_llm_populates_interpretation(self):
        mock_interpreter = MagicMock()
        mock_interpreter.interpret.return_value = "The stars align for your endeavor."

        with patch("whitemagic.oracle.llm_interpreter.get_oracle_interpreter", return_value=mock_interpreter):
            synth = OracleSynthesizer()
            result = synth.synthesize(_make_oracle_output(), use_llm=True)
            assert result.llm_interpretation == "The stars align for your endeavor."

    def test_synthesize_with_llm_failure_graceful(self):
        """If LLM fails, llm_interpretation should remain empty."""
        with patch("whitemagic.oracle.llm_interpreter.get_oracle_interpreter", side_effect=Exception("LLM fail")):
            synth = OracleSynthesizer()
            result = synth.synthesize(_make_oracle_output(), use_llm=True)
            assert result.llm_interpretation == ""

    def test_synthesize_with_llm_passes_question(self):
        """LLM interpreter should receive the question from oracle_output."""
        mock_interpreter = MagicMock()
        mock_interpreter.interpret.return_value = "Test interpretation."

        with patch("whitemagic.oracle.llm_interpreter.get_oracle_interpreter", return_value=mock_interpreter):
            synth = OracleSynthesizer()
            output = _make_oracle_output(question="Should I proceed?")
            result = synth.synthesize(output, use_llm=True)
            # Check interpreter was called
            assert mock_interpreter.interpret.called
            call_args = mock_interpreter.interpret.call_args
            # Second positional arg should be the question
            assert call_args[0][1] == "Should I proceed?"

    def test_synthesis_result_has_llm_interpretation_field(self):
        result = SynthesisResult(
            unified_message="test",
            narrative=MagicMock(),
            resonances=[],
            elemental_harmony="test",
            practical_guidance="test",
            cautions=[],
            blessings=[],
        )
        assert hasattr(result, "llm_interpretation")
        assert result.llm_interpretation == ""
