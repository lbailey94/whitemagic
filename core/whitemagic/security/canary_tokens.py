"""CanaryToken Layer — active deception defense for AI agent security.

Deploys canary tokens (honeytokens) that trigger alerts when accessed or used,
providing early warning of unauthorized access or insider threats.

Token types:
  - API key canaries: fake API keys that alert when used
  - Database record canaries: fake DB entries that alert when queried
  - File canaries: fake files that alert when opened
  - Endpoint canaries: fake MCP endpoints that alert when called
  - Credential canaries: fake credentials in config files that alert when used

Integrates with SecurityEventBus for real-time alerting.
"""
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CanaryType(Enum):
    API_KEY = "api_key"
    DB_RECORD = "db_record"
    FILE = "file"
    ENDPOINT = "endpoint"
    CREDENTIAL = "credential"


class CanaryStatus(Enum):
    DEPLOYED = "deployed"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class CanaryToken:
    """A canary token deployed for deception detection."""
    token_id: str
    canary_type: CanaryType
    token_value: str
    description: str
    location: str  # where the token was placed
    deployed_at: float
    expires_at: float
    status: CanaryStatus = CanaryStatus.DEPLOYED
    triggered_at: float | None = None
    triggered_by: str | None = None
    trigger_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "canary_type": self.canary_type.value,
            "token_value": self.token_value[:8] + "..." if len(self.token_value) > 8 else self.token_value,
            "description": self.description,
            "location": self.location,
            "deployed_at": self.deployed_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "triggered_at": self.triggered_at,
            "triggered_by": self.triggered_by,
        }


