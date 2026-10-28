"""Behavioral tests for generation-safe release-tail helpers."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.release_tail import (
    contract_path,
    export_contract,
    family_for_version,
    select_workflow_run,
    validate_contract,
    verify_health_record,
)
import scripts.release_tail as release_tail


SHA = "f1b57f81c97f7bc3d9ba365ec5e5fe9d349d6342"
MANIFEST_SHA = "a" * 64


def manifest(version: str, family: str) -> dict:
    source = {
        "gen2": "running binary registry (one exact revision)",
        "gen3": "running binary registry (Gen3 hybrid contract bridge)",
    }[family]
    return {
        "kind": "whitemagic-route-schema-manifest",
        "format_version": 1,
        "generated_by": "wm contract --json",
        "version": version,
        "source": source,
        "counts": {"routes": 2, "declared": 1, "undeclared": 1},
        "tools": [
            {"route": "memory.get", "declared": True},
            {"route": "memory.search", "declared": False},
        ],
    }


def health_record(version: str = "10.6.1", manifest_sha: str = MANIFEST_SHA) -> dict:
    return {
        "kind": "wm.release-health",
        "schema": 1,
        "version": version,
        "tag": f"v{version}",
        "status": "healthy",
        "registries": {
            "github-release": {
                "status": "live",
                "manifest_signature_valid": True,
                "artifact_integrity": "verified",
                "manifest_sha256": manifest_sha,
            },
            "crates.io": {"status": "live"},
            "npm": {"status": "live"},
            "docker": {"status": "live"},
            "mcp-registry": {"status": "live"},
        },
        "install_certification": {
            name: {
                "status": "pass",
                "bound_manifest_sha256": manifest_sha,
                "artifact_integrity": "verified",
                "runtime_selftest": "pass",
                "selftest": {"status": "ok", "invariants": "pass"},
            }
            for name in ("npm", "docker")
        },
    }


class ReleaseTailTests(unittest.TestCase):
    def test_release_family_is_explicit_and_unknown_major_fails_closed(self):
        self.assertEqual(family_for_version("v9.3.4"), "gen2")
        self.assertEqual(family_for_version("10.6.1-alpha.1"), "gen3")
        with self.assertRaisesRegex(ValueError, "no registered release family"):
            family_for_version("11.0.0")

    def test_gen2_export_uses_out_and_its_own_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root / "mock-wm9"
            payload = json.dumps(manifest("9.3.4", "gen2"))
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "assert sys.argv[1:3] == ['contract', '--out']\n"
                "pathlib.Path(sys.argv[3]).write_text(" + repr(payload) + ")\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            destination = export_contract("9.3.4", binary, root)
            self.assertEqual(destination, contract_path(root, "gen2"))
            self.assertEqual(json.loads(destination.read_text()), manifest("9.3.4", "gen2"))
            self.assertFalse((root / "docs/gen3/route-schema-manifest.json").exists())

    def test_gen3_export_uses_json_and_preserves_gen2_contract_and_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root / "mock-wm10"
            payload = json.dumps(manifest("10.6.1", "gen3"))
            calls = root / "calls"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "pathlib.Path(" + repr(str(calls)) + ").write_text(' '.join(sys.argv[1:]))\n"
                "assert sys.argv[1:] == ['contract', '--json']\n"
                "print(" + repr(payload) + ")\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            gen2_contract = root / "docs/contract/route-schema-manifest.json"
            gen2_contract.parent.mkdir(parents=True)
            gen2_contract.write_text("sealed Gen2 schema\n", encoding="utf-8")
            catalog = root / "catalogs/routes_v9_enriched.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text("sealed Gen2 catalog\n", encoding="utf-8")

            destination = export_contract("10.6.1", binary, root)
            self.assertEqual(destination, contract_path(root, "gen3"))
            self.assertEqual(calls.read_text(), "contract --json")
            self.assertEqual(json.loads(destination.read_text()), manifest("10.6.1", "gen3"))
            self.assertEqual(gen2_contract.read_text(), "sealed Gen2 schema\n")
            self.assertEqual(catalog.read_text(), "sealed Gen2 catalog\n")

    def test_contract_integer_fields_reject_json_booleans(self):
        cases = (
            ("format_version", None, True),
            ("routes", "routes", True),
            ("declared", "declared", True),
            ("undeclared", "undeclared", False),
        )
        for case, nested, value in cases:
            with self.subTest(case=case):
                payload = manifest("10.6.1", "gen3")
                if case == "format_version":
                    payload[case] = value
                elif case == "routes":
                    payload["tools"] = payload["tools"][:1]
                    payload["counts"] = {"routes": value, "declared": 1, "undeclared": 0}
                elif case == "declared":
                    payload["counts"][nested] = value
                    payload["counts"]["undeclared"] = 0
                else:
                    payload["counts"][nested] = value
                    payload["counts"]["declared"] = 1
                with self.assertRaises(ValueError):
                    validate_contract(payload, "10.6.1", "gen3")

    def test_bad_or_cross_family_manifest_cannot_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root / "mock-wm10"
            destination = contract_path(root, "gen3")
            destination.parent.mkdir(parents=True)
            destination.write_text("previous valid bytes\n", encoding="utf-8")
            payload = manifest("9.3.4", "gen2")
            binary.write_text(
                "#!/usr/bin/env python3\nprint(" + repr(json.dumps(payload)) + ")\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "version"):
                export_contract("10.6.1", binary, root)
            self.assertEqual(destination.read_text(), "previous valid bytes\n")

            payload = manifest("10.6.1", "gen2")
            binary.write_text(
                "#!/usr/bin/env python3\nprint(" + repr(json.dumps(payload)) + ")\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source"):
                export_contract("10.6.1", binary, root)
            self.assertEqual(destination.read_text(), "previous valid bytes\n")

    def test_gen3_symlinked_output_parent_cannot_overwrite_gen2_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gen2 = contract_path(root, "gen2")
            gen2.parent.mkdir(parents=True)
            gen2.write_text("sealed Gen2 bytes\n")
            (root / "docs/gen3").symlink_to(root / "docs/contract", target_is_directory=True)
            binary = root / "mock-wm10"
            payload = json.dumps(manifest("10.6.1", "gen3"))
            binary.write_text("#!/usr/bin/env python3\nprint(" + repr(payload) + ")\n", encoding="utf-8")
            binary.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                export_contract("10.6.1", binary, root)
            self.assertEqual(gen2.read_text(), "sealed Gen2 bytes\n")

    def test_dry_run_does_not_launch_binary_or_create_contract_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root / "mock-wm10"
            calls = root / "calls"
            binary.write_text(
                "#!/bin/sh\nprintf called > " + str(calls) + "\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            destination = export_contract("10.6.1", binary, root, dry_run=True)
            self.assertEqual(destination, contract_path(root, "gen3"))
            self.assertFalse(calls.exists())
            self.assertFalse(destination.parent.exists())

    def test_contract_subprocess_timeout_does_not_write_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(
                release_tail.subprocess,
                "run",
                side_effect=release_tail.subprocess.TimeoutExpired(["wm"], 120),
            ) as run:
                with self.assertRaises(release_tail.subprocess.TimeoutExpired):
                    export_contract("10.6.1", root / "wm", root)
            run.assert_called_once()
            self.assertEqual(run.call_args.kwargs["timeout"], 120)
            self.assertFalse(contract_path(root, "gen3").exists())

    def test_health_run_selects_newest_exact_workflow_run_even_while_pending(self):
        rows = [
            {
                "databaseId": 1,
                "event": "schedule",
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:00:00Z",
            },
            {
                "databaseId": 2,
                "event": "workflow_dispatch",
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:01:00Z",
            },
            {
                "databaseId": 3,
                "event": "workflow_run",
                "headSha": "b" * 40,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:02:00Z",
            },
            {
                "databaseId": 4,
                "event": "workflow_run",
                "headSha": SHA,
                "status": "completed",
                "conclusion": "failure",
                "createdAt": "2026-10-28T00:03:00Z",
            },
            {
                "databaseId": 5,
                "event": "workflow_run",
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:04:00Z",
            },
            {
                "databaseId": 6,
                "event": "workflow_run",
                "headSha": SHA,
                "status": "in_progress",
                "conclusion": None,
                "createdAt": "2026-10-28T00:05:00Z",
            },
        ]
        self.assertEqual(select_workflow_run(rows, "10.6.1", SHA, "health"), "6")
        rows[-1]["status"] = "completed"
        rows[-1]["conclusion"] = "failure"
        self.assertEqual(select_workflow_run(rows, "10.6.1", SHA, "health"), "6")
        self.assertEqual(select_workflow_run(rows[:-1], "10.6.1", SHA, "health"), "5")
        self.assertIsNone(select_workflow_run(rows[:3], "10.6.1", SHA, "health"))

    def test_release_run_selects_newest_exact_tag_source_in_any_state(self):
        rows = [
            {
                "databaseId": 1,
                "event": "push",
                "headBranch": "v10.6.1",
                "headSha": "b" * 40,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:00:00Z",
            },
            {
                "databaseId": 2,
                "event": "push",
                "headBranch": "v10.6.1",
                "headSha": SHA,
                "status": "completed",
                "conclusion": "success",
                "createdAt": "2026-10-28T00:01:00Z",
            },
            {
                "databaseId": 3,
                "event": "push",
                "headBranch": "v10.6.1",
                "headSha": SHA,
                "status": "queued",
                "conclusion": None,
                "createdAt": "2026-10-28T00:02:00Z",
            },
        ]
        self.assertEqual(select_workflow_run(rows, "10.6.1", SHA, "release"), "3")
        rows[-1]["status"] = "completed"
        rows[-1]["conclusion"] = "failure"
        self.assertEqual(select_workflow_run(rows, "10.6.1", SHA, "release"), "3")
        rows.append({
            "databaseId": 4,
            "event": "workflow_dispatch",
            "headBranch": "v10.6.1",
            "headSha": SHA,
            "status": "completed",
            "conclusion": "success",
            "createdAt": "2026-10-28T00:03:00Z",
        })
        self.assertEqual(select_workflow_run(rows, "10.6.1", SHA, "release"), "3")

    def test_health_record_binds_version_manifest_and_both_install_certifications(self):
        verify_health_record(health_record(), "10.6.1", MANIFEST_SHA)
        for wrong_version, wrong_sha in (("10.6.0", MANIFEST_SHA), ("10.6.1", "b" * 64)):
            with self.subTest(version=wrong_version, sha=wrong_sha):
                with self.assertRaises(ValueError):
                    verify_health_record(health_record(), wrong_version, wrong_sha)
        broken = health_record()
        broken["install_certification"]["docker"]["bound_manifest_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "docker certification"):
            verify_health_record(broken, "10.6.1", MANIFEST_SHA)
        for field, value in (("tag", "v10.6.0"), ("kind", "other"), ("schema", 2), ("schema", True)):
            broken = health_record()
            broken[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_health_record(broken, "10.6.1", MANIFEST_SHA)
        broken = health_record()
        broken["registries"]["mcp-registry"]["status"] = "missing"
        with self.assertRaisesRegex(ValueError, "mcp-registry"):
            verify_health_record(broken, "10.6.1", MANIFEST_SHA)
        broken = health_record()
        broken["install_certification"]["npm"]["selftest"] = {"status": "failed"}
        with self.assertRaisesRegex(ValueError, "passing runtime self-test"):
            verify_health_record(broken, "10.6.1", MANIFEST_SHA)

    def test_selftest_passed_field_requires_literal_true_and_status_only_ok_is_supported(self):
        accepted = health_record()
        accepted["install_certification"]["docker"]["selftest"] = {"passed": True}
        verify_health_record(accepted, "10.6.1", MANIFEST_SHA)

        for selftest in (
            {"passed": "false", "status": "failed"},
            {"passed": 1, "status": "failed"},
            {"passed": False, "status": "ok"},
            {"passed": "false", "status": "ok"},
        ):
            with self.subTest(selftest=selftest):
                broken = health_record()
                broken["install_certification"]["npm"]["selftest"] = selftest
                with self.assertRaisesRegex(ValueError, "passing runtime self-test"):
                    verify_health_record(broken, "10.6.1", MANIFEST_SHA)


if __name__ == "__main__":
    unittest.main()
