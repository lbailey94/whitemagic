"""Local-only tests for crystal envelope encryption and integrity checks."""

import copy
import hashlib
import json
import os
import sys
import tempfile
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

_PARENT = Path(__file__).resolve().parents[1]
SCRIPTS = _PARENT / "src" if (_PARENT / "src" / "crystal_client.py").is_file() else _PARENT
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
            cc.pull_crystal("../../other-path", auth_token="dummy-token")

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

    def test_all_owner_requests_are_authenticated_and_use_fixed_paths(self) -> None:
        locator = "sha256:" + "a" * 64

        class Response:
            def __init__(self, value):
                self.payload = json.dumps(value).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return self.payload

        opener = Mock()
        opener.open.side_effect = [
            Response({"stored": True}),
            Response({"crystal_id": "sha256:" + "b" * 64}),
            Response({"crystals": []}),
            Response({"owner_locator": locator}),
        ]
        token = "dummy-owner-token"
        with patch.object(cc.urllib.request, "build_opener", return_value=opener) as build:
            cc.push_crystal({"ciphertext": "fixture"}, auth_token=token)
            cc.pull_crystal("sha256:" + "b" * 64, auth_token=token)
            self.assertEqual(cc.pull_lineage(auth_token=token), [])
            self.assertEqual(cc.fetch_owner_locator(auth_token=token), locator)

        requests = [call.args[0] for call in opener.open.call_args_list]
        self.assertEqual([request.get_method() for request in requests], ["POST", "GET", "GET", "GET"])
        self.assertTrue(all(request.get_header("Authorization") == f"Bearer {token}" for request in requests))
        self.assertEqual(requests[0].full_url, "https://api.whitemagic.dev/crystals")
        self.assertEqual(requests[1].full_url, f"https://api.whitemagic.dev/crystals/{'b' * 64}")
        self.assertEqual(requests[2].full_url, "https://api.whitemagic.dev/crystals/lineage")
        self.assertEqual(requests[3].full_url, "https://api.whitemagic.dev/crystals/owner-locator")
        self.assertTrue(all("tenant=" not in request.full_url for request in requests))
        self.assertEqual(build.call_count, 4)
        self.assertTrue(all(call.args == (cc._NoRedirectHandler,) for call in build.call_args_list))

    def test_invalid_id_and_origins_fail_before_network_for_all_owner_requests(self) -> None:
        invalid_origins = (
            "http://example.test",
            "https://user:pass@example.test",
            "https://example.test/path",
            "https://example.test?x=1",
            "https://example.test:bad",
        )
        with patch.object(cc.urllib.request, "build_opener") as build:
            for origin in invalid_origins:
                calls = (
                    lambda: cc.push_crystal({}, api_url=origin, auth_token="dummy"),
                    lambda: cc.pull_crystal("b" * 64, api_url=origin, auth_token="dummy"),
                    lambda: cc.pull_lineage(api_url=origin, auth_token="dummy"),
                    lambda: cc.fetch_owner_locator(api_url=origin, auth_token="dummy"),
                )
                for call in calls:
                    with self.subTest(origin=origin), self.assertRaises(ValueError):
                        call()
            for malformed in ("../escape", "g" * 64, "a" * 63, "a" * 64 + "/x"):
                with self.assertRaises(ValueError):
                    cc.pull_crystal(malformed, auth_token="dummy")
            build.assert_not_called()

    def test_redirects_are_refused_for_all_owner_requests_without_echoing_token(self) -> None:
        token = "dummy-owner-token"
        calls = (
            lambda: cc.push_crystal({}, auth_token=token),
            lambda: cc.pull_crystal("a" * 64, auth_token=token),
            lambda: cc.pull_lineage(auth_token=token),
            lambda: cc.fetch_owner_locator(auth_token=token),
        )
        for call in calls:
            fake_opener = Mock()
            fake_opener.open.side_effect = HTTPError(
                "https://api.whitemagic.dev/crystals", 302, "Found", {},
                BytesIO(token.encode()),
            )
            with patch.object(cc.urllib.request, "build_opener", return_value=fake_opener) as build:
                with self.assertRaisesRegex(RuntimeError, "redirect refused") as raised:
                    call()
            self.assertNotIn(token, str(raised.exception))
            build.assert_called_once_with(cc._NoRedirectHandler)

    def test_owner_calls_require_keyword_auth_and_token_file_is_protected(self) -> None:
        with self.assertRaises(TypeError):
            cc.pull_crystal("a" * 64, "legacy-tenant")
        with self.assertRaises(TypeError):
            cc.pull_lineage("legacy-tenant")

        with tempfile.TemporaryDirectory() as td:
            token_path = Path(td) / "token"
            token_path.write_text("dummy-token\n", encoding="utf-8")
            os.chmod(token_path, 0o600)
            self.assertEqual(cc._token_from_inputs("UNSET_WM_CRYSTAL_TOKEN", str(token_path)), "dummy-token")
            if os.name == "posix":
                os.chmod(token_path, 0o644)
                with self.assertRaises(ValueError):
                    cc._token_from_inputs("UNSET_WM_CRYSTAL_TOKEN", str(token_path))
            link_path = Path(td) / "token-link"
            link_path.symlink_to(token_path)
            with self.assertRaises((OSError, ValueError)):
                cc._token_from_inputs("UNSET_WM_CRYSTAL_TOKEN", str(link_path))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO support required")
    def test_fifo_token_path_is_rejected_without_blocking(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td) / "token-fifo"
            os.mkfifo(fifo)
            code = (
                "import importlib.util,sys; "
                "s=importlib.util.spec_from_file_location('cc',sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "\ntry: m._token_from_inputs('UNSET',sys.argv[2])\n"
                "except (ValueError,OSError): raise SystemExit(0)\n"
                "raise SystemExit(4)"
            )
            result = subprocess.run(
                [sys.executable, "-c", code, str(SCRIPTS / "crystal_client.py"), str(fifo)],
                capture_output=True, timeout=3, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_cli_uses_env_or_file_credentials_and_no_tenant_or_token_arguments(self) -> None:
        import contextlib
        import io

        original_argv = sys.argv
        output = io.StringIO()
        try:
            for command in ("seal", "push", "pull", "lineage"):
                sys.argv = [str(SCRIPTS / "crystal_client.py"), command, "--help"]
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                    cc.main()
                help_text = output.getvalue()
                self.assertIn("--token-env", help_text)
                self.assertIn("--token-file", help_text)
                self.assertNotIn("--token ", help_text)
                if command in ("seal", "pull", "lineage"):
                    self.assertNotIn("--tenant", help_text)
                output.seek(0)
                output.truncate(0)
        finally:
            sys.argv = original_argv

    def test_i1_i2_kek_version_cell_id_binding_rotation_and_dek_erasure(self) -> None:
        kek_v1 = bytes(range(32))
        kek_v2 = bytes(reversed(range(32)))
        plaintext = b"SAIHM-aligned non-custodial crystal payload"

        env = cc.seal_crystal(plaintext, kek_v1, "test-tenant", cipher="chacha20-poly1305", kek_version=1)
        self.assertEqual(env["kek_version"], 1)
        self.assertEqual(env["id_kek_version"], 1)
        self.assertIsNotNone(env["wrapped_dek"])
        self.assertEqual(cc.unseal_crystal(env, kek_v1), plaintext)

        # I1: mutating nonce or id_kek_version must fail content-address verification before AEAD
        tampered_nonce = copy.deepcopy(env)
        tampered_nonce["nonce"] = cc.base64.urlsafe_b64encode(b"0" * 12).decode("ascii")
        with self.assertRaisesRegex(ValueError, "content-address verification failed"):
            cc.unseal_crystal(tampered_nonce, kek_v1)

        # I2: KEK rotation re-wraps DEK under kek_v2 (version 2) without changing crystal_id
        rotated = cc.rotate_crystal_kek(env, kek_v1, kek_v2, 2)
        self.assertEqual(rotated["crystal_id"], env["crystal_id"])
        self.assertEqual(rotated["id_kek_version"], 1)
        self.assertEqual(rotated["kek_version"], 2)
        self.assertNotEqual(rotated["wrapped_dek"], env["wrapped_dek"])
        with self.assertRaises((ValueError, InvalidTag)):
            cc.unseal_crystal(rotated, kek_v1)
        self.assertEqual(cc.unseal_crystal(rotated, kek_v2), plaintext)

        # I2/I3: scrubbing the wrapped DEK renders the scrubbed envelope copy undecryptable
        erased = cc.destroy_crystal_dek(rotated)
        self.assertIsNone(erased["wrapped_dek"])
        self.assertTrue(erased["dek_destroyed"])
        with self.assertRaisesRegex(ValueError, "scrubbed from this envelope"):
            cc.unseal_crystal(erased, kek_v2)
        # Scope check (C2): a retained pre-scrub envelope copy remains decryptable if KEK is retained
        self.assertEqual(cc.unseal_crystal(rotated, kek_v2), plaintext)

    def test_c5_signed_kek_rotation_requires_signer_key_and_resigns_atomically(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        kek_v1 = bytes(range(32))
        kek_v2 = bytes(reversed(range(32)))
        ed_seed = b"c5-holder-ed25519-seed-32-bytes!"
        wrong_seed = b"c5-wrong!-ed25519-seed-32-bytes!"
        ed_pub = Ed25519PrivateKey.from_private_bytes(ed_seed).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        tenant_hash = cc.compute_tenant_hash("tenant-c5")

        env = cc.seal_crystal(b"signed rotatable payload", kek_v1, "tenant-c5", kek_version=1)
        signed_env = cc.sign_crystal_envelope(env, ed_seed)

        # Rotating a signed envelope without ed25519_private_key must fail closed
        with self.assertRaisesRegex(ValueError, "requires ed25519_private_key"):
            cc.rotate_crystal_kek(signed_env, kek_v1, kek_v2, 2)

        # Rotating with a mismatched Ed25519 private key must fail closed
        with self.assertRaisesRegex(ValueError, "does not match existing envelope"):
            cc.rotate_crystal_kek(signed_env, kek_v1, kek_v2, 2, ed25519_private_key=wrong_seed)

        # Rotating with the matching Ed25519 private key re-signs atomically and verifies cleanly
        rotated_signed = cc.rotate_crystal_kek(signed_env, kek_v1, kek_v2, 2, ed25519_private_key=ed_seed)
        self.assertEqual(rotated_signed["crystal_id"], signed_env["crystal_id"])
        self.assertEqual(rotated_signed["kek_version"], 2)
        self.assertEqual(cc.unseal_crystal(rotated_signed, kek_v2), b"signed rotatable payload")

        comm = cc.compute_crystal_set_commitment([rotated_signed], tenant_hash, signing_key=ed_seed)
        res = cc.verify_crystal_set_third_party(
            [rotated_signed], tenant_hash, expected_commitment=comm, signer_public_key=ed_pub
        )
        self.assertTrue(res["verified"])

    def test_i4_i6_client_sig_and_set_commitment_read_path(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        kek = bytes(range(32))
        ed_seed = b"test-ed25519-crystal-seed-32byte"
        anchor_seed = b"test-ed25519-anchor-seed-32bytes"
        anchor_pub = Ed25519PrivateKey.from_private_bytes(anchor_seed).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        tenant_hash = cc.compute_tenant_hash("tenant-i6")

        c1 = cc.seal_crystal(b"step 1", kek, "tenant-i6", kek_version=1)
        c1 = cc.sign_crystal_envelope(c1, ed_seed)
        c2 = cc.seal_crystal(b"step 2", kek, "tenant-i6", parent_crystal_id=c1["crystal_id"], kek_version=1)
        c2 = cc.sign_crystal_envelope(c2, ed_seed, pq_alg="ml-dsa-65", pq_public_key_b64="cHFfcHVi", pq_sig_b64="cHFfc2ln")

        # An external PQ pin is a required profile policy, even if an attacker
        # rewrites the unsigned signature metadata to claim Ed25519 only.
        downgraded = copy.deepcopy(c2)
        downgraded["client_sig"] = {"alg": "ed25519", **{
            k: v for k, v in downgraded["client_sig"].items() if k in ("public_key", "value")
        }}
        with self.assertRaisesRegex(cc.CrystalVerificationError, "required hybrid"):
            cc.verify_crystal_set_third_party(
                [downgraded], tenant_hash, expected_commitment=cc.compute_crystal_set_commitment([downgraded], tenant_hash, signing_key=anchor_seed),
                signer_public_key=anchor_pub, expected_pq_public_key="cHFfcHVi",
                pq_verifier=lambda pub, msg, sig: True,
            )

        self.assertTrue(cc.verify_crystal_client_sig(c1))
        # Fail-closed check (C1): hybrid profile without pq_verifier must raise ValueError
        with self.assertRaisesRegex(ValueError, "requires an explicit pq_verifier"):
            cc.verify_crystal_client_sig(c2)
        self.assertTrue(cc.verify_crystal_client_sig(c2, pq_verifier=lambda pub, msg, sig: sig == "cHFfc2ln"))
        verifier_calls = []
        def original_only_verifier(public_key, message, signature):
            verifier_calls.append(signature)
            return signature == "cHFfc2ln"
        with self.assertRaisesRegex(ValueError, "hybrid KEK rotation is unsupported"):
            cc.rotate_crystal_kek(c2, kek, bytes(reversed(kek)), 2, ed25519_private_key=ed_seed,
                                  pq_alg="ml-dsa-65", pq_public_key_b64="cHFfcHVi",
                                  pq_sig_b64="invalid-new-signature",
                                  pq_verifier=original_only_verifier)
        # The supplied new signature is never emitted or accepted. Rotation is
        # refused before a hybrid result can silently downgrade or go unverified.
        self.assertEqual(verifier_calls, ["cHFfc2ln"])

        # Use standard Ed25519 on c2 for standard read-path unseal without custom pq_verifier
        c2_ed = cc.sign_crystal_envelope(
            cc.seal_crystal(b"step 2", kek, "tenant-i6", parent_crystal_id=c1["crystal_id"], kek_version=1),
            ed_seed,
        )
        comm = cc.compute_crystal_set_commitment([c1, c2_ed], tenant_hash, signing_key=anchor_seed)
        pts = cc.verify_and_unseal_crystal_set(
            [c1, c2_ed], kek, tenant_hash, expected_commitment=comm, anchor_public_key=anchor_pub
        )
        self.assertEqual(pts, [b"step 1", b"step 2"])

        # Rollback / truncation to [c1] must raise CrystalRollbackError against comm
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set(
                [c1], kek, tenant_hash, expected_commitment=comm, anchor_public_key=anchor_pub
            )

    def test_unanchored_verify_policy_strict_default(self) -> None:
        from pathlib import Path

        kek = bytes(range(32))
        tenant_hash = cc.compute_tenant_hash("tenant-anchor-policy")
        c1 = cc.seal_crystal(
            b"one", kek, "tenant-anchor-policy", kek_version=1
        )
        # Default (phase 2 strict): no anchor -> refused fail-closed.
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set([c1], kek, tenant_hash)
        # Explicit opt-out: allowed.
        pts = cc.verify_and_unseal_crystal_set([c1], kek, tenant_hash, require_anchor=False)
        self.assertEqual(pts, [b"one"])
        # Anchored: passes cleanly.
        comm = cc.compute_crystal_set_commitment([c1], tenant_hash)
        pts_anchored = cc.verify_and_unseal_crystal_set(
            [c1], kek, tenant_hash, expected_commitment=comm
        )
        self.assertEqual(pts_anchored, [b"one"])

        # Off-store anchor path resolution helper
        p_dir = Path("/tmp/my-test-store")
        resolved = cc.resolve_offstore_anchor_path(p_dir)
        self.assertEqual(resolved, Path("/tmp/my-test-store.anchor/commitment.json"))
        # Must not be inside store boundary
        self.assertFalse(str(resolved).startswith(str(p_dir) + "/"))

    def test_l5_third_party_zero_knowledge_verifier_rejects_all_t1_t9_without_kek(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        kek = bytes(range(32))
        ed_seed = b"l5-holder-ed25519-seed-32-bytes!"
        ed_pub = Ed25519PrivateKey.from_private_bytes(ed_seed).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        notary_seed = b"l5-notary-ed25519-seed-32-bytes!"
        notary_pub = Ed25519PrivateKey.from_private_bytes(notary_seed).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        tenant_hash = cc.compute_tenant_hash("tenant-l5")

        crystals = []
        parent = None
        for idx in range(3):
            env = cc.seal_crystal(
                f"confidential memory #{idx}".encode(),
                kek,
                "tenant-l5",
                parent_crystal_id=parent,
                metadata_public={"step": idx},
                kek_version=1,
            )
            env = cc.sign_crystal_envelope(env, ed_seed)
            parent = env["crystal_id"]
            crystals.append(env)

        comm_v2 = cc.compute_crystal_set_commitment(crystals[:2], tenant_hash, signing_key=ed_seed)
        comm_v3 = cc.compute_crystal_set_commitment(crystals, tenant_hash, signing_key=ed_seed)
        signed_notarization = cc.sign_context_notarization(
            comm_v3["commitment_digest"], notary_seed, highwater_count=3
        )
        notary = {"receipt": signed_notarization}

        # Happy path: third party verifies [c0, c1, c2] WITHOUT kek using trusted notary_public_key
        res = cc.verify_crystal_set_third_party(
            crystals,
            tenant_hash,
            expected_commitment=comm_v3,
            signer_public_key=ed_pub,
            notarization=notary,
            notary_public_key=notary_pub,
        )
        self.assertTrue(res["verified"])
        self.assertEqual(res["level"], "L5-third-party-zero-knowledge")
        self.assertEqual(res["count"], 3)
        self.assertTrue(res["notarized"])

        bool_version_notary = copy.deepcopy(notary)
        bool_version_notary["receipt"]["version"] = True
        with self.assertRaisesRegex(cc.CrystalVerificationError, "unsupported notarization version"):
            cc.verify_crystal_set_third_party(
                crystals, tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub,
                notarization=bool_version_notary, notary_public_key=notary_pub,
            )

        conflicting_descriptors = copy.deepcopy(notary)
        other_seed = b"other-l5-notary-seed-32-bytes!!!"
        other_pub = Ed25519PrivateKey.from_private_bytes(other_seed).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        encoded = b"\xed\x01" + other_pub
        number = int.from_bytes(encoded, "big")
        did_suffix = ""
        while number:
            number, rem = divmod(number, 58)
            did_suffix = alphabet[rem] + did_suffix
        leading_zeros = len(encoded) - len(encoded.lstrip(b"\0"))
        other_did = "did:key:z" + "1" * leading_zeros + did_suffix
        conflicting_descriptors["receipt"]["sig"]["key"] = other_did
        with self.assertRaisesRegex(cc.CrystalVerificationError, "does not match trusted"):
            cc.verify_crystal_set_third_party(
                crystals, tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub,
                notarization=conflicting_descriptors, notary_public_key=notary_pub,
            )

        # C1 negative probe: replacing Ed25519 client_sig with alg="ml-dsa-65" + garbage pq_sig + tampered metadata MUST fail
        c1_bypass = copy.deepcopy(crystals)
        c1_bypass[1]["metadata_public"] = {"step": 999999, "tampered": True}
        c1_bypass[1]["client_sig"] = {
            "alg": "ml-dsa-65",
            "public_key": ed_pub.hex(),
            "pq_public_key": "garbage",
            "pq_sig": "not-verified-at-all",
        }
        with self.assertRaises(cc.CrystalVerificationError):
            cc.verify_crystal_set_third_party(
                c1_bypass, tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # C3 negative probe: unsigned two-field notarization dict MUST fail
        unsigned_notary = {
            "receipt": {
                "kind": "wm.context-notarization",
                "context_digest": comm_v3["commitment_digest"],
            }
        }
        with self.assertRaises(cc.CrystalVerificationError):
            cc.verify_crystal_set_third_party(
                crystals,
                tenant_hash,
                expected_commitment=comm_v3,
                signer_public_key=ed_pub,
                notarization=unsigned_notary,
                notary_public_key=notary_pub,
            )
        # Omitting notary_public_key when notarization is supplied MUST fail closed
        with self.assertRaises(cc.CrystalVerificationError):
            cc.verify_crystal_set_third_party(
                crystals,
                tenant_hash,
                expected_commitment=comm_v3,
                signer_public_key=ed_pub,
                notarization=notary,
            )

        # T1 (tamper ciphertext) -> rejected without KEK
        t1 = copy.deepcopy(crystals)
        raw_ct = bytearray(cc.base64.urlsafe_b64decode(t1[1]["ciphertext"]))
        raw_ct[0] ^= 0xFF
        t1[1]["ciphertext"] = cc.base64.urlsafe_b64encode(bytes(raw_ct)).decode("ascii")
        with self.assertRaises((cc.CrystalVerificationError, ValueError)):
            cc.verify_crystal_set_third_party(
                t1, tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T2 (truncate tail) -> rejected without KEK
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_crystal_set_third_party(
                crystals[:2], tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T3 (delete middle) -> rejected without KEK
        with self.assertRaises(cc.CrystalLineageError):
            cc.verify_crystal_set_third_party(
                [crystals[0], crystals[2]], tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T4 (reorder) -> rejected without KEK
        with self.assertRaises(cc.CrystalLineageError):
            cc.verify_crystal_set_third_party(
                [crystals[0], crystals[2], crystals[1]],
                tenant_hash,
                expected_commitment=comm_v3,
                signer_public_key=ed_pub,
            )

        # T5 (forge by attacker without holder's Ed25519 key) -> rejected without KEK
        attacker_seed = b"attacker-ed25519-seed-32-bytes!!"
        forged = cc.seal_crystal(
            b"forged", os.urandom(32), "tenant-l5", parent_crystal_id=crystals[2]["crystal_id"], kek_version=1
        )
        forged = cc.sign_crystal_envelope(forged, attacker_seed)
        with self.assertRaises(cc.CrystalVerificationError):
            cc.verify_crystal_set_third_party(
                crystals + [forged], tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T6 (cross_replay from another tenant) -> rejected without KEK
        other = cc.seal_crystal(b"other", kek, "other-tenant", parent_crystal_id=crystals[2]["crystal_id"], kek_version=1)
        other = cc.sign_crystal_envelope(other, ed_seed)
        with self.assertRaises(cc.CrystalContextError):
            cc.verify_crystal_set_third_party(
                crystals + [other], tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T7 (rollback_replay duplicate crystal) -> rejected without KEK
        with self.assertRaises(cc.CrystalLineageError):
            cc.verify_crystal_set_third_party(
                crystals + [crystals[1]], tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T8 (metadata_tamper) -> rejected without KEK via client_sig
        t8 = copy.deepcopy(crystals)
        t8[1]["metadata_public"] = {"step": 999}
        with self.assertRaises(ValueError):
            cc.verify_crystal_set_third_party(
                t8, tenant_hash, expected_commitment=comm_v3, signer_public_key=ed_pub
            )

        # T9 (snapshot_rollback to older valid snapshot [c0, c1] + comm_v2 when notary/anchor is at comm_v3)
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_crystal_set_third_party(
                crystals[:2],
                tenant_hash,
                expected_commitment=comm_v2,
                signer_public_key=ed_pub,
                notarization=notary,
                notary_public_key=notary_pub,
            )


class CrystalAnchorPathTest(unittest.TestCase):
    def test_default_directory_anchor_is_a_sibling_without_creating_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store = root / "store"
            self.assertEqual(
                cc.resolve_offstore_anchor_path(store),
                root / "store.anchor" / "commitment.json",
            )
            self.assertEqual(list(root.iterdir()), [])

    def test_explicit_base_outside_store_is_resolved_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store = root / "store"
            store.mkdir()
            outside = root / "anchors" / "nested"
            self.assertEqual(
                cc.resolve_offstore_anchor_path(store, base_dir=outside),
                outside / "commitment.json",
            )
            self.assertFalse((root / "anchors").exists())
            self.assertEqual(list(store.iterdir()), [])

    def test_base_inside_store_and_candidate_equal_to_store_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store = root / "store"
            store.mkdir()
            for base in (store, store / "anchors", store / "missing" / "nested"):
                with self.subTest(base=base), self.assertRaisesRegex(ValueError, "outside"):
                    cc.resolve_offstore_anchor_path(store, base_dir=base)
            self.assertEqual(list(store.iterdir()), [])
            with self.assertRaisesRegex(ValueError, "outside"):
                cc.resolve_offstore_anchor_path(root / "commitment.json", base_dir=root)

    def test_file_store_uses_its_directory_as_the_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store_dir = root / "store"
            store_dir.mkdir()
            store_file = store_dir / "data.mdb"
            store_file.write_bytes(b"synthetic store")
            self.assertEqual(
                cc.resolve_offstore_anchor_path(store_file),
                root / "store.anchor" / "commitment.json",
            )
            with self.assertRaisesRegex(ValueError, "outside"):
                cc.resolve_offstore_anchor_path(store_file, base_dir=store_dir / "anchors")
            self.assertEqual(store_file.read_bytes(), b"synthetic store")
            self.assertEqual(list(store_dir.iterdir()), [store_file])

    def test_base_and_commitment_symlinks_into_store_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store = root / "store"
            store.mkdir()
            alias = root / "anchor-alias"
            alias.symlink_to(store, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside"):
                cc.resolve_offstore_anchor_path(store, base_dir=alias)

            outside = root / "outside"
            outside.mkdir()
            retained = store / "retained.json"
            retained.write_bytes(b"unchanged synthetic anchor")
            (outside / "commitment.json").symlink_to(retained)
            with self.assertRaisesRegex(ValueError, "outside"):
                cc.resolve_offstore_anchor_path(store, base_dir=outside)
            self.assertEqual(retained.read_bytes(), b"unchanged synthetic anchor")

    def test_store_symlinks_use_the_resolved_directory_and_file_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            actual = root / "actual-store"
            actual.mkdir()
            store_file = actual / "data.mdb"
            store_file.write_bytes(b"synthetic store")
            directory_alias = root / "directory-alias"
            directory_alias.symlink_to(actual, target_is_directory=True)
            file_alias = root / "file-alias"
            file_alias.symlink_to(store_file)
            expected = root / "actual-store.anchor" / "commitment.json"
            for store in (directory_alias, file_alias):
                with self.subTest(store=store):
                    self.assertEqual(cc.resolve_offstore_anchor_path(store), expected)
                    with self.assertRaisesRegex(ValueError, "outside"):
                        cc.resolve_offstore_anchor_path(store, base_dir=actual)

    def test_tenant_default_uses_canonical_component_without_creating_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            home = root / "home"
            tenant_hash = cc.compute_tenant_hash("test-tenant")
            with patch.object(cc.Path, "home", return_value=home):
                self.assertEqual(
                    cc.resolve_offstore_anchor_path(root / "store", tenant_hash=tenant_hash),
                    home / ".whitemagic" / "anchors" / tenant_hash / "commitment.json",
                )
            self.assertEqual(list(root.iterdir()), [])

    def test_tenant_default_inside_store_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = Path(td).resolve()
            with patch.object(cc.Path, "home", return_value=store):
                with self.assertRaisesRegex(ValueError, "outside"):
                    cc.resolve_offstore_anchor_path(
                        store, tenant_hash=cc.compute_tenant_hash("test-tenant")
                    )
            self.assertEqual(list(store.iterdir()), [])

    def test_noncanonical_or_traversing_tenant_components_are_rejected(self) -> None:
        invalid_values = (
            "", ".", "..", "../escape", "/absolute/escape", "a" * 64,
            "sha256:" + "a" * 64 + "/../escape", "sha256:" + "A" * 64,
            "sha256:" + "g" * 64, "sha256:short", "sha256:" + "a" * 64 + "\n",
            0, False, b"sha256:" + b"a" * 64,
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            for tenant_hash in invalid_values:
                for base in (None, root / "outside"):
                    with self.subTest(tenant_hash=tenant_hash, base=base):
                        with self.assertRaisesRegex(ValueError, "tenant_hash"):
                            cc.resolve_offstore_anchor_path(
                                root / "store", tenant_hash=tenant_hash, base_dir=base
                            )
            self.assertEqual(list(root.iterdir()), [])

    def test_anchor_requirement_accepts_only_booleans_even_with_a_commitment(self) -> None:
        key = bytes(range(32))
        tenant_hash = cc.compute_tenant_hash("strict-anchor-flag")
        commitment = cc.compute_crystal_set_commitment([], tenant_hash)
        for flag in (None, 0, 1, 0.0, 1.0, "", "false", [], {}):
            for expected in (None, commitment):
                with self.subTest(flag=flag, anchored=expected is not None):
                    with self.assertRaisesRegex(cc.CrystalVerificationError, "must be a boolean"):
                        cc.verify_and_unseal_crystal_set(
                            [], key, tenant_hash, expected_commitment=expected,
                            require_anchor=flag,
                        )
        self.assertEqual(
            cc.verify_and_unseal_crystal_set([], key, tenant_hash, require_anchor=False), []
        )
        self.assertEqual(
            cc.verify_and_unseal_crystal_set(
                [], key, tenant_hash, expected_commitment=commitment, require_anchor=True
            ), []
        )
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set([], key, tenant_hash, require_anchor=True)


@unittest.skipIf(cc.AESGCM is None or cc.ChaCha20Poly1305 is None, "cryptography is optional")
class LocalCrystalStoreTests(unittest.TestCase):
    def test_zero_config_auto_persists_offstore_anchor_and_defeats_rollback_and_erasure_resurrection(self) -> None:
        import json
        import shutil
        import stat
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        kek = cc.generate_key()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store_dir = root / "agent-store"
            xdg_state = root / "xdg-state"
            with patch.dict("os.environ", {"XDG_STATE_HOME": str(xdg_state)}):
                store = cc.LocalCrystalStore(store_dir, key=kek, tenant_id="tenant-zero")

                # Off-store anchor + key live outside store_dir with private permissions.
                self.assertFalse(store.anchor_path.is_relative_to(store.store_dir))
                self.assertTrue(store.anchor_path.is_file())
                self.assertTrue((store.anchor_dir / "anchor.key").is_file())
                self.assertEqual(stat.S_IMODE(store.anchor_path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE((store.anchor_dir / "anchor.key").stat().st_mode), 0o600)
                self.assertFalse((store.store_dir / "commitment.json").exists())

                e1 = store.append("fact one", metadata_public={"slot": "s1"})
                e2 = store.append("fact two", metadata_public={"slot": "s2"})
                records = store.read_all()
                self.assertEqual([r["plaintext"] for r in records], [b"fact one", b"fact two"])

                # Third-party no-KEK verification succeeds on the auto-signed envelopes + anchor.
                audit = store.verify_third_party()
                self.assertTrue(audit["verified"])
                self.assertEqual(audit["count"], 2)

                # Snapshot store_dir only, then append e3 (T9 setup).
                snap_t9 = root / "snap-t9"
                shutil.copytree(store_dir, snap_t9)
                e3 = store.append("fact three", metadata_public={"slot": "s3"})
                self.assertEqual(len(store.read_all()), 3)

                # Restore pre-append store_dir (T9): off-store anchor detects rollback on read AND refuses append laundering.
                shutil.rmtree(store_dir)
                shutil.copytree(snap_t9, store_dir)
                with self.assertRaises(cc.CrystalRollbackError):
                    store.read_all()
                with self.assertRaises(cc.CrystalRollbackError):
                    store.append("laundered fact")
                self.assertEqual(json.loads(store.anchor_path.read_text(encoding="utf-8"))["count"], 3)

                # Reset to genuine 3-crystal state, snapshot pre-erasure, erase tail e3, then restore pre-erasure store_dir (T10).
                store.crystals_path.write_text(json.dumps([e1, e2, e3]), encoding="utf-8")
                self.assertEqual(len(store.read_all()), 3)
                snap_t10 = root / "snap-t10"
                shutil.copytree(store_dir, snap_t10)
                erased = store.erase(e3["crystal_id"])
                self.assertEqual(len(erased), 1)
                self.assertEqual([r["plaintext"] for r in store.read_all()], [b"fact one", b"fact two"])

                shutil.rmtree(store_dir)
                shutil.copytree(snap_t10, store_dir)
                with self.assertRaises(cc.CrystalRollbackError):
                    store.read_all()

    def test_refuses_in_store_anchor_deleted_anchor_symlinks_metadata_tamper_and_middle_erase(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        kek = cc.generate_key()
        seed = cc.generate_key()
        pub = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            store_dir = root / "store"
            anchor_base = root / "anchors"

            with self.assertRaisesRegex(ValueError, "outside"):
                cc.LocalCrystalStore(
                    store_dir, key=kek, tenant_id="t1",
                    anchor_signing_key=seed, anchor_path=store_dir / "commitment.json",
                )

            store = cc.LocalCrystalStore(
                store_dir, key=kek, tenant_id="t1",
                anchor_signing_key=seed, anchor_base_dir=anchor_base,
            )
            e1 = store.append("first", metadata_public={"role": "system"})
            e2 = store.append("second", metadata_public={"role": "user"})

            # Read-only view validates but refuses mutations.
            ro = cc.LocalCrystalStore(
                store_dir, key=kek, tenant_id="t1",
                anchor_public_key=pub, anchor_base_dir=anchor_base, create=False,
            )
            self.assertEqual(ro.verify_and_unseal(), [b"first", b"second"])
            with self.assertRaises(cc.CrystalVerificationError):
                ro.append("blocked")
            with self.assertRaises(cc.CrystalVerificationError):
                ro.erase()

            # Interior erase without erase_descendants refuses to break linear lineage.
            with self.assertRaises(cc.CrystalLineageError):
                store.erase(e1["crystal_id"])
            self.assertEqual(len(store.read_all()), 2)

            # Metadata tamper (T8) is caught on read by kek_version=1 AAD + client_sig.
            raw = json.loads(store.crystals_path.read_text(encoding="utf-8"))
            orig_raw = json.loads(json.dumps(raw))
            raw[1]["metadata_public"]["role"] = "admin"
            store.crystals_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(cc.CrystalVerificationError):
                store.read_all()
            store.crystals_path.write_text(json.dumps(orig_raw), encoding="utf-8")

            # Deleting off-store anchor on a populated store fails closed on reopen AND read/write.
            saved_anchor = store.anchor_path.read_text(encoding="utf-8")
            store.anchor_path.unlink()
            reopened = cc.LocalCrystalStore(
                store_dir, key=kek, tenant_id="t1",
                anchor_signing_key=seed, anchor_base_dir=anchor_base,
            )
            with self.assertRaises(cc.CrystalRollbackError):
                reopened.read_all()
            with self.assertRaises(cc.CrystalRollbackError):
                reopened.append("should-not-bootstrap")

            # Replacing off-store anchor with a symlink back into store_dir is refused.
            in_store_copy = store_dir / "fake-anchor.json"
            in_store_copy.write_text(saved_anchor, encoding="utf-8")
            store.anchor_path.symlink_to(in_store_copy)
            with self.assertRaises(cc.CrystalVerificationError):
                reopened.read_all()
            store.anchor_path.unlink()
            in_store_copy.unlink()

            # Restore valid anchor and erase from e1 with erase_descendants=True cleanly.
            store.anchor_path.write_text(saved_anchor, encoding="utf-8")
            erased = store.erase(e1["crystal_id"], erase_descendants=True)
            self.assertEqual(len(erased), 2)
            self.assertEqual(store.read_all(), [])

            # Unsigned AEAD metadata tamper (sign_envelope=False) is also rejected via kek_version=1 AAD.
            e_unsigned = store.append("unsigned-meta", metadata_public={"role": "user"}, sign_envelope=False)
            raw_u = json.loads(store.crystals_path.read_text(encoding="utf-8"))
            raw_u[0]["metadata_public"]["role"] = "admin"
            store.crystals_path.write_text(json.dumps(raw_u), encoding="utf-8")
            with self.assertRaises(cc.CrystalVerificationError):
                store.read_all()
            self.assertEqual(e_unsigned["tenant_hash"], store.tenant_hash)

    def test_validates_commitment_types_digest_and_bool_version_trap(self) -> None:
        kek = bytes(range(32))
        tenant_hash = cc.compute_tenant_hash("t-types")
        seed = bytes([7]) * 32
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        c1 = cc.seal_crystal("one", kek, "t-types", kek_version=1)
        comm = cc.compute_crystal_set_commitment([c1], tenant_hash, signing_key=seed, erasures=[])

        bad_ver = dict(comm, version=True)
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set([c1], kek, tenant_hash, expected_commitment=bad_ver, anchor_public_key=pub)

        bad_digest = dict(comm, commitment_digest="sha256:" + "0" * 64)
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set([c1], kek, tenant_hash, expected_commitment=bad_digest, anchor_public_key=pub)

        bad_pub = dict(comm, sig=dict(comm["sig"], public_key="00" * 32))
        with self.assertRaises(cc.CrystalRollbackError):
            cc.verify_and_unseal_crystal_set([c1], kek, tenant_hash, expected_commitment=bad_pub, anchor_public_key=pub)


if __name__ == "__main__":
    unittest.main()
