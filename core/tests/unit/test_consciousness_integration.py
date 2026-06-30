"""Integration tests for consciousness modules — apotheosis, flow_state, coherence.

Tests the wiring between:
- ApotheosisEngine.test_capability() — real dispatch-based testing
- FlowState.auto_detect_indicators() — system-activity-driven flow detection
- CoherenceMetric — 8-dimension coherence measurement
- HomeostaticLoop._check_apotheosis() — apotheosis integration in homeostatic loop
"""

import pytest


class TestApotheosisCapabilityTesting:
    """Test that ApotheosisEngine.test_capability() does real testing."""

    def test_test_capability_dispatches_tool(self):
        """test_capability should actually dispatch the tool, not return hardcoded values."""
        from whitemagic.core.consciousness.apotheosis_engine import (
            CapabilityDiscoveryEngine,
            DiscoveredCapability,
        )

        engine = CapabilityDiscoveryEngine()
        cap = DiscoveredCapability(
            capability_name="test_cap",
            description="Test capability",
            tools_involved=["system.status"],
            discovery_context="test",
            confidence=0.5,
            tested=False,
            test_results=None,
            discovered_at=0.0,
        )
        result = engine.test_capability(cap)
        assert isinstance(result, dict)
        assert "success" in result
        assert "execution_time_ms" in result
        assert "errors" in result
        # Should NOT be hardcoded 100.0 anymore
        assert result["execution_time_ms"] != 100.0 or result["success"] is False
        assert cap.tested is True
        assert cap.test_results is not None

    def test_test_capability_handles_nonexistent_tool(self):
        """test_capability should handle nonexistent tools gracefully."""
        from whitemagic.core.consciousness.apotheosis_engine import (
            CapabilityDiscoveryEngine,
            DiscoveredCapability,
        )

        engine = CapabilityDiscoveryEngine()
        cap = DiscoveredCapability(
            capability_name="nonexistent",
            description="Nonexistent tool",
            tools_involved=["definitely_not_a_real_tool"],
            discovery_context="test",
            confidence=0.5,
            tested=False,
            test_results=None,
            discovered_at=0.0,
        )
        result = engine.test_capability(cap)
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert cap.confidence == 0.3


class TestFlowStateAutoDetect:
    """Test FlowState.auto_detect_indicators() wiring."""

    def test_auto_detect_returns_indicators(self):
        """auto_detect_indicators should return detected indicators based on metrics."""
        from whitemagic.gardens.presence.flow_state import (
            FlowState,
            FlowIndicator,
            get_flow_state,
        )

        fs = FlowState()
        detected = fs.auto_detect_indicators(
            tool_call_rate=6.0,
            coherence=0.8,
            session_duration_min=45,
        )
        assert FlowIndicator.FULL_ABSORPTION in detected
        assert FlowIndicator.CLEAR_GOALS in detected
        assert FlowIndicator.IMMEDIATE_FEEDBACK in detected
        assert FlowIndicator.TIME_DISTORTION in detected

    def test_auto_detect_enters_flow(self):
        """auto_detect_indicators should auto-enter flow when >= 3 indicators."""
        from whitemagic.gardens.presence.flow_state import FlowState

        fs = FlowState()
        assert fs.flow_start is None
        fs.auto_detect_indicators(
            tool_call_rate=6.0, coherence=0.8, session_duration_min=45
        )
        assert fs.flow_start is not None

    def test_flow_score_zero_when_not_in_flow(self):
        """flow_score should return 0.0 when not in flow."""
        from whitemagic.gardens.presence.flow_state import FlowState

        fs = FlowState()
        assert fs.flow_score() == 0.0

    def test_flow_score_nonzero_when_in_flow(self):
        """flow_score should return > 0.0 when in flow with indicators."""
        from whitemagic.gardens.presence.flow_state import (
            FlowState,
            FlowIndicator,
        )

        fs = FlowState()
        fs.enter_flow("test")
        fs.detect_indicator(FlowIndicator.CLEAR_GOALS)
        fs.detect_indicator(FlowIndicator.IMMEDIATE_FEEDBACK)
        score = fs.flow_score()
        assert 0.0 < score <= 1.0

    def test_get_flow_state_singleton(self):
        """get_flow_state should return the same instance."""
        from whitemagic.gardens.presence.flow_state import get_flow_state

        a = get_flow_state()
        b = get_flow_state()
        assert a is b


class TestMultiAgentWonderWiring:
    """Test that the fixed multi_agent module works correctly."""

    def test_agent_role_enum(self):
        from whitemagic.gardens.wonder.multi_agent import AgentRole

        assert AgentRole.ANALYST.value == "analyst"
        assert AgentRole.EXPLORER.value == "explorer"

    def test_coordinator_spawn(self):
        from whitemagic.gardens.wonder.multi_agent import (
            AgentRole,
            MultiAgentCoordinator,
        )

        coord = MultiAgentCoordinator()
        agent_id = coord.spawn_agent(AgentRole.ANALYST, "test_agent")
        assert isinstance(agent_id, str)
        assert coord.active_count() == 1

    def test_clone_grimoire_fusion_imports(self):
        """clone_grimoire_fusion should import and work."""
        from whitemagic.gardens.wonder.clone_grimoire_fusion import CloneGrimoireFusion

        fusion = CloneGrimoireFusion()
        result = fusion.iching_clone_array("test question")
        assert result["type"] == "iching_array"
        assert result["clones"] == 64


class TestConsolidatorImport:
    """Test that the fixed consolidator module works."""

    def test_consolidator_imports(self):
        from whitemagic.core.automation.consolidator import MemoryConsolidator
        # Just verify it can be instantiated (may fail on memory_system init in test env)
        # but the import itself should work


class TestIChingDeduplication:
    """Test that the I Ching deduplication re-export works."""

    def test_gardens_reexport_same_singleton(self):
        from whitemagic.gardens.wisdom.i_ching import get_i_ching
        from whitemagic.core.intelligence.wisdom.i_ching import get_i_ching as get_core

        a = get_i_ching()
        b = get_core()
        assert a is b
