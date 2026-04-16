"""WhiteMagic Vault — Encrypted local secret storage.

Stores API keys and secrets in an AES-GCM encrypted SQLite database.
Keys are derived from a passphrase (Argon2-like via PBKDF2) or OS keychain.

Usage:
    from whitemagic.security.vault import get_vault
    vault = get_vault()
    vault.set("OPENAI_API_KEY", "sk-abc123...")
    key = vault.get("OPENAI_API_KEY")
"""

import base64
import hashlib
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

# AES-GCM constants
_NONCE_SIZE = 12
_TAG_SIZE = 16
_KEY_SIZE = 32
_PBKDF2_ITERATIONS = 600_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from a passphrase using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, _PBKDF2_ITERATIONS)


def _encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Encrypt plaintext with AES-256-GCM. Returns (ciphertext_with_tag, nonce).

    Requires the cryptography package for secure AES-GCM encryption.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise ImportError(
            "The 'cryptography' package is required for vault encryption. "
            "Install it with: pip install cryptography"
        ) from e

    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return ct, nonce


def _decrypt(ciphertext_with_tag: bytes, nonce: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM ciphertext. Returns plaintext.

    Requires the cryptography package for secure AES-GCM decryption.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise ImportError(
            "The 'cryptography' package is required for vault decryption. "
            "Install it with: pip install cryptography"
        ) from e

    aesgcm = AESGCM(key)
    result = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    return cast(bytes, result)


class Vault:
    """Encrypted local secret storage backed by SQLite."""

    def __init__(self, db_path: Path | None = None, passphrase: str | None = None) -> None:
        from whitemagic.config.paths import WM_ROOT
        self.db_path = db_path or (WM_ROOT / "vault" / "secrets.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to chmod the vault directory to owner-only
        try:
            self.db_path.parent.chmod(0o700)
        except OSError as e:
            logger.debug("Could not restrict vault directory permissions: %s", e)

        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS vault (
                name TEXT PRIMARY KEY,
                encrypted_value BLOB NOT NULL,
                nonce BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_meta (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )
        """)
        self._conn.commit()

        # Derive encryption key
        self._master_key = self._resolve_key(passphrase)

    def _resolve_key(self, passphrase: str | None) -> bytes:
        """Resolve the master encryption key from available sources."""
        # Priority 1: Environment variable
        env_key = os.environ.get("WM_ENCRYPTION_KEY")
        if env_key:
            try:
                return base64.b64decode(env_key)
            except Exception:
                logger.warning("WM_ENCRYPTION_KEY is not valid base64; ignoring")

        # Priority 2: OS keychain
        try:
            import keyring
            stored = keyring.get_password("whitemagic", "vault_master_key")
            if stored:
                return base64.b64decode(stored)
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to read vault master key from OS keychain: {e}", exc_info=True)

        # Priority 3: Passphrase
        if passphrase:
            salt = self._get_or_create_salt()
            return _derive_key(passphrase, salt)

        # Priority 4: Machine key file (persistent random key)
        salt = self._get_or_create_salt()
        machine_key = self._get_or_create_machine_key()
        if machine_key:
            return _derive_key(machine_key, salt)

        # No valid key source available
        raise ValueError(
            "Vault encryption key not available. Set WM_ENCRYPTION_KEY environment variable, "
            "provide a passphrase, or ensure OS keyring is available. "
            "For security, guessable fallback keys have been removed."
        )

    def _get_or_create_salt(self) -> bytes:
        """Get or create the PBKDF2 salt (stored in DB metadata)."""
        row = self._conn.execute(
            "SELECT value FROM vault_meta WHERE key = 'salt'"
        ).fetchone()
        if row:
            return bytes(row[0])
        salt = os.urandom(32)
        self._conn.execute(
            "INSERT INTO vault_meta (key, value) VALUES ('salt', ?)", (salt,)
        )
        self._conn.commit()
        return salt

    def _get_or_create_machine_key(self) -> str | None:
        """Get or create a persistent machine-specific key for vault encryption.
        
        This is stored in a file with 0o600 permissions, providing better security
        than the guessable login@hostname fallback.
        """
        from whitemagic.config.paths import SECURITY_DIR
        key_file = SECURITY_DIR / ".vault_machine_key"

        try:
            if key_file.exists():
                return key_file.read_text()
            # Generate a new random key
            import secrets
            key = secrets.token_urlsafe(32)
            key_file.write_text(key)
            key_file.chmod(0o600)
            return key
        except (ImportError, ModuleNotFoundError):
            # Fall back if we can't create the key file
            return None

    def set(self, name: str, value: str) -> None:
        """Store an encrypted secret."""
        ct, nonce = _encrypt(value.encode("utf-8"), self._master_key)
        now = datetime.now().isoformat()
        self._conn.execute("""
            INSERT INTO vault (name, encrypted_value, nonce, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                encrypted_value = excluded.encrypted_value,
                nonce = excluded.nonce,
                updated_at = excluded.updated_at
        """, (name, ct, nonce, now, now))
        self._conn.commit()
        logger.info(f"Vault: stored secret '{name}'")

    def get(self, name: str) -> str | None:
        """Retrieve a decrypted secret."""
        row = self._conn.execute(
            "SELECT encrypted_value, nonce FROM vault WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        ct, nonce = row
        plaintext = _decrypt(ct, nonce, self._master_key)
        return plaintext.decode("utf-8")

    def delete(self, name: str) -> bool:
        """Delete a secret."""
        cursor = self._conn.execute("DELETE FROM vault WHERE name = ?", (name,))
        self._conn.commit()
        return cursor.rowcount > 0

    def list(self) -> list[str]:
        """List all secret names (never returns values)."""
        rows = self._conn.execute("SELECT name FROM vault ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def exists(self, name: str) -> bool:
        """Check if a secret exists."""
        row = self._conn.execute(
            "SELECT 1 FROM vault WHERE name = ?", (name,)
        ).fetchone()
        return row is not None

    def rekey(self, new_passphrase: str) -> int:
        """Re-encrypt all secrets with a new passphrase. Returns count of re-encrypted secrets."""
        old_key = self._master_key
        salt = os.urandom(32)

        # Update salt
        self._conn.execute(
            "INSERT OR REPLACE INTO vault_meta (key, value) VALUES ('salt', ?)", (salt,)
        )
        new_key = _derive_key(new_passphrase, salt)

        # Re-encrypt all secrets
        rows = self._conn.execute("SELECT name, encrypted_value, nonce FROM vault").fetchall()
        count = 0
        for name, ct, nonce in rows:
            plaintext = _decrypt(ct, nonce, old_key)
            new_ct, new_nonce = _encrypt(plaintext, new_key)
            self._conn.execute(
                "UPDATE vault SET encrypted_value = ?, nonce = ?, updated_at = ? WHERE name = ?",
                (new_ct, new_nonce, datetime.now().isoformat(), name),
            )
            count += 1

        self._conn.commit()
        self._master_key = new_key

        # Update machine key file to match new passphrase
        try:
            from whitemagic.config.paths import SECURITY_DIR
            key_file = SECURITY_DIR / ".vault_machine_key"
            if key_file.exists():
                import secrets
                new_machine_key = secrets.token_urlsafe(32)
                key_file.write_text(new_machine_key)
                key_file.chmod(0o600)
        except Exception:
            logger.debug("Could not update machine key file during rekey")

        logger.info(f"Vault: re-keyed {count} secrets")
        return count

    def __enter__(self) -> Vault:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the vault connection."""
        self._conn.close()


# Global singleton
_vault: Vault | None = None


def get_vault(passphrase: str | None = None) -> Vault:
    """Get or create the global Vault instance."""
    global _vault
    if _vault is None:
        _vault = Vault(passphrase=passphrase)
    return _vault
