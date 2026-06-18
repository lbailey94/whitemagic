"""Gana Willow Health Check and Resilience System.

This module provides health checks and recovery procedures for Gana Willow
to prevent MCP hang issues. Implements circuit breaker validation,
Koka handler timeout wrapping, and automatic recovery.
"""
# ruff: noqa: BLE001

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class WillowHealthStatus:
    """Health status for Willow tools."""
    is_healthy: bool
    circuit_breaker_ok: bool
    koka_responsive: bool
    last_check: float
    error_count: int
    issues: list[str]

class WillowHealthChecker:
    """Health monitoring and recovery for Gana Willow."""

    def __init__(self):
        self._last_check = 0
        self._health_cache: WillowHealthStatus | None = None
        self._check_interval = 30  # seconds
        self._error_count = 0
        self._recovery_attempts = 0

    async def check_willow_health(self, force: bool = False) -> WillowHealthStatus:
        """Comprehensive health check for Willow tools."""
        current_time = time.time()

        # Use cache if recent and not forced
        if (not force and
            self._health_cache and
            current_time - self._last_check < self._check_interval and
            self._health_cache.is_healthy):
            return self._health_cache

        logger.info("🌿 Performing Willow health check...")

        issues = []
        circuit_ok = True
        koka_ok = True

        # 1. Check circuit breaker state
        try:
            from whitemagic.tools.circuit_breaker import get_breaker_registry
            registry = get_breaker_registry()

            # Check Willow-specific breakers
            willow_breakers = [
                "grimoire_list", "grimoire_read", "grimoire_cast",
                "cast_oracle", "fool_guard_ralph", "fool_guard_dare_to_die"
            ]

            for breaker_name in willow_breakers:
                breaker = registry.get(breaker_name)
                if breaker and breaker.is_open():
                    issues.append(f"Circuit breaker open: {breaker_name}")
                    circuit_ok = False

        except ImportError:
            issues.append("Circuit breaker registry unavailable")
            circuit_ok = False
        except (ImportError, ModuleNotFoundError) as e:
            issues.append(f"Circuit breaker check failed: {e}")
            circuit_ok = False

        # 2. Test Koka handler responsiveness
        try:
            # Quick Koka health check
            from whitemagic.core.acceleration.koka_bridge import koka_health_check
            koka_result = await koka_health_check()

            if koka_result.get("status") not in ("success", "partial"):
                issues.append(f"Koka handler unresponsive: {koka_result}")
                koka_ok = False

        except ImportError:
            logger.debug("Koka bridge not available, skipping check")
            koka_ok = None  # Not an error if unavailable
        except (ImportError, ModuleNotFoundError) as e:
            issues.append(f"Koka health check failed: {e}")
            koka_ok = False

        # 3. Test grimoire handler availability
        try:
            # Quick non-blocking test
            test_result = await self._test_grimoire_handler()
            if not test_result:
                issues.append("Grimoire handler test failed")

        except ImportError:
            issues.append("Grimoire handler unavailable")
        except (ImportError, ModuleNotFoundError) as e:
            issues.append(f"Grimoire handler test failed: {e}")

        # Determine overall health
        is_healthy = circuit_ok and (koka_ok is not False) and len(issues) == 0

        # Update error count
        if not is_healthy:
            self._error_count += 1
        else:
            self._error_count = max(0, self._error_count - 1)  # Decay errors

        # Create status
        status = WillowHealthStatus(
            is_healthy=is_healthy,
            circuit_breaker_ok=circuit_ok,
            koka_responsive=koka_ok,
            last_check=current_time,
            error_count=self._error_count,
            issues=issues
        )

        self._health_cache = status
        self._last_check = current_time

        logger.info(f"🌿 Willow health check complete: {'✅' if is_healthy else '❌'}")
        if issues:
            logger.warning(f"🌿 Issues found: {issues}")

        return status

    async def _test_grimoire_handler(self) -> bool:
        """Test grimoire handler with minimal load."""
        try:
            # Import and test basic functionality
            from whitemagic.tools.handlers.grimoire import handle_grimoire_list

            # Quick list operation with timeout
            result = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(handle_grimoire_list, limit=1)),
                timeout=5.0
            )

            return result.get("status") == "success"

        except TimeoutError:
            logger.warning("🌿 Grimoire handler timeout")
            return False
        except Exception as e:
            logger.warning(f"🌿 Grimoire handler test error: {e}")
            return False

    async def attempt_recovery(self) -> bool:
        """Attempt to recover Willow functionality."""
        self._recovery_attempts += 1
        logger.info(f"🌿 Attempting Willow recovery (attempt #{self._recovery_attempts})")

        recovery_success = False

        # 1. Reset circuit breakers
        try:
            from whitemagic.tools.circuit_breaker import get_breaker_registry
            registry = get_breaker_registry()

            willow_breakers = [
                "grimoire_list", "grimoire_read", "grimoire_cast",
                "cast_oracle", "fool_guard_ralph", "fool_guard_dare_to_die"
            ]

            for breaker_name in willow_breakers:
                breaker = registry.get_breaker(breaker_name)
                if breaker and breaker.is_open():
                    breaker.reset()
                    logger.info(f"🌿 Reset circuit breaker: {breaker_name}")
                    recovery_success = True

        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.error(f"🌿 Circuit breaker recovery failed: {e}")

        # 2. Reinitialize Koka bridge
        try:
            from whitemagic.core.acceleration.koka_bridge import reinitialize_koka
            koka_result = await reinitialize_koka()
            if koka_result.get("status") == "success":
                logger.info("🌿 Koka bridge reinitialized")
                recovery_success = True

        except ImportError:
            logger.debug("Koka bridge not available for recovery")
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"🌿 Koka recovery failed: {e}")

        # 3. Clear health cache to force recheck
        self._health_cache = None

        # Test recovery
        if recovery_success:
            await asyncio.sleep(1)  # Brief pause for stabilization
            health = await self.check_willow_health(force=True)
            return health.is_healthy

        return False

    async def get_willow_recommendations(self) -> dict[str, Any]:
        """Get recommendations for Willow optimization."""
        health = await self.check_willow_health()

        recommendations = []

        if not health.circuit_breaker_ok:
            recommendations.append({
                "type": "circuit_breaker",
                "priority": "high",
                "action": "Reset circuit breakers for Willow tools",
                "auto_recover": True
            })

        if health.koka_responsive is False:
            recommendations.append({
                "type": "koka_handler",
                "priority": "medium",
                "action": "Reinitialize Koka bridge",
                "auto_recover": True
            })

        if health.error_count > 5:
            recommendations.append({
                "type": "error_rate",
                "priority": "medium",
                "action": "Investigate recurring errors in Willow operations",
                "auto_recover": False
            })

        return {
            "health": health,
            "recommendations": recommendations,
            "auto_recovery_available": any(r.get("auto_recover", False) for r in recommendations)
        }

