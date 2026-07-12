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
from typing import Any

from whitemagic.config.paths import ECONOMY_DIR
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

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


@dataclass
class TransactionVerdict:
    """Result of firewall validation."""

    approved: bool
    reason: str
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
        self._lock = threading.Lock()
        self._spend_log_path = ECONOMY_DIR / "transaction_log.jsonl"
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
        policy = self.get_policy(request.agent_id)

        with self._lock:
            # ── Check 1: Single transaction limit ──
            if request.amount > policy.max_single_transaction:
                return TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Single transaction {request.amount} {request.currency} "
                        f"exceeds limit {policy.max_single_transaction}"
                    ),
                    policy=policy,
                )

            # ── Check 2: Daily cumulative limit ──
            self._rollover_daily(request.agent_id)
            spent = self._daily_spent.get(request.agent_id, 0.0)
            if spent + request.amount > policy.daily_limit:
                return TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Daily limit exceeded: {spent + request.amount:.2f} "
                        f"would exceed {policy.daily_limit}"
                    ),
                    policy=policy,
                    daily_spent=spent,
                )

            # ── Check 3: Rate limit ──
            now = request.timestamp
            log = self._rate_log.setdefault(request.agent_id, [])
            log[:] = [t for t in log if now - t < 60.0]
            if len(log) >= policy.rate_limit_per_minute:
                return TransactionVerdict(
                    approved=False,
                    reason=(
                        f"Rate limit: {len(log)} transactions in last 60s, "
                        f"limit is {policy.rate_limit_per_minute}"
                    ),
                    policy=policy,
                    rate_remaining=0,
                )

            # ── Check 4: Recipient blocklist ──
            if request.recipient in policy.blocked_recipients:
                return TransactionVerdict(
                    approved=False,
                    reason=f"Recipient {request.recipient} is blocked",
                    policy=policy,
                )

            # ── Check 5: Recipient allowlist (if non-empty) ──
            if policy.allowed_recipients and request.recipient not in policy.allowed_recipients:
                return TransactionVerdict(
                    approved=False,
                    reason=f"Recipient {request.recipient} not in allowlist",
                    policy=policy,
                )

            # ── Check 6: Dharma ethical sign-off ──
            if policy.dharma_check_required:
                dharma_ok = self._check_dharma(request)
                if not dharma_ok:
                    return TransactionVerdict(
                        approved=False,
                        reason=(
                            f"Dharma check failed (threshold={policy.dharma_threshold})"
                        ),
                        policy=policy,
                    )

            # ── All checks passed — record spend ──
            self._daily_spent[request.agent_id] = spent + request.amount
            log.append(now)
            self._persist_spend(request)

            return TransactionVerdict(
                approved=True,
                reason="approved",
                policy=policy,
                daily_spent=self._daily_spent[request.agent_id],
                rate_remaining=policy.rate_limit_per_minute - len(log),
            )

    # ── Dharma integration ──

    def _check_dharma(self, request: TransactionRequest) -> bool:
        """Ask DharmaEngine for ethical sign-off."""
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
            return True  # Permissive if dharma unavailable
        except Exception as e:
            logger.debug("Dharma check failed (permissive): %s", e)
            return True

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
