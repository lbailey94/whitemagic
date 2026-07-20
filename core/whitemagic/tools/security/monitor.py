"""Real-time security monitoring — watch for new vulnerabilities and alerts."""
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event, Thread
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SecurityAlert:
    alert_id: str
    severity: str
    source: str
    message: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


class SecurityMonitor:
    """Real-time security monitoring with alerting."""

    def __init__(self, max_history: int = 1000) -> None:
        self._alerts: deque[SecurityAlert] = deque(maxlen=max_history)
        self._callbacks: list[Callable[[SecurityAlert], None]] = []
        self._running = False
        self._stop_event = Event()
        self._monitor_thread: Thread | None = None
        self._alert_counter = 0

    def add_alert(self, severity: str, source: str, message: str, data: dict[str, Any] | None = None) -> SecurityAlert:
        """Add a security alert and notify callbacks."""
        self._alert_counter += 1
        alert = SecurityAlert(
            alert_id=f"ALT-{self._alert_counter:06d}",
            severity=severity,
            source=source,
            message=message,
            timestamp=time.time(),
            data=data or {},
        )
        self._alerts.append(alert)
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception as e:  # noqa: BLE001
                logger.warning("Alert callback failed: %s", e)
        logger.info("Security alert [%s]: %s — %s", severity, source, message)
        return alert

    def register_callback(self, callback: Callable[[SecurityAlert], None]) -> None:
        self._callbacks.append(callback)

    def get_alerts(self, severity: str | None = None, limit: int = 100) -> list[SecurityAlert]:
        """Get recent alerts, optionally filtered by severity."""
        alerts = list(self._alerts)
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts[-limit:]

    def start_monitoring(self, check_interval: int = 60) -> None:
        """Start background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, args=(check_interval,), daemon=True)
        self._monitor_thread.start()
        logger.info("Security monitoring started (interval=%ds)", check_interval)

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._stop_event.set()
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Security monitoring stopped")

    def _monitor_loop(self, interval: int) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._run_checks()
            except Exception as e:  # noqa: BLE001
                logger.warning("Monitor check failed: %s", e)
            self._stop_event.wait(interval)

    def _run_checks(self) -> None:
        """Run periodic security checks."""
        # Check for new bounty targets
        # Check for new vulnerability disclosures
        # Check for monitored contract state changes
        pass

    def monitor_contract(self, address: str, chain_id: int = 1) -> dict[str, Any]:
        """Register a contract for monitoring."""
        return {
            "address": address,
            "chain_id": chain_id,
            "monitoring": True,
            "registered_at": time.time(),
        }

    def monitor_contest(self, contest_url: str) -> dict[str, Any]:
        """Register a contest for monitoring."""
        return {
            "contest_url": contest_url,
            "monitoring": True,
            "registered_at": time.time(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "total_alerts": len(self._alerts),
            "callbacks": len(self._callbacks),
            "critical_alerts": sum(1 for a in self._alerts if a.severity == "critical"),
            "high_alerts": sum(1 for a in self._alerts if a.severity == "high"),
        }


_monitor: SecurityMonitor | None = None


def get_security_monitor() -> SecurityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SecurityMonitor()
    return _monitor
