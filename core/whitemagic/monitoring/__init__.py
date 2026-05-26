"""Monitoring and observability infrastructure for WhiteMagic.

Provides:
- Structured logging
- Metrics collection
- Performance tracing
- Health checks
- Alerting hooks
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Generator, Optional


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """Structured logger with JSON-formatted output."""

    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))

        # JSON formatter for structured output
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )

        # Console handler — only add if not already present to avoid duplication
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Log a structured message.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured fields
        """
        log_entry = {"message": message, **kwargs}
        self.logger.log(getattr(logging, level.value), log_entry)

    def debug(self, message: str, **kwargs) -> None:
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self.log(LogLevel.CRITICAL, message, **kwargs)


# Global logger instance
logger = StructuredLogger("whitemagic.monitoring")


# ---------------------------------------------------------------------------
# Metrics Collection
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """A counter metric (monotonically increasing)."""
    name: str
    value: int = 0
    tags: dict[str, str] = field(default_factory=dict)

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        self.value += amount

    def to_metric(self) -> Metric:
        """Convert to Metric."""
        return Metric(name=self.name, value=float(self.value), tags=self.tags)


@dataclass
class Gauge:
    """A gauge metric (can go up or down)."""
    name: str
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set the gauge value."""
        self.value = value

    def increment(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        self.value += amount

    def decrement(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        self.value -= amount

    def to_metric(self) -> Metric:
        """Convert to Metric."""
        return Metric(name=self.name, value=self.value, tags=self.tags)


@dataclass
class Histogram:
    """A histogram metric (distribution of values)."""
    name: str
    values: list[float] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    max_samples: int = 1000

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.values.append(value)
        if len(self.values) > self.max_samples:
            self.values.pop(0)

    def summary(self) -> dict[str, float]:
        """Get summary statistics."""
        if not self.values:
            return {}

        import statistics
        return {
            "count": len(self.values),
            "min": min(self.values),
            "max": max(self.values),
            "mean": statistics.mean(self.values),
            "median": statistics.median(self.values),
            "p95": statistics.quantiles(self.values, n=20)[18] if len(self.values) >= 20 else max(self.values),
        }


class MetricsRegistry:
    """Registry for collecting metrics."""

    def __init__(self):
        self.counters: dict[str, Counter] = {}
        self.gauges: dict[str, Gauge] = {}
        self.histograms: dict[str, Histogram] = {}

    def counter(self, name: str, tags: Optional[dict[str, str]] = None) -> Counter:
        """Get or create a counter."""
        if name not in self.counters:
            self.counters[name] = Counter(name=name, tags=tags or {})
        return self.counters[name]

    def gauge(self, name: str, tags: Optional[dict[str, str]] = None) -> Gauge:
        """Get or create a gauge."""
        if name not in self.gauges:
            self.gauges[name] = Gauge(name=name, tags=tags or {})
        return self.gauges[name]

    def histogram(self, name: str, tags: Optional[dict[str, str]] = None) -> Histogram:
        """Get or create a histogram."""
        if name not in self.histograms:
            self.histograms[name] = Histogram(name=name, tags=tags or {})
        return self.histograms[name]

    def collect(self) -> list[Metric]:
        """Collect all metrics."""
        metrics = []
        for counter in self.counters.values():
            metrics.append(counter.to_metric())
        for gauge in self.gauges.values():
            metrics.append(gauge.to_metric())
        return metrics


# Global metrics registry
metrics = MetricsRegistry()


# ---------------------------------------------------------------------------
# Performance Tracing
# ---------------------------------------------------------------------------

@dataclass
class Span:
    """A performance span (trace segment)."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    tags: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        """Finish the span."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@contextmanager
def trace(name: str, **tags) -> Generator[Span, None, None]:
    """Context manager for tracing a code block.

    Args:
        name: Name of the span
        **tags: Additional tags

    Yields:
        Span object
    """
    span = Span(name=name, start_time=time.perf_counter(), tags=tags)
    try:
        yield span
    finally:
        span.finish()
        logger.info(
            f"Trace: {name}",
            duration_ms=span.duration_ms,
            **tags
        )
        # Record in histogram
        metrics.histogram(f"trace.{name}.duration_ms").observe(span.duration_ms or 0)


