"""Unit tests for workspace competition MCP tools (ignite, pending, ignitions)."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_wct_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.consciousness import global_workspace as gw_mod  # noqa: E402
from whitemagic.tools.handlers.neuro_cognitive import (  # noqa: E402
    handle_workspace_propose,
    handle_workspace_ignite,
    handle_workspace_pending,
    handle_workspace_ignitions,
    handle_workspace_state,
)


def _reset_singleton(**kwargs):
    """Reset the global workspace singleton with fresh config."""
    gw_mod._workspace = None
    gw = gw_mod.get_global_workspace()
    # Reconfigure the singleton
    gw._fast_ignite_threshold = kwargs.get("fast_ignite_threshold", 0.8)
    gw._competition_window = kwargs.get("competition_window", 10.0)
    gw._min_ignite_salience = kwargs.get("min_ignite_salience", 0.3)
    gw._pending = []
    gw._history = []
    gw._total_broadcasts = 0
    gw._total_proposals = 0
    gw._ignition_count = 0
    gw._window_start = 0.0
    gw._modules = {}
    return gw


class TestWorkspaceIgniteTool:
    def test_ignite_empty_returns_not_ignited(self):
        _reset_singleton()
        result = handle_workspace_ignite()
        assert result["status"] == "success"
        assert result["ignited"] is False

    def test_ignite_with_pending_selects_winner(self):
        gw = _reset_singleton()
        gw.register("mod-c", lambda b: None)
        gw.propose("mod-a", {"x": 1}, salience=0.4)
        gw.propose("mod-b", {"x": 2}, salience=0.6)
        result = handle_workspace_ignite()
        assert result["status"] == "success"
        assert result["ignited"] is True
        assert result["source"] == "mod-b"
        assert result["salience"] == 0.6


class TestWorkspacePendingTool:
    def test_pending_empty(self):
        _reset_singleton()
        result = handle_workspace_pending()
        assert result["status"] == "success"
        assert result["pending_count"] == 0

    def test_pending_with_proposals(self):
        gw = _reset_singleton()
        gw.register("mod", lambda b: None)
        gw.propose("src-a", {"x": 1}, salience=0.4)
        gw.propose("src-b", {"x": 2}, salience=0.5)
        result = handle_workspace_pending()
        assert result["status"] == "success"
        assert result["pending_count"] == 2
        assert len(result["proposals"]) == 2
        assert result["competition_active"] is True


class TestWorkspaceIgnitionsTool:
    def test_ignitions_empty_trajectory(self):
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
        cycle = get_citta_cycle()
        cycle.reset()
        result = handle_workspace_ignitions()
        assert result["status"] == "success"
        assert result["ignition_count"] == 0
        assert result["trajectory_length"] == 0

    def test_ignitions_with_threshold(self):
        result = handle_workspace_ignitions(threshold=3.0)
        assert result["status"] == "success"
        assert result["threshold"] == 3.0


class TestWorkspaceProposeCompetition:
    def test_propose_high_salience_fast_ignite(self):
        gw = _reset_singleton()
        gw.register("mod-b", lambda b: None)
        result = handle_workspace_propose(
            source="mod-a", content={"info": "test"}, salience=0.9
        )
        assert result["status"] == "success"
        assert result["broadcast"] is True
        assert result["ignition"] == "fast"

    def test_propose_low_salience_enters_competition(self):
        gw = _reset_singleton()
        gw.register("mod-b", lambda b: None)
        result = handle_workspace_propose(
            source="mod-a", content={"info": "test"}, salience=0.4
        )
        assert result["status"] == "success"
        assert result["broadcast"] is False
        assert result["reason"] == "entered_competition"
        assert result["pending_count"] == 1


class TestWorkspaceStateTool:
    def test_state_includes_competition_fields(self):
        gw = _reset_singleton()
        gw.register("mod", lambda b: None)
        gw.propose("src", {"x": 1}, salience=0.4)
        result = handle_workspace_state()
        assert result["status"] == "success"
        assert "ignition_count" in result
        assert "pending_proposals" in result
        assert "competition_active" in result
        assert result["pending_proposals"] == 1
