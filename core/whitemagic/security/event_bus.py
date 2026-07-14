"""Unified Security Event Bus — single pub/sub channel for all security modules.

All security modules (SecurityMonitor, ToolGate, HermitCrab, TransactionFirewall,
WasmVerifier, EngagementTokenManager, McpIntegrity) publish events here.
Subscribers (ImmuneSystem, ZodiacLedger, AuditSigner) receive events in real-time.

Backed by Redis if available (for multi-process), otherwise in-memory.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)

# Redis channel prefix for security events
_REDIS_CHANNEL = "whitemagic:security:events"


@dataclass
class SecurityEvent:
    """A security event published to the bus."""

    event_type: str
    source: str  # Module that emitted the event (e.g. "transaction_firewall")
    severity: str = "info"  # info | low | medium | high | critical
    tool_name: str = ""
    agent_id: str = ""
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    epoch: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "severity": self.severity,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "detail": self.detail,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "epoch": self.epoch,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecurityEvent:
        return cls(
            event_type=data.get("event_type", ""),
            source=data.get("source", ""),
            severity=data.get("severity", "info"),
            tool_name=data.get("tool_name", ""),
            agent_id=data.get("agent_id", ""),
            detail=data.get("detail", ""),
            metadata=data.get("metadata", {}),
            event_id=data.get("event_id", str(uuid4())),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            epoch=data.get("epoch", time.time()),
        )


# ── Well-known event types ───────────────────────────────────────────────

class SecurityEventType:
    """Canonical security event type names."""

    TOOL_BLOCKED = "security.tool_blocked"
    PATH_VIOLATION = "security.path_violation"
    URL_BLOCKED = "security.url_blocked"
    PROMPT_INJECTION_DETECTED = "security.prompt_injection_detected"
    RAPID_FIRE_DETECTED = "security.rapid_fire_detected"
    LATERAL_MOVEMENT = "security.lateral_movement"
    ESCALATION_ATTEMPT = "security.escalation_attempt"
    TRANSACTION_BLOCKED = "security.transaction_blocked"
    TRANSACTION_APPROVED = "security.transaction_approved"
    WASM_VERIFICATION_FAILED = "security.wasm_verification_failed"
    HERMIT_CRAB_STATE_CHANGE = "security.hermit_crab_state_change"
    ENGAGEMENT_TOKEN_ISSUED = "security.engagement_token_issued"
    ENGAGEMENT_TOKEN_REVOKED = "security.engagement_token_revoked"
    ENGAGEMENT_TOKEN_VALIDATED = "security.engagement_token_validated"
    ENGAGEMENT_TOKEN_REJECTED = "security.engagement_token_rejected"
    MCP_DRIFT_DETECTED = "security.mcp_drift_detected"
    MODEL_VERIFICATION_FAILED = "security.model_verification_failed"
    SHELTER_CREATED = "security.shelter_created"
    SHELTER_DESTROYED = "security.shelter_destroyed"
    DHARMA_BLOCKED = "security.dharma_blocked"


# ── SecurityEventBus ─────────────────────────────────────────────────────


class SecurityEventBus:
    """Unified pub/sub event bus for all security modules.

    In-memory by default. If Redis is available, events are also published
    to a Redis channel for cross-process distribution.
    """

    def __init__(self, max_history: int = 10000) -> None:
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Callable[[SecurityEvent], None]]] = defaultdict(list)
        self._wildcard_subscribers: list[Callable[[SecurityEvent], None]] = []
        self._history: deque[SecurityEvent] = deque(maxlen=max_history)
        self._redis_pub = None
        self._redis_sub = None
        self._redis_thread = None
        self._redis_enabled = False
        self._stats: dict[str, int] = defaultdict(int)

    def subscribe(
        self,
        event_type: str | None,
        callback: Callable[[SecurityEvent], None],
    ) -> None:
        """Subscribe to events. If event_type is None, receives all events."""
        with self._lock:
            if event_type is None:
                self._wildcard_subscribers.append(callback)
            else:
                self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        event_type: str | None,
        callback: Callable[[SecurityEvent], None],
    ) -> None:
        """Remove a subscriber."""
        with self._lock:
            if event_type is None:
                try:
                    self._wildcard_subscribers.remove(callback)
                except ValueError:
                    logger.debug("Ignored ValueError in event_bus.py:144")
            else:
                try:
                    self._subscribers[event_type].remove(callback)
                except (ValueError, KeyError):
                    logger.debug("Ignored ValueError, KeyError in event_bus.py:149")

    def publish(self, event: SecurityEvent) -> None:
        """Publish an event to all matching subscribers."""
        with self._lock:
            self._history.append(event)
            self._stats[event.event_type] += 1
            subs = list(self._subscribers.get(event.event_type, []))
            wildcards = list(self._wildcard_subscribers)

        # Notify subscribers outside the lock to prevent deadlocks
        for cb in subs + wildcards:
            try:
                cb(event)
            except Exception as e:
                logger.debug("Security event subscriber error: %s", e)

        # Publish to Redis if available
        if self._redis_enabled and self._redis_pub is not None:
            try:
                self._redis_pub.publish(_REDIS_CHANNEL, _json_dumps(event.to_dict()))
            except Exception as e:
                logger.debug("Redis publish failed: %s", e)

    def emit(
        self,
        event_type: str,
        source: str,
        severity: str = "info",
        tool_name: str = "",
        agent_id: str = "",
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Convenience: create and publish an event in one call."""
        event = SecurityEvent(
            event_type=event_type,
            source=source,
            severity=severity,
            tool_name=tool_name,
            agent_id=agent_id,
            detail=detail,
            metadata=metadata or {},
        )
        self.publish(event)
        return event

    def history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        """Get recent events, optionally filtered."""
        with self._lock:
            events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        return events[-limit:]

    def stats(self) -> dict[str, Any]:
        """Get event statistics."""
        with self._lock:
            return {
                "total_events": len(self._history),
                "by_type": dict(self._stats),
                "subscriber_count": sum(len(v) for v in self._subscribers.values()) + len(self._wildcard_subscribers),
                "redis_enabled": self._redis_enabled,
            }

    def clear(self) -> None:
        """Clear history and stats (for testing)."""
        with self._lock:
            self._history.clear()
            self._stats.clear()

    def connect_redis(self, url: str | None = None) -> bool:
        """Attempt to connect to Redis for cross-process event distribution."""
        if url is None:
            url = (
                os.environ.get("WHITEMAGIC_REDIS_URL")
                or os.environ.get("REDIS_URL")
                or os.environ.get("REDISCLOUD_URL")
            )
        if not url:
            return False
        try:
            import redis

            self._redis_pub = redis.Redis.from_url(url, decode_responses=True)
            self._redis_pub.ping()
            self._redis_enabled = True

            # Start subscriber listener
            self._redis_sub = redis.Redis.from_url(url, decode_responses=True)
            self._redis_thread = threading.Thread(
                target=self._redis_listen, daemon=True, name="sec-event-bus-redis"
            )
            self._redis_thread.start()
            logger.info("SecurityEventBus: Redis connected at %s", url[:30])
            return True
        except ImportError:
            logger.debug("Redis not available — using in-memory event bus")
            return False
        except Exception as e:
            logger.debug("Redis connection failed: %s", e)
            return False

    def _redis_listen(self) -> None:
        """Listen for events from Redis and re-publish locally."""
        if self._redis_sub is None:
            return
        try:
            pubsub = self._redis_sub.pubsub()
            pubsub.subscribe(_REDIS_CHANNEL)
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        from whitemagic.utils.fast_json import loads as _json_loads

                        data = _json_loads(message["data"])
                        event = SecurityEvent.from_dict(data)
                        # Re-publish locally (without re-sending to Redis)
                        with self._lock:
                            self._history.append(event)
                            self._stats[event.event_type] += 1
                            subs = list(self._subscribers.get(event.event_type, []))
                            wildcards = list(self._wildcard_subscribers)
                        for cb in subs + wildcards:
                            try:
                                cb(event)
                            except Exception:
                                logger.debug("Ignored error in event_bus.py:283")
                    except Exception:
                        logger.debug("Ignored error in event_bus.py:285")
        except Exception as e:
            logger.debug("Redis listener stopped: %s", e)


# ── Singleton ────────────────────────────────────────────────────────────

_bus: SecurityEventBus | None = None
_bus_lock = threading.RLock()


def get_security_event_bus() -> SecurityEventBus:
    """Get the global SecurityEventBus singleton."""
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = SecurityEventBus()
    return _bus


def reset_security_event_bus() -> None:
    """Reset the global bus (for testing)."""
    global _bus
    with _bus_lock:
        _bus = None