def traced(name: Optional[str] = None, **tags) -> Callable:
    """Decorator to trace a function.

    Args:
        name: Name of the span (defaults to function name)
        **tags: Additional tags

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            with trace(span_name, **tags):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthChecker:
    """Health check registry."""

    def __init__(self):
        self.checks: dict[str, Callable[[], HealthCheckResult]] = {}

    def register(self, name: str) -> Callable:
        """Decorator to register a health check.

        Args:
            name: Name of the health check

        Returns:
            Decorator function
        """
        def decorator(func: Callable[[], HealthCheckResult]) -> Callable:
            self.checks[name] = func
            return func
        return decorator

    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check.

        Args:
            name: Name of the check

        Returns:
            HealthCheckResult
        """
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check not found: {name}"
            )

        start = time.perf_counter()
        result = self.checks[name]()
        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    def run_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks.

        Returns:
            Dictionary mapping check names to results
        """
        return {name: self.run_check(name) for name in self.checks}


# Global health checker
health_checker = HealthChecker()


# Default health checks
@health_checker.register("database")
def check_database() -> HealthCheckResult:
    """Check database connectivity."""
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        mem = get_unified_memory()
        # Simple query to test connectivity
        _ = len(mem)  # This triggers a DB query
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database accessible"
        )
    except Exception as e:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )


@health_checker.register("rust_bridge")
def check_rust_bridge() -> HealthCheckResult:
    """Check Rust bridge availability."""
    try:
        import whitemagic_rs
        return HealthCheckResult(
            name="rust_bridge",
            status=HealthStatus.HEALTHY,
            message="Rust bridge loaded"
        )
    except ImportError:
        return HealthCheckResult(
            name="rust_bridge",
            status=HealthStatus.DEGRADED,
            message="Rust bridge not available (optional)"
        )


@health_checker.register("memory_size")
def check_memory_size() -> HealthCheckResult:
    """Check memory database size."""
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        mem = get_unified_memory()
        size = len(mem)
        return HealthCheckResult(
            name="memory_size",
            status=HealthStatus.HEALTHY,
            message=f"{size} memories in database"
        )
    except Exception as e:
        return HealthCheckResult(
            name="memory_size",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )


# ---------------------------------------------------------------------------
# Alerting Hooks
# ---------------------------------------------------------------------------

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert event."""
    severity: AlertSeverity
    title: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: dict[str, str] = field(default_factory=dict)


class AlertManager:
    """Manager for alerting."""

    def __init__(self):
        self.handlers: list[Callable[[Alert], None]] = []
        self.alerts: list[Alert] = []

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler.

        Args:
            handler: Function to handle alerts
        """
        self.handlers.append(handler)

    def alert(self, severity: AlertSeverity, title: str, message: str, **tags) -> None:
        """Emit an alert.

        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            **tags: Additional tags
        """
        alert = Alert(severity=severity, title=title, message=message, tags=tags)
        self.alerts.append(alert)

        # Log the alert
        log_level = {
            AlertSeverity.INFO: LogLevel.INFO,
            AlertSeverity.WARNING: LogLevel.WARNING,
            AlertSeverity.ERROR: LogLevel.ERROR,
            AlertSeverity.CRITICAL: LogLevel.CRITICAL,
        }[severity]

        logger.log(log_level, f"[{title}] {message}", **tags)

        # Call handlers
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")


# Global alert manager
alert_manager = AlertManager()


# Default alert handler: log to file
def log_alert_to_file(alert: Alert) -> None:
    """Log alert to a file."""
    try:
        from whitemagic.config.paths import get_state_root
        state_root = get_state_root()
        log_dir = state_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "alerts.log"

        with open(log_file, "a") as f:
            f.write(
                f"[{alert.timestamp}] [{alert.severity.value}] "
                f"{alert.title}: {alert.message}\n"
            )
    except Exception as e:
        # Fallback to stdout if file logging fails
        print(f"Failed to log alert to file: {e}")
        print(f"Alert: [{alert.severity.value}] {alert.title}: {alert.message}")


alert_manager.add_handler(log_alert_to_file)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def get_system_status() -> dict[str, Any]:
    """Get overall system status.

    Returns:
        Dictionary with system status information
    """
    health_results = health_checker.run_all()
    overall_status = HealthStatus.HEALTHY

    for result in health_results.values():
        if result.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
            break
        elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.DEGRADED

    return {
        "status": overall_status.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health_checks": {
            name: {
                "status": result.status.value,
                "message": result.message,
                "duration_ms": result.duration_ms,
            }
            for name, result in health_results.items()
        },
        "metrics_count": len(metrics.collect()),
        "recent_alerts": len([a for a in alert_manager.alerts if a.timestamp >= (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()]),
    }


if __name__ == "__main__":
    # Test the monitoring system
    print("Testing WhiteMagic Monitoring System")

    # Test logging
    logger.info("System started", component="monitoring")

    # Test metrics
    counter = metrics.counter("test_counter")
    counter.increment()
    counter.increment(5)
    print(f"Counter: {counter.value}")

    gauge = metrics.gauge("test_gauge")
    gauge.set(42.0)
    print(f"Gauge: {gauge.value}")

    # Test tracing
    with trace("test_operation", operation="test"):
        time.sleep(0.1)

    # Test health checks
    print("\nHealth Checks:")
    for name, result in health_checker.run_all().items():
        print(f"  {name}: {result.status.value} - {result.message}")

    # Test system status
    print("\nSystem Status:")
    import json
    print(json.dumps(get_system_status(), indent=2))
