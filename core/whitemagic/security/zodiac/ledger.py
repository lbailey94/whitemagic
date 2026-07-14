# ruff: noqa: BLE001
"""Zodiac Ledger — Cryptographic Provenance System (MandalaOS Kernel).
======================================================================
Implements an append-only, cryptographically verifiable ledger for all
WhiteMagic state changes, memory creations, and agentic actions.

This prevents 'black box' recursive drift by ensuring every action
can be traced back to its parent context, the active Dharma tenets,
and the human user's consent.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from whitemagic.config.paths import DB_PATH
from whitemagic.core.memory.db_manager import get_db_pool
from whitemagic.utils.fast_json import dumps_str as _json_dumps


import logging
@dataclass
class ZodiacEntry:
    """ZodiacEntry: zodiac entry.

    Value object: equality and repr are field-based."""

    entry_id: str
    timestamp: float
    actor_id: str  # e.g., "clone_alpha_01" or "user"
    action_type: str  # e.g., "memory_create", "file_write", "tool_call"
    payload: dict[str, Any]
    parent_hash: str  # Link to previous entry in chain
    context_id: str | None = None
    consent_token: str | None = None
    hash_signature: str = field(init=False)
    # Ed25519 signature fields (Phase 5: Cryptographic Provenance Unification)
    ed25519_signature: str | None = None  # base64 signature
    key_id: str | None = None  # signer key fingerprint
    sig_alg: str | None = None  # e.g., "Ed25519"

    def __post_init__(self):
        self.hash_signature = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate the SHA-256 hash of this entry's contents."""
        components = [
            self.entry_id,
            str(self.timestamp),
            self.actor_id,
            self.action_type,
            _json_dumps(self.payload),
            self.parent_hash,
            str(self.context_id),
            str(self.consent_token),
        ]
        hasher = hashlib.sha256()
        hasher.update("||".join(components).encode("utf-8"))
        return hasher.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "actor_id": self.action_type,
            "action_type": self.action_type,
            "payload": self.payload,
            "parent_hash": self.parent_hash,
            "context_id": self.context_id,
            "consent_token": self.consent_token,
            "hash_signature": self.hash_signature,
            "ed25519_signature": self.ed25519_signature,
            "key_id": self.key_id,
            "sig_alg": self.sig_alg,
        }


