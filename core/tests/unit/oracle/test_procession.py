"""Tests for the 12-step procession definitions and alchemical loop restructure."""

from unittest.mock import AsyncMock, patch

import pytest

from whitemagic.core.intelligence.procession_steps import (
    COLOR_STAGES,
    FIXED_CHECKPOINTS,
    YANG_BY_SIGN,
    YANG_PROCESSION,
    YIN_BY_SIGN,
    YIN_PROCESSION,
    get_checkpoint_description,
    get_color_stage_for_step,
)


class TestProcessionStructure:
    """Tests for the 12-step procession definitions."""

    def test_yin_has_12_steps(self):
        assert len(YIN_PROCESSION) == 12

    def test_yang_has_12_steps(self):
        assert len(YANG_PROCESSION) == 12

    def test_yin_order_is_precessional(self):
        signs = [s.sign for s in YIN_PROCESSION]
        assert signs == [
            "pisces",
            "aquarius",
            "capricorn",
            "sagittarius",
            "scorpio",
            "libra",
            "virgo",
            "leo",
            "cancer",
            "gemini",
            "taurus",
            "aries",
        ]

    def test_yang_order_is_zodiacal(self):
        signs = [s.sign for s in YANG_PROCESSION]
        assert signs == [
            "aries",
            "taurus",
            "gemini",
            "cancer",
            "leo",
            "virgo",
            "libra",
            "scorpio",
            "sagittarius",
            "capricorn",
            "aquarius",
            "pisces",
        ]

    def test_step_numbers_sequential(self):
        for i, step in enumerate(YIN_PROCESSION, 1):
            assert step.step_number == i
        for i, step in enumerate(YANG_PROCESSION, 1):
            assert step.step_number == i

    def test_all_fields_populated(self):
        for step in YIN_PROCESSION + YANG_PROCESSION:
            assert step.sign, f"Empty sign for step {step.step_number}"
            assert step.symbol, f"Empty symbol for {step.sign}"
            assert step.enochian, f"Empty enochian for {step.sign}"
            assert step.enochian_meaning, f"Empty enochian_meaning for {step.sign}"
            assert step.operation, f"Empty operation for {step.sign}"
            assert step.ripley_gate, f"Empty ripley_gate for {step.sign}"
            assert step.color_stage, f"Empty color_stage for {step.sign}"
            assert step.wu_xing, f"Empty wu_xing for {step.sign}"
            assert step.modality, f"Empty modality for {step.sign}"
            assert step.yang_action, f"Empty yang_action for {step.sign}"
            assert step.yin_action, f"Empty yin_action for {step.sign}"

    def test_fixed_signs_at_correct_positions(self):
        yin_fixed = [s.step_number for s in YIN_PROCESSION if s.is_fixed]
        yang_fixed = [s.step_number for s in YANG_PROCESSION if s.is_fixed]
        assert yin_fixed == [2, 5, 8, 11]
        assert yang_fixed == [2, 5, 8, 11]

    def test_fixed_signs_match(self):
        yin_fixed_signs = [s.sign for s in YIN_PROCESSION if s.is_fixed]
        yang_fixed_signs = [s.sign for s in YANG_PROCESSION if s.is_fixed]
        assert set(yin_fixed_signs) == set(yang_fixed_signs) == set(FIXED_CHECKPOINTS)

    def test_checkpoint_flags_match_fixed(self):
        for step in YIN_PROCESSION + YANG_PROCESSION:
            assert step.is_checkpoint == step.is_fixed

    def test_lookup_by_sign(self):
        assert YIN_BY_SIGN["pisces"].step_number == 1
        assert YANG_BY_SIGN["aries"].step_number == 1

    def test_checkpoint_descriptions(self):
        for sign in FIXED_CHECKPOINTS:
            desc = get_checkpoint_description(sign)
            assert desc, f"Empty checkpoint description for {sign}"

    def test_color_stages_list(self):
        assert COLOR_STAGES == [
            "Nigredo",
            "Cauda Pavonis",
            "Albedo",
            "Citrinitas",
            "Rubedo",
        ]

    def test_color_stage_for_yin(self):
        assert get_color_stage_for_step(1, "yin") == "Nigredo"
        assert get_color_stage_for_step(12, "yin") == "Rubedo"

    def test_color_stage_for_yang(self):
        assert get_color_stage_for_step(1, "yang") == "Rubedo"
        assert get_color_stage_for_step(12, "yang") == "Nigredo"

    def test_enochian_names_present(self):
        expected_names = {
            "ORO",
            "IBAH",
            "AOZPI",
            "MPH",
            "ARSL",
            "GAIOL",
            "OIP",
            "TEAA",
            "PDOCE",
            "MOR",
            "DIAL",
            "HCTGA",
        }
        yin_names = {s.enochian for s in YIN_PROCESSION}
        yang_names = {s.enochian for s in YANG_PROCESSION}
        assert yin_names == expected_names
        assert yang_names == expected_names

    def test_ripley_gates_all_present(self):
        expected_gates = {
            "Calcination",
            "Dissolution",
            "Separation",
            "Conjunction",
            "Putrefaction",
            "Congelation",
            "Cibation",
            "Sublimation",
            "Fermentation",
            "Exaltation",
            "Multiplication",
            "Projection",
        }
        yin_gates = {s.ripley_gate for s in YIN_PROCESSION}
        yang_gates = {s.ripley_gate for s in YANG_PROCESSION}
        assert yin_gates == expected_gates
        assert yang_gates == expected_gates


