# ruff: noqa: BLE001
"""Audit Signing — Ed25519 cryptographic signatures for tamper-evident records.

Implements the IETF GAR (Governance Audit Record) non-suppressibility requirement
at Level 1: every audit record is signed at creation and can be verified
independently.

Key design: graceful degradation. If cryptography is unavailable or the key
is missing, the system continues operating but emits a warning. No tool call
should ever fail because signing failed.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy crypto import (never block init) ────────────────────────────
_CRYPTO_AVAILABLE = False
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    _CRYPTO_AVAILABLE = True
except ImportError:
    pass


# ── Key storage layout ──────────────────────────────────────────────
#  $WM_STATE_ROOT/security/audit_key.pem       — private key (PKCS8)
#  $WM_STATE_ROOT/security/audit_key.pub.pem   — public key (SPKI)
#  $WM_STATE_ROOT is resolved from config/paths.py


def _state_root() -> Path:
    from whitemagic.config.paths import get_state_root

    return get_state_root()


def _key_dir() -> Path:
    d = _state_root() / "security"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _private_key_path() -> Path:
    return _key_dir() / "audit_key.pem"


def _public_key_path() -> Path:
    return _key_dir() / "audit_key.pub.pem"


class AuditSigner:
    """Ed25519 signer for audit records.

    Generates a keypair on first use if none exists. Keys are stored
    outside the repo under ``$WM_STATE_ROOT/security/``.
    """

    _instance: AuditSigner | None = None
    _lock: Any = None

    def __new__(cls) -> AuditSigner:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._private_key: Any = None  # type: ignore[misc,has-type]
            cls._instance._public_key: Any = None  # type: ignore[misc,has-type]
            cls._instance._key_id: str = ""  # type: ignore[misc,has-type]
            import threading

            cls._lock = threading.Lock()
        return cls._instance

    def _ensure_key(self) -> bool:
        """Load or generate the Ed25519 keypair. Returns True on success."""
        if self._private_key is not None:  # type: ignore[has-type]
            return True
        if not _CRYPTO_AVAILABLE:
            logger.warning("cryptography library unavailable; audit signing disabled")
            return False
        with self._lock:
            if self._private_key is not None:  # type: ignore[has-type]
                return True
            priv_path = _private_key_path()
            pub_path = _public_key_path()
            if priv_path.exists():
                try:
                    priv_pem = priv_path.read_bytes()
                    self._private_key = serialization.load_pem_private_key(
                        priv_pem, password=None
                    )
                    self._public_key = self._private_key.public_key()
                except Exception as exc:
                    logger.warning("Failed to load audit key: %s", exc)
                    return False
            else:
                try:
                    self._private_key = Ed25519PrivateKey.generate()
                    self._public_key = self._private_key.public_key()
                    # Persist private key
                    priv_pem = self._private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                    priv_path.write_bytes(priv_pem)
                    priv_path.chmod(0o600)
                    # Persist public key
                    pub_pem = self._public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    pub_path.write_bytes(pub_pem)
                    pub_path.chmod(0o644)
                except Exception as exc:
                    logger.warning("Failed to generate audit key: %s", exc)
                    return False
            # Key ID = first 16 hex chars of public-key fingerprint
            pub_der = self._public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            import hashlib

            self._key_id = hashlib.sha256(pub_der).hexdigest()[:16]
            return True

    def is_available(self) -> bool:
        """
        Check whether the available condition holds.

        Returns:
            bool
        """
        return _CRYPTO_AVAILABLE and self._ensure_key()

    def sign(self, payload: str | bytes) -> dict[str, str] | None:
        """Sign a payload and return a signature envelope.

        Returns:
            { "signature": base64(sig), "key_id": "abcd...", "alg": "Ed25519" }
            or None if signing is unavailable.
        """
        if not self._ensure_key():
            return None
        try:
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            assert self._private_key is not None
            sig = self._private_key.sign(data)  # type: ignore[union-attr, call-arg]
            return {
                "signature": base64.b64encode(sig).decode("ascii"),
                "key_id": self._key_id,
                "alg": "Ed25519",
            }
        except Exception as exc:
            logger.warning("Audit sign failed: %s", exc)
            return None

    def verify(
        self, payload: str | bytes, signature_b64: str, key_id: str | None = None
    ) -> bool:
        """Verify a signature against this signer's public key.

        If *key_id* is supplied and doesn't match the current key,
        verification fails (no key rotation support yet).
        """
        if not self._ensure_key():
            return False
        if key_id is not None and key_id != self._key_id:
            logger.debug("Key ID mismatch: expected %s, got %s", self._key_id, key_id)
            return False
        try:
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            sig = base64.b64decode(signature_b64)
            self._public_key.verify(sig, data)
            return True
        except InvalidSignature:
            return False
        except Exception as exc:
            logger.debug("Audit verify error: %s", exc)
            return False

    def public_key_pem(self) -> str | None:
        """Return the public key in PEM format for external custody."""
        if not self._ensure_key():
            return None
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")


def get_audit_signer() -> AuditSigner:
    """Return the singleton AuditSigner."""
    return AuditSigner()
