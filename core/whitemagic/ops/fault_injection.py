"""Fault Injection Harness — Controlled failure injection for testing.

Phase 8 WI 2 of the Codebase Hardening Strategy.

Injects controlled failures into the running system to verify:
- Error handling paths work correctly
- Fallbacks engage properly
- Partial operations report errors explicitly
- Native bridges fail over to Python
- Cache corruption is detected
- Network failures are handled gracefully

Fault types:
- database_lock: Simulates SQLite database lock contention
- corrupt_schema: Simulates schema mismatch / corruption
- missing_dependency: Simulates optional import failure
- native_bridge_crash: Simulates native bridge process crash
- malformed_tool_response: Simulates handler returning bad data
- cache_corruption: Simulates cache returning stale/wrong data
- network_failure: Simulates network timeout / connection error

Usage::

    from whitemagic.ops.fault_injection import FaultInjector, FaultType

    injector = FaultInjector()
    injector.inject(FaultType.DATABASE_LOCK, duration_s=2.0)

    try:
        result = dispatch("search_memories", query="test")
        assert result["status"] == "error"
        assert result["error_code"] == "database_locked"
    finally:
        injector.clear()
"""
from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from unittest.mock import patch

logger = logging.getLogger(__name__)


class FaultType(StrEnum):
    """Types of faults that can be injected."""

    DATABASE_LOCK = "database_lock"
    CORRUPT_SCHEMA = "corrupt_schema"
    MISSING_DEPENDENCY = "missing_dependency"
    NATIVE_BRIDGE_CRASH = "native_bridge_crash"
    MALFORMED_TOOL_RESPONSE = "malformed_tool_response"
    CACHE_CORRUPTION = "cache_corruption"
    NETWORK_FAILURE = "network_failure"


@dataclass
class FaultConfig:
    """Configuration for an injected fault."""

    fault_type: FaultType
    duration_s: float = 5.0
    target_module: str = ""
    target_function: str = ""
    target_tool: str = ""
    error_message: str = ""
    inject_probability: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultRecord:
    """Record of a fault injection and its outcome."""

    fault_type: FaultType
    injected_at: float = 0.0
    cleared_at: float = 0.0
    triggered_count: int = 0
    config: FaultConfig | None = None