class CanaryTokenManager:
    """Manages canary tokens for active deception defense.

    Deploys fake credentials, API keys, and endpoints that trigger alerts
    when accessed. Integrates with SecurityEventBus for real-time alerting.
    """

    def __init__(self) -> None:
        self._tokens: dict[str, CanaryToken] = {}
        self._value_index: dict[str, str] = {}  # token_value -> token_id
        self._trigger_log: list[dict[str, Any]] = []

    def deploy(
        self,
        canary_type: CanaryType,
        description: str,
        location: str,
        ttl_seconds: float = 86400.0,
        token_value: str | None = None,
    ) -> CanaryToken:
        """Deploy a new canary token.

        Args:
            canary_type: Type of canary (API key, DB record, etc.)
            description: Human-readable description of the canary.
            location: Where the canary is placed (e.g., "config.yaml", "users table").
            ttl_seconds: Time-to-live in seconds (default 24h).
            token_value: Optional explicit value. Auto-generated if None.
        """
        token_id = f"canary_{secrets.token_hex(8)}"
        if token_value is None:
            token_value = self._generate_token_value(canary_type)

        now = time.time()
        canary = CanaryToken(
            token_id=token_id,
            canary_type=canary_type,
            token_value=token_value,
            description=description,
            location=location,
            deployed_at=now,
            expires_at=now + ttl_seconds,
        )

        self._tokens[token_id] = canary
        self._value_index[token_value] = token_id
        logger.info("Canary token deployed: %s (%s) at %s", token_id, canary_type.value, location)
        return canary

    def check_trigger(self, token_value: str, triggered_by: str = "unknown", context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Check if a given value matches a canary token. If so, trigger it.

        Args:
            token_value: The value to check against deployed canaries.
            triggered_by: Identifier of who accessed the token.
            context: Additional context about the access.
        """
        context = context or {}
        token_id = self._value_index.get(token_value)
        if not token_id:
            return {"triggered": False, "reason": "no_match"}

        canary = self._tokens.get(token_id)
        if not canary:
            return {"triggered": False, "reason": "token_not_found"}

        if canary.status == CanaryStatus.REVOKED:
            return {"triggered": False, "reason": "revoked"}

        if canary.status == CanaryStatus.TRIGGERED:
            return {"triggered": False, "reason": "already_triggered"}

        if time.time() > canary.expires_at:
            canary.status = CanaryStatus.EXPIRED
            return {"triggered": False, "reason": "expired"}

        canary.status = CanaryStatus.TRIGGERED
        canary.triggered_at = time.time()
        canary.triggered_by = triggered_by
        canary.trigger_context = context

        trigger_record = {
            "token_id": token_id,
            "canary_type": canary.canary_type.value,
            "triggered_by": triggered_by,
            "triggered_at": canary.triggered_at,
            "location": canary.location,
            "context": context,
        }
        self._trigger_log.append(trigger_record)

        self._emit_security_event(canary, triggered_by, context)

        logger.warning(
            "CANARY TRIGGERED: %s (%s) at %s by %s",
            token_id, canary.canary_type.value, canary.location, triggered_by,
        )

        return {
            "triggered": True,
            "token_id": token_id,
            "canary_type": canary.canary_type.value,
            "location": canary.location,
            "triggered_by": triggered_by,
        }

    def revoke(self, token_id: str) -> dict[str, Any]:
        """Revoke a canary token."""
        canary = self._tokens.get(token_id)
        if not canary:
            return {"status": "error", "error": "Token not found"}

        canary.status = CanaryStatus.REVOKED

        return {"status": "success", "token_id": token_id, "revoked": True}

    def list_tokens(self, status_filter: CanaryStatus | None = None) -> list[dict[str, Any]]:
        """List all canary tokens, optionally filtered by status."""
        tokens = list(self._tokens.values())
        if status_filter:
            tokens = [t for t in tokens if t.status == status_filter]
        return [t.to_dict() for t in tokens]

    def get_trigger_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get the log of triggered canaries."""
        return self._trigger_log[-limit:]

    def status(self) -> dict[str, Any]:
        """Get canary token layer status."""
        active = sum(1 for t in self._tokens.values() if t.status == CanaryStatus.DEPLOYED)
        triggered = sum(1 for t in self._tokens.values() if t.status == CanaryStatus.TRIGGERED)
        expired = sum(1 for t in self._tokens.values() if t.status == CanaryStatus.EXPIRED)
        revoked = sum(1 for t in self._tokens.values() if t.status == CanaryStatus.REVOKED)

        return {
            "total_tokens": len(self._tokens),
            "active": active,
            "triggered": triggered,
            "expired": expired,
            "revoked": revoked,
            "trigger_log_count": len(self._trigger_log),
        }

    def deploy_api_key_canary(self, location: str, description: str = "", ttl: float = 86400) -> CanaryToken:
        """Convenience: deploy a fake API key canary."""
        return self.deploy(CanaryType.API_KEY, description or "API key canary", location, ttl)

    def deploy_credential_canary(self, location: str, description: str = "", ttl: float = 86400) -> CanaryToken:
        """Convenience: deploy a fake credential canary."""
        return self.deploy(CanaryType.CREDENTIAL, description or "Credential canary", location, ttl)

    def deploy_endpoint_canary(self, location: str, description: str = "", ttl: float = 86400) -> CanaryToken:
        """Convenience: deploy a fake endpoint canary."""
        return self.deploy(CanaryType.ENDPOINT, description or "Endpoint canary", location, ttl)

    def _generate_token_value(self, canary_type: CanaryType) -> str:
        """Generate a realistic-looking token value based on type."""
        raw = secrets.token_hex(24)
        if canary_type == CanaryType.API_KEY:
            return f"sk-{raw[:32]}"
        elif canary_type == CanaryType.CREDENTIAL:
            return f"wm_cred_{raw[:32]}"
        elif canary_type == CanaryType.ENDPOINT:
            return f"/api/internal/{raw[:16]}"
        elif canary_type == CanaryType.DB_RECORD:
            return f"canary_user_{raw[:12]}"
        else:
            return raw

    def _emit_security_event(self, canary: CanaryToken, triggered_by: str, context: dict[str, Any]) -> None:
        """Emit a security event when a canary is triggered."""
        try:
            from whitemagic.security.event_bus import SecurityEvent, get_event_bus

            bus = get_event_bus()
            bus.publish(SecurityEvent(
                event_type="CANARY_TRIGGERED",
                source="canary_token_manager",
                data={
                    "token_id": canary.token_id,
                    "canary_type": canary.canary_type.value,
                    "location": canary.location,
                    "triggered_by": triggered_by,
                    "context": context,
                },
            ))
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to emit canary security event: %s", e)

    def cleanup_expired(self) -> int:
        """Remove expired tokens. Returns count removed."""
        now = time.time()
        expired_ids = [
            tid for tid, t in self._tokens.items()
            if now > t.expires_at and t.status != CanaryStatus.TRIGGERED
        ]
        for tid in expired_ids:
            t = self._tokens[tid]
            if t.token_value in self._value_index:
                del self._value_index[t.token_value]
            del self._tokens[tid]
        return len(expired_ids)


_manager: CanaryTokenManager | None = None


def get_canary_manager() -> CanaryTokenManager:
    global _manager
    if _manager is None:
        _manager = CanaryTokenManager()
    return _manager
