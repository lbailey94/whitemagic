"""Local-only tests for crystal envelope encryption and integrity checks."""

import copy
import hashlib
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request

try:
    from cryptography.exceptions import InvalidTag
except ImportError:  # Keep the test module importable when the optional package is absent.
    InvalidTag = ValueError

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import crystal_client as cc  # noqa: E402


@unittest.skipIf(cc.AESGCM is None or cc.ChaCha20Poly1305 is None, "cryptography is optional")
class CrystalClientTest(unittest.TestCase):
    def test_round_trip_for_each_supported_cipher(self) -> None:
        key = bytes(range(32))
        plaintext = b"local crystal round trip"
        for cipher in ("aes-256-gcm", "chacha20-poly1305"):
            with self.subTest(cipher=cipher):
                envelope = cc.seal_crystal(plaintext, key, "test-tenant", cipher=cipher)
                self.assertEqual(cc.unseal_crystal(envelope, key), plaintext)

    def test_authenticated_fields_reject_tampering(self) -> None:
        key = bytes(range(32))
        envelope = cc.seal_crystal(
            b"tamper check", key, "test-tenant", parent_crystal_id="sha256:parent"
        )
        for field, value in (
            ("tenant_hash", "sha256:" + "0" * 64),
            ("parent_crystal_id", "sha256:other-parent"),
            ("created_at", "2030-01-01T00:00:00Z"),
            ("cipher", "chacha20-poly1305"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(envelope)
                changed[field] = value
                # Keep content-address verification from masking the AAD check.
                if field == "cipher":
                    ciphertext = cc.base64.urlsafe_b64decode(changed["ciphertext"])
                    changed["crystal_id"] = f"sha256:{hashlib.sha256(ciphertext).hexdigest()}"
                with self.assertRaises((ValueError, InvalidTag)):
                    cc.unseal_crystal(changed, key)

    def test_public_metadata_is_not_aad_bound(self) -> None:
        key = bytes(range(32))
        envelope = cc.seal_crystal(b"public metadata", key, "test-tenant", metadata_public={"label": "a"})
        envelope["metadata_public"] = {"label": "changed"}
        self.assertEqual(cc.unseal_crystal(envelope, key), b"public metadata")

    def test_api_urls_require_https_and_reject_embedded_secrets(self) -> None:
        for url in (
            "http://example.test",
            "https://user:pass@example.test",
            "https://example.test/path",
            "https://example.test?x=1",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                cc._require_https_api(url)

    def test_pull_rejects_malformed_ids_before_network_access(self) -> None:
        with self.assertRaises(ValueError):
            cc.pull_crystal("../../other-path", "test-tenant")

    def test_push_fails_closed_on_redirect(self) -> None:
        fake_opener = Mock()
        fake_opener.open.side_effect = HTTPError(
            "https://api.whitemagic.dev/crystals",
            307,
            "temporary redirect",
            {},
            BytesIO(b"secret-test-token reflected by endpoint"),
        )
        with patch.object(cc.urllib.request, "build_opener", return_value=fake_opener) as build_opener:
            with self.assertRaisesRegex(RuntimeError, "HTTP 307") as raised:
                cc.push_crystal({"ciphertext": "opaque"}, auth_token="secret-test-token")
        self.assertNotIn("secret-test-token", str(raised.exception))

        build_opener.assert_called_once_with(cc._NoRedirectHandler)
        fake_opener.open.assert_called_once()
        handler = cc._NoRedirectHandler()
        request = Request("https://api.whitemagic.dev/crystals", data=b"{}", method="POST")
        with self.assertRaises(HTTPError) as raised:
            handler.redirect_request(
                request,
                BytesIO(b""),
                307,
                "temporary redirect",
                {},
                "http://attacker.invalid/collect",
            )
        self.assertEqual(raised.exception.code, 307)


if __name__ == "__main__":
    unittest.main()