class TestAlchemicalLoopRestructure:
    """Tests for the restructured 12-step alchemical loop."""

    @pytest.fixture(autouse=True)
    def _mock_heavy_ops(self):
        """Mock rabbit_hole and filter_research to avoid 7s+ tool dispatch."""
        with patch(
            "whitemagic.core.intelligence.alchemical_loop.AlchemicalLoop._call_rabbit_hole",
            new_callable=AsyncMock,
            return_value={"entries": 0, "connections": 0, "new_holes": 0, "synthesis": "test"},
        ), patch(
            "whitemagic.core.intelligence.alchemical_loop.AlchemicalLoop._filter_research",
            new_callable=AsyncMock,
            return_value={"filtered": [], "count": 0},
        ):
            yield

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cycle_has_12_yang_steps(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        assert len(result.cycles) == 1
        assert len(result.cycles[0].yang_stages) == 12

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cycle_has_12_yin_steps(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        assert len(result.cycles[0].yin_stages) == 12

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cycle_has_8_fixed_hubs(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        # 4 fixed hubs per phase = 8 total
        assert len(result.cycles[0].fixed_hub_results) == 8

    @pytest.mark.asyncio
    async def test_oracle_has_4_layers(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        og = result.cycles[0].oracle_guidance
        # Layer 1: Zodiacal
        assert "sign" in og
        assert "element" in og
        # Layer 2: Wu Xing
        assert "wu_xing" in og
        # Layer 3: I Ching
        assert "iching_number" in og
        assert "iching_name" in og
        # Layer 4: Ifa
        assert "ifa_odu" in og
        assert "ifa_odu_number" in og

    @pytest.mark.asyncio
    async def test_step_info_carries_enochian(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        first_yang = result.cycles[0].yang_stages[0]
        assert "enochian" in first_yang.step_info
        assert first_yang.step_info["enochian"] == "HCTGA"  # Aries

    @pytest.mark.asyncio
    async def test_step_info_carries_color_stage(self):
        from whitemagic.core.intelligence.alchemical_loop import AlchemicalLoop

        loop = AlchemicalLoop(task="test task", cycles=1, enable_web=False)
        result = await loop.run()
        first_yang = result.cycles[0].yang_stages[0]
        assert "color_stage" in first_yang.step_info
