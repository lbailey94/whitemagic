# ruff: noqa: BLE001
"""Jaynes Voice Audit — Scan for hallucinated tool invocations.

Named after Julian Jaynes' bicameral mind theory: the "voice" that commands
action. In AI, this is the internal monologue generating tool-call intents.

This module provides:
  - ClaimLog: where internal modules register "I claim I called tool X"
  - VoiceAuditScanner: compares claims against Karma Ledger actuals
  - Quarantine trigger: when a claim has no matching ledger entry

Usage:
    from whitemagic.core.governance.voice_audit import get_voice_audit_scanner
    scanner = get_voice_audit_scanner()
    scanner.register_claim("my_module", "delete_memory", {"memory_id": "123"})
    # ... later ...
    report = scanner.scan()
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClaimEntry:
    """A claim that a module made a tool call."""

    claim_id: str
    module: str
    tool: str
    params: dict[str, Any]
    claimed_at: datetime
    verified: bool = False
    verified_at: datetime | None = None


@dataclass
class AuditReport:
    """Result of a voice audit scan."""

    scanned_claims: int = 0
    verified_claims: int = 0
    hallucinated_claims: list[dict[str, Any]] = field(default_factory=list)
    orphaned_ledger_entries: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    quarantine_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "scanned_claims": self.scanned_claims,
            "verified_claims": self.verified_claims,
            "hallucinated_count": len(self.hallucinated_claims),
            "hallucinated_claims": self.hallucinated_claims,
            "orphaned_ledger_count": len(self.orphaned_ledger_entries),
            "orphaned_ledger_entries": self.orphaned_ledger_entries,
            "timestamp": self.timestamp,
            "quarantine_triggered": self.quarantine_triggered,
        }


class ClaimLog:
    """In-memory log of claimed tool invocations."""

    def __init__(self, max_age_minutes: int = 60) -> None:
        self._claims: list[ClaimEntry] = []
        self._lock = threading.RLock()
        self._max_age = timedelta(minutes=max_age_minutes)

    def register(
        self,
        module: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Register a claim. Returns claim_id."""
        claim_id = f"claim_{uuid.uuid4().hex[:12]}"
        entry = ClaimEntry(
            claim_id=claim_id,
            module=module,
            tool=tool,
            params=params or {},
            claimed_at=datetime.now(UTC),
        )
        with self._lock:
            self._claims.append(entry)
            self._prune_old()
        return claim_id

    def verify(
        self, tool: str, params: dict[str, Any] | None = None
    ) -> ClaimEntry | None:
        """Mark the oldest unverified claim for this tool as verified."""
        with self._lock:
            self._prune_old()
            for claim in self._claims:
                if not claim.verified and claim.tool == tool:
                    if params is None or self._params_match(claim.params, params):
                        claim.verified = True
                        claim.verified_at = datetime.now(UTC)
                        return claim
        return None

    def get_unverified(self) -> list[ClaimEntry]:
        """
        Get the unverified.

        Returns:
            list[ClaimEntry]
        """
        with self._lock:
            self._prune_old()
            return [c for c in self._claims if not c.verified]

    def _prune_old(self) -> None:
        cutoff = datetime.now(UTC) - self._max_age
        self._claims = [c for c in self._claims if c.claimed_at > cutoff]

    @staticmethod
    def _params_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
        """Best-effort param matching (subset)."""
        if not b:
            return True
        for k, v in b.items():
            if k not in a or a[k] != v:
                return False
        return True


class VoiceAuditScanner:
    """Compares ClaimLog against Karma Ledger to find hallucinations."""

    def __init__(self, claim_log: ClaimLog | None = None) -> None:
        self._claim_log = claim_log or ClaimLog()
        self._scan_count = 0
        self._last_report: AuditReport | None = None

    @property
    def claim_log(self) -> ClaimLog:
        """
        Perform the claim log operation.

        Returns:
            ClaimLog
        """
        return self._claim_log

    def register_claim(
        self,
        module: str,
        tool: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Convenience: register a claim in the underlying log."""
        return self._claim_log.register(module, tool, params)

    def verify_claim(
        self, tool: str, params: dict[str, Any] | None = None
    ) -> ClaimEntry | None:
        """Convenience: verify a claim in the underlying log."""
        return self._claim_log.verify(tool, params)

    def scan(self) -> AuditReport:
        """Run one audit pass: compare claims vs ledger entries."""
        report = AuditReport()
        unverified = self._claim_log.get_unverified()
        report.scanned_claims = len(unverified)

        ledger_entries: list[dict[str, Any]] = []
        try:
            from whitemagic.dharma.karma_ledger import get_karma_ledger

            ledger = get_karma_ledger()
            with ledger._lock:
                ledger_entries = [e.to_dict() for e in ledger._entries[-5000:]]
        except Exception as exc:
            logger.warning(
                "VoiceAudit could not read karma ledger: %s", exc, exc_info=True
            )

        # Build a lookup of recent tool calls from ledger
        ledger_tools: set[str] = {e["tool"] for e in ledger_entries}

        for claim in unverified:
            if claim.tool in ledger_tools:
                report.verified_claims += 1
            else:
                report.hallucinated_claims.append(
                    {
                        "claim_id": claim.claim_id,
                        "module": claim.module,
                        "tool": claim.tool,
                        "params": claim.params,
                        "claimed_at": claim.claimed_at.isoformat(),
                    }
                )

        # Orphaned ledger entries: tools in ledger with no claim at all
        # (this is normal for direct tool calls; only report if configured)
        report.orphaned_ledger_entries = []

        report.quarantine_triggered = len(report.hallucinated_claims) > 0
        self._last_report = report
        self._scan_count += 1

        if report.quarantine_triggered:
            logger.warning(
                "VoiceAudit: %s hallucinated claims detected",
                len(report.hallucinated_claims),
            )

        return report

    def get_stats(self) -> dict[str, Any]:
        """
        Get the stats.

        Returns:
            dict[str, Any]
        """
        return {
            "scan_count": self._scan_count,
            "last_report": self._last_report.to_dict() if self._last_report else None,
        }


_scanner_instance: VoiceAuditScanner | None = None
_scanner_lock = threading.RLock()


def get_voice_audit_scanner() -> VoiceAuditScanner:
    """Get the global VoiceAuditScanner singleton."""
    global _scanner_instance
    if _scanner_instance is None:
        with _scanner_lock:
            if _scanner_instance is None:
                _scanner_instance = VoiceAuditScanner()
    return _scanner_instance