# Global health checker
_willow_health_checker: WillowHealthChecker | None = None

def get_willow_health_checker() -> WillowHealthChecker:
    """Get the global Willow health checker."""
    global _willow_health_checker
    if _willow_health_checker is None:
        _willow_health_checker = WillowHealthChecker()
    return _willow_health_checker

# Integration with unified API
async def willow_pre_check(tool_name: str) -> bool:
    """Pre-check for Willow tool operations."""
    checker = get_willow_health_checker()
    health = await checker.check_willow_health()

    if not health.is_healthy:
        # Attempt auto-recovery
        recovered = await checker.attempt_recovery()
        if recovered:
            logger.info(f"🌿 Auto-recovered before {tool_name}")
            return True
        else:
            logger.warning(f"🌿 Willow unhealthy, blocking {tool_name}")
            return False

    return True

# Timeout wrapper for Koka operations
async def koka_timeout_wrapper(operation, timeout_seconds: float = 5.0):
    """Wrap Koka operations with timeout and error handling."""
    try:
        result = await asyncio.wait_for(operation, timeout=timeout_seconds)
        return {"status": "success", "result": result}
    except TimeoutError:
        logger.warning(f"🌿 Koka operation timed out after {timeout_seconds}s")
        return {"status": "error", "error": "timeout"}
    except Exception as e:
        logger.warning(f"🌿 Koka operation failed: {e}")
        return {"status": "error", "error": str(e)}
