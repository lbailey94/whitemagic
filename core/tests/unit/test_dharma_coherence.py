"""Unit tests for Dharma coherence integration and workspace persistence."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_dh_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.consciousness.dharma import (  # noqa: E402
    DharmaProtocol,
    EthicsViolation,
    Intent,
)
from whitemagic.core.consciousness.global_workspace import (  # noqa: E402
    GlobalWorkspace,
    WorkspaceBroadcast,
)


class TestDharmaCoherence:
    """Test coherence-aware conservative mode in Dharma."""

    def test_high_coherence_allows_normal_action(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(0.9)
        dharma.validate_action("test", Intent.UPLIFTMENT, {"risk_level": "high"})

    def test_low_coherence_rejects_high_risk(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(0.3)
        try:
            dharma.validate_action(
                "risky_op", Intent.EVOLUTION, {"risk_level": "high"}
            )
            assert False, "Should have raised EthicsViolation"
        except EthicsViolation:
            pass

    def test_low_coherence_allows_low_risk(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(0.3)
        dharma.validate_action("safe_op", Intent.UPLIFTMENT, {"risk_level": "low"})

    def test_forbidden_always_rejected(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(1.0)
        try:
            dharma.validate_action("bad", Intent.HARM, {})
            assert False, "Should have raised EthicsViolation"
        except EthicsViolation:
            pass

    def test_conservative_mode_flag(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(0.3)
        assert dharma.is_conservative_mode() is True
        dharma.set_coherence(0.8)
        assert dharma.is_conservative_mode() is False

    def test_coherence_clamped(self):
        dharma = DharmaProtocol()
        dharma.set_coherence(-0.5)
        assert dharma._coherence_level == 0.0
        dharma.set_coherence(2.0)
        assert dharma._coherence_level == 1.0


class TestWorkspacePersistence:
    """Test GlobalWorkspace state persistence across sessions."""

    def test_persist_and_load_state(self):
        from whitemagic.core.consciousness.global_workspace import _GW_STATE_FILE
        if _GW_STATE_FILE.exists():
            _GW_STATE_FILE.unlink()

        gw1 = GlobalWorkspace()
        gw1.register("mod-b", lambda b: None)
        gw1.propose("mod-a", {"x": 1}, salience=0.9)
        gw1.propose("mod-a", {"x": 2}, salience=0.85)
        gw1.persist_state()

        # Create new instance and load
        gw2 = GlobalWorkspace()
        gw2.load_state()
        assert gw2._total_broadcasts == 2
        assert gw2._total_proposals == 2
        assert len(gw2._history) == 2

        # Cleanup
        if _GW_STATE_FILE.exists():
            _GW_STATE_FILE.unlink()

    def test_load_nonexistent_state(self):
        from whitemagic.core.consciousness.global_workspace import _GW_STATE_FILE
        if _GW_STATE_FILE.exists():
            _GW_STATE_FILE.unlink()

        gw = GlobalWorkspace()
        gw.load_state()  # Should not raise
        assert gw._total_broadcasts == 0

    def test_get_current_state_includes_competition(self):
        gw = GlobalWorkspace(
            fast_ignite_threshold=0.8, competition_window=10.0
        )
        gw.register("mod", lambda b: None)
        gw.propose("src", {"x": 1}, salience=0.4)
        state = gw.get_current_state()
        assert "ignition_count" in state
        assert "pending_proposals" in state
        assert "competition_active" in state
        assert state["pending_proposals"] == 1
        assert state["competition_active"] is True
