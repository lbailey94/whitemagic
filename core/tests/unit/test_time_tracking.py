"""Tests for time_tracking module."""

import time

import pytest

from whitemagic.tools.time_tracking import (
    PhaseTimer,
    PhaseTiming,
    WorkflowTimer,
    get_current_time,
    get_local_time,
    timed,
)


class TestPhaseTiming:
    def test_basic_creation(self):
        pt = PhaseTiming(phase_name="test", start_time=time.time())
        assert pt.phase_name == "test"
        assert pt.end_time is None
        assert pt.duration_seconds is None

    def test_duration_calculation(self):
        start = time.time()
        pt = PhaseTiming(phase_name="test", start_time=start, end_time=start + 2.5)
        assert pt.duration_seconds == pytest.approx(2.5, abs=0.01)

    def test_to_dict(self):
        start = time.time()
        pt = PhaseTiming(
            phase_name="test",
            start_time=start,
            end_time=start + 1.0,
            metadata={"key": "val"},
        )
        d = pt.to_dict()
        assert d["phase_name"] == "test"
        assert d["duration_seconds"] == pytest.approx(1.0, abs=0.01)
        assert d["metadata"] == {"key": "val"}


class TestPhaseTimer:
    def test_context_manager(self):
        with PhaseTimer("test_phase") as timer:
            assert timer._timing is not None
            assert timer._timing.phase_name == "test_phase"
        assert timer._timing.end_time is not None
        assert timer._timing.duration_seconds is not None

    def test_context_manager_with_exception(self):
        with pytest.raises(ValueError):
            with PhaseTimer("fail_phase"):
                raise ValueError("boom")

    def test_timing_property(self):
        pt = PhaseTimer("test")
        assert pt.timing is None
        with pt:
            pass
        assert pt.timing is not None


class TestWorkflowTimer:
    def test_workflow_lifecycle(self):
        wf = WorkflowTimer("test_workflow")
        wf.start_workflow()
        assert wf._workflow_start is not None

        with wf.phase("phase1") as p1:
            time.sleep(0.01)
        wf.record_phase(p1)

        wf.end_workflow()
        assert wf._workflow_end is not None

        report = wf.get_report()
        assert report["workflow_name"] == "test_workflow"
        assert report["total_seconds"] > 0
        assert report["phase_count"] == 1

    def test_empty_report(self):
        wf = WorkflowTimer("empty")
        report = wf.get_report()
        assert report["total_seconds"] == 0.0
        assert report["phase_count"] == 0


class TestConvenienceFunctions:
    def test_timed_returns_timer(self):
        t = timed("quick")
        assert isinstance(t, PhaseTimer)

    def test_get_current_time(self):
        ct = get_current_time()
        assert isinstance(ct, str)
        assert "T" in ct  # ISO format

    def test_get_local_time(self):
        lt = get_local_time("UTC")
        assert isinstance(lt, str)
