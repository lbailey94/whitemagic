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


@dataclass
class ZodiacEntry:
    entry_id: str
    timestamp: float
    actor_id: str          # e.g., "clone_alpha_01" or "user"
    action_type: str       # e.g., "memory_create", "file_write", "tool_call"
    payload: dict[str, Any]
    parent_hash: str       # Link to previous entry in chain
    context_id: str | None = None
    consent_token: str | None = None
    hash_signature: str = field(init=False)

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
            str(self.consent_token)
        ]
        hasher = hashlib.sha256()
        hasher.update("||".join(components).encode('utf-8'))
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
            "hash_signature": self.hash_signature
        }

class ZodiacLedger:
    """In-memory and persistent cryptographic ledger."""

    def __init__(self, db_manager=None):
        self._chain: list[ZodiacEntry] = []
        self._genesis_hash = hashlib.sha256(b"WHITEMAGIC_GENESIS_v16").hexdigest()
        self._current_tail = self._genesis_hash
        self._db = db_manager # Hook for SQLite persistence
        self._lock = __import__('threading').Lock()

    def record_action(
        self,
        actor_id: str,
        action_type: str,
        payload: dict[str, Any],
        context_id: str | None = None,
        consent_token: str | None = None
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
                consent_token=consent_token
            )

            self._chain.append(entry)
            self._current_tail = entry.hash_signature

            # Persist to SQLite ledger table via db_manager
            try:
                pool = get_db_pool(str(DB_PATH))
                with pool.connection() as conn:
                    with conn:
                        conn.execute("""
                            INSERT INTO zodiac_ledger (
                                entry_id, timestamp, actor_id, action_type,
                                payload, parent_hash, context_id, consent_token, hash_signature
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            entry.entry_id, entry.timestamp, entry.actor_id, entry.action_type,
                            _json_dumps(entry.payload), entry.parent_hash,
                            entry.context_id, entry.consent_token, entry.hash_signature
                        ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to persist zodiac entry: {e}")

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
