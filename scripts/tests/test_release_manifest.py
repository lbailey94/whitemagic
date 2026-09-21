#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import release_manifest as rm  # noqa: E402


class ReleaseManifestFactsTest(unittest.TestCase):
    def test_workspace_crate_count_reads_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Cargo.lock").write_text(
                '[[package]]\nname = "wm-core"\nversion = "9.1.4"\n\n'
                '[[package]]\nname = "whitemagic"\nversion = "9.1.4"\n\n'
                '[[package]]\nname = "serde"\nversion = "1"\n'
                'source = "registry+https://github.com/rust-lang/crates.io-index"\n',
                encoding="utf-8",
            )
            self.assertEqual(rm.workspace_crate_count(root), 2)

    def test_install_gated_defaults_to_linux_arches(self) -> None:
        self.assertEqual(
            rm.DEFAULT_INSTALL_GATED, ["linux-x86_64", "linux-aarch64"]
        )

    def test_arm64_artifacts_map_to_manifest_targets(self) -> None:
        self.assertEqual(rm.TARGETS["wm-linux-aarch64"], "linux-aarch64")
        self.assertEqual(rm.TARGETS["wm-linux-aarch64-musl"], "linux-aarch64-musl")

    def test_load_tests_and_benchmarks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "tests.json"
            tests.write_text(
                json.dumps(
                    {"passed": 4431, "ignored": 2, "failed": 0, "source": "ci-34788815848"}
                ),
                encoding="utf-8",
            )
            bench = Path(tmp) / "benchmark_results.txt"
            bench.write_text("dispatch p50 1.1us\n", encoding="utf-8")
            self.assertEqual(rm.load_tests(tests)["passed"], 4431)
            self.assertEqual(rm.load_tests(tests)["ignored"], 2)
            self.assertEqual(rm.load_benchmarks(bench)["raw"], "dispatch p50 1.1us")

    def test_sha256_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blob"
            path.write_bytes(b"abc")
            self.assertEqual(
                rm.sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_channel_is_required(self) -> None:
        old_argv = sys.argv
        sys.argv = ["release_manifest.py", "--version", "9.2.0"]
        try:
            with self.assertRaises(SystemExit) as ctx:
                with contextlib.redirect_stderr(io.StringIO()):
                    rm.main()
            self.assertEqual(ctx.exception.code, 2)
        finally:
            sys.argv = old_argv

    def test_release_workflow_passes_channel(self) -> None:
        workflow = SCRIPTS.parent / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("--channel", text)


if __name__ == "__main__":
    unittest.main()
