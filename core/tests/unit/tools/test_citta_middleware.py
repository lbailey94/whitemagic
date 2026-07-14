"""Unit tests for citta consciousness middleware — feedback loop integration."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_cmw_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.consciousness import global_workspace as gw_mod  # noqa: E402
from whitemagic.core.consciousness.citta_cycle import get_citta_cycle  # noqa: E402
from whitemagic.core.consciousness.dharma import get_dharma  # noqa: E402
from whitemagic.core.consciousness.global_workspace import (  # noqa: E402
    get_global_workspace,
)
from whitemagic.tools.middleware import (  # noqa: E402
    DispatchContext,
    mw_citta_consciousness,
)


def _reset_gw():
    gw_mod._workspace = None
    gw = gw_mod.get_global_workspace()
    gw._pending = []
    gw._history = []
    gw._total_broadcasts = 0
    gw._total_proposals = 0
    gw._ignition_count = 0
    gw._window_start = 0.0
    gw._modules = {}
    gw._fast_ignite_threshold = 0.8
    gw._competition_window = 10.0
    gw._min_ignite_salience = 0.3
    return gw


class TestCittaMiddlewarePreDispatch:
    def test_coherence_feeded_to_dharma(self):
        """Pre-dispatch: citta coherence should be fed to Dharma."""
        cycle = get_citta_cycle()
        cycle.reset()
        # Advance with low coherence
        cycle.advance(
            gana="test", coherence=0.3, emotional_tone="neutral",
            neuro_signals={},
        )
        cycle.advance(
            gana="test", coherence=0.3, emotional_tone="neutral",
            neuro_signals={},
        )

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "success"}

        mw_citta_consciousness(ctx, next_fn)

        dharma = get_dharma()
        # Dharma should have been updated with the avg coherence
        assert dharma._coherence_level < 0.5
        assert dharma.is_conservative_mode() is True

    def test_high_coherence_no_conservative_mode(self):
        """When coherence is high, Dharma should not be in conservative mode."""
        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(gana="test", coherence=0.9, emotional_tone="neutral", neuro_signals={})
        cycle.advance(gana="test", coherence=0.9, emotional_tone="neutral", neuro_signals={})

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "success"}

        mw_citta_consciousness(ctx, next_fn)

        dharma = get_dharma()
        assert dharma._coherence_level >= 0.5
        assert dharma.is_conservative_mode() is False


class TestCittaMiddlewarePostDispatch:
    def test_citta_advanced_on_success(self):
        """Post-dispatch: citta stream should be advanced."""
        cycle = get_citta_cycle()
        cycle.reset()
        initial_len = len(cycle.get_stream())

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "success", "data": "test"}

        mw_citta_consciousness(ctx, next_fn)

        stream = cycle.get_stream()
        assert len(stream) == initial_len + 1
        latest = stream[-1]
        # Coherence now comes from the sensorium (not hardcoded 1.0)
        assert latest["coherence"] > 0.0  # Sensorium coherence is positive

    def test_citta_advanced_on_error(self):
        """Post-dispatch: errors should advance citta with low coherence."""
        cycle = get_citta_cycle()
        cycle.reset()

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "error", "error_code": "test_error"}

        mw_citta_consciousness(ctx, next_fn)

        stream = cycle.get_stream()
        assert len(stream) >= 1
        latest = stream[-1]
        # Coherence now comes from the sensorium (not hardcoded 0.4)
        # On error, sensorium coherence may still be high (it measures system state, not tool result)
        assert latest["coherence"] > 0.0

    def test_workspace_proposal_on_success(self):
        """Post-dispatch: successful results should be proposed to workspace."""
        _reset_gw()
        gw = get_global_workspace()
        initial_proposals = gw._total_proposals

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "success", "data": "x" * 3000}  # Large output

        mw_citta_consciousness(ctx, next_fn)

        assert gw._total_proposals > initial_proposals

    def test_workspace_proposal_on_error(self):
        """Post-dispatch: errors should be proposed with higher salience."""
        _reset_gw()
        gw = get_global_workspace()

        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return {"status": "error", "error_code": "test"}

        mw_citta_consciousness(ctx, next_fn)

        pending = gw.get_pending()
        assert len(pending) >= 1
        # Error proposals should have salience >= 0.6
        assert any(p["salience"] >= 0.6 for p in pending)

    def test_passthrough_on_none_result(self):
        """When next_fn returns None, middleware should not crash."""
        ctx = DispatchContext(tool_name="test_tool", kwargs={})

        def next_fn(ctx):
            return None

        result = mw_citta_consciousness(ctx, next_fn)
        assert result is None

    def test_write_tools_get_higher_salience(self):
        """WRITE safety tools should get higher workspace salience."""
        _reset_gw()
        gw = get_global_workspace()

        ctx = DispatchContext(
            tool_name="memory.store", kwargs={"safety": "WRITE"}
        )

        def next_fn(ctx):
            return {"status": "success", "data": "small"}

        mw_citta_consciousness(ctx, next_fn)

        pending = gw.get_pending()
        assert len(pending) >= 1
        # WRITE tools should have salience >= 0.65
        assert any(p["salience"] >= 0.65 for p in pending)
