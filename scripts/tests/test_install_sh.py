"""Black-box regression tests for scripts/install.sh shell-profile wiring.

Background (2026-09-15 external reliability audit, P0): on reinstall, when
``~/.profile`` already exported ``~/.local/bin``, ``path_fixed`` stayed 0 and
the installer's ``else`` branch rewrote ``~/.profile`` with ``>`` — destroying
every unrelated line in the file. The audit's sentinel-lines reproduction is
codified here as a permanent test.

The tests run the real script in a temp HOME with a stub ``curl`` on PATH, so
no network is used and the exact production logic is exercised.
"""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INSTALL_SH = os.path.join(REPO_ROOT, "scripts", "install.sh")

FAKE_BINARY = b"#!/bin/sh\necho fake wm\n"
FAKE_BINARY_SHA256 = hashlib.sha256(FAKE_BINARY).hexdigest()

STUB_CURL = """#!/bin/sh
# Stub curl for installer tests: serves a fake release over the same URL
# shapes install.sh uses (latest-release API, sha256 probe, downloads).
url=""
out=""
code_mode=0
while [ $# -gt 0 ]; do
    case "$1" in
        -o) out="$2"; shift 2 ;;
        -w) code_mode=1; shift 2 ;;
        -*) shift ;;
        *) url="$1"; shift ;;
    esac
done
case "$url" in
    *api.github.com*)
        printf '{"tag_name": "v9.1.6"}'
        ;;
    *.sha256*)
        if [ "$code_mode" = "1" ]; then
            printf '200'
        else
            printf '%s  wm\\n' "@@DIGEST@@" > "$out"
        fi
        ;;
    *wm-linux-x86_64-musl*)
        cp "$STUB_BINARY" "$out"
        ;;
    *)
        printf '200'
        ;;
esac
"""


class InstallScriptProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wm-install-test-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.shim_dir = os.path.join(self.tmp, "shim")
        os.makedirs(self.shim_dir)
        self.stub_binary = os.path.join(self.tmp, "fake-wm")
        with open(self.stub_binary, "wb") as fh:
            fh.write(FAKE_BINARY)
        curl_path = os.path.join(self.shim_dir, "curl")
        with open(curl_path, "w", encoding="utf-8") as fh:
            fh.write(STUB_CURL.replace("@@DIGEST@@", FAKE_BINARY_SHA256))
        os.chmod(curl_path, os.stat(curl_path).st_mode | stat.S_IEXEC)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_installer(self, *extra_args, env_extra=None):
        env = dict(os.environ)
        env["HOME"] = self.home
        env["STUB_BINARY"] = self.stub_binary
        # The host's store location must never be touched by a test run.
        env.pop("XDG_DATA_HOME", None)
        env.pop("WM_INSTALL_REF", None)
        if env_extra:
            env.update(env_extra)
        # PATH must not already contain the install dir, so the wiring branch
        # under test is actually reached.
        env["PATH"] = self.shim_dir + ":/usr/bin:/bin"
        return subprocess.run(
            [
                "sh",
                INSTALL_SH,
                "--version",
                "v9.1.6",
                "--target",
                "x86_64-unknown-linux-musl",
                *extra_args,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def expected_line(self):
        return f'export PATH="{self.home}/.local/bin:$PATH"'

    def default_store_root(self):
        return os.path.join(self.home, ".local", "share", "whitemagic")

    def read_marker(self, store_root=None):
        path = os.path.join(store_root or self.default_store_root(), "install_channel")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def read_profile(self):
        path = os.path.join(self.home, ".profile")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_reinstall_preserves_existing_profile_lines(self):
        # The exact audit reproduction: sentinel + the WM path line already
        # present, then install again. The sentinel must survive.
        profile = (
            "export SENTINEL=keepme\n"
            "# Added by the WhiteMagic installer\n"
            f"{self.expected_line()}\n"
        )
        with open(os.path.join(self.home, ".profile"), "w", encoding="utf-8") as fh:
            fh.write(profile)

        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        after_first = self.read_profile()
        self.assertIn("export SENTINEL=keepme", after_first)
        self.assertEqual(after_first.count(self.expected_line()), 1)

        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        after_second = self.read_profile()
        self.assertEqual(after_first, after_second, "reinstall must not modify the profile")

    def test_append_is_idempotent_and_preserves_sentinels(self):
        with open(os.path.join(self.home, ".profile"), "w", encoding="utf-8") as fh:
            fh.write("export SENTINEL=keepme\n")

        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        after_first = self.read_profile()
        self.assertIn("export SENTINEL=keepme", after_first)
        self.assertEqual(after_first.count(self.expected_line()), 1)

        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        after_second = self.read_profile()
        self.assertEqual(after_first, after_second, "second install must be a no-op")

    def test_commented_mention_does_not_count_as_wired(self):
        # A stale/commented mention must not suppress the working export line
        # (2026-09-15 review: `grep -q` matched any mention).
        with open(os.path.join(self.home, ".profile"), "w", encoding="utf-8") as fh:
            fh.write(f'# export PATH="{self.home}/.local/bin:$PATH"  # old note\n')
            fh.write("export SENTINEL=keepme\n")

        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        profile = self.read_profile()
        self.assertIn("export SENTINEL=keepme", profile)
        lines = [line for line in profile.splitlines() if line == self.expected_line()]
        self.assertEqual(lines, [self.expected_line()], "working line appended exactly once")

    def test_creates_profile_when_none_exists(self):
        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        profile = self.read_profile()
        self.assertIsNotNone(profile, "installer should create ~/.profile")
        self.assertIn(self.expected_line(), profile)

        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(profile, self.read_profile())

    def test_binary_installed_and_executable(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = os.path.join(self.home, ".local", "bin", "wm")
        self.assertTrue(os.path.exists(installed))
        self.assertTrue(os.stat(installed).st_mode & stat.S_IEXEC)

    # ── Local install-funnel marker (scope 1) ──────────────────────────

    def test_installer_writes_local_channel_marker(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_marker(), "install_sh\n")
        self.assertFalse(
            os.path.exists(os.path.join(self.default_store_root(), "lmdb")),
            "the marker is best-effort attribution — it must not create lmdb/",
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(self.default_store_root(), ".install_channel.tmp")
            ),
            "atomic write must not leave the tmp file behind",
        )

    def test_installer_records_sanitized_ref(self):
        result = self.run_installer("--ref", "Hero-Ref_2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_marker(), "install_sh:hero-ref_2\n")

    def test_installer_sanitizes_unsafe_ref(self):
        # Site middleware rule: lowercase, [a-z0-9_-] only, 24 chars max.
        result = self.run_installer("--ref", "Bad Ref!!<script>")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_marker(), "install_sh:badrefscript\n")

        result = self.run_installer("--ref", "A" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_marker(), "install_sh:" + "a" * 24 + "\n")

    def test_installer_honors_wm_install_ref(self):
        result = self.run_installer(env_extra={"WM_INSTALL_REF": "Newsletter"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_marker(), "install_sh:newsletter\n")

    def test_installer_respects_xdg_data_home(self):
        xdg = os.path.join(self.tmp, "xdg-data")
        result = self.run_installer(env_extra={"XDG_DATA_HOME": xdg})
        self.assertEqual(result.returncode, 0, result.stderr)
        marker = self.read_marker(os.path.join(xdg, "whitemagic"))
        self.assertEqual(marker, "install_sh\n")
        self.assertIsNone(
            self.read_marker(),
            "XDG_DATA_HOME must win over the ~/.local/share default",
        )

    def test_reinstall_updates_marker_atomically(self):
        first = self.run_installer("--ref", "one")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.read_marker(), "install_sh:one\n")

        second = self.run_installer("--ref", "two")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.read_marker(), "install_sh:two\n")

        third = self.run_installer()
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertEqual(self.read_marker(), "install_sh\n", "reinstall without a ref clears it")
        self.assertFalse(
            os.path.exists(
                os.path.join(self.default_store_root(), ".install_channel.tmp")
            )
        )


if __name__ == "__main__":
    unittest.main()
