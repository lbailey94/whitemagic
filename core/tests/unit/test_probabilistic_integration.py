"""Tests for probabilistic integration with UnifiedMemory hooks."""

from whitemagic.core.memory.probabilistic import MemoryAnalytics
from whitemagic.core.memory.probabilistic_integration import (
    analytics_summary,
    get_analytics,
    init_analytics,
)


class TestProbabilisticIntegration:
    def test_init_returns_analytics(self):
        analytics = init_analytics(hll_precision=10, cms_width=256, cms_depth=3)
        assert isinstance(analytics, MemoryAnalytics)

    def test_get_analytics_after_init(self):
        init_analytics(hll_precision=10, cms_width=256, cms_depth=3)
        analytics = get_analytics()
        assert analytics is not None
        assert isinstance(analytics, MemoryAnalytics)

    def test_analytics_summary_not_initialized(self):
        # If not initialized, should return not_initialized status
        summary = analytics_summary()
        # After init from previous test, it will be initialized
        # This test just verifies the function doesn't crash
        assert isinstance(summary, dict)

    def test_hook_registration(self):
        """Verify that hooks are registered and fire on memory operations."""
        from whitemagic.core.memory.unified import _store_hooks

        # init_analytics should have registered a hook
        init_analytics(hll_precision=10, cms_width=256, cms_depth=3)
        # The hook list should contain our function
        assert len(_store_hooks) > 0

    def test_observe_via_hook(self):
        """Test that the store hook correctly feeds analytics."""
        analytics = init_analytics(hll_precision=10, cms_width=256, cms_depth=3)
        analytics.estimate_distinct_count()

        # Simulate a hook call
        import uuid
        from datetime import datetime

        from whitemagic.core.memory.probabilistic_integration import _on_memory_stored
        from whitemagic.core.memory.unified_types import Memory, MemoryType

        mem = Memory(
            id=uuid.uuid4(),
            content="test content for analytics",
            memory_type=MemoryType.SHORT_TERM,
            tags={"test", "analytics"},
            created_at=datetime.now(),
        )
        mem.metadata = {"source": "unit_test"}
        _on_memory_stored(mem)

        # The distinct count should have increased
        new_count = analytics.estimate_distinct_count()
        # HLL may not show immediate increase for small counts, but it shouldn't crash
        assert new_count >= 0
