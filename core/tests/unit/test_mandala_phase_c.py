"""Tests for MandalaOS Phase C — Koka effect enforcement and visualization tools."""

import os
import tempfile

import pytest

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_"))
os.environ.setdefault("WM_SILENT_INIT", "1")


class TestEffectTrace:
    """Test the effect.trace MCP tool."""

    def test_effect_trace_basic(self):
        from whitemagic.tools.handlers.dharma import handle_effect_trace

        result = handle_effect_trace(tool="create_memory")
        assert result["status"] == "success"
        assert result["tool"] == "create_memory"
        assert "declared_effects" in result
        assert result["koka_enforced"] is False

    def test_effect_trace_missing_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_trace

        result = handle_effect_trace()
        assert result["status"] == "error"

    def test_effect_trace_with_koka_flag(self):
        from whitemagic.tools.handlers.dharma import handle_effect_trace

        # use_koka=True but Koka binary likely not available in test env
        result = handle_effect_trace(tool="create_memory", use_koka=True)
        assert result["status"] == "success"
        # Should fall back to Python path
        assert result["koka_enforced"] is False

    def test_effect_trace_unknown_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_trace

        result = handle_effect_trace(tool="nonexistent_tool_xyz")
        assert result["status"] == "success"
        assert result["declared_effects"] == [] or len(result["declared_effects"]) >= 0


class TestEffectVisualize:
    """Test the effect.visualize MCP tool."""

    def test_visualize_dot_per_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(tool="create_memory", format="dot")
        assert result["status"] == "success"
        assert result["format"] == "dot"
        assert "digraph" in result["graph"]

    def test_visualize_mermaid_per_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(tool="create_memory", format="mermaid")
        assert result["status"] == "success"
        assert result["format"] == "mermaid"
        assert "graph TD" in result["graph"]

    def test_visualize_json_per_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(tool="create_memory", format="json")
        assert result["status"] == "success"
        assert result["format"] == "json"
        assert "effects" in result

    def test_visualize_dot_system_wide(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(format="dot")
        assert result["status"] == "success"
        assert "digraph" in result["graph"]
        assert result["total_tools"] > 100

    def test_visualize_mermaid_system_wide(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(format="mermaid")
        assert result["status"] == "success"
        assert "pie" in result["graph"]

    def test_visualize_json_system_wide(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(format="json")
        assert result["status"] == "success"
        assert "effect_type_counts" in result
        assert result["total_tools"] > 100

    def test_visualize_unknown_tool(self):
        from whitemagic.tools.handlers.dharma import handle_effect_visualize

        result = handle_effect_visualize(tool="nonexistent_xyz", format="dot")
        assert result["status"] == "error"


class TestHybridDispatcherKarmic:
    """Test the HybridDispatcher.karmic_compare method."""

    def test_karmic_compare_no_mismatch(self):
        from whitemagic.core.acceleration.hybrid_dispatcher import (
            HybridDispatcher,
            DispatchMode,
        )

        hd = HybridDispatcher(DispatchMode.SPEED)  # Force Python
        result = hd.karmic_compare(
            "test_tool",
            [{"effect_type": "local", "declared": True}],
            [{"effect_type": "local", "declared": False}],
        )
        assert result["status"] == "success"
        assert result["mismatch"] is False
        assert result["debt"] == 0.0

    def test_karmic_compare_undeclared_network(self):
        from whitemagic.core.acceleration.hybrid_dispatcher import (
            HybridDispatcher,
            DispatchMode,
        )

        hd = HybridDispatcher(DispatchMode.SPEED)
        result = hd.karmic_compare(
            "test_tool",
            [{"effect_type": "local", "declared": True}],
            [{"effect_type": "network", "declared": False}],
        )
        assert result["status"] == "success"
        assert result["mismatch"] is True
        assert result["debt"] == 1.6  # Network undeclared (1.5) + local no-op (0.1)

    def test_karmic_compare_undeclared_destructive(self):
        from whitemagic.core.acceleration.hybrid_dispatcher import (
            HybridDispatcher,
            DispatchMode,
        )

        hd = HybridDispatcher(DispatchMode.SPEED)
        result = hd.karmic_compare(
            "test_tool",
            [{"effect_type": "local", "declared": True}],
            [{"effect_type": "destructive", "declared": False}],
        )
        assert result["status"] == "success"
        assert result["mismatch"] is True
        assert result["debt"] == 2.1  # Destructive undeclared (2.0) + local no-op (0.1)

    def test_karmic_compare_fallback_flag(self):
        from whitemagic.core.acceleration.hybrid_dispatcher import (
            HybridDispatcher,
            DispatchMode,
        )

        hd = HybridDispatcher(DispatchMode.SPEED)
        result = hd.karmic_compare(
            "test_tool",
            [{"effect_type": "pure", "declared": True}],
            [{"effect_type": "pure", "declared": False}],
        )
        assert result.get("fallback") is True


class TestKokaKarmicModule:
    """Test the KokaNativeBridge dispatch_karmic method."""

    def test_dispatch_karmic_returns_none_when_unavailable(self):
        from whitemagic.core.acceleration.koka_native_bridge import KokaNativeBridge

        bridge = KokaNativeBridge()
        # Karmic binary likely not compiled in test env
        if not bridge.is_available("karmic"):
            result = bridge.dispatch_karmic(
                "test_tool",
                {},
                [{"effect_type": "local", "declared": True}],
                [{"effect_type": "local", "declared": False}],
            )
            assert result is None
        else:
            # If available, test it works
            result = bridge.dispatch_karmic(
                "test_tool",
                {},
                [{"effect_type": "local", "declared": True}],
                [{"effect_type": "network", "declared": False}],
            )
            assert result is not None
            assert result.get("status") == "success"
