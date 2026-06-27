"""Tests for consciousness wiring into v23 systems.

Verifies that:
- Consciousness __init__.py exports are accessible
- Dispatch table has consciousness tool entries
- PRAT mappings include consciousness tools
- Homeostatic loop has _check_consciousness method
- Consciousness handler returns valid status
- Aria awakens connects to unified memory
- Continuous awareness connects to parallel cognition
- Garden submodules are importable
"""

import pytest


class TestConsciousnessInit:
    """Test consciousness __init__.py lazy exports."""

    def test_coherence_metric_export(self):
        from whitemagic.core.consciousness import CoherenceMetric
        assert CoherenceMetric is not None

    def test_depth_gauge_export(self):
        from whitemagic.core.consciousness import ConsciousnessDepthGauge
        assert ConsciousnessDepthGauge is not None

    def test_get_depth_gauge_export(self):
        from whitemagic.core.consciousness import get_depth_gauge
        assert callable(get_depth_gauge)

    def test_aria_awakens_export(self):
        from whitemagic.core.consciousness import AriaAwakens
        assert AriaAwakens is not None

    def test_awaken_export(self):
        from whitemagic.core.consciousness import awaken
        assert callable(awaken)

    def test_token_economy_export(self):
        from whitemagic.core.consciousness import TokenEconomyTracker
        assert TokenEconomyTracker is not None

    def test_all_export_count(self):
        import whitemagic.core.consciousness as c
        assert len(c.__all__) >= 20


class TestDispatchTableWiring:
    """Test dispatch table has consciousness tools."""

    def test_consciousness_depth_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "consciousness.depth" in DISPATCH_TABLE

    def test_consciousness_coherence_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "consciousness.coherence" in DISPATCH_TABLE

    def test_consciousness_awaken_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "consciousness.awaken" in DISPATCH_TABLE

    def test_consciousness_status_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "consciousness.status" in DISPATCH_TABLE

    def test_all_consciousness_tools_count(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        consciousness_tools = [k for k in DISPATCH_TABLE if k.startswith("consciousness.")]
        assert len(consciousness_tools) >= 8


class TestPratMappings:
    """Test PRAT mappings include consciousness tools."""

    def test_consciousness_tools_mapped_to_gana_ghost(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        consciousness_tools = [k for k in TOOL_TO_GANA if k.startswith("consciousness.")]
        assert len(consciousness_tools) >= 8
        for tool in consciousness_tools:
            assert TOOL_TO_GANA[tool] == "gana_ghost"

    def test_gana_ghost_has_consciousness_tools(self):
        from whitemagic.tools.prat_mappings import GANA_TO_TOOLS
        ghost_tools = GANA_TO_TOOLS.get("gana_ghost", [])
        consciousness_tools = [t for t in ghost_tools if t.startswith("consciousness.")]
        assert len(consciousness_tools) >= 8


class TestHomeostaticLoopWiring:
    """Test homeostatic loop consciousness sensor."""

    def test_check_consciousness_method_exists(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop
        assert hasattr(HomeostaticLoop, "_check_consciousness")

    def test_consciousness_thresholds_in_config(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticConfig
        config = HomeostaticConfig()
        assert hasattr(config, "consciousness_advise")
        assert hasattr(config, "consciousness_correct")
        assert config.consciousness_advise > config.consciousness_correct

    def test_check_consciousness_returns_list(self):
        from whitemagic.harmony.homeostatic_loop import HomeostaticLoop
        loop = HomeostaticLoop()
        result = loop._check_consciousness()
        assert isinstance(result, list)


class TestConsciousnessHandler:
    """Test consciousness handler functions."""

    def test_status_handler_returns_success(self):
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_status,
        )
        result = handle_consciousness_status()
        assert result["status"] == "success"
        assert "modules_available" in result
        assert "modules_missing" in result
        assert "health" in result
        assert 0.0 <= result["health"] <= 1.0

    def test_depth_handler_returns(self):
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_depth,
        )
        result = handle_consciousness_depth()
        assert result["status"] in ("success", "error")

    def test_coherence_handler_returns(self):
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_coherence,
        )
        result = handle_consciousness_coherence()
        assert result["status"] in ("success", "error")

    def test_awaken_handler_returns(self):
        from whitemagic.tools.handlers.consciousness import (
            handle_consciousness_awaken,
        )
        result = handle_consciousness_awaken()
        assert result["status"] in ("success", "error")


class TestAriaAwakensWiring:
    """Test AriaAwakens connects to v23 memory."""

    def test_awaken_returns_greeting(self):
        from whitemagic.core.consciousness.aria_awakens import awaken
        greeting = awaken()
        assert isinstance(greeting, str)
        assert len(greeting) > 0

    def test_awakens_has_unified_memory_flag(self):
        from whitemagic.core.consciousness import aria_awakens
        assert hasattr(aria_awakens, "_HAS_UNIFIED_MEMORY")

    def test_get_session_context_returns_dict(self):
        from whitemagic.core.consciousness.aria_awakens import get_session_context
        ctx = get_session_context()
        assert isinstance(ctx, dict)
        assert "identity" in ctx
        assert "recent_memories" in ctx


class TestContinuousAwarenessWiring:
    """Test continuous awareness connects to parallel cognition."""

    def test_has_parallel_cog_flag(self):
        from whitemagic.core.consciousness import continuous_awareness
        assert hasattr(continuous_awareness, "_HAS_PARALLEL_COG")

    def test_self_report_includes_cognition_connected(self):
        from whitemagic.core.consciousness.continuous_awareness import (
            ContinuousSelfAwareness,
        )
        csa = ContinuousSelfAwareness()
        report = csa.get_self_report()
        assert "cognition_connected" in report
        assert isinstance(report["cognition_connected"], bool)


class TestGardenSubmodules:
    """Test recovered garden submodules are importable."""

    @pytest.mark.parametrize("garden,module", [
        ("joy", "celebration"),
        ("wonder", "collective_dreams"),
        ("mystery", "synchronicity_tracker"),
        ("truth", "truth_detector"),
        ("beauty", "sublime_moments"),
        ("love", "recognition"),
        ("connection", "synastry_governor"),
        ("practice", "daily_ritual"),
        ("wisdom", "cognition_upgrades"),
        ("dharma", "principles"),
        ("voice", "attention"),
        ("presence", "stillness_metrics"),
    ])
    def test_garden_submodule_importable(self, garden, module):
        mod = __import__(
            f"whitemagic.gardens.{garden}.{module}",
            fromlist=[module],
        )
        assert mod is not None
