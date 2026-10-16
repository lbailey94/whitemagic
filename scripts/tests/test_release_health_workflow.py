"""Offline regression fixtures for release-health trust and checkout ordering."""
from __future__ import annotations

import json
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/release-health.yml"


class ReleaseHealthWorkflowTests(unittest.TestCase):
    def test_checkout_step_preserves_and_runs_saved_checker_with_tag_metadata(self) -> None:
        text = WORKFLOW.read_text()
        marker = "      - name: Check out the release tree\n"
        section = text.split(marker, 1)[1].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        shell = "\n".join(line[10:] for line in section.splitlines() if line.startswith("          "))
        shell = shell.replace('${{ steps.version.outputs.version }}', '9.3.4')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = root / "checkout"
            runner = root / "runner"
            (checkout / "scripts").mkdir(parents=True)
            runner.mkdir()
            shutil.copy(ROOT / "scripts/release_health.py", checkout / "scripts/release_health.py")
            shutil.copy(ROOT / "scripts/crates_publish_order.py", checkout / "scripts/crates_publish_order.py")
            (checkout / "Cargo.toml").write_text('[workspace.package]\nversion="9.3.4"\n')
            old_probe = "# immutable old-tag probe marker\n"
            fakebin = root / "bin"
            fakebin.mkdir()
            git = fakebin / "git"
            git.write_text("""#!/usr/bin/env python3
import pathlib, sys
args=sys.argv[1:]
if args[:1] == ['fetch']:
    raise SystemExit(0)
if args[:2] == ['checkout', '--detach']:
    pathlib.Path('Cargo.toml').write_text('[workspace.package]\\nversion=\\"9.3.4\\"\\n')
    pathlib.Path('scripts/release_health.py').write_text('# immutable old-tag probe marker\\n')
    raise SystemExit(0)
if args[:2] == ['log', '-1']:
    print('fake-tag-commit')
    raise SystemExit(0)
raise SystemExit('unexpected git '+repr(args))
""")
            git.chmod(0o755)
            cargo = fakebin / "cargo"
            cargo.write_text("""#!/usr/bin/env python3
import json, pathlib, re, os
version=re.search(r'version=\\\"([^\\\"]+)', pathlib.Path('Cargo.toml').read_text()).group(1)
name='wm-core' if version.startswith('9.') else 'wm-gen3-core'
pathlib.Path(os.environ['CARGO_FIXTURE_LOG']).write_text(version+' '+name)
ident=f'path+file:///tag#{name}@{version}'
print(json.dumps({'packages':[{'id':ident,'name':name,'publish':None,'dependencies':[]}], 'workspace_members':[ident]}))
""")
            cargo.chmod(0o755)
            env = dict(os.environ, PATH=f"{fakebin}:{os.environ['PATH']}", RUNNER_TEMP=str(runner))
            proc = subprocess.run(["bash", "-eu", "-c", shell], cwd=checkout, env=env, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            saved = runner / "release_health.py"
            self.assertEqual(saved.read_bytes(), (ROOT / "scripts/release_health.py").read_bytes())
            self.assertEqual((checkout / "scripts/release_health.py").read_text(), old_probe)

            # Load and execute the exact saved file after tag checkout. The
            # tag's Cargo metadata is the source for the copied helper's
            # subprocess; HTTP is mocked at the registry boundary.
            helper = runner / "crates_publish_order.py"
            helper.write_bytes((ROOT / "scripts/crates_publish_order.py").read_bytes())
            spec = importlib.util.spec_from_file_location("saved_release_health_fixture", saved)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            from unittest.mock import patch
            previous_cwd = Path.cwd()
            try:
                os.chdir(checkout)
                cargo_log = root / "cargo-observed.txt"
                with patch.object(module, "fetch_json", return_value=(200, None)), patch.dict(os.environ, {"PATH": f"{fakebin}:{os.environ['PATH']}", "CARGO_FIXTURE_LOG": str(cargo_log)}):
                    crates = module.probe_crates("9.3.4")
            finally:
                os.chdir(previous_cwd)
            self.assertEqual(crates["status"], "live")
            self.assertEqual(crates["live"], ["wm-core"])
            self.assertEqual(crates["total"], 1)
            self.assertEqual(cargo_log.read_text(), "9.3.4 wm-core")

    def test_checker_is_saved_before_tag_checkout_and_used_for_both_probes(self) -> None:
        text = WORKFLOW.read_text()
        save = text.index('cp scripts/release_health.py "$RUNNER_TEMP/release_health.py"')
        fetch = text.index('git fetch --depth=1 origin "refs/tags/v${V}"')
        checkout = text.index('git checkout --detach FETCH_HEAD')
        self.assertLess(save, fetch)
        self.assertLess(fetch, checkout)
        self.assertEqual(text.count('python3 "$RUNNER_TEMP/release_health.py"'), 2)
        self.assertIn('TREE_V=', text[checkout:])
        # A v9 fixture remains tied to v9 metadata by the existing exact tag
        # version assertion, while the saved checker is independent of tag code.
        tag_version = "9.3.4"
        self.assertIn('"$TREE_V" = "$V"', text)
        self.assertEqual(tag_version.split('.')[0], '9')

    def test_saved_checker_selects_v9_asset_matrix_for_old_tag(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import release_health as checker
        original = (checker.TARGETS, checker.COMPRESSED_TARGETS, checker.REQUIRED_RELEASE_ASSETS,
                    checker.EXPECTED_MANIFEST_TARGETS, checker.probe_all)
        try:
            observed = {}
            checker.probe_all = lambda repo, version: observed.update({
                "version": version, "targets": set(checker.TARGETS),
                "manifest": set(checker.EXPECTED_MANIFEST_TARGETS),
                "required": set(checker.REQUIRED_RELEASE_ASSETS),
            }) or {"status": "healthy", "version": version, "registries": {}}
            old_argv = sys.argv
            sys.argv = ["release_health.py", "--version", "9.3.4", "--profile", "auto", "--quiet"]
            try:
                self.assertEqual(checker.main(), 0)
            finally:
                sys.argv = old_argv
            self.assertIn("wm-linux-x86_64-musl", observed["targets"])
            self.assertIn("wm-windows-x86_64.exe", observed["targets"])
            self.assertNotIn("wm-windows-x86_64.exe.gz", observed["required"])
            self.assertNotIn("wm-windows-x86_64.exe.gz.sha256", observed["required"])
            self.assertEqual(observed["version"], "9.3.4")
            sys.argv = ["release_health.py", "--version", "10.4.0", "--profile", "auto", "--quiet"]
            checker.probe_all = lambda repo, version: observed.update({"version": version, "targets": set(checker.TARGETS), "required": set(checker.REQUIRED_RELEASE_ASSETS)}) or {"status":"healthy","version":version,"registries":{}}
            self.assertEqual(checker.main(), 0)
            self.assertIn("wm-linux-x86_64", observed["targets"])
            self.assertNotIn("wm-linux-x86_64-musl", observed["targets"])
        finally:
            (checker.TARGETS, checker.COMPRESSED_TARGETS, checker.REQUIRED_RELEASE_ASSETS,
             checker.EXPECTED_MANIFEST_TARGETS, checker.probe_all) = original

    def test_final_gate_binds_each_certification_to_verified_manifest(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn('.install_certification.npm.bound_manifest_sha256 == .registries["github-release"].manifest_sha256', text)
        self.assertIn('.install_certification.docker.bound_manifest_sha256 == .registries["github-release"].manifest_sha256', text)

    def test_github_asset_identity_metadata_is_required(self) -> None:
        code = (ROOT / "scripts/release_health.py").read_text()
        self.assertIn("GitHub asset size missing or invalid", code)
        self.assertIn("GitHub asset digest missing or unsupported", code)

    def test_extracted_final_gate_accepts_exact_binding_and_rejects_wrong_or_missing(self) -> None:
        text = WORKFLOW.read_text()
        marker = "      - name: Gate — every surface live, artifact integrity verified, and every install certified\n"
        section = text.split(marker, 1)[1].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        shell = "\n".join(line[10:] for line in section.splitlines() if line.startswith("          "))
        shell = shell.replace("${{ steps.version.outputs.version }}", "10.3.0")
        sha = "a" * 64
        for binding, expected in ((sha, True), ("b" * 64, False), (None, False)):
            with tempfile.TemporaryDirectory() as temp:
                record = {"status":"healthy", "registries":{"github-release":{"manifest_signature_valid":True,"artifact_integrity":"verified","manifest_sha256":sha}}, "install_certification":{}}
                for channel in ("npm", "docker"):
                    record["install_certification"][channel] = {"status":"pass","bound_manifest_sha256":binding}
                Path(temp, "release-health.json").write_text(json.dumps(record))
                proc = subprocess.run(["bash", "-eu", "-c", shell], cwd=temp, text=True, capture_output=True)
                self.assertEqual(proc.returncode == 0, expected, proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
