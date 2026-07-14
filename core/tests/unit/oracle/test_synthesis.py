"""Tests for the Oracle Wisdom Synthesis layer."""

import pytest

from whitemagic.oracle.wisdom_synthesis import (
    SynthesisResult,
    get_synthesizer,
    synthesize_oracle,
)


@pytest.fixture
def sample_oracle_output():
    """Sample oracle output matching consult_oracle() structure."""
    return {
        "hexagram": 46,
        "element": "fire",
        "phase": "yang",
        "guidance": "Create, express, manifest.",
        "sign": "aries",
        "symbol": "♈",
        "modality": "cardinal",
        "wu_xing": "fire",
        "iching_number": 46,
        "iching_name": "Pushing Upward",
        "iching_judgment": "Pushing upward has supreme success. One must see the great man. Fear not. Departure toward the south brings good fortune.",
        "iching_guidance": "Step by step progress. Patience reveals the path.",
        "ifa_odu": "Ogbe-Otura",
        "ifa_odu_number": 28,
        "ifa_binary": "00000100",
        "ifa_wisdom": "Honesty and gentle character open the way. Seek counsel when uncertain.",
        "ifa_ire": "Abundance, long life, success through integrity",
        "ifa_osogbo": "Arrogance, overconfidence, neglect of foundations",
    }


@pytest.fixture
def sample_yin_oracle():
    """Sample oracle output for yin phase."""
    return {
        "hexagram": 11,
        "element": "water",
        "phase": "yin",
        "guidance": "Receive, reflect, integrate.",
        "sign": "pisces",
        "symbol": "♓",
        "modality": "mutable",
        "wu_xing": "water",
        "iching_number": 11,
        "iching_name": "Peace",
        "iching_judgment": "Peace. The small departs, the great approaches. Good fortune. Success.",
        "iching_guidance": "Harmony prevails. Nurture what is good.",
        "ifa_odu": "Otura-Osa",
        "ifa_odu_number": 206,
        "ifa_binary": "01001010",
        "ifa_wisdom": "Seek counsel when uncertain. Cycles reach completion through moral integrity.",
        "ifa_ire": "Wisdom, clarity, spiritual growth",
        "ifa_osogbo": "Confusion, loss of direction",
    }


