# ruff: noqa: BLE001
"""NetworkGuard — Privacy enforcement and network egress auditing.

All outbound network calls must pass through this module. In local_only
mode, all outbound connections are blocked and logged. This is the
privacy enforcement layer for WhiteMagic's local-first design.

Usage:
    from whitemagic.core.consciousness.network_guard import get_network_guard

    guard = get_network_guard()
    guard.check_egress("api.openai.com", 443)  # raises in local_only
    guard.record_egress("localhost", 11434, 1024)  # local, allowed
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import file_lock

logger = logging.getLogger(__name__)

AUDIT_DIR = WM_ROOT / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# Hosts that are always allowed (local only)
_ALLOWED_LOCAL_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
})


@dataclass
class EgressRecord:
    """A single network egress attempt record."""

    timestamp: float
    host: str
    port: int
    bytes_sent: int
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "host": self.host,
            "port": self.port,
            "bytes_sent": self.bytes_sent,
            "allowed": self.allowed,
            "reason": self.reason,
        }


class NetworkGuard:
    """Privacy enforcement — blocks all non-local network egress by default.

    Modes:
    - local_only: Only localhost connections allowed. All others blocked + logged.
    - mesh_enabled: Localhost + mesh peer connections allowed.
    - cloud_enabled: All connections allowed (user explicitly opted in).
    """

    def __init__(self, mode: str = "local_only") -> None:
        self._mode = mode
        self._lock = threading.RLock()
        self._total_bytes_egress = 0
        self._records: list[EgressRecord] = []
        self._audit_file = AUDIT_DIR / "network.jsonl"
        self._allowed_hosts: set[str] = set(_ALLOWED_LOCAL_HOSTS)

        if mode == "mesh_enabled":
            # Mesh peers will be added dynamically
            pass
        elif mode == "cloud_enabled":
            # All hosts allowed
            self._allowed_hosts = None  # type: ignore[assignment]

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def total_bytes_egress(self) -> int:
        return self._total_bytes_egress

    @property
    def privacy_status(self) -> str:
        """Human-readable privacy status for display."""
        if self._mode == "local_only":
            return "local_only"
        elif self._mode == "mesh_enabled":
            return "mesh_enabled"
        elif self._mode == "cloud_enabled":
            return "cloud_enabled"
        return "local_only"

    def is_local(self, host: str) -> bool:
        """Check if a host is local."""
        return host in _ALLOWED_LOCAL_HOSTS

    def check_egress(self, host: str, port: int) -> bool:
        """Check if an outbound connection is allowed.

        Returns True if allowed, False if blocked.
        In local_only mode, only localhost connections are allowed.
        """
        if self._allowed_hosts is None:
            return True  # cloud_enabled, everything allowed

        if host in self._allowed_hosts:
            return True

        # Block and log
        self._record_egress(host, port, 0, allowed=False, reason=f"blocked_by_{self._mode}")
        logger.warning("NetworkGuard: blocked egress to %s:%d (mode=%s)", host, port, self._mode)
        return False

    def record_egress(self, host: str, port: int, bytes_sent: int) -> None:
        """Record a successful egress (for audit trail)."""
        if self.is_local(host):
            return  # Don't log localhost traffic
        self._record_egress(host, port, bytes_sent, allowed=True, reason="permitted")
        with self._lock:
            self._total_bytes_egress += bytes_sent

    def add_allowed_host(self, host: str) -> None:
        """Add a host to the allowlist (e.g., mesh peer)."""
        with self._lock:
            self._allowed_hosts.add(host)

    def remove_allowed_host(self, host: str) -> None:
        """Remove a host from the allowlist."""
        with self._lock:
            self._allowed_hosts.discard(host)

    def set_mode(self, mode: str) -> None:
        """Change the privacy mode."""
        with self._lock:
            self._mode = mode
            if mode == "local_only":
                self._allowed_hosts = set(_ALLOWED_LOCAL_HOSTS)
            elif mode == "mesh_enabled":
                self._allowed_hosts = set(_ALLOWED_LOCAL_HOSTS)
            elif mode == "cloud_enabled":
                self._allowed_hosts = None  # type: ignore[assignment]
            logger.info("NetworkGuard: mode set to %s", mode)

    def get_status(self) -> dict[str, Any]:
        """Get current privacy status for display."""
        return {
            "mode": self._mode,
            "privacy_status": self.privacy_status,
            "total_bytes_egress": self._total_bytes_egress,
            "allowed_hosts": list(self._allowed_hosts) if self._allowed_hosts else "all",
            "records_count": len(self._records),
        }

    def _record_egress(
        self, host: str, port: int, bytes_sent: int, allowed: bool, reason: str,
    ) -> None:
        record = EgressRecord(
            timestamp=time.time(),
            host=host,
            port=port,
            bytes_sent=bytes_sent,
            allowed=allowed,
            reason=reason,
        )
        with self._lock:
            self._records.append(record)
            # Keep only last 1000 records in memory
            if len(self._records) > 1000:
                self._records = self._records[-500:]

        # Persist to audit file
        try:
            with file_lock(self._audit_file):
                with open(self._audit_file, "a") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as e:
            logger.debug("Failed to write network audit: %s", e)


_guard: NetworkGuard | None = None
_guard_lock = threading.RLock()


def get_network_guard() -> NetworkGuard:
    """Get the global NetworkGuard singleton."""
    global _guard
    if _guard is None:
        with _guard_lock:
            if _guard is None:
                mode = os.environ.get("WM_PRIVACY_MODE", "local_only")
                _guard = NetworkGuard(mode=mode)
    return _guard
