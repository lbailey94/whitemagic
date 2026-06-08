"""Verify Ed25519 signing integration in Karma Ledger.

Validates that the existing signing infrastructure (whitemagic.security.audit_signing)
works correctly with KarmaLedger.record() and verify_chain().

Run: pytest tests/unit/test_karma_ledger_signing.py -v
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from whitemagic.dharma.karma_ledger import KarmaLedger
from whitemagic.security.audit_signing import get_audit_signer


class TestKarmaLedgerSigning:

    def test_audit_signer_generates_ed25519_signature(self):
        signer = get_audit_signer()
        if not signer.is_available():
            import pytest
            pytest.skip("cryptography library unavailable")

        sig_data = signer.sign("test_payload")
        assert sig_data is not None
        assert "signature" in sig_data
        assert "key_id" in sig_data
        assert sig_data["alg"] == "Ed25519"
        assert len(sig_data["signature"]) > 0
        assert len(sig_data["key_id"]) == 16  # hex fingerprint

    def test_audit_signer_verify_roundtrip(self):
        signer = get_audit_signer()
        if not signer.is_available():
            import pytest
            pytest.skip("cryptography library unavailable")

        payload = "karma_test_payload"
        sig_data = signer.sign(payload)
        assert sig_data is not None
        assert signer.verify(payload, sig_data["signature"], sig_data["key_id"])
        assert not signer.verify(payload + "_tampered", sig_data["signature"], sig_data["key_id"])

    def test_ledger_record_includes_signature(self):
        signer = get_audit_signer()
        if not signer.is_available():
            import pytest
            pytest.skip("cryptography library unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = KarmaLedger(storage_dir=Path(tmpdir))
            entry = ledger.record(
                tool="test_tool",
                declared_safety="READ",
                actual_writes=0,
                success=True,
            )
            assert entry.signature != ""
            assert entry.key_id != ""
            assert len(entry.signature) > 0
            assert len(entry.key_id) == 16

    def test_verify_chain_checks_signatures(self):
        signer = get_audit_signer()
        if not signer.is_available():
            import pytest
            pytest.skip("cryptography library unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = KarmaLedger(storage_dir=Path(tmpdir))
            ledger.record(tool="t1", declared_safety="READ", actual_writes=0, success=True)
            ledger.record(tool="t2", declared_safety="WRITE", actual_writes=1, success=True)

            result = ledger.verify_chain()
            assert result["valid"] is True
            assert result.get("signatures_verified", 0) >= 2

    def test_tampered_entry_fails_signature_verification(self):
        signer = get_audit_signer()
        if not signer.is_available():
            import pytest
            pytest.skip("cryptography library unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = KarmaLedger(storage_dir=Path(tmpdir))
            entry = ledger.record(
                tool="test_tool",
                declared_safety="READ",
                actual_writes=0,
                success=True,
            )
            # Tamper the entry
            entry.signature = "dGVzdHRhbXBlcmVkCg=="  # base64 "tampered"
            result = ledger.verify_chain()
            # The chain should fail at the tampered entry
            assert result["valid"] is False
            assert "signature" in result["message"].lower()
