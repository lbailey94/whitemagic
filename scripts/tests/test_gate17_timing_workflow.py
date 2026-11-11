"""Exercise Gate17 qualification failures without running a timing benchmark."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts/qualify_gate17_timing.sh"
TEST_NAME = "test_gate17_release_recall_latency"


class Gate17TimingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gate17-wrapper-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        cargo = self.directory / "cargo"
        cargo.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$@" > "$GATE17_TEST_ARGS"\n'
            'printf "%s\\n" "$GATE17_FAKE_OUTPUT"\n'
            'exit "${GATE17_FAKE_RETURN:-0}"\n'
        )
        cargo.chmod(0o700)
        self.args_path = self.directory / "args.txt"

    def record(self):
        return {
            "protocol": "gate17-full-recall-v1",
            "profile": "release",
            "source_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "test_sha256": hashlib.sha256(
                (ROOT / "crates/wm-gen3-core/tests/gate17_spreading_activation.rs").read_bytes()
            ).hexdigest(),
            "ops_sha256": hashlib.sha256(
                (ROOT / "crates/wm-gen3-core/src/ops.rs").read_bytes()
            ).hexdigest(),
            "budget_ns": 5_000_000,
            "samples_ns": [100_000] * 9,
        }

    def output(self, record):
        return (
            f"running 1 test\ntest {TEST_NAME} ... \n"
            f"GATE17_TIMING_JSON={json.dumps(record)}\nok\n"
            "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 2 filtered out; finished in 0.01s\n"
        )

    def run_wrapper(self, output, return_code=0, name="result.log"):
        log = self.directory / name
        environment = dict(os.environ)
        environment.update(
            PATH=f"{self.directory}{os.pathsep}{environment['PATH']}",
            GATE17_TEST_ARGS=str(self.args_path),
            GATE17_FAKE_OUTPUT=output,
            GATE17_FAKE_RETURN=str(return_code),
        )
        result = subprocess.run(
            ["bash", str(WRAPPER), str(log)], cwd=ROOT, env=environment,
            capture_output=True, text=True,
        )
        return result, log

    def test_valid_exact_release_execution_is_accepted(self):
        result, log = self.run_wrapper(self.output(self.record()))
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.args_path.read_text().splitlines()
        for required in ("--locked", "--release", "--exact", "--ignored", "--test-threads=1", TEST_NAME):
            self.assertIn(required, args)
        self.assertIn("GATE17_TIMING_JSON=", log.read_text())

    def test_zero_or_ignored_tests_cannot_qualify(self):
        for count, ignored in ((0, 0), (1, 1)):
            with self.subTest(count=count, ignored=ignored):
                output = (
                    f"running {count} tests\n"
                    f"test result: ok. 0 passed; 0 failed; {ignored} ignored; 0 measured; 0 filtered out\n"
                )
                result, _ = self.run_wrapper(output, name=f"missing-{count}.log")
                self.assertNotEqual(result.returncode, 0)

    def test_wrong_source_profile_budget_or_samples_cannot_qualify(self):
        cases = {
            "revision": {"source_revision": "wrong"},
            "hash": {"test_sha256": "0" * 64},
            "debug": {"profile": "debug"},
            "budget": {"budget_ns": 6_000_000},
            "missing-sample": {"samples_ns": [100_000] * 8},
            "boundary": {"samples_ns": [100_000] * 8 + [5_000_000]},
        }
        for name, change in cases.items():
            with self.subTest(name=name):
                record = self.record()
                record.update(change)
                result, _ = self.run_wrapper(self.output(record), name=f"{name}.log")
                self.assertNotEqual(result.returncode, 0)

    def test_duplicate_record_cannot_qualify(self):
        output = self.output(self.record()) + f"GATE17_TIMING_JSON={json.dumps(self.record())}\n"
        result, _ = self.run_wrapper(output)
        self.assertNotEqual(result.returncode, 0)

    def test_failed_cargo_retains_its_output(self):
        result, log = self.run_wrapper("recorded failure", return_code=101)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(log.read_text(), "recorded failure\n")

    def test_existing_result_is_preserved(self):
        existing = self.directory / "result.log"
        existing.write_text("retained earlier observation\n")
        result, _ = self.run_wrapper(self.output(self.record()))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_text(), "retained earlier observation\n")
        self.assertFalse(self.args_path.exists())

    def test_linux_and_macos_require_and_retain_qualification(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        for job, artifact in (("test-linux", "Linux-X64"), ("test-macos", "macOS-ARM64")):
            with self.subTest(job=job):
                # Split only at a sibling job, not at an indented step.
                block = workflow.split(f"  {job}:\n", 1)[1]
                block = re.split(r"\n  [a-z][a-z0-9-]*:\n", block, maxsplit=1)[0]
                qualifier = block.split("      - name: Qualify Gate17", 1)[1].split("      - name:", 1)[0]
                self.assertIn(f"bash scripts/qualify_gate17_timing.sh gate17-timing-{artifact}.log", qualifier)
                self.assertNotIn("continue-on-error", qualifier)
                self.assertIn(f"path: gate17-timing-{artifact}.log", block)
                self.assertIn("always() && !cancelled()", block)


if __name__ == "__main__":
    unittest.main()
