# ruff: noqa: BLE001
"""Transaction Firewall — Economic Safety Layer.
================================================================
Intercepts, validates, and rate-limits all outbound economic
actions before they reach the blockchain or external payment
processor.

Checks:
  - Per-transaction amount limit
  - Daily cumulative spend limit
  - Rate limit (transactions per minute)
  - Recipient allowlist / blocklist
  - Dharma ethical sign-off (optional)

Usage::

    from whitemagic.security.transaction_firewall import get_transaction_firewall

    fw = get_transaction_firewall()
    verdict = fw.validate(TransactionRequest(
        agent_id="agent_1",
        amount=5.0,
        currency="XRP",
        recipient="raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy",
        purpose="bounty reward",
        tool_name="bounty.create",
    ))
    if not verdict.approved:
        raise ValueError(verdict.reason)
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from whitemagic.config.paths import ECONOMY_DIR
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


def _is_fail_closed() -> bool:
    """Check if firewall should fail-closed on dependency failures."""
    return os.environ.get("WM_FIREWALL_FAIL_CLOSED", "0") in ("1", "true", "yes")


def _is_maintenance_mode() -> bool:
    """Check if maintenance mode bypass is active."""
    return os.environ.get("WM_FIREWALL_MAINTENANCE", "0") in ("1", "true", "yes")

# ── Economic tools that must pass through the firewall ──────────────

ECONOMIC_TOOLS: set[str] = {
    "bounty.create",
    "bounty.link_escrow",
    "bounty.complete",
    "wallet.transfer",
    "wallet.send",
    "wallet.balance",
    "tip.send",
    "gratitude.tip",
    "mesh.payment",
    "payment.channel",
    "engagement.issue",
    "engagement.revoke",
}

# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class TransactionPolicy:
    """Per-agent spending policy."""

    max_single_transaction: float = 100.0
    daily_limit: float = 1000.0
    allowed_recipients: set[str] = field(default_factory=set)
    blocked_recipients: set[str] = field(default_factory=set)
    rate_limit_per_minute: int = 10
    dharma_check_required: bool = True
    dharma_threshold: float = 0.5


@dataclass
class TransactionRequest:
    """Normalized internal representation of an economic action."""

    agent_id: str
    amount: float
    currency: str
    recipient: str
    purpose: str
    tool_name: str
    timestamp: float = field(default_factory=time.time)


class VerdictReason(StrEnum):
    """Typed reason for a firewall verdict."""

    APPROVED = "approved"
    POLICY_DENIED = "policy_denied"
    POLICY_UNAVAILABLE = "policy_unavailable"
    POLICY_MALFORMED = "policy_malformed"
    POLICY_STORAGE_ERROR = "policy_storage_error"
    MAINTENANCE_BYPASS = "maintenance_bypass"


@dataclass
class SecurityEvent:
    """Append-only security event for audit trail."""

    timestamp: float
    tool_name: str
    agent_id: str
    verdict_reason: str
    approved: bool
    amount: float = 0.0
    recipient: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "verdict_reason": self.verdict_reason,
            "approved": self.approved,
            "amount": self.amount,
            "recipient": self.recipient,
            "detail": self.detail,
        }


@dataclass
class TransactionVerdict:
    """Result of firewall validation."""

    approved: bool
    reason: str
    verdict_reason: VerdictReason = VerdictReason.POLICY_DENIED
    policy: TransactionPolicy | None = None
    daily_spent: float = 0.0
    rate_remaining: int = 0


# ── Firewall ─────────────────────────────────────────────────────────


class TransactionFirewall:
    """Validates economic actions before execution."""

    def __init__(self) -> None:
        self._policies: dict[str, TransactionPolicy] = {}
        self._default_policy = TransactionPolicy()
        self._daily_spent: dict[str, float] = {}  # agent_id -> amount today
        self._daily_date: dict[str, str] = {}  # agent_id -> date string
        self._rate_log: dict[str, list[float]] = {}  # agent_id -> timestamps
        self._lock = threading.RLock()
        self._spend_log_path = ECONOMY_DIR / "transaction_log.jsonl"
        self._security_log_path = ECONOMY_DIR / "security_events.jsonl"
        self._spend_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_daily_spent()

    # ── Policy management ──

    def set_policy(self, agent_id: str, policy: TransactionPolicy) -> None:
        with self._lock:
            self._policies[agent_id] = policy

    def get_policy(self, agent_id: str) -> TransactionPolicy:
        return self._policies.get(agent_id, self._default_policy)

    # ── Validation ──

    def validate(self, request: TransactionRequest) -> TransactionVerdict:
        """Run all checks and return a verdict."""
        # ── Maintenance mode bypass ──
        if _is_maintenance_mode():
            verdict = TransactionVerdict(
                approved=True,
                reason="Maintenance mode bypass active",
                verdict_reason=VerdictReason.MAINTENANCE_BYPASS,
            )
            self._emit_security_event(request, verdict)
            return verdict

        # ── Check 0: Malformed input validation ──
        malformed = self._validate_request(request)
        if malformed is not None:
            return malformed

        policy = self.get_policy(request.agent_id)

        with self._lock:
            # ── Check 1: Single transaction limit ──
            if request.amount > policy.max_single_transaction:
                v = TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Single transaction {request.amount} {request.currency} "
                        f"exceeds limit {policy.max_single_transaction}"
                    ),
                    verdict_reason=VerdictReason.POLICY_DENIED,
                    policy=policy,
                )
                self._emit_security_event(request, v)
                return v

            # ── Check 2: Daily cumulative limit ──
            self._rollover_daily(request.agent_id)
            spent = self._daily_spent.get(request.agent_id, 0.0)
            if spent + request.amount > policy.daily_limit:
                v = TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Daily limit exceeded: {spent + request.amount:.2f} "
                        f"would exceed {policy.daily_limit}"
                    ),
                    verdict_reason=VerdictReason.POLICY_DENIED,
                    policy=policy,
                    daily_spent=spent,
                )
                self._emit_security_event(request, v)
                return v

            # ── Check 3: Rate limit ──
            now = request.timestamp
            log = self._rate_log.setdefault(request.agent_id, [])
            log[:] = [t for t in log if now - t < 60.0]
            if len(log) >= policy.rate_limit_per_minute:
                v = TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Rate limit: {len(log)} transactions in last 60s, "
                        f"limit is {policy.rate_limit_per_minute}"
                    ),
                    verdict_reason=VerdictReason.POLICY_DENIED,
                    policy=policy,
                    rate_remaining=0,
                )
                self._emit_security_event(request, v)
                return v

            # ── Check 4: Recipient blocklist ──
            if request.recipient in policy.blocked_recipients:
                v = TransactionVerdict(
                    approved=False,
                    reason=f"Recipient {request.recipient} is blocked",
                    verdict_reason=VerdictReason.POLICY_DENIED,
                    policy=policy,
                )
                self._emit_security_event(request, v)
                return v

            # ── Check 5: Recipient allowlist (if non-empty) ──
            if policy.allowed_recipients and request.recipient not in policy.allowed_recipients:
                v = TransactionVerdict(
                    approved=False,
                    reason=f"Recipient {request.recipient} not in allowlist",
                    verdict_reason=VerdictReason.POLICY_DENIED,
                    policy=policy,
                )
                self._emit_security_event(request, v)
                return v

            # ── Check 6: Dharma ethical sign-off ──
            if policy.dharma_check_required:
                try:
                    dharma_result = self._check_dharma(request)
                except Exception as e:
                    logger.debug("Dharma check raised: %s", e)
                    dharma_result = None
                if dharma_result is False:
                    v = TransactionVerdict(
                        approved=False,
                        reason=(
                            f"Dharma check failed (threshold={policy.dharma_threshold})"
                        ),
                        verdict_reason=VerdictReason.POLICY_DENIED,
                        policy=policy,
                    )
                    self._emit_security_event(request, v)
                    # Publish Dharma-specific blocked event
                    try:
                        from whitemagic.security.event_bus import SecurityEventType, get_security_event_bus

                        bus = get_security_event_bus()
                        bus.emit(
                            event_type=SecurityEventType.DHARMA_BLOCKED,
                            source="transaction_firewall",
                            severity="high",
                            tool_name=request.tool_name,
                            agent_id=request.agent_id,
                            detail=f"Dharma denied: {v.reason}",
                            metadata={
                                "amount": request.amount,
                                "recipient": request.recipient,
                                "threshold": policy.dharma_threshold,
                            },
                        )
                    except Exception:
                        logger.debug("Ignored Exception in transaction_firewall.py:307")
                    return v
                if dharma_result is None:
                    # Dharma unavailable — fail-closed or permissive
                    if _is_fail_closed():
                        v = TransactionVerdict(
                            approved=False,
                            reason="Dharma engine unavailable (fail-closed)",
                            verdict_reason=VerdictReason.POLICY_UNAVAILABLE,
                            policy=policy,
                        )
                        self._emit_security_event(request, v)
                        return v
                    # Permissive mode: log but allow
                    logger.warning("Dharma unavailable (permissive mode) — allowing transaction")

            # ── All checks passed — record spend ──
            self._daily_spent[request.agent_id] = spent + request.amount
            log.append(now)
            self._persist_spend(request)

            v = TransactionVerdict(
                approved=True,
                reason="approved",
                verdict_reason=VerdictReason.APPROVED,
                policy=policy,
                daily_spent=self._daily_spent[request.agent_id],
                rate_remaining=policy.rate_limit_per_minute - len(log),
            )
            self._emit_security_event(request, v)
            return v

    # ── Dharma integration ──

    def _check_dharma(self, request: TransactionRequest) -> bool | None:
        """Ask DharmaRulesEngine for ethical sign-off on a transaction.

        Uses the actual DharmaRulesEngine.evaluate() which returns a
        DharmaDecision with action (allow/deny/block), score, and
        triggered_rules.  Falls back to the legacy consciousness Dharma
        if the rules engine is unavailable.

        Returns:
            True  — dharma approved (action=allow, score >= threshold)
            False — dharma denied (action=deny/block, or score < threshold)
            None  — dharma engine unavailable
        """
        # ── Primary: DharmaRulesEngine ──
        try:
            from whitemagic.dharma.rules import get_rules_engine

            engine = get_rules_engine()
            action_dict = {
                "tool": request.tool_name,
                "description": request.purpose or f"Transaction of {request.amount} {request.currency} to {request.recipient}",
                "safety": "economic",
                "amount": request.amount,
                "currency": request.currency,
                "recipient": request.recipient,
                "agent_id": request.agent_id,
            }
            decision = engine.evaluate(action_dict)
            threshold = self.get_policy(request.agent_id).dharma_threshold

            # DharmaDecision.action is a DharmaAction enum (allow/deny/block/log)
            action_val = decision.action.value if hasattr(decision.action, "value") else str(decision.action)

            if action_val in ("deny", "block"):
                logger.info(
                    "Dharma denied transaction: %s (score=%.2f, rules=%s)",
                    decision.explain,
                    decision.score,
                    decision.triggered_rules,
                )
                return False
            if action_val in ("allow", "log"):
                return decision.score >= threshold
            # Unknown action — use score
            return decision.score >= threshold
        except ImportError:
            logger.debug("Ignored ImportError in transaction_firewall.py:387")
        except Exception as e:
            logger.debug("DharmaRulesEngine check failed: %s", e)

        # ── Fallback: legacy consciousness Dharma ──
        try:
            from whitemagic.core.consciousness.dharma import get_dharma

            dharma = get_dharma()
            score = dharma.evaluate_action(
                action_type=request.tool_name,
                context={
                    "amount": request.amount,
                    "currency": request.currency,
                    "recipient": request.recipient,
                    "purpose": request.purpose,
                    "agent_id": request.agent_id,
                },
            )
            if isinstance(score, (int, float)):
                return score >= self.get_policy(request.agent_id).dharma_threshold
            if isinstance(score, dict):
                return float(score.get("score", 0.5)) >= self.get_policy(
                    request.agent_id
                ).dharma_threshold
            return None  # Unrecognized response type
        except Exception as e:
            logger.debug("Legacy Dharma check failed: %s", e)
            return None  # Unavailable

    # ── Malformed input validation ──

    def _validate_request(self, request: TransactionRequest) -> TransactionVerdict | None:
        """Validate request structure. Returns a verdict if malformed, None if valid."""
        if not isinstance(request.agent_id, str) or not request.agent_id.strip():
            v = TransactionVerdict(
                approved=False,
                reason="Malformed request: agent_id is empty or not a string",
                verdict_reason=VerdictReason.POLICY_MALFORMED,
            )
            self._emit_security_event(request, v)
            return v
        if not isinstance(request.amount, (int, float)) or request.amount < 0:
            v = TransactionVerdict(
                approved=False,
                reason=f"Malformed request: invalid amount {request.amount}",
                verdict_reason=VerdictReason.POLICY_MALFORMED,
            )
            self._emit_security_event(request, v)
            return v
        if not isinstance(request.tool_name, str) or not request.tool_name.strip():
            v = TransactionVerdict(
                approved=False,
                reason="Malformed request: tool_name is empty",
                verdict_reason=VerdictReason.POLICY_MALFORMED,
            )
            self._emit_security_event(request, v)
            return v
        return None

    # ── Security event stream ──

    def _emit_security_event(self, request: TransactionRequest, verdict: TransactionVerdict) -> None:
        """Append a security event to the audit log and publish to SecurityEventBus."""
        event = SecurityEvent(
            timestamp=request.timestamp,
            tool_name=request.tool_name,
            agent_id=request.agent_id,
            verdict_reason=verdict.verdict_reason.value,
            approved=verdict.approved,
            amount=request.amount,
            recipient=request.recipient,
            detail=verdict.reason if not verdict.approved else "",
        )
        try:
            with open(self._security_log_path, "a", encoding="utf-8") as f:
                f.write(_json_dumps(event.to_dict()) + "\n")
        except (OSError, ValueError) as e:
            logger.warning("Failed to persist security event: %s", e)
        # Publish to unified SecurityEventBus
        try:
            from whitemagic.security.event_bus import SecurityEventType, get_security_event_bus

            bus = get_security_event_bus()
            bus.emit(
                event_type=(
                    SecurityEventType.TRANSACTION_APPROVED
                    if verdict.approved
                    else SecurityEventType.TRANSACTION_BLOCKED
                ),
                source="transaction_firewall",
                severity="info" if verdict.approved else "high",
                tool_name=request.tool_name,
                agent_id=request.agent_id,
                detail=verdict.reason,
                metadata={
                    "amount": request.amount,
                    "currency": request.currency,
                    "recipient": request.recipient,
                    "verdict_reason": verdict.verdict_reason.value,
                },
            )
        except Exception as e:
            logger.debug("Failed to publish to SecurityEventBus: %s", e)

    # ── Daily spend tracking ──

    def _rollover_daily(self, agent_id: str) -> None:
        """Reset daily spend if it's a new day."""
        today = time.strftime("%Y-%m-%d")
        last_day = self._daily_date.get(agent_id)
        if last_day != today:
            self._daily_spent[agent_id] = 0.0
            self._daily_date[agent_id] = today

    def _persist_spend(self, request: TransactionRequest) -> None:
        """Append transaction to audit log."""
        entry = {
            "agent_id": request.agent_id,
            "amount": request.amount,
            "currency": request.currency,
            "recipient": request.recipient,
            "purpose": request.purpose,
            "tool_name": request.tool_name,
            "timestamp": request.timestamp,
        }
        try:
            with open(self._spend_log_path, "a", encoding="utf-8") as f:
                f.write(_json_dumps(entry) + "\n")
        except (OSError, ValueError) as e:
            logger.warning("Failed to persist transaction log: %s", e)

    def _load_daily_spent(self) -> None:
        """Load today's spend from the audit log."""
        if not self._spend_log_path.exists():
            return
        today = time.strftime("%Y-%m-%d")
        try:
            with open(self._spend_log_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = _json_loads(line)
                    except Exception:
                        continue
                    ts = entry.get("timestamp", 0)
                    entry_date = time.strftime("%Y-%m-%d", time.localtime(ts))
                    if entry_date == today:
                        agent = entry.get("agent_id", "default")
                        amount = float(entry.get("amount", 0))
                        self._daily_spent[agent] = (
                            self._daily_spent.get(agent, 0.0) + amount
                        )
                        self._daily_date[agent] = today
        except (OSError, ValueError) as e:
            logger.warning("Failed to load daily spent: %s", e)

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Return firewall status for MCP tool."""
        today = time.strftime("%Y-%m-%d")
        return {
            "enabled": os.environ.get("WM_TRANSACTION_FIREWALL", "1")
            not in ("0", "false", "no"),
            "fail_closed": _is_fail_closed(),
            "maintenance_mode": _is_maintenance_mode(),
            "default_policy": {
                "max_single_transaction": self._default_policy.max_single_transaction,
                "daily_limit": self._default_policy.daily_limit,
                "rate_limit_per_minute": self._default_policy.rate_limit_per_minute,
                "dharma_check_required": self._default_policy.dharma_check_required,
            },
            "custom_policies": len(self._policies),
            "daily_spent": dict(self._daily_spent),
            "daily_date": today,
            "economic_tools": sorted(ECONOMIC_TOOLS),
        }


# ── Singleton ────────────────────────────────────────────────────────

_firewall: TransactionFirewall | None = None


def get_transaction_firewall() -> TransactionFirewall:
    """Get the global TransactionFirewall singleton."""
    global _firewall
    if _firewall is None:
        _firewall = TransactionFirewall()
    return _firewall
