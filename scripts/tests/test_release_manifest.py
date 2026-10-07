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

    def test_install_gated_defaults_to_the_gated_lines(self) -> None:
        # 2026-10-04: the v10 matrix is glibc Linux + macOS arm64 + Windows
        # (5d9b03d, ONNX runtime is glibc-only); musl and macos-x86_64 are
        # not built, so they are not install-gated claims. Mirrors the
        # release.yml matrix — the manifest must declare what CI builds.
        self.assertEqual(
            rm.DEFAULT_INSTALL_GATED,
            [
                "linux-x86_64",
                "linux-aarch64",
                "macos-aarch64",
                "windows-x86_64",
            ],
        )

    def test_arm64_artifacts_map_to_manifest_targets(self) -> None:
        self.assertEqual(rm.TARGETS["wm-linux-aarch64"], "linux-aarch64")
        self.assertEqual(rm.TARGETS["wm-windows-x86_64.exe"], "windows-x86_64")

    def test_health_required_assets_match_manifest_targets(self) -> None:
        # The release-health probe's required-asset list must stay in
        # lockstep with the build matrix. Windows is parked out of the alpha
        # matrix (release.yml, 2026-10-05: ONNX link/DLL work pending), so its
        # manifest targets are excluded from the current expectation — re-add
        # them here only together with the matrix entry.
        import release_health as rh

        expected = set()
        for filename in rm.TARGETS:
            if filename.endswith(".exe"):
                continue
            expected.add(filename)
            expected.add(f"{filename}.sha256")
            if not filename.endswith(".exe"):
                expected.add(f"{filename}.gz")
                expected.add(f"{filename}.gz.sha256")
        expected |= {"release-manifest.json", "release-manifest.json.sig"}
        self.assertEqual(set(rh.REQUIRED_RELEASE_ASSETS), expected)
        self.assertEqual(len(rh.REQUIRED_RELEASE_ASSETS), len(expected))

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
