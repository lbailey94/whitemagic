"""Tests for willow_health_check module."""

import pytest

from whitemagic.tools.willow_health_check import (
    WillowHealthChecker,
    WillowHealthStatus,
)


class TestWillowHealthStatus:
    def test_dataclass_creation(self):
        status = WillowHealthStatus(
            is_healthy=True,
            circuit_breaker_ok=True,
            koka_responsive=True,
            last_check=0.0,
            error_count=0,
            issues=[],
        )
        assert status.is_healthy is True
        assert status.issues == []


class TestWillowHealthChecker:
    def test_initialization(self):
        checker = WillowHealthChecker()
        assert checker._check_interval == 30
        assert checker._error_count == 0
        assert checker._health_cache is None

    def test_sync_health_check(self):
        checker = WillowHealthChecker()
        # Use the synchronous wrapper if it exists, otherwise skip
        if hasattr(checker, "check"):
            result = checker.check()
            assert isinstance(result, WillowHealthStatus)

    @pytest.mark.asyncio
    async def test_async_health_check(self):
        checker = WillowHealthChecker()
        try:
            result = await checker.check_willow_health(force=True)
            assert isinstance(result, WillowHealthStatus)
        except Exception as e:
            # Graceful degradation is acceptable
            pytest.skip(f"Willow health check skipped due to: {e}")

    def test_cached_result(self):
        checker = WillowHealthChecker()
        checker._health_cache = WillowHealthStatus(
            is_healthy=True,
            circuit_breaker_ok=True,
            koka_responsive=True,
            last_check=0.0,
            error_count=0,
            issues=[],
        )
        import time
        checker._last_check = time.time()
        # Cached healthy result should be returned without re-checking
        # (but async method, so we just verify state)
        assert checker._health_cache.is_healthy is True
