"""Unit tests for global workspace system."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_gw_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.consciousness.global_workspace import (  # noqa: E402
    GlobalWorkspace,
    WorkspaceBroadcast,
    get_global_workspace,
)


class TestGlobalWorkspace:
    def test_register_and_unregister(self):
        gw = GlobalWorkspace()
        received = []
        gw.register("test-mod", lambda b: received.append(b))
        assert gw.stats()["total_modules"] >= 1
        gw.unregister("test-mod")
        assert gw.stats()["total_modules"] == 0

    def test_propose_high_salience_broadcasts(self):
        gw = GlobalWorkspace()
        received = []
        gw.register("mod-a", lambda b: received.append(b))
        gw.register("mod-b", lambda b: received.append(b))
        result = gw.propose("mod-a", {"info": "test"}, salience=0.8)
        assert result is not None
        # mod-b should have received it, but not mod-a (source)
        assert len(received) == 1

    def test_propose_low_salience_enters_competition(self):
        gw = GlobalWorkspace()
        received = []
        gw.register("mod-b", lambda b: received.append(b))
        result = gw.propose("mod-a", {"info": "test"}, salience=0.2)
        assert result is None
        assert len(received) == 0
        # Should be pending in competition window
        pending = gw.get_pending()
        assert len(pending) == 1

    def test_broadcast_excludes_source(self):
        gw = GlobalWorkspace()
        a_received = []
        b_received = []
        gw.register("mod-a", lambda b: a_received.append(b))
        gw.register("mod-b", lambda b: b_received.append(b))
        gw.propose("mod-a", {"data": 1}, salience=0.9)
        assert len(a_received) == 0
        assert len(b_received) == 1

    def test_history(self):
        gw = GlobalWorkspace()
        gw.register("mod-b", lambda b: None)
        gw.propose("mod-a", {"d": 1}, salience=0.9)
        gw.propose("mod-a", {"d": 2}, salience=0.85)
        history = gw.get_history()
        assert len(history) == 2
        assert history[-1]["salience"] == 0.85

    def test_stats(self):
        gw = GlobalWorkspace()
        gw.register("mod", lambda b: None)
        gw.propose("source", {"x": 1}, salience=0.6)
        s = gw.stats()
        assert "total_broadcasts" in s
        assert "total_proposals" in s
        assert s["total_proposals"] >= 1

    def test_get_current_state(self):
        gw = GlobalWorkspace()
        gw.register("mod", lambda b: None)
        gw.propose("src", {"key": "val"}, salience=0.9)
        state = gw.get_current_state()
        assert state["latest_broadcast"] is not None
        assert state["latest_broadcast"]["source"] == "src"

    def test_singleton(self):
        gw1 = get_global_workspace()
        gw2 = get_global_workspace()
        assert gw1 is gw2


class TestWorkspaceCompetition:
    """Test the competitive ignition model (replaces simple threshold)."""

    def test_fast_ignite_high_salience(self):
        gw = GlobalWorkspace(fast_ignite_threshold=0.8)
        received = []
        gw.register("mod-b", lambda b: received.append(b))
        result = gw.propose("mod-a", {"x": 1}, salience=0.9)
        assert result is not None
        assert len(received) == 1
        assert gw.stats()["ignition_count"] == 1

    def test_competition_window_accumulates(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8,
            competition_window=10.0,
            min_ignite_salience=0.3,
        )
        gw.register("mod-c", lambda b: None)
        gw.propose("mod-a", {"x": 1}, salience=0.4)
        gw.propose("mod-b", {"x": 2}, salience=0.5)
        assert len(gw.get_pending()) == 2

    def test_ignite_selects_most_salient(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8,
            competition_window=10.0,
            min_ignite_salience=0.3,
        )
        received = []
        gw.register("mod-c", lambda b: received.append(b))
        gw.propose("mod-a", {"x": 1}, salience=0.4)
        gw.propose("mod-b", {"x": 2}, salience=0.6)
        winner = gw.ignite()
        assert winner is not None
        assert winner.salience == 0.6
        assert winner.source == "mod-b"
        assert len(received) == 1
        assert gw.stats()["ignition_count"] == 1

    def test_ignite_below_min_salience_returns_none(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8,
            competition_window=10.0,
            min_ignite_salience=0.5,
        )
        gw.register("mod-c", lambda b: None)
        gw.propose("mod-a", {"x": 1}, salience=0.3)
        winner = gw.ignite()
        assert winner is None

    def test_fast_ignite_clears_pending(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8,
            competition_window=10.0,
        )
        gw.register("mod-c", lambda b: None)
        gw.propose("mod-a", {"x": 1}, salience=0.4)
        gw.propose("mod-b", {"x": 2}, salience=0.5)
        assert len(gw.get_pending()) == 2
        # Fast ignite should clear pending
        gw.propose("mod-d", {"x": 3}, salience=0.9)
        assert len(gw.get_pending()) == 0

    def test_ignite_empty_returns_none(self):
        gw = GlobalWorkspace()
        assert gw.ignite() is None

    def test_stats_include_competition(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8,
            competition_window=10.0,
        )
        gw.register("mod", lambda b: None)
        gw.propose("src", {"x": 1}, salience=0.4)
        s = gw.stats()
        assert "ignition_count" in s
        assert "pending_proposals" in s
        assert s["pending_proposals"] == 1
        assert s["competition_active"] is True
