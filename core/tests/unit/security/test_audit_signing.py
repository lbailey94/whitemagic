"""Tests for audit_signing Ed25519 module."""

import pytest

from whitemagic.security.audit_signing import (
    AuditSigner,
    _CRYPTO_AVAILABLE,
    get_audit_signer,
)


@pytest.fixture(autouse=True)
def _isolate_keys(monkeypatch, tmp_path):
    """Redirect key storage to a temp directory for each test."""
    monkeypatch.setattr(
        "whitemagic.security.audit_signing._state_root",
        lambda: tmp_path,
    )
    # Reset singleton between tests
    AuditSigner._instance = None
    AuditSigner._lock = None


class TestAuditSigner:
    @pytest.mark.skipif(not _CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_generate_keypair_on_first_use(self, tmp_path):
        signer = get_audit_signer()
        assert signer.is_available()
        assert signer._key_id
        # Keys persisted
        assert (tmp_path / "security" / "audit_key.pem").exists()
        assert (tmp_path / "security" / "audit_key.pub.pem").exists()

    @pytest.mark.skipif(not _CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_sign_and_verify_roundtrip(self, tmp_path):
        signer = get_audit_signer()
        envelope = signer.sign("hello audit")
        assert envelope is not None
        assert envelope["alg"] == "Ed25519"
        assert envelope["signature"]
        assert envelope["key_id"]

        assert signer.verify("hello audit", envelope["signature"], envelope["key_id"])

    @pytest.mark.skipif(not _CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_verify_wrong_payload_fails(self, tmp_path):
        signer = get_audit_signer()
        envelope = signer.sign("original")
        assert not signer.verify("tampered", envelope["signature"], envelope["key_id"])

    @pytest.mark.skipif(not _CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_public_key_pem(self, tmp_path):
        signer = get_audit_signer()
        pem = signer.public_key_pem()
        assert pem
        assert "BEGIN PUBLIC KEY" in pem

    @pytest.mark.skipif(not _CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_singleton_same_key(self, tmp_path):
        s1 = get_audit_signer()
        s2 = get_audit_signer()
        assert s1._key_id == s2._key_id

    def test_graceful_degradation_when_crypto_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.security.audit_signing._CRYPTO_AVAILABLE", False
        )
        # Reset singleton so it picks up the new flag
        AuditSigner._instance = None
        signer = get_audit_signer()
        assert not signer.is_available()
        assert signer.sign("anything") is None
        assert not signer.verify("anything", "fake", "fake")
