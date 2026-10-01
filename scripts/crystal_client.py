#!/usr/bin/env python3
"""crystal_client.py — client-encrypted WhiteMagic Memory Crystal utility.

Provides client-side authenticated encryption (AES-256-GCM / ChaCha20-Poly1305)
for agent memory states. Plaintext is sealed locally before a caller explicitly
uses ``push``; the remote API also receives public envelope metadata, including
the tenant hash, cipher, parent ID, timestamp, size, and content address.

Spec: wm-crystal/1.0
Local plaintext and ciphertext limit: 2 MiB each (before JSON/base64 envelope overhead)
Content Addressing: sha256:<sha256(ciphertext)>
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
except ImportError:
    AESGCM = None
    ChaCha20Poly1305 = None

SPEC = "wm-crystal/1.0"
SALT = "whitemagic-crystal-salt-v1"
MAX_SIZE = 2 * 1024 * 1024  # local plaintext/ciphertext limit, not serialized envelope size
CRYSTAL_ID_RE = re.compile(r"(?:sha256:)?([0-9a-fA-F]{64})\Z")


def compute_tenant_hash(tenant_id: str, salt: str = SALT) -> str:
    """Derive deterministic tenant hash: sha256(salt:tenant_id)."""
    digest = hashlib.sha256(f"{salt}:{tenant_id}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_aad(cipher: str, tenant_hash: str, parent_crystal_id: str | None, created_at: str) -> bytes:
    """Bind cipher, tenant hash, parent ID, and creation time as AEAD data."""
    parent_str = parent_crystal_id if parent_crystal_id is not None else "genesis"
    return f"{cipher}|{tenant_hash}|{parent_str}|{created_at}".encode("utf-8")


def generate_key(cipher: str = "AES-256-GCM") -> bytes:
    """Generate a random 32-byte cryptographic key."""
    _normalize_cipher(cipher)
    return os.urandom(32)


def _normalize_cipher(cipher: str) -> str:
    normalized = cipher.lower().replace("_", "-")
    if normalized in ("aes-256-gcm", "chacha20-poly1305"):
        return normalized
    raise ValueError(f"unsupported cipher: {cipher}")


def _require_crypto() -> None:
    if AESGCM is None or ChaCha20Poly1305 is None:
        raise RuntimeError(
            "cryptography library required for crystal operations (pip install cryptography)"
        )


def _require_https_api(api_url: str) -> str:
    parsed = urllib.parse.urlsplit(api_url)
    if (parsed.scheme != "https" or not parsed.netloc or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("API URL must be an HTTPS origin without embedded credentials")
    if parsed.path not in ("", "/"):
        raise ValueError("API URL must be an HTTPS origin without a path")
    if parsed.query or parsed.fragment:
        raise ValueError("API URL must not include a query or fragment")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("API URL has an invalid port") from exc
    return api_url.rstrip("/")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so push credentials cannot be forwarded elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            "redirect refused for crystal API request",
            headers,
            fp,
        )


def seal_crystal(
    content: str | bytes | dict,
    key: bytes,
    tenant_id: str,
    parent_crystal_id: str | None = None,
    metadata_public: dict[str, Any] | None = None,
    cipher: str = "aes-256-gcm",
    owner_locator: str | None = None,
) -> dict[str, Any]:
    """Seal memory content locally into a client-encrypted crystal envelope."""
    _require_crypto()
    if len(key) != 32:
        raise ValueError("encryption key must be exactly 32 bytes (256-bit)")

    cipher_norm = _normalize_cipher(cipher)

    if isinstance(content, dict):
        raw_plaintext = json.dumps(content, sort_keys=True).encode("utf-8")
    elif isinstance(content, str):
        raw_plaintext = content.encode("utf-8")
    else:
        raw_plaintext = content

    if len(raw_plaintext) > MAX_SIZE:
        raise ValueError(f"plaintext size {len(raw_plaintext)} exceeds maximum {MAX_SIZE} bytes")

    if owner_locator is None:
        tenant_hash = compute_tenant_hash(tenant_id)
    elif not isinstance(owner_locator, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", owner_locator):
        raise ValueError("owner_locator must be sha256:<64 lowercase hex> from authenticated bootstrap")
    else:
        tenant_hash = owner_locator
    created_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    aad = build_aad(cipher_norm, tenant_hash, parent_crystal_id, created_at)

    nonce = os.urandom(12)
    if cipher_norm == "aes-256-gcm":
        aes = AESGCM(key)
        ciphertext = aes.encrypt(nonce, raw_plaintext, aad)
    elif cipher_norm == "chacha20-poly1305":
        chacha = ChaCha20Poly1305(key)
        ciphertext = chacha.encrypt(nonce, raw_plaintext, aad)
    else:
        raise ValueError(f"unsupported cipher: {cipher}")

    if len(ciphertext) > MAX_SIZE:
        raise ValueError(f"ciphertext size {len(ciphertext)} exceeds maximum {MAX_SIZE} bytes")

    crystal_id = f"sha256:{hashlib.sha256(ciphertext).hexdigest()}"

    return {
        "spec": SPEC,
        "crystal_id": crystal_id,
        "parent_crystal_id": parent_crystal_id,
        "tenant_hash": tenant_hash,
        "cipher": cipher_norm,
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        "size_bytes": len(ciphertext),
        "created_at": created_at,
        "metadata_public": metadata_public or {},
    }


def unseal_crystal(crystal_envelope: dict[str, Any], key: bytes) -> bytes:
    """Client-side unseal and verification of a Memory Crystal envelope."""
    _require_crypto()
    if len(key) != 32:
        raise ValueError("encryption key must be exactly 32 bytes (256-bit)")

    for field in ("crystal_id", "tenant_hash", "cipher", "nonce", "ciphertext", "created_at"):
        if field not in crystal_envelope:
            raise ValueError(f"malformed envelope: missing field {field!r}")

    cipher_norm = _normalize_cipher(crystal_envelope["cipher"])
    nonce = base64.urlsafe_b64decode(crystal_envelope["nonce"])
    ciphertext = base64.urlsafe_b64decode(crystal_envelope["ciphertext"])

    # Verify content address integrity
    expected_id = f"sha256:{hashlib.sha256(ciphertext).hexdigest()}"
    if crystal_envelope["crystal_id"].lower() != expected_id.lower():
        raise ValueError(f"crystal content-address verification failed: {crystal_envelope['crystal_id']} != {expected_id}")

    aad = build_aad(
        cipher_norm,
        crystal_envelope["tenant_hash"],
        crystal_envelope.get("parent_crystal_id"),
        crystal_envelope["created_at"],
    )

    if cipher_norm == "aes-256-gcm":
        aes = AESGCM(key)
        return aes.decrypt(nonce, ciphertext, aad)
    if cipher_norm == "chacha20-poly1305":
        chacha = ChaCha20Poly1305(key)
        return chacha.decrypt(nonce, ciphertext, aad)
    raise ValueError(f"unsupported cipher: {crystal_envelope['cipher']}")


def push_crystal(
    crystal_envelope: dict[str, Any],
    api_url: str = "https://api.whitemagic.dev",
    *, auth_token: str,
) -> dict[str, Any]:
    """Store sealed Memory Crystal envelope on remote gateway (requires auth/session pass)."""
    target = _require_https_api(api_url) + "/crystals"
    data = json.dumps(crystal_envelope).encode("utf-8")
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("auth_token is required")
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(data)),
    }
    headers["Authorization"] = f"Bearer {auth_token}"
    if auth_token.startswith("wm_pass_"):
        headers["X-Session-Pass"] = auth_token

    req = urllib.request.Request(target, data=data, headers=headers, method="POST")
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with opener.open(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            raise RuntimeError(f"HTTP {e.code}: redirect refused") from None
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_msg}") from e


def pull_crystal(
    crystal_id: str,
    *,
    auth_token: str,
    api_url: str = "https://api.whitemagic.dev",
) -> dict[str, Any]:
    """Fetch a crystal from the authenticated owner's server-derived scope."""
    match = CRYSTAL_ID_RE.fullmatch(crystal_id) if isinstance(crystal_id, str) else None
    if not match:
        raise ValueError("crystal ID must be a SHA-256 hex digest, optionally prefixed by 'sha256:'")
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("auth_token is required")
    clean_id = match.group(1).lower()
    target = f"{_require_https_api(api_url)}/crystals/{clean_id}"

    req = urllib.request.Request(
        target,
        headers={"User-Agent": "whitemagic-crystal-client/1.0", "Authorization": f"Bearer {auth_token}"},
        method="GET",
    )
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with opener.open(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            raise RuntimeError(f"HTTP {e.code}: redirect refused") from None
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_msg}") from e


