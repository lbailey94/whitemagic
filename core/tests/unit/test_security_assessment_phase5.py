"""Tests for Security Capabilities Assessment Phase 5: Cryptographic Provenance Unification.

Covers:
  - ZodiacEntry Ed25519 signature fields
  - ZodiacLedger signs entries via AuditSigner
  - verify_signed_chain() checks both SHA-256 and Ed25519
  - SecurityEventBus auto-recording to ledger
  - Graceful degradation when crypto unavailable
  - to_dict includes signature fields
"""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase5_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── ZodiacEntry Signature Fields ────────────────────────────────────────


class TestZodiacEntrySignatures:
    """Test that ZodiacEntry has Ed25519 signature fields."""

    def test_entry_has_signature_fields(self):
        from whitemagic.security.zodiac.ledger import ZodiacEntry

        entry = ZodiacEntry(
            entry_id="test-1",
            timestamp=1000.0,
            actor_id="test",
            action_type="test_action",
            payload={"key": "value"},
            parent_hash="genesis",
        )
        assert entry.ed25519_signature is None
        assert entry.key_id is None
        assert entry.sig_alg is None
        assert entry.hash_signature is not None

    def test_to_dict_includes_signature_fields(self):
        from whitemagic.security.zodiac.ledger import ZodiacEntry

        entry = ZodiacEntry(
            entry_id="test-2",
            timestamp=1000.0,
            actor_id="test",
            action_type="test_action",
            payload={},
            parent_hash="genesis",
        )
        d = entry.to_dict()
        assert "ed25519_signature" in d
        assert "key_id" in d
        assert "sig_alg" in d
        assert d["ed25519_signature"] is None  # Not signed yet


# ─── ZodiacLedger Signing ────────────────────────────────────────────────


class TestZodiacLedgerSigning:
    """Test that ZodiacLedger signs entries with AuditSigner."""

    def test_record_action_signs_entry(self):
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        ledger = ZodiacLedger()
        entry = ledger.record_action(
            actor_id="test",
            action_type="test_action",
            payload={"data": "test"},
        )
        # If cryptography is available, entry should be signed
        # If not, it should still be None (graceful degradation)
        from whitemagic.security.audit_signing import _CRYPTO_AVAILABLE

        if _CRYPTO_AVAILABLE:
            assert entry.ed25519_signature is not None
            assert entry.key_id is not None
            assert entry.sig_alg == "Ed25519"
        else:
            assert entry.ed25519_signature is None

    def test_verify_chain_still_works(self):
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        ledger = ZodiacLedger()
        ledger.record_action(actor_id="a", action_type="x", payload={})
        ledger.record_action(actor_id="b", action_type="y", payload={})
        assert ledger.verify_chain() is True

    def test_verify_signed_chain(self):
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        ledger = ZodiacLedger()
        ledger.record_action(actor_id="a", action_type="x", payload={})
        ledger.record_action(actor_id="b", action_type="y", payload={})

        result = ledger.verify_signed_chain()
        assert "chain_valid" in result
        assert "signatures_valid" in result
        assert "signed_count" in result
        assert "unsigned_count" in result
        assert "total" in result
        assert result["total"] == 2
        assert result["chain_valid"] is True

    def test_signed_entries_have_valid_signatures(self):
        from whitemagic.security.audit_signing import _CRYPTO_AVAILABLE
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        if not _CRYPTO_AVAILABLE:
            pytest.skip("cryptography library not available")

        ledger = ZodiacLedger()
        ledger.record_action(actor_id="a", action_type="x", payload={"v": 1})
        ledger.record_action(actor_id="b", action_type="y", payload={"v": 2})

        result = ledger.verify_signed_chain()
        assert result["signed_count"] == 2
        assert result["unsigned_count"] == 0
        assert result["signatures_valid"] is True

    def test_tampered_entry_detected(self):
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        ledger = ZodiacLedger()
        entry = ledger.record_action(actor_id="a", action_type="x", payload={"v": 1})
        # Tamper with the entry
        entry.payload = {"v": 999}

        result = ledger.verify_signed_chain()
        assert result["chain_valid"] is False

    def test_graceful_degradation_unsigned(self):
        """Entries should still work even if signing fails."""
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        ledger = ZodiacLedger()
        # Force signer to be unavailable
        ledger._signer = None
        ledger._get_signer = lambda: None

        entry = ledger.record_action(
            actor_id="test",
            action_type="test",
            payload={},
        )
        assert entry.ed25519_signature is None
        assert entry.hash_signature is not None
        assert ledger.verify_chain() is True


# ─── SecurityEventBus Integration ────────────────────────────────────────


class TestSecurityEventBusLedgerIntegration:
    """Test that SecurityEventBus events are recorded to the ledger."""

    def test_subscribe_to_event_bus(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        reset_security_event_bus()
        bus = get_security_event_bus()
        ledger = ZodiacLedger()
        ledger.subscribe_to_event_bus()
        assert ledger._event_bus_subscribed is True

        # Publish an event
        bus.emit(
            event_type=SecurityEventType.TOOL_BLOCKED,
            source="test",
            detail="test event for ledger",
        )

        # Ledger should have recorded the event
        assert len(ledger._chain) >= 1
        entry = ledger._chain[-1]
        assert "security_event" in entry.action_type
        assert entry.action_type == "security_event:security.tool_blocked"

    def test_multiple_events_recorded(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        reset_security_event_bus()
        bus = get_security_event_bus()
        ledger = ZodiacLedger()
        ledger.subscribe_to_event_bus()

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.emit(event_type=SecurityEventType.URL_BLOCKED, source="b")
        bus.emit(event_type=SecurityEventType.TRANSACTION_BLOCKED, source="c")

        assert len(ledger._chain) >= 3

    def test_event_payload_in_ledger(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        reset_security_event_bus()
        bus = get_security_event_bus()
        ledger = ZodiacLedger()
        ledger.subscribe_to_event_bus()

        bus.emit(
            event_type=SecurityEventType.TRANSACTION_BLOCKED,
            source="tx_firewall",
            severity="high",
            detail="Blocked large transaction",
            metadata={"amount": 5000},
        )

        entry = ledger._chain[-1]
        assert "amount" in entry.payload["metadata"]
        assert entry.payload["severity"] == "high"

    def test_chain_integrity_with_events(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        reset_security_event_bus()
        bus = get_security_event_bus()
        ledger = ZodiacLedger()
        ledger.subscribe_to_event_bus()

        bus.emit(event_type=SecurityEventType.TOOL_BLOCKED, source="a")
        bus.emit(event_type=SecurityEventType.URL_BLOCKED, source="b")
        bus.emit(event_type=SecurityEventType.HERMIT_CRAB_STATE_CHANGE, source="c")

        assert ledger.verify_chain() is True

    def test_double_subscribe_safe(self):
        from whitemagic.security.event_bus import get_security_event_bus
        from whitemagic.security.zodiac.ledger import ZodiacLedger

        get_security_event_bus()
        ledger = ZodiacLedger()
        ledger.subscribe_to_event_bus()
        ledger.subscribe_to_event_bus()  # Should not duplicate
        assert ledger._event_bus_subscribed is True