class ZodiacLedger:
    """In-memory and persistent cryptographic ledger with Ed25519 signing."""

    def __init__(self, db_manager=None):
        self._chain: list[ZodiacEntry] = []
        self._genesis_hash = hashlib.sha256(b"WHITEMAGIC_GENESIS_v16").hexdigest()
        self._current_tail = self._genesis_hash
        self._db = db_manager  # Hook for SQLite persistence
        self._lock = __import__("threading").RLock()
        self._signer = None  # Lazy-loaded AuditSigner
        self._event_bus_subscribed = False

    def _get_signer(self):
        """Lazy-load the AuditSigner singleton."""
        if self._signer is None:
            try:
                from whitemagic.security.audit_signing import get_audit_signer

                self._signer = get_audit_signer()
            except Exception:
                logger.debug("Ignored Exception in ledger.py:106")
        return self._signer

    def _sign_entry(self, entry: ZodiacEntry) -> None:
        """Sign a ledger entry with Ed25519 via AuditSigner."""
        signer = self._get_signer()
        if signer is None or not signer.is_available():
            return  # Graceful degradation: unsigned but still chained
        sig_envelope = signer.sign(entry.hash_signature)
        if sig_envelope is not None:
            entry.ed25519_signature = sig_envelope["signature"]
            entry.key_id = sig_envelope["key_id"]
            entry.sig_alg = sig_envelope["alg"]

    def record_action(
        self,
        actor_id: str,
        action_type: str,
        payload: dict[str, Any],
        context_id: str | None = None,
        consent_token: str | None = None,
    ) -> ZodiacEntry:
        """Record an action in the cryptographic ledger."""
        with self._lock:
            entry = ZodiacEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=time.time(),
                actor_id=actor_id,
                action_type=action_type,
                payload=payload,
                parent_hash=self._current_tail,
                context_id=context_id,
                consent_token=consent_token,
            )

            # Sign entry with Ed25519 (Phase 5)
            self._sign_entry(entry)

            self._chain.append(entry)
            self._current_tail = entry.hash_signature

            # Persist to SQLite ledger table via db_manager
            try:
                pool = get_db_pool(str(DB_PATH))
                with pool.connection() as conn:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO zodiac_ledger (
                                entry_id, timestamp, actor_id, action_type,
                                payload, parent_hash, context_id, consent_token, hash_signature,
                                ed25519_signature, key_id, sig_alg
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                entry.entry_id,
                                entry.timestamp,
                                entry.actor_id,
                                entry.action_type,
                                _json_dumps(entry.payload),
                                entry.parent_hash,
                                entry.context_id,
                                entry.consent_token,
                                entry.hash_signature,
                                entry.ed25519_signature,
                                entry.key_id,
                                entry.sig_alg,
                            ),
                        )
            except Exception as e:
                # Fallback: try without new columns (migration not yet applied)
                try:
                    pool = get_db_pool(str(DB_PATH))
                    with pool.connection() as conn:
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO zodiac_ledger (
                                    entry_id, timestamp, actor_id, action_type,
                                    payload, parent_hash, context_id, consent_token, hash_signature
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    entry.entry_id,
                                    entry.timestamp,
                                    entry.actor_id,
                                    entry.action_type,
                                    _json_dumps(entry.payload),
                                    entry.parent_hash,
                                    entry.context_id,
                                    entry.consent_token,
                                    entry.hash_signature,
                                ),
                            )
                except Exception as e2:
                    import logging

                    logging.getLogger(__name__).error(
                        "Failed to persist zodiac entry: %s (fallback also failed: %s)", e, e2
                    )

            return entry

    def verify_chain(self) -> bool:
        """Verify the cryptographic integrity of the entire ledger chain."""
        with self._lock:
            if not self._chain:
                return True

            expected_parent = self._genesis_hash

            for entry in self._chain:
                if entry.parent_hash != expected_parent:
                    return False
                if entry.hash_signature != entry._calculate_hash():
                    return False
                expected_parent = entry.hash_signature

            return True

    def verify_signed_chain(self) -> dict[str, Any]:
        """Verify both SHA-256 chain integrity and Ed25519 signatures.

        Returns a dict with:
            - chain_valid: bool — SHA-256 chain integrity
            - signatures_valid: bool — all Ed25519 signatures verify
            - signed_count: int — entries with signatures
            - unsigned_count: int — entries without signatures
            - total: int — total entries
        """
        with self._lock:
            chain_valid = True
            signatures_valid = True
            signed_count = 0
            unsigned_count = 0
            expected_parent = self._genesis_hash
            signer = self._get_signer()

            for entry in self._chain:
                if entry.parent_hash != expected_parent:
                    chain_valid = False
                if entry.hash_signature != entry._calculate_hash():
                    chain_valid = False
                expected_parent = entry.hash_signature

                if entry.ed25519_signature is not None:
                    signed_count += 1
                    if signer is not None and signer.is_available():
                        if not signer.verify(entry.hash_signature, entry.ed25519_signature, entry.key_id):
                            signatures_valid = False
                else:
                    unsigned_count += 1

            return {
                "chain_valid": chain_valid,
                "signatures_valid": signatures_valid,
                "signed_count": signed_count,
                "unsigned_count": unsigned_count,
                "total": len(self._chain),
            }

    def subscribe_to_event_bus(self) -> None:
        """Subscribe to SecurityEventBus to auto-record security events as ledger entries."""
        if self._event_bus_subscribed:
            return
        try:
            from whitemagic.security.event_bus import get_security_event_bus

            bus = get_security_event_bus()
            bus.subscribe(None, self._on_security_event)
            self._event_bus_subscribed = True
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(
                "Failed to subscribe ZodiacLedger to SecurityEventBus: %s", e
            )

    def _on_security_event(self, event) -> None:
        """Callback for SecurityEventBus events — records them as ledger entries."""
        try:
            self.record_action(
                actor_id=event.agent_id or event.source,
                action_type=f"security_event:{event.event_type}",
                payload=event.to_dict(),
                context_id=event.event_id,
            )
        except Exception:
            logger.debug("Ignored Exception in ledger.py:295")


# Global singleton accessor
_ledger_instance = None


def get_ledger() -> ZodiacLedger:
    """
    Get the ledger.

    Returns:
        ZodiacLedger
    """
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = ZodiacLedger()
    return _ledger_instance