def pull_lineage(
    *,
    auth_token: str,
    api_url: str = "https://api.whitemagic.dev",
) -> list[dict[str, Any]]:
    """Fetch DAG lineage for the authenticated owner."""
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("auth_token is required")
    target = f"{_require_https_api(api_url)}/crystals/lineage"

    req = urllib.request.Request(
        target,
        headers={"User-Agent": "whitemagic-crystal-client/1.0", "Authorization": f"Bearer {auth_token}"},
        method="GET",
    )
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with opener.open(req, timeout=30) as res:
            doc = json.loads(res.read().decode("utf-8"))
            return doc.get("crystals", [])
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            raise RuntimeError(f"HTTP {e.code}: redirect refused") from None
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_msg}") from e


def fetch_owner_locator(*, auth_token: str, api_url: str = "https://api.whitemagic.dev") -> str:
    """Fetch the registry-mapped locator after explicit owner authentication."""
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("auth_token is required")
    target = f"{_require_https_api(api_url)}/crystals/owner-locator"
    req = urllib.request.Request(target, headers={
        "User-Agent": "whitemagic-crystal-client/1.0",
        "Authorization": f"Bearer {auth_token}",
    }, method="GET")
    try:
        opener = urllib.request.build_opener(_NoRedirectHandler)
        with opener.open(req, timeout=30) as res:
            doc = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            raise RuntimeError(f"HTTP {e.code}: redirect refused") from None
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_msg}") from e
    locator = doc.get("owner_locator") if isinstance(doc, dict) else None
    if not isinstance(locator, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", locator):
        raise RuntimeError("gateway returned an invalid owner locator")
    return locator


def _token_from_inputs(token_env: str, token_file: str | None) -> str:
    if token_file:
        fd = os.open(
            token_file,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError("token file must be a regular non-symlink file")
            if os.name == "posix" and st.st_mode & 0o077:
                raise ValueError("token file permissions must be 0600 or stricter")
            if st.st_size > 4096:
                raise ValueError("token file exceeds 4096 bytes")
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                fd = -1
                raw_token = stream.read(4097)
                if len(raw_token.encode("utf-8")) > 4096:
                    raise ValueError("token file exceeds 4096 bytes")
                token = raw_token.strip()
        finally:
            if fd >= 0:
                os.close(fd)
    else:
        token = os.environ.get(token_env, "")
    if not token:
        raise ValueError(f"credential unavailable; set {token_env} or use --token-file")
    return token


def main():
    ap = argparse.ArgumentParser(description="Client-encrypted WhiteMagic Memory Crystal utility")
    sub = ap.add_subparsers(dest="command")

    # genkey
    gen_cmd = sub.add_parser("genkey", help="Generate a random 32-byte crystal key")
    gen_cmd.add_argument("--out", default="", help="Save key to binary file")

    # seal
    seal_cmd = sub.add_parser("seal", help="Seal memory content into an encrypted crystal envelope")
    seal_cmd.add_argument("--content", help="Plaintext content string")
    seal_cmd.add_argument("--file", help="Path to plaintext file")
    seal_cmd.add_argument("--key", help="Hex-encoded 32-byte key or key file path", required=True)
    seal_cmd.add_argument("--api", default="https://api.whitemagic.dev", help="Gateway URL")
    seal_cmd.add_argument("--token-env", default="WM_CRYSTAL_TOKEN", help="Environment variable containing bearer credential")
    seal_cmd.add_argument("--token-file", help="Protected credential file (0600 or stricter)")
    seal_cmd.add_argument("--parent", help="Parent crystal ID (for chain DAG)", default=None)
    seal_cmd.add_argument("--cipher", choices=["AES-256-GCM", "ChaCha20-Poly1305"], default="AES-256-GCM")
    seal_cmd.add_argument("--out", help="Output JSON envelope file")

    # unseal
    unseal_cmd = sub.add_parser("unseal", help="Decrypt and verify a crystal envelope")
    unseal_cmd.add_argument("--envelope", help="Path to crystal envelope JSON", required=True)
    unseal_cmd.add_argument("--key", help="Hex-encoded 32-byte key or key file path", required=True)

    # push
    push_cmd = sub.add_parser("push", help="Push sealed crystal to remote gateway")
    push_cmd.add_argument("--envelope", help="Path to crystal envelope JSON", required=True)
    push_cmd.add_argument("--api", default="https://api.whitemagic.dev", help="Gateway URL")
    push_cmd.add_argument(
        "--token-env",
        default="WM_CRYSTAL_TOKEN",
        help="environment variable containing the API key or session pass (default: WM_CRYSTAL_TOKEN)",
    )
    push_cmd.add_argument("--token-file", help="Protected credential file (0600 or stricter)")

    # pull
    pull_cmd = sub.add_parser("pull", help="Pull crystal envelope from authenticated owner scope")
    pull_cmd.add_argument("--id", help="Crystal ID (sha256:... or hex)", required=True)
    pull_cmd.add_argument("--token-env", default="WM_CRYSTAL_TOKEN", help="Environment variable containing bearer credential")
    pull_cmd.add_argument("--token-file", help="Protected credential file (0600 or stricter)")
    pull_cmd.add_argument("--api", default="https://api.whitemagic.dev", help="Gateway URL")
    pull_cmd.add_argument("--out", help="Save pulled envelope to JSON file")

    # lineage
    lineage_cmd = sub.add_parser("lineage", help="Fetch crystal lineage DAG for authenticated owner")
    lineage_cmd.add_argument("--token-env", default="WM_CRYSTAL_TOKEN", help="Environment variable containing bearer credential")
    lineage_cmd.add_argument("--token-file", help="Protected credential file (0600 or stricter)")
    lineage_cmd.add_argument("--api", default="https://api.whitemagic.dev", help="Gateway URL")

    args = ap.parse_args()

    def resolve_key(key_str: str) -> bytes:
        if os.path.isfile(key_str):
            raw = open(key_str, "rb").read()
            if len(raw) == 32:
                return raw
            raw_text = raw.strip()
            if len(raw_text) == 64:
                return bytes.fromhex(raw_text.decode("ascii"))
        if len(key_str) == 64:
            return bytes.fromhex(key_str)
        if len(key_str.encode("utf-8")) == 32:
            return key_str.encode("utf-8")
        raise ValueError("key must be 32 bytes or 64 hex characters")

    if args.command == "genkey":
        key = generate_key()
        if args.out:
            fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
            print(f"Key written to {args.out}")
        else:
            print(key.hex())

    elif args.command == "seal":
        key = resolve_key(args.key)
        if args.file:
            content = open(args.file, "rb").read()
        elif args.content:
            content = args.content
        else:
            content = sys.stdin.read()
        token = _token_from_inputs(args.token_env, args.token_file)
        locator = fetch_owner_locator(auth_token=token, api_url=args.api)
        envelope = seal_crystal(
            content=content,
            key=key,
            tenant_id="owner-locator",
            parent_crystal_id=args.parent,
            cipher=args.cipher,
            owner_locator=locator,
        )
        out_json = json.dumps(envelope, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_json + "\n")
            print(f"Sealed crystal {envelope['crystal_id']} saved to {args.out}")
        else:
            print(out_json)

    elif args.command == "unseal":
        key = resolve_key(args.key)
        envelope = json.loads(open(args.envelope, "r", encoding="utf-8").read())
        plaintext = unseal_crystal(envelope, key)
        sys.stdout.buffer.write(plaintext)
        if not plaintext.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")

    elif args.command == "push":
        envelope = json.loads(open(args.envelope, "r", encoding="utf-8").read())
        token = _token_from_inputs(args.token_env, args.token_file)
        res = push_crystal(envelope, api_url=args.api, auth_token=token)
        print(json.dumps(res, indent=2))

    elif args.command == "pull":
        doc = pull_crystal(args.id, auth_token=_token_from_inputs(args.token_env, args.token_file), api_url=args.api)
        out_json = json.dumps(doc, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_json + "\n")
            print(f"Pulled crystal saved to {args.out}")
        else:
            print(out_json)

    elif args.command == "lineage":
        items = pull_lineage(auth_token=_token_from_inputs(args.token_env, args.token_file), api_url=args.api)
        print(json.dumps(items, indent=2))

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
