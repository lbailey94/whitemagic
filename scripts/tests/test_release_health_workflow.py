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
    def test_release_tail_probes_gen3_crates_and_preserves_npm_stable_selector(self) -> None:
        release = (ROOT / "scripts/release.sh").read_text()
        registry = release.split('banner "REGISTRIES"', 1)[1].split(
            '# The MCP registry search index lags', 1
        )[0]
        for crate in (
            "wm-gen3-core", "wm-gen3-shm", "wm-gen3-vault",
            "wm-gen3-systemone", "wm-gen3-zeropointfive", "wm-gen3-harness",
        ):
            self.assertIn(crate, registry)
        self.assertIn('https://crates.io/api/v1/crates/$crate', registry)
        self.assertIn('registry.npmjs.org/whitemagic-mcp', registry)
        self.assertIn("dist-tags\"].next", registry)
        self.assertIn("dist-tags\"].latest", registry)
        self.assertIn('if [ "$npm_latest" = "$VERSION" ]', registry)
        self.assertNotIn('registry.npmjs.org/whitemagic-mcp/latest', registry)

    def test_selector_policy_keeps_gen3_preview_off_latest_even_when_misflagged(self) -> None:
        helper = ROOT / "scripts/release_channels.py"
        cases = (
            ("9.3.4", "false", "latest"),
            ("9.4.0", "true", "next"),
            ("10.6.0", "false", "next"),
            ("10.5.1", "true", "next"),
            ("10.6.0", "true", "skip", "10.6.1"),
            ("10.6.0-beta.3", "true", "skip", "10.6.0-beta.4"),
            ("9.3.5", "false", "skip", "9.3.6"),
        )
        for case in cases:
            version, prerelease, expected, *current = case
            with self.subTest(version=version, prerelease=prerelease):
                result = subprocess.run(
                    [sys.executable, str(helper), version, prerelease, *current],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_release_publication_is_quarantined_and_waits_for_native_cert(self) -> None:
        release = (ROOT / ".github/workflows/release.yml").read_text()
        health = WORKFLOW.read_text()
        self.assertRegex(
            release,
            r"  registries:\n[\s\S]*?\n    needs: \[publish, certify-install\]",
        )
        npm_publish = release.split("      - name: Publish npm\n", 1)[1].split("\n      - ", 1)[0]
        self.assertIn("npm publish --access public --tag quarantine", npm_publish)
        docker_publish = release.split("      - name: Publish Docker Hub (multi-arch; skips without secrets)\n", 1)[1].split("\n      - ", 1)[0]
        self.assertIn('TAGS=(-t "lbailey94/whitemagic:${VERSION}")', docker_publish)
        self.assertNotIn("whitemagic:latest", docker_publish)

        retry = health.split("      - name: Retry npm (if lagging)\n", 1)[1].split(
            "\n      - ", 1
        )[0]
        self.assertLess(retry.index('status == "live"'), retry.index("npm publish"))
        self.assertIn("manifest_signature_valid == true", retry)
        self.assertIn('artifact_integrity == "verified"', retry)
        self.assertIn("npm publish --access public --tag quarantine", retry)
        self.assertNotRegex(retry, r"npm publish[^\n]*--tag (latest|next)")

        npm_cert = health.split("      - name: Certify npm install (download funnel + selftest)\n", 1)[1].split(
            "\n      - ", 1
        )[0]
        self.assertNotIn("continue-on-error", npm_cert)
        self.assertIn('npm install -g "whitemagic-mcp@${{ steps.version.outputs.version }}"', npm_cert)
        self.assertIn("whitemagic-mcp selftest --json", npm_cert)
        self.assertIn('"status":"failed"', npm_cert)

        gate = health.index("      - name: Gate — every surface live, artifact integrity verified, and every install certified\n")
        promote = health.index("      - name: Promote certified npm selector\n")
        docker_alias = health.index("      - name: Promote certified stable Docker aliases\n")
        self.assertLess(gate, promote)
        self.assertLess(gate, docker_alias)
        self.assertIn("npm dist-tag add", health[promote:])
        self.assertIn('"$RUNNER_TEMP/release_channels.py"', health[promote:])
        self.assertIn('"${CURRENT:-<none>}"', health[promote:])
        self.assertIn('cannot determine current npm ${SELECTOR}', health[promote:])
        self.assertIn('refusing downgrade to ${VERSION}', health[promote:])
        docker_step = health[docker_alias:].split("\n      - ", 1)[0]
        self.assertIn("docker buildx imagetools create", docker_step)
        self.assertIn('cmp -s source-manifest.json', docker_step)
        self.assertIn("docker pull lbailey94/whitemagic:latest", docker_step)
        self.assertIn("CURRENT_DOCKER_VERSION", docker_step)
        self.assertIn("refusing downgrade to ${VERSION}", docker_step)
        self.assertNotIn("docker tag ", docker_step)
        self.assertNotIn("docker push ", docker_step)

    def test_incomplete_misflagged_release_cannot_publish_or_move_npm_selectors(self) -> None:
        text = WORKFLOW.read_text()
        marker = "      - name: Retry npm (if lagging)\n"
        section = text.split(marker, 1)[1].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        shell = "\n".join(line[10:] for line in section.splitlines() if line.startswith("          "))
        shell = shell.replace("${{ steps.version.outputs.version }}", "10.6.0")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fakebin = root / "bin"
            fakebin.mkdir()
            (root / "release-health.json").write_text(
                '{"version":"10.6.0","release_prerelease":false,'
                '"registries":{"npm":{"status":"missing"},'
                '"github-release":{"status":"lagging",'
                '"manifest_signature_valid":false,"artifact_integrity":"unverified"}}}'
            )
            jq = fakebin / "jq"
            jq.write_text("""#!/usr/bin/env bash
case "$*" in
  *'.registries.npm.status'*) echo missing ;;
  *'manifest_signature_valid == true'*) exit 1 ;;
  *) exit 2 ;;
esac
""")
            npm = fakebin / "npm"
            npm.write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$NPM_CALLS"
""")
            jq.chmod(0o755)
            npm.chmod(0o755)
            (root / "npm/whitemagic-mcp").mkdir(parents=True)
            calls = root / "npm-calls"
            env = dict(os.environ, PATH=f"{fakebin}:{os.environ['PATH']}", NPM_CALLS=str(calls))
            proc = subprocess.run(["bash", "-eu", "-c", shell], cwd=root, env=env,
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertIn("refusing npm publication", proc.stdout)
            self.assertFalse(calls.exists(), "incomplete release must not publish or move a selector")

    def test_stable_docker_alias_promotion_preserves_source_manifest_index(self) -> None:
        text = WORKFLOW.read_text()
        marker = "      - name: Promote certified stable Docker aliases\n"
        section = text.split(marker, 1)[1].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        shell = "\n".join(line[10:] for line in section.splitlines() if line.startswith("          "))
        shell = shell.replace("${{ steps.version.outputs.version }}", "9.3.5")
        shell = shell.replace("${{ github.repository }}", "lbailey94/whitemagic")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fakebin = root / "bin"
            fakebin.mkdir()
            runner = root / "runner"
            runner.mkdir()
            shutil.copy(ROOT / "scripts/release_channels.py", runner / "release_channels.py")
            source = root / "source-manifest.json"
            source.write_text('{"schemaVersion":2,"manifests":[{"platform":{"architecture":"amd64","os":"linux"}},{"platform":{"architecture":"arm64","os":"linux"}}]}')
            calls = root / "docker-calls"
            gh = fakebin / "gh"
            gh.write_text("#!/usr/bin/env bash\necho false\n")
            docker = fakebin / "docker"
            docker.write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$DOCKER_CALLS"
if [[ "$1 $2 $3 $4" == "buildx imagetools inspect --raw" ]]; then
  ref="$5"
  if [[ "${DOCKER_ALIAS_DRIFT:-0}" == 1 && "$ref" == *:latest ]]; then
    printf '{"schemaVersion":2,"manifests":[{"platform":{"architecture":"amd64","os":"linux"}}]}\\n'
  else
    cat "$DOCKER_SOURCE_MANIFEST"
  fi
elif [[ "$1 $2 $3" == "buildx imagetools inspect" ]]; then
  printf 'Digest: sha256:fixture\\n'
elif [[ "$1 $2 $3" == "buildx imagetools create" ]]; then
  echo "$*" >> "$DOCKER_CALLS"
elif [[ "$1 $2" == "image inspect" ]]; then
  echo "${DOCKER_CURRENT_VERSION:-9.3.4}"
elif [[ "$1 $2" == "pull lbailey94/whitemagic:latest" ]]; then
  :
elif [[ "$1" == login ]]; then
  cat >/dev/null
else
  exit 91
fi
""")
            gh.chmod(0o755)
            docker.chmod(0o755)
            env = dict(os.environ, PATH=f"{fakebin}:{os.environ['PATH']}",
                       RUNNER_TEMP=str(runner), GH_TOKEN="fixture",
                       DOCKERHUB_USERNAME="fixture", DOCKERHUB_TOKEN="fixture",
                       DOCKER_CALLS=str(calls), DOCKER_SOURCE_MANIFEST=str(source))
            proc = subprocess.run(["bash", "-eu", "-c", shell], cwd=root, env=env,
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            recorded = calls.read_text()
            self.assertIn("buildx imagetools create", recorded)
            self.assertIn("pull lbailey94/whitemagic:latest", recorded)
            self.assertNotRegex(recorded, r"(^|\n)(tag|push) ")

            calls.write_text("")
            env["DOCKER_ALIAS_DRIFT"] = "1"
            drift = subprocess.run(["bash", "-eu", "-c", shell], cwd=root, env=env,
                                   text=True, capture_output=True)
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("does not preserve the exact version manifest digest", drift.stderr)

            calls.write_text("")
            env["DOCKER_ALIAS_DRIFT"] = "0"
            env["DOCKER_CURRENT_VERSION"] = "9.3.6"
            older = subprocess.run(["bash", "-eu", "-c", shell], cwd=root, env=env,
                                   text=True, capture_output=True)
            self.assertEqual(older.returncode, 0, older.stderr or older.stdout)
            self.assertIn("refusing downgrade to 9.3.5", older.stdout)
            self.assertNotIn("buildx imagetools create", calls.read_text())

    def test_source_checker_uses_its_workspace_from_an_unrelated_cwd(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "release_health_outside_checkout", ROOT / "scripts/release_health.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            decoy = Path(tmp)
            (decoy / "Cargo.toml").write_text(
                '[package]\nname="unrelated-checkout"\nversion="0.0.1"\nedition="2021"\n'
            )
            (decoy / "src").mkdir()
            (decoy / "src/lib.rs").write_text("")
            previous_cwd = Path.cwd()
            try:
                os.chdir(decoy)
                with patch.object(module, "fetch_json", return_value=(200, {})), patch.object(
                    module.time, "sleep"
                ):
                    result = module.probe_crates("10.5.1")
            finally:
                os.chdir(previous_cwd)
        self.assertEqual(result["status"], "live", result)
        self.assertEqual(result["total"], 6)
        self.assertNotIn("unrelated-checkout", result["live"])
        self.assertIn("wm-gen3-harness", result["live"])

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
            shutil.copy(ROOT / "scripts/release_channels.py", checkout / "scripts/release_channels.py")
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
            self.assertEqual((runner / "release_channels.py").read_bytes(), (ROOT / "scripts/release_channels.py").read_bytes())
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
        channel_save = text.index('cp scripts/release_channels.py "$RUNNER_TEMP/release_channels.py"')
        fetch = text.index('git fetch --depth=1 origin "refs/tags/v${V}"')
        checkout = text.index('git checkout --detach FETCH_HEAD')
        self.assertLess(save, fetch)
        self.assertLess(channel_save, fetch)
        self.assertLess(fetch, checkout)
        self.assertEqual(text.count('python3 "$RUNNER_TEMP/release_health.py"'), 2)
        self.assertEqual(text.count('python3 "$RUNNER_TEMP/release_channels.py"'), 4)
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

    def test_merge_and_gate_require_valid_manifest_digest(self) -> None:
        text = WORKFLOW.read_text()

        def step(name: str) -> str:
            section = text.split(f"      - name: {name}\n", 1)[1].split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
            return "\n".join(line[10:] for line in section.splitlines() if line.startswith("          ")).replace("${{ steps.version.outputs.version }}", "10.3.0")

        merge = step("Merge certifications into the record")
        gate = step("Gate — every surface live, artifact integrity verified, and every install certified")
        absent = object()
        cases = (absent, None, "", "not-a-sha256", "a" * 63, "g" * 64, "a" * 64 + "\n", 123, ["a" * 64], "a" * 64)
        for digest in cases:
            valid = digest == "a" * 64
            for run_merge in (False, True):
                with self.subTest(digest=str(digest), merge=run_merge), tempfile.TemporaryDirectory() as temp:
                    gh = {"manifest_signature_valid": True, "artifact_integrity": "verified"}
                    if digest is not absent:
                        gh["manifest_sha256"] = digest
                    record = {"status": "healthy", "registries": {"github-release": gh}, "install_certification": {}}
                    for channel in ("npm", "docker"):
                        cert = {"status": "pass"}
                        if digest is not absent:
                            cert["bound_manifest_sha256"] = digest
                        record["install_certification"][channel] = cert
                        Path(temp, f"{channel}-selftest.json").write_text('{"status":"ok","invariants":"pass"}')
                    path = Path(temp, "release-health.json")
                    path.write_text(json.dumps(record))
                    if run_merge:
                        merged = subprocess.run(["bash", "-eu", "-c", merge], cwd=temp, text=True, capture_output=True)
                        self.assertEqual(merged.returncode, 0, merged.stderr or merged.stdout)
                        result = json.loads(path.read_text())
                        for cert in result["install_certification"].values():
                            self.assertEqual(cert["status"], "pass" if valid else "fail")
                    proc = subprocess.run(["bash", "-eu", "-c", gate], cwd=temp, text=True, capture_output=True)
                    self.assertEqual(proc.returncode == 0, valid, proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
