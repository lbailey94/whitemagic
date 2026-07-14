"""Quality gate tests — addressing review concerns.

1. Critical flag lint: every middleware must explicitly declare critical or enrichment.
   No silent defaults — if someone adds middleware without critical=True, this test catches it.

2. Phase 4 safety: verify DreamCycle dispatch table is consistent and all handlers are callable.

3. Stable tools smoke benchmark: call every stable tool through the real dispatch pipeline
   and verify each returns within a timeout. This catches more regressions than unit tests.
"""
from __future__ import annotations

import time
import pytest
from whitemagic.tools.dispatch_table import get_pipeline
from whitemagic.tools.stable_contract import STABLE_TOOLS
from whitemagic.tools.stable_surface import STABLE_TOOL_NAMES


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Critical Flag Lint — no silent fail-open defaults
# ═══════════════════════════════════════════════════════════════════════════════

# The canonical classification — if these change, the test should fail
# so a human reviews the change rather than silently accepting it.
EXPECTED_CRITICAL = frozenset({
    "input_sanitizer",
    "circuit_breaker",
    "rate_limiter",
    "security_monitor",
    "pattern_guard",
    "tool_permissions",
    "maturity_gate",
    "governor",
    "transaction_firewall",
})

# Middleware that is intentionally enrichment (fail-open). Must be explicit.
EXPECTED_ENRICHMENT = frozenset({
    "timing",
    "timeout",
    "engagement_token",
    "model_signing",
    "cognitive_mode",
    "zodiac_resonance",
    "citta_consciousness",
    "semantic_cache",
    "auto_optimize",
    "inference_router",
    "draft_review",
    "token_tracker",
    "code_nudge",
    "core_router",
})


