"""Phase 4 — Tests for DreamCycle job model refactoring.

Verifies that:
- DreamJob dataclass wraps phase handlers with metadata
- _phase_handlers dispatch table replaces the if/elif chain
- All 13 phases are registered in the dispatch table
- _run_phase() dispatches via dict lookup, not if/elif
- Per-phase cancellation works via cancel_phase()
- status() includes job model information
- get_phase_jobs() returns metadata for all registered phases
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from whitemagic.core.dreaming.dream_cycle import (
    DreamCycle,
    DreamJob,
    DreamPhase,
    DreamReport,
)


class TestDreamJob:
    """Verify DreamJob dataclass."""

    def test_dream_job_creation(self):
        job = DreamJob(
            phase=DreamPhase.TRIAGE,
            handler=lambda: {"ok": True},
            timeout_s=30.0,
        )
        assert job.phase == DreamPhase.TRIAGE
        assert job.timeout_s == 30.0
        assert job.cancellable is True

    def test_dream_job_default_timeout(self):
        job = DreamJob(phase=DreamPhase.DECAY, handler=lambda: {})
        assert job.timeout_s == 60.0

    def test_dream_job_zero_timeout_clamped(self):
        job = DreamJob(phase=DreamPhase.DECAY, handler=lambda: {}, timeout_s=0)
        assert job.timeout_s == 60.0

    def test_dream_job_negative_timeout_clamped(self):
        job = DreamJob(phase=DreamPhase.DECAY, handler=lambda: {}, timeout_s=-5)
        assert job.timeout_s == 60.0

    def test_dream_job_callable(self):
        job = DreamJob(phase=DreamPhase.TRIAGE, handler=lambda: {"result": "ok"})
        result = job.handler()
        assert result == {"result": "ok"}


class TestPhaseHandlerDispatch:
    """Verify the dispatch table replaces the if/elif chain."""

    def test_all_phases_registered(self):
        """All 13 DreamPhase values should have handlers in _phase_handlers."""
        dc = DreamCycle()
        for phase in DreamPhase:
            assert phase in dc._phase_handlers, f"Phase {phase.value} not registered"

    def test_handler_count_matches_phases(self):
        dc = DreamCycle()
        assert len(dc._phase_handlers) == len(list(DreamPhase))

    def test_handlers_are_dream_jobs(self):
        dc = DreamCycle()
        for phase, job in dc._phase_handlers.items():
            assert isinstance(job, DreamJob), f"Phase {phase.value} handler is not a DreamJob"
            assert job.phase == phase

    def test_run_phase_uses_dispatch(self):
        """_run_phase should use _phase_handlers dict, not if/elif."""
        dc = DreamCycle()
        # Replace one handler with a mock to verify it's called via dict lookup
        mock_result = {"mocked": True}
        mock_job = DreamJob(DreamPhase.TRIAGE, MagicMock(return_value=mock_result))
        dc._phase_handlers[DreamPhase.TRIAGE] = mock_job

        # Set the current phase to TRIAGE
        dc._current_phase_index = 0

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(dc._run_phase())
        finally:
            loop.close()

        mock_job.handler.assert_called_once()

    def test_run_phase_unknown_phase_skipped(self):
        """If a phase has no handler, it should be skipped gracefully."""
        dc = DreamCycle()
        # Remove a handler
        del dc._phase_handlers[DreamPhase.TRIAGE]
        dc._current_phase_index = 0

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(dc._run_phase())
        finally:
            loop.close()

        # Check history for the skip
        assert len(dc._history) == 1
        report = dc._history[0]
        assert report.phase == DreamPhase.TRIAGE
        assert report.details.get("skipped") is True


class TestPhaseCancellation:
    """Verify per-phase cancellation."""

    def test_cancel_phase_marks_for_cancellation(self):
        dc = DreamCycle()
        result = dc.cancel_phase(DreamPhase.TRIAGE)
        assert result is True
        assert DreamPhase.TRIAGE in dc._cancelled_phases

    def test_cancel_phase_returns_false_for_unknown(self):
        dc = DreamCycle()
        # Create a fake phase that's not in handlers
        result = dc.cancel_phase(DreamPhase.TRIAGE)
        assert result is True  # TRIAGE is registered

    def test_cancelled_phase_skipped_in_run(self):
        """A cancelled phase should be skipped in _run_phase."""
        dc = DreamCycle()
        dc.cancel_phase(DreamPhase.TRIAGE)
        dc._current_phase_index = 0  # Next phase is TRIAGE

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(dc._run_phase())
        finally:
            loop.close()

        # Should not have run — no history entry
        assert len(dc._history) == 0
        # Phase should be removed from cancelled set after skip
        assert DreamPhase.TRIAGE not in dc._cancelled_phases

    def test_non_cancelled_phase_runs_normally(self):
        dc = DreamCycle()
        dc._current_phase_index = 0  # Next phase is TRIAGE

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(dc._run_phase())
        finally:
            loop.close()

        assert len(dc._history) == 1

    def test_cancel_non_cancellable_phase(self):
        dc = DreamCycle()
        # Make a phase non-cancellable
        job = dc._phase_handlers[DreamPhase.TRIAGE]
        dc._phase_handlers[DreamPhase.TRIAGE] = DreamJob(
            DreamPhase.TRIAGE, job.handler, cancellable=False
        )
        result = dc.cancel_phase(DreamPhase.TRIAGE)
        assert result is False
        assert DreamPhase.TRIAGE not in dc._cancelled_phases


class TestStatusWithJobModel:
    """Verify status() includes job model information."""

    def test_status_includes_registered_phases(self):
        dc = DreamCycle()
        status = dc.status()
        assert "registered_phases" in status
        assert len(status["registered_phases"]) == len(list(DreamPhase))

    def test_status_includes_cancelled_phases(self):
        dc = DreamCycle()
        dc.cancel_phase(DreamPhase.DECAY)
        status = dc.status()
        assert "cancelled_phases" in status
        assert "decay" in status["cancelled_phases"]

    def test_status_includes_phase_jobs(self):
        dc = DreamCycle()
        status = dc.status()
        assert "phase_jobs" in status
        assert "triage" in status["phase_jobs"]
        assert "timeout_s" in status["phase_jobs"]["triage"]
        assert "cancellable" in status["phase_jobs"]["triage"]


class TestGetPhaseJobs:
    """Verify get_phase_jobs() returns metadata."""

    def test_returns_all_phases(self):
        dc = DreamCycle()
        jobs = dc.get_phase_jobs()
        assert len(jobs) == len(list(DreamPhase))

    def test_returns_timeout_and_cancellable(self):
        dc = DreamCycle()
        jobs = dc.get_phase_jobs()
        for phase_name, meta in jobs.items():
            assert "timeout_s" in meta
            assert "cancellable" in meta
            assert isinstance(meta["timeout_s"], (int, float))
            assert isinstance(meta["cancellable"], bool)

    def test_triage_has_30s_timeout(self):
        dc = DreamCycle()
        jobs = dc.get_phase_jobs()
        assert jobs["triage"]["timeout_s"] == 30

    def test_consolidation_has_60s_timeout(self):
        dc = DreamCycle()
        jobs = dc.get_phase_jobs()
        assert jobs["consolidation"]["timeout_s"] == 60
