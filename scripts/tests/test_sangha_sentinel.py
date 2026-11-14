"""Regression tests for Sangha claim states and Sentinel post deduplication."""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SANGHA_PATH = REPO_ROOT / "scripts" / "sangha.py"


def load_sangha_isolated(root: Path):
    """Load scripts/sangha.py bound to an isolated temporary Sangha root."""
    env_overrides = {
        "SANGHA_ROOT": str(root),
        "SANGHA_BRIDGE_URL": "http://127.0.0.1:1",
        "SANGHA_AGENT": "opencode",
        "SANGHA_CHECKOUTS": str(root / "checkouts.json"),
        "SANGHA_SENTINEL_STATE": str(root / "sentinel-last.json"),
        "SANGHA_PEERS": str(root / "peers.json"),
        "SANGHA_SYNCTHING_CONFIG": str(root / "no-syncthing.xml"),
        "SANGHA_WM_BIN": str(root / "no-wm-bin"),
    }
    previous = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    try:
        spec = importlib.util.spec_from_file_location("sangha_sentinel_under_test", SANGHA_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, previous
    except Exception:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        raise


def init_git_repo(root: Path, name: str = "repo-a") -> Path:
    repo = root / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "f.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


def expire_claim_post(post: Path) -> None:
    lines = []
    for line in post.read_text(encoding="utf-8").splitlines():
        if line.startswith("> Type:") and "Expires:" in line:
            parts = [p.strip() for p in line[2:].split("·") if "Expires" not in p]
            line = "> " + " · ".join(parts + ["Expires: 2020-01-01T00:00:00Z"])
        lines.append(line)
    post.write_text("\n".join(lines) + "\n", encoding="utf-8")


class SanghaSentinelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sangha-sentinel-")
        self.root = Path(self.temp.name)
        (self.root / "board").mkdir()
        (self.root / ".sangha" / "inbox").mkdir(parents=True)
        self.sangha, self.prev_env = load_sangha_isolated(self.root)

    def tearDown(self):
        for k, v in self.prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.temp.cleanup()

    def _run_sentinel(self, *, stale_min=30, post=False, json_out=True):
        buf = io.StringIO()
        args = argparse.Namespace(
            stale_min=stale_min,
            recent_hours=24,
            expire_window=15,
            json=json_out,
            post=post,
            author="sentinel",
        )
        with contextlib.redirect_stdout(buf):
            self.sangha.cmd_sentinel(args)
        return buf.getvalue()

    def test_released_claim_stays_released_after_ttl_passes(self):
        repo = init_git_repo(self.root)
        (repo / "f.txt").write_text("dirty\n", encoding="utf-8")
        (self.root / "checkouts.json").write_text(
            json.dumps([{"name": "repo-a", "path": str(repo)}]),
            encoding="utf-8",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            self.sangha.cmd_claim(argparse.Namespace(
                scope="repo-a", intent="test", ttl="2h", target="@all", author="opencode", body=None
            ))
            self.sangha.cmd_release(argparse.Namespace(item="repo-a", author="opencode"))

        claim_post = next((self.root / "board").glob("*-claim-repo-a-*.md"))
        expire_claim_post(claim_post)

        claims = self.sangha.all_claims()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["state"], "released")

        doc = json.loads(self._run_sentinel(stale_min=30, json_out=True))
        kinds = [f["kind"] for f in doc["findings"]]
        self.assertNotIn("expired-claim-dirty", kinds)

    def test_unreleased_expired_claim_over_dirty_tree_still_flagged(self):
        repo = init_git_repo(self.root)
        (repo / "f.txt").write_text("dirty\n", encoding="utf-8")
        (self.root / "checkouts.json").write_text(
            json.dumps([{"name": "repo-a", "path": str(repo)}]),
            encoding="utf-8",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            self.sangha.cmd_claim(argparse.Namespace(
                scope="repo-a", intent="unfinished", ttl="2h", target="@all", author="opencode", body=None
            ))

        claim_post = next((self.root / "board").glob("*-claim-repo-a-*.md"))
        expire_claim_post(claim_post)

        claims = self.sangha.all_claims()
        self.assertEqual(claims[0]["state"], "expired")

        doc = json.loads(self._run_sentinel(stale_min=30, json_out=True))
        kinds = [f["kind"] for f in doc["findings"]]
        self.assertIn("expired-claim-dirty", kinds)

    def test_sentinel_post_digest_ignores_age_ticks_for_unchanged_dirty_files(self):
        repo = init_git_repo(self.root)
        dirty = repo / "f.txt"
        dirty.write_text("dirty\n", encoding="utf-8")
        two_hours_ago = self.sangha.datetime.now(self.sangha.UTC).timestamp() - 2 * 3600
        os.utime(dirty, (two_hours_ago, two_hours_ago))
        (self.root / "checkouts.json").write_text(
            json.dumps([{"name": "repo-a", "path": str(repo)}]),
            encoding="utf-8",
        )

        self._run_sentinel(stale_min=30, post=True, json_out=False)
        posts_after_first = list((self.root / "board").glob("*sentinel*finding*.md"))
        self.assertEqual(len(posts_after_first), 1)

        # Age the same file by another hour: oldest_min increases, but file set is unchanged.
        three_hours_ago = two_hours_ago - 3600
        os.utime(dirty, (three_hours_ago, three_hours_ago))
        out = self._run_sentinel(stale_min=30, post=True, json_out=False)
        self.assertIn("not re-posting", out)
        self.assertEqual(len(list((self.root / "board").glob("*sentinel*finding*.md"))), 1)

        # Adding a second dirty file must change the digest and trigger a new post.
        second = repo / "g.txt"
        second.write_text("another\n", encoding="utf-8")
        os.utime(second, (three_hours_ago, three_hours_ago))
        self._run_sentinel(stale_min=30, post=True, json_out=False)
        self.assertEqual(len(list((self.root / "board").glob("*sentinel*finding*.md"))), 2)

    def test_cli_ignores_non_python_sangha_shim_in_sangha_root(self):
        (self.root / "sangha.py").write_text("#!/usr/bin/env bash\necho shim\n", encoding="utf-8")
        env = dict(os.environ)
        env["SANGHA_ROOT"] = str(self.root)
        proc = subprocess.run(
            [sys.executable, str(SANGHA_PATH), "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