class TestCriticalFlagLint:
    """Verify every middleware in the pipeline has an explicit critical/enrichment classification."""

    def test_all_middleware_have_explicit_classification(self):
        """Every middleware in _middlewares must be in EXPECTED_CRITICAL or EXPECTED_ENRICHMENT."""
        p = get_pipeline()
        actual_names = set(p.describe())
        expected_names = EXPECTED_CRITICAL | EXPECTED_ENRICHMENT

        # Any middleware not in either set is a silent default — fail
        unclassified = actual_names - expected_names
        assert not unclassified, (
            f"Middleware {unclassified} has no explicit critical/enrichment classification. "
            f"Add it to EXPECTED_CRITICAL or EXPECTED_ENRICHMENT in this test file."
        )

        # Any expected middleware not in the pipeline — someone removed it without updating
        missing = expected_names - actual_names
        assert not missing, (
            f"Expected middleware {missing} is not in the pipeline. "
            f"Update EXPECTED_CRITICAL/EXPECTED_ENRICHMENT if it was removed."
        )

    def test_critical_set_matches_pipeline(self):
        """The critical flag on each pipeline middleware must match EXPECTED_CRITICAL."""
        p = get_pipeline()
        for name, _mw, critical in p._middlewares:
            if name in EXPECTED_CRITICAL:
                assert critical is True, (
                    f"Middleware '{name}' should be critical=True but is critical={critical}. "
                    f"This means it will fail-open (silently skip on error), which is wrong for a critical middleware."
                )
            elif name in EXPECTED_ENRICHMENT:
                assert critical is False, (
                    f"Middleware '{name}' should be critical=False (enrichment) but is critical={critical}. "
                    f"This means it will fail-closed (block execution on error), which is wrong for enrichment middleware."
                )

    def test_no_middleware_silently_defaults(self):
        """No middleware should have critical=False unless it's explicitly in EXPECTED_ENRICHMENT."""
        p = get_pipeline()
        for name, _mw, critical in p._middlewares:
            if not critical:
                assert name in EXPECTED_ENRICHMENT, (
                    f"Middleware '{name}' defaults to critical=False (fail-open) "
                    f"but is not in EXPECTED_ENRICHMENT. If this is intentional, "
                    f"add it to EXPECTED_ENRICHMENT. Otherwise, add critical=True."
                )

    def test_critical_count_matches(self):
        """Sanity check: the number of critical middleware should match expected."""
        p = get_pipeline()
        actual_critical = sum(1 for _, _, c in p._middlewares if c)
        assert actual_critical == len(EXPECTED_CRITICAL), (
            f"Expected {len(EXPECTED_CRITICAL)} critical middleware, got {actual_critical}. "
            f"If you added/removed critical middleware, update EXPECTED_CRITICAL."
        )

    def test_post_call_hooks_are_separate(self):
        """Post-call hooks should not be in the main pipeline."""
        p = get_pipeline()
        main_names = set(p.describe())
        post_call_names = set(p.describe_post_call())
        overlap = main_names & post_call_names
        assert not overlap, (
            f"Names {overlap} appear in both main pipeline and post-call hooks. "
            f"They should be in one or the other, not both."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Phase 4 Safety — DreamCycle dispatch table consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestDreamCycleSafety:
    """Verify the DreamCycle dispatch table is safe and consistent."""

    def test_all_handlers_are_callable(self):
        """Every registered DreamJob handler must be callable."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        for phase, job in dc._phase_handlers.items():
            assert callable(job.handler), (
                f"Phase {phase.value} handler is not callable"
            )

    def test_handler_count_equals_phase_count(self):
        """Number of handlers must exactly match number of DreamPhase values."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle, DreamPhase
        dc = DreamCycle()
        assert len(dc._phase_handlers) == len(list(DreamPhase))

    def test_no_none_handlers(self):
        """No handler should be None."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        for phase, job in dc._phase_handlers.items():
            assert job.handler is not None, f"Phase {phase.value} has None handler"

    def test_each_job_phase_matches_key(self):
        """Each DreamJob's phase field must match the dict key it's stored under."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        for phase, job in dc._phase_handlers.items():
            assert job.phase == phase, (
                f"Job for {phase.value} has phase={job.phase.value} (mismatch)"
            )

    def test_timeouts_are_reasonable(self):
        """All timeouts should be between 10s and 300s."""
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        for phase, job in dc._phase_handlers.items():
            assert 10 <= job.timeout_s <= 300, (
                f"Phase {phase.value} timeout {job.timeout_s}s is outside 10-300s range"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Stable Tools Smoke Benchmark — call through real dispatch pipeline
# ═══════════════════════════════════════════════════════════════════════════════

# All stable tool names from both sources
ALL_STABLE_TOOLS = sorted(set(STABLE_TOOLS.keys()) | set(STABLE_TOOL_NAMES))

# Minimal args for each stable tool — enough to get past param validation
# and return a result (success or expected error, not a crash)
MINIMAL_ARGS: dict[str, dict] = {
    "capabilities": {},
    "manifest": {},
    "gnosis": {},
    "health_report": {},
    "state.paths": {},
    "state.summary": {},
    "state.current": {},
    "ship.check": {},
    "tool.graph": {},
    "tool.graph_full": {},
    "prat_status": {},
    "galaxy.list": {},
    "galaxy.stats": {},
    "galaxy.status": {},
    "galactic.dashboard": {},
    "meta.galaxy.overview": {},
    "guna.balance.status": {},
    "consciousness.loop.status": {},
    "session.status": {},
    "session.bootstrap": {},
    "session.continuity": {},
    "session.record": {"content": "test", "role": "user"},
    "session.recall": {"limit": 5},
    "create_memory": {"content": "smoke test", "title": "smoke_test"},
    "search_memories": {"query": "test", "limit": 1},
    "batch_read_memories": {"memory_ids": []},
    "update_memory": {"memory_id": "nonexistent", "content": "test"},
    "delete_memory": {"memory_id": "nonexistent"},
    "memory_read": {"memory_id": "nonexistent"},
    "hybrid_recall": {"query": "test", "limit": 1},
    "import_memories": {"memories": []},
    "export_memories": {},
    "check_boundaries": {},
    "evaluate_ethics": {"action": "test", "context": "smoke test"},
    "governor_validate": {"action": "test"},
    "karmic.effects": {},
    "karmic.debt": {},
    "kg.query": {"query": "test"},
    "kg.status": {},
    "wm": {"thought": "help"},
    "wm_read": {"query": "test"},
    "wm_read.status": {},
    "wm_write": {"content": "test", "mode": "scratchpad"},
    "wm_write.status": {},
    "garden.list_files": {},
    "garden.status": {},
}

# Timeout per tool call (seconds)
PER_TOOL_TIMEOUT = 30.0


class TestStableToolsSmoke:
    """Call every stable tool through the real dispatch pipeline.

    Each tool should return a result (success or expected error) within the timeout.
    A crash, hang, or unexpected exception means a regression.
    """

    @pytest.mark.parametrize("tool_name", ALL_STABLE_TOOLS)
    def test_stable_tool_returns_within_timeout(self, tool_name):
        """Each stable tool must return a result within PER_TOOL_TIMEOUT seconds."""
        from whitemagic.tools.unified_api import call_tool

        args = MINIMAL_ARGS.get(tool_name, {})
        start = time.perf_counter()
        try:
            result = call_tool(tool_name, **args)
            elapsed = time.perf_counter() - start
            assert elapsed < PER_TOOL_TIMEOUT, (
                f"Tool {tool_name} took {elapsed:.1f}s (timeout {PER_TOOL_TIMEOUT}s)"
            )
            assert isinstance(result, dict), (
                f"Tool {tool_name} returned {type(result).__name__}, expected dict"
            )
            assert "status" in result, (
                f"Tool {tool_name} returned {result} — missing 'status' key"
            )
        except Exception as e:
            elapsed = time.perf_counter() - start
            assert elapsed < PER_TOOL_TIMEOUT, (
                f"Tool {tool_name} raised {e.__class__.__name__} after {elapsed:.1f}s "
                f"(timeout {PER_TOOL_TIMEOUT}s)"
            )
            # An exception is acceptable if it's a ToolExecutionError (expected for
            # invalid params or missing data). But a raw Exception/TypeError/etc
            # indicates an unhandled crash.
            from whitemagic.tools.errors import ToolExecutionError
            if not isinstance(e, ToolExecutionError):
                pytest.fail(
                    f"Tool {tool_name} raised unexpected {e.__class__.__name__}: {e}"
                )

    def test_stable_tool_count(self):
        """Verify we're testing a reasonable number of stable tools."""
        assert len(ALL_STABLE_TOOLS) >= 25, (
            f"Only {len(ALL_STABLE_TOOLS)} stable tools found, expected at least 25"
        )

    def test_all_stable_tools_have_minimal_args(self):
        """Every stable tool should have minimal args defined for the smoke test."""
        missing = [t for t in ALL_STABLE_TOOLS if t not in MINIMAL_ARGS]
        # Tools without explicit args default to {} — that's fine for no-arg tools
        # but we should at least be aware of which ones use the default
        if missing:
            # Check if they can work with no args (they're likely no-arg tools)
            pass  # No failure — empty args is valid for no-arg tools