class FaultInjector:
    """Controlled fault injection harness for testing.

    Injects failures into the running system using mocks, patches,
    and environment manipulation. All faults are automatically cleared
    on exit or when clear() is called.

    Usage::

        injector = FaultInjector()

        # Inject a database lock fault
        injector.inject(FaultType.DATABASE_LOCK, duration_s=2.0)

        # Run your test
        result = dispatch("search_memories", query="test")
        assert result["status"] == "error"

        # Clear all faults
        injector.clear()
    """

    def __init__(self) -> None:
        self._active_faults: dict[FaultType, FaultConfig] = {}
        self._patches: list[Any] = []
        self._records: list[FaultRecord] = []
        self._triggered: dict[FaultType, int] = {}

    @property
    def active_faults(self) -> list[FaultType]:
        return list(self._active_faults.keys())

    @property
    def records(self) -> list[FaultRecord]:
        return list(self._records)

    def inject(
        self,
        fault_type: FaultType,
        duration_s: float = 5.0,
        target_module: str = "",
        target_function: str = "",
        target_tool: str = "",
        error_message: str = "",
        **metadata: Any,
    ) -> FaultConfig:
        """Inject a fault of the given type."""
        config = FaultConfig(
            fault_type=fault_type,
            duration_s=duration_s,
            target_module=target_module,
            target_function=target_function,
            target_tool=target_tool,
            error_message=error_message or f"Injected {fault_type.value} fault",
            metadata=metadata,
        )
        self._active_faults[fault_type] = config
        self._triggered[fault_type] = 0
        self._apply_fault(config)
        logger.info("Injected fault: %s (duration=%.1fs)", fault_type.value, duration_s)
        return config

    def clear(self) -> None:
        """Clear all injected faults."""
        for fault_type, config in list(self._active_faults.items()):
            record = FaultRecord(
                fault_type=fault_type,
                injected_at=config.metadata.get("_injected_at", 0.0),
                cleared_at=time.time(),
                triggered_count=self._triggered.get(fault_type, 0),
                config=config,
            )
            self._records.append(record)

        for p in self._patches:
            try:
                p.stop()
            except Exception:  # noqa: BLE001
                logger.debug("Ignored error in fault_injection.py:165")
        self._patches.clear()
        self._active_faults.clear()
        self._triggered.clear()
        logger.info("All faults cleared")

    def clear_fault(self, fault_type: FaultType) -> None:
        """Clear a single fault type."""
        if fault_type not in self._active_faults:
            return
        config = self._active_faults.pop(fault_type)
        record = FaultRecord(
            fault_type=fault_type,
            injected_at=config.metadata.get("_injected_at", 0.0),
            cleared_at=time.time(),
            triggered_count=self._triggered.get(fault_type, 0),
            config=config,
        )
        self._records.append(record)
        # Re-apply remaining faults (some patches may need to be re-established)
        # For simplicity, we just clear all and re-apply
        for p in self._patches:
            try:
                p.stop()
            except Exception:  # noqa: BLE001
                logger.debug("Ignored error in fault_injection.py:190")
        self._patches.clear()
        remaining = dict(self._active_faults)
        self._active_faults.clear()
        for ft, cfg in remaining.items():
            self._active_faults[ft] = cfg
            self._apply_fault(cfg)

    def is_fault_active(self, fault_type: FaultType) -> bool:
        return fault_type in self._active_faults

    def _trigger(self, fault_type: FaultType) -> None:
        self._triggered[fault_type] = self._triggered.get(fault_type, 0) + 1

    def _apply_fault(self, config: FaultConfig) -> None:
        """Apply the fault using appropriate mocking/patching."""
        config.metadata["_injected_at"] = time.time()
        ft = config.fault_type

        if ft == FaultType.DATABASE_LOCK:
            self._apply_database_lock(config)
        elif ft == FaultType.CORRUPT_SCHEMA:
            self._apply_corrupt_schema(config)
        elif ft == FaultType.MISSING_DEPENDENCY:
            self._apply_missing_dependency(config)
        elif ft == FaultType.NATIVE_BRIDGE_CRASH:
            self._apply_native_bridge_crash(config)
        elif ft == FaultType.MALFORMED_TOOL_RESPONSE:
            self._apply_malformed_response(config)
        elif ft == FaultType.CACHE_CORRUPTION:
            self._apply_cache_corruption(config)
        elif ft == FaultType.NETWORK_FAILURE:
            self._apply_network_failure(config)

    def _apply_database_lock(self, config: FaultConfig) -> None:
        """Inject database lock contention."""
        lock_error = sqlite3.OperationalError("database is locked")

        def _locked_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            self._trigger(FaultType.DATABASE_LOCK)
            raise lock_error

        p = patch("sqlite3.connect", side_effect=_locked_connect)
        p.start()
        self._patches.append(p)

    def _apply_corrupt_schema(self, config: FaultConfig) -> None:
        """Inject schema corruption."""
        error = sqlite3.DatabaseError("database disk image is malformed")

        def _corrupt_execute(self: Any, sql: str, *args: Any, **kwargs: Any) -> Any:
            if "CREATE TABLE" in sql or "SELECT" in sql:
                self._trigger(FaultType.CORRUPT_SCHEMA)
                raise error
            return self.__class__.__bases__[0].execute(self, sql, *args, **kwargs)  # type: ignore[no-any-return]

        p = patch("sqlite3.Cursor.execute", side_effect=_corrupt_execute)
        p.start()
        self._patches.append(p)

    def _apply_missing_dependency(self, config: FaultConfig) -> None:
        """Inject missing optional dependency."""
        target = config.target_module or "whitemagic.core.acceleration.rust_bridge"
        p = patch.dict("sys.modules", {target: None})
        p.start()
        self._patches.append(p)

    def _apply_native_bridge_crash(self, config: FaultConfig) -> None:
        """Inject native bridge process crash."""
        from whitemagic.core.acceleration.process_supervisor import BridgeResult

        injector = self

        def _crash_call(*args: Any, **kwargs: Any) -> BridgeResult:
            injector._trigger(FaultType.NATIVE_BRIDGE_CRASH)
            return BridgeResult(
                ok=False,
                data=None,
                fallback=True,
                error="Injected bridge crash",
            )

        p = patch(
            "whitemagic.core.acceleration.process_supervisor.ProcessSupervisor.call",
            side_effect=_crash_call,
        )
        p.start()
        self._patches.append(p)

    def _apply_malformed_response(self, config: FaultConfig) -> None:
        """Inject malformed tool response."""
        target = config.target_tool or "gnosis"

        def _malformed_handler(*args: Any, **kwargs: Any) -> dict[str, Any]:
            self._trigger(FaultType.MALFORMED_TOOL_RESPONSE)
            return {"invalid": True, "no_status_field": "malformed"}  # type: ignore[dict-item]

        # Patch the dispatch to return malformed data for the target tool
        original_dispatch: Callable[..., Any] | None = None
        try:
            from whitemagic.tools.dispatch_table import dispatch as _orig

            original_dispatch = _orig
        except ImportError:
            logger.debug("Optional dependency unavailable: ImportError")

        def _patched_dispatch(tool_name: str, **kwargs: Any) -> dict[str, Any]:
            if tool_name == target or not target:
                self._trigger(FaultType.MALFORMED_TOOL_RESPONSE)
                return {"invalid": True, "no_status_field": "malformed"}  # type: ignore[dict-item]
            if original_dispatch is not None:
                return original_dispatch(tool_name, **kwargs)  # type: ignore[no-any-return]
            return {"status": "error", "error_code": "dispatch_unavailable"}

        p = patch("whitemagic.tools.dispatch_table.dispatch", side_effect=_patched_dispatch)
        p.start()
        self._patches.append(p)

    def _apply_cache_corruption(self, config: FaultConfig) -> None:
        """Inject cache corruption — cache returns wrong data."""

        _corrupt_cache: dict[str, dict[str, Any]] = {}

        def _corrupted_key(*args: Any, **kwargs: Any) -> str:
            self._trigger(FaultType.CACHE_CORRUPTION)
            return "corrupted_cache_key_injected"

        p = patch("whitemagic.tools.middleware._cache_key", side_effect=_corrupted_key)
        p.start()
        self._patches.append(p)

    def _apply_network_failure(self, config: FaultConfig) -> None:
        """Inject network failure."""

        def _network_error(*args: Any, **kwargs: Any) -> Any:
            self._trigger(FaultType.NETWORK_FAILURE)
            raise TimeoutError("Injected network timeout")

        p = patch("socket.socket.connect", side_effect=_network_error)
        p.start()
        self._patches.append(p)


@contextmanager
def fault_injected(fault_type: FaultType, **kwargs: Any):
    """Context manager for scoped fault injection.

    Usage::

        with fault_injected(FaultType.DATABASE_LOCK):
            result = dispatch("search_memories", query="test")
            assert result["status"] == "error"
    """
    injector = FaultInjector()
    injector.inject(fault_type, **kwargs)
    try:
        yield injector
    finally:
        injector.clear()
