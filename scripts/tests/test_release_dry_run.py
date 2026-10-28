"""The real release tail's dry-run path must stay local and mutation-free."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ReleaseDryRunTests(unittest.TestCase):
    def test_tail_only_dry_run_makes_no_network_or_repository_changes(self):
        with tempfile.TemporaryDirectory(prefix="wm-release-dry-run-") as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            archive = subprocess.run(
                ["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True
            )
            subprocess.run(
                ["tar", "-x", "-C", str(root)], input=archive.stdout, check=True
            )

            changed = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"], cwd=ROOT,
                text=True, capture_output=True, check=True,
            ).stdout.splitlines()
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT,
                text=True, capture_output=True, check=True,
            ).stdout.splitlines()
            for name in sorted(set(changed + untracked)):
                source = ROOT / name
                destination = root / name
                if source.is_file():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)

            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Dry Run Fixture"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            source_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
            ).stdout.strip()
            subprocess.run(["git", "remote", "add", "origin", "https://invalid.example/repo.git"], cwd=root, check=True)
            subprocess.run(["git", "update-ref", "refs/remotes/origin/main", source_head], cwd=root, check=True)

            fakebin = Path(temp) / "bin"
            fakebin.mkdir()
            real_git = shutil.which("git")
            assert real_git
            calls = Path(temp) / "side-effects.log"
            git_wrapper = fakebin / "git"
            git_wrapper.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in fetch|push|commit|tag)\n"
                f"  printf 'git %s\\n' \"$*\" >> {str(calls)!r}; exit 97 ;;\n"
                "esac\n"
                f"exec {real_git!r} \"$@\"\n",
                encoding="utf-8",
            )
            git_wrapper.chmod(0o755)
            for name in ("gh", "curl", "cargo", "jq"):
                stub = fakebin / name
                stub.write_text(
                    "#!/bin/sh\n"
                    f"printf '{name} %s\\n' \"$*\" >> {str(calls)!r}; exit 98\n",
                    encoding="utf-8",
                )
                stub.chmod(0o755)

            env = dict(os.environ, PATH=f"{fakebin}:{os.environ['PATH']}")
            proc = subprocess.run(
                ["bash", "scripts/release.sh", "10.6.1", "--tail-only", "--dry-run"],
                cwd=root, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + "\n" + proc.stdout)
            self.assertIn("no tag/run lookup, network request", proc.stdout)
            self.assertIn("docs/gen3/route-schema-manifest.json", proc.stdout)
            self.assertFalse(calls.exists(), calls.read_text() if calls.exists() else "")
            self.assertEqual(
                subprocess.run(["git", "status", "--porcelain"], cwd=root,
                               text=True, capture_output=True, check=True).stdout,
                "",
            )
            self.assertEqual(
                subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                               text=True, capture_output=True, check=True).stdout.strip(),
                source_head,
            )
            self.assertFalse((root / "docs/gen3/route-schema-manifest.json").exists())
            self.assertFalse((root / "release-health.json").exists())


if __name__ == "__main__":
    unittest.main()