class TestSynthesisBasics:
    """Basic synthesis functionality."""

    def test_synthesize_returns_result(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert isinstance(result, SynthesisResult)

    def test_unified_message_not_empty(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.unified_message) > 20

    def test_narrative_has_three_acts(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.narrative.act_1) > 10
        assert len(result.narrative.act_2) > 10
        assert len(result.narrative.act_3) > 10

    def test_narrative_arc_type(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert result.narrative.arc_type == "inception-catalysis-resolution"

    def test_yin_narrative_arc_type(self, sample_yin_oracle):
        result = synthesize_oracle(sample_yin_oracle)
        assert result.narrative.arc_type == "preparation-work-fruition"

    def test_resonances_not_empty(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.resonances) > 0

    def test_elemental_harmony_not_empty(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.elemental_harmony) > 10

    def test_practical_guidance_not_empty(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.practical_guidance) > 20

    def test_cautions_extracted(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.cautions) > 0

    def test_blessings_extracted(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert len(result.blessings) > 0

    def test_raw_layers_preserved(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert result.raw_layers == sample_oracle_output


class TestResonanceDetection:
    """Test cross-layer resonance detection."""

    def test_element_alignment_resonance(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        # fire zodiac -> fire wu_xing = alignment
        alignment = [r for r in result.resonances if r.theme == "Elemental Alignment"]
        assert len(alignment) == 1
        assert alignment[0].strength == 0.9

    def test_generative_flow_resonance(self, sample_yin_oracle):
        # Modify to create generative relationship
        oracle = dict(sample_yin_oracle)
        oracle["wu_xing"] = "wood"  # water generates wood
        result = synthesize_oracle(oracle)
        gen = [r for r in result.resonances if r.theme == "Generative Flow"]
        assert len(gen) == 1
        assert gen[0].strength == 0.7

    def test_creative_tension_resonance(self):
        oracle = {
            "sign": "aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "metal",  # fire controls metal
            "iching_number": 1,
            "iching_name": "Creative",
            "iching_judgment": "Success",
            "iching_guidance": "Act",
            "ifa_odu": "Eji Ogbe",
            "ifa_wisdom": "Begin with clarity",
            "ifa_ire": "Success",
            "ifa_osogbo": "Arrogance",
        }
        result = synthesize_oracle(oracle)
        tension = [r for r in result.resonances if r.theme == "Creative Tension"]
        assert len(tension) == 1

    def test_shared_vocabulary_resonance(self):
        oracle = {
            "sign": "aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "fire",
            "iching_number": 43,
            "iching_name": "Breakthrough",
            "iching_judgment": "Breakthrough requires resolve",
            "iching_guidance": "Speak truth with clarity and resolve",
            "ifa_odu": "Eji Ogbe",
            "ifa_wisdom": "Honesty and clarity open the way. Speak truth.",
            "ifa_ire": "Success",
            "ifa_osogbo": "Deception",
        }
        result = synthesize_oracle(oracle)
        shared = [r for r in result.resonances if r.theme == "Shared Vocabulary"]
        assert len(shared) >= 1
        assert shared[0].strength == 0.8

    def test_alchemical_phase_resonance(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        alchemy = [r for r in result.resonances if r.theme == "Alchemical Phase"]
        assert len(alchemy) == 1


class TestNarrativeArc:
    """Test narrative arc construction."""

    def test_yang_act_1_mentions_phase(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert "yang" in result.narrative.act_1.lower()

    def test_yin_act_1_mentions_phase(self, sample_yin_oracle):
        result = synthesize_oracle(sample_yin_oracle)
        assert "yin" in result.narrative.act_1.lower()

    def test_act_2_contains_iching(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert "Pushing Upward" in result.narrative.act_2

    def test_act_3_contains_ifa(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert "Ogbe-Otura" in result.narrative.act_3


class TestElementalHarmony:
    """Test elemental harmony assessment."""

    def test_harmonious(self, sample_oracle_output):
        result = synthesize_oracle(sample_oracle_output)
        assert "Harmonious" in result.elemental_harmony

    def test_generative(self):
        oracle = {
            "sign": "pisces",
            "element": "water",
            "modality": "mutable",
            "phase": "yin",
            "wu_xing": "wood",
            "iching_number": 1,
            "iching_name": "Test",
            "iching_judgment": "Test",
            "iching_guidance": "Test",
            "ifa_odu": "Test",
            "ifa_wisdom": "Test",
            "ifa_ire": "",
            "ifa_osogbo": "",
        }
        result = synthesize_oracle(oracle)
        assert "Generative" in result.elemental_harmony

    def test_tension(self):
        oracle = {
            "sign": "aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "metal",
            "iching_number": 1,
            "iching_name": "Test",
            "iching_judgment": "Test",
            "iching_guidance": "Test",
            "ifa_odu": "Test",
            "ifa_wisdom": "Test",
            "ifa_ire": "",
            "ifa_osogbo": "",
        }
        result = synthesize_oracle(oracle)
        assert "Tension" in result.elemental_harmony


class TestSingleton:
    """Test singleton pattern."""

    def test_get_synthesizer_returns_same_instance(self):
        s1 = get_synthesizer()
        s2 = get_synthesizer()
        assert s1 is s2


class TestEdgeCases:
    """Test edge cases and missing data."""

    def test_empty_oracle(self):
        result = synthesize_oracle({})
        assert isinstance(result, SynthesisResult)
        assert len(result.unified_message) > 0

    def test_missing_iching(self):
        oracle = {
            "sign": "aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "fire",
            "ifa_odu": "Eji Ogbe",
            "ifa_wisdom": "Begin with clarity",
            "ifa_ire": "Success",
            "ifa_osogbo": "Arrogance",
        }
        result = synthesize_oracle(oracle)
        assert "Eji Ogbe" in result.narrative.act_3

    def test_missing_ifa(self):
        oracle = {
            "sign": "aries",
            "element": "fire",
            "modality": "cardinal",
            "phase": "yang",
            "wu_xing": "fire",
            "iching_number": 1,
            "iching_name": "Creative",
            "iching_judgment": "Success",
            "iching_guidance": "Act",
        }
        result = synthesize_oracle(oracle)
        assert "Creative" in result.narrative.act_2
