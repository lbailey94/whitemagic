"""Focused unit regressions for fail-closed RPC response handling."""
import importlib.util
import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "zero_egress_rpc.py"
SPEC = importlib.util.spec_from_file_location("zero_egress_rpc", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DecodeToolPayloadTests(unittest.TestCase):
    def response(self, text, *, rid=3, is_error=False):
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "isError": is_error, "content": [{"type": "text", "text": text}]}}

    def test_valid_payload(self):
        self.assertEqual(module.decode_tool_payload(self.response('{"status":"success"}'), 3),
                         {"status": "success"})

    def test_wrong_rpc_id_fails(self):
        with self.assertRaisesRegex(module.HarnessError, "id mismatch"):
            module.decode_tool_payload(self.response('{"status":"success"}', rid=9), 3)

    def test_json_rpc_error_fails(self):
        with self.assertRaisesRegex(module.HarnessError, "JSON-RPC error"):
            module.decode_tool_payload({"id": 3, "error": {"code": -1}}, 3)

    def test_tool_error_flag_fails(self):
        with self.assertRaisesRegex(module.HarnessError, "error result"):
            module.decode_tool_payload(self.response('{"status":"success"}', is_error=True), 3)

    def test_malformed_tool_json_fails(self):
        with self.assertRaisesRegex(module.HarnessError, "malformed JSON"):
            module.decode_tool_payload(self.response("not-json"), 3)

    def test_missing_content_fails(self):
        with self.assertRaisesRegex(module.HarnessError, "no text content"):
            module.decode_tool_payload({"id": 3, "result": {"content": []}}, 3)


class EgressClassificationTests(unittest.TestCase):
    def test_no_route_is_namespace_evidence(self):
        import errno
        self.assertEqual(module.classify_egress_error(errno.ENETUNREACH), "namespace-route-block")
        self.assertEqual(module.classify_egress_error(errno.EHOSTUNREACH), "namespace-route-block")

    def test_policy_denial_is_not_namespace_evidence(self):
        import errno
        self.assertEqual(module.classify_egress_error(errno.EPERM), "host-policy-block")
        self.assertEqual(module.classify_egress_error(errno.EACCES), "host-policy-block")

    def test_unexpected_error_is_not_a_pass(self):
        self.assertEqual(module.classify_egress_error(None), "unexpected-connect-error")

    def test_eprem_connect_maps_to_host_policy_exception(self):
        import errno
        class DeniedSocket:
            def settimeout(self, timeout):
                self.timeout = timeout
            def connect(self, address):
                raise OSError(errno.EPERM, "simulated host policy denial")
            def close(self):
                pass
        with self.assertRaisesRegex(module.HostPolicyBlock, "not namespace proof"):
            module.check_egress_blocked(lambda *_args: DeniedSocket())


class RpcDeadlineTests(unittest.TestCase):
    def test_rpc_deadline_fails_and_child_is_terminated(self):
        with tempfile.TemporaryDirectory(prefix="wm-rpc-timeout-test-") as tmp:
            root = pathlib.Path(tmp)
            fake_server = root / "fake_server.py"
            fake_binary = root / "fake-wm"
            fake_server.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import sys, time
                sys.stdin.readline()
                time.sleep(60)
            """))
            fake_binary.write_text(f"#!/bin/sh\nexec {os.sys.executable} {fake_server} \"$@\"\n")
            fake_binary.chmod(0o755)
            old_env = {k: os.environ.get(k) for k in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME")}
            os.environ.update({"HOME": str(root), "XDG_DATA_HOME": str(root / "data"),
                               "XDG_CONFIG_HOME": str(root / "config")})
            old_timeout = module.RPC_TIMEOUT_SECONDS
            client = None
            try:
                module.RPC_TIMEOUT_SECONDS = 0.05
                client = module.RpcClient(str(fake_binary), str(root / "store"))
                with self.assertRaisesRegex(module.HarnessError, "deadline exceeded"):
                    client.rpc(1, "initialize", {})
            finally:
                module.RPC_TIMEOUT_SECONDS = old_timeout
                if client is not None:
                    proc = client.proc
                    client.close()
                    self.assertIsNotNone(proc.poll(), "RPC timeout cleanup must terminate the child")
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


class NamespaceFailClosedTests(unittest.TestCase):
    def test_unavailable_namespace_exits_nonzero(self):
        script = pathlib.Path(__file__).parents[1] / "zero_egress_test.sh"
        with tempfile.TemporaryDirectory(prefix="wm-no-net-unshare-test-") as tmp:
            root = pathlib.Path(tmp)
            fakebin = root / "bin"
            fakebin.mkdir()
            binary = fakebin / "wm-fixture"
            binary.write_text("#!/bin/sh\necho 'wm 10.5.0'\n")
            binary.chmod(0o755)
            unshare = fakebin / "unshare"
            unshare.write_text("#!/bin/sh\necho 'simulated namespace unavailable' >&2\nexit 1\n")
            unshare.chmod(0o755)
            env = {"PATH": f"{fakebin}:/usr/bin:/bin", "WM_BINARY": str(binary),
                   "HOME": str(root), "TMPDIR": str(root)}
            result = subprocess.run([str(script)], env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=10, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("namespace unavailability is not a pass", result.stdout)


class BinaryIdentityTests(unittest.TestCase):
    def test_wrong_expected_sha_refuses_before_executing_binary(self):
        script = pathlib.Path(__file__).parents[1] / "zero_egress_test.sh"
        with tempfile.TemporaryDirectory(prefix="wm-wrong-sha-test-") as tmp:
            root = pathlib.Path(tmp)
            marker = root / "binary-was-executed"
            binary = root / "wm-fixture"
            binary.write_text(
                "#!/bin/sh\n"
                f"touch '{marker}'\n"
                "echo 'wm 10.5.0'\n"
            )
            binary.chmod(0o755)
            env = {"PATH": "/usr/bin:/bin", "WM_BINARY": str(binary),
                   "WM_EXPECTED_SHA256": "0" * 64, "HOME": str(root),
                   "TMPDIR": str(root)}
            result = subprocess.run([str(script)], env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=10, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("binary SHA-256 mismatch", result.stdout)
            self.assertFalse(marker.exists(), "a hash-mismatched binary must not be executed")


if __name__ == "__main__":
    unittest.main()
