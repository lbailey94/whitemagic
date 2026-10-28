"""Tests for scripts/release_notes.py (no network, temp fixtures)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "release_notes.py"

CHANGELOG = """# Changelog

## [10.6.1] — 2026-10-27

### Changed
- Gen3 release note fixture.

## [9.3.4] — 2026-10-01

### Changed
- Gen2 release note fixture.

## [9.2.9] — 2026-09-30

### Fixed
- **A door that told two stories** — one coherent sentence.

### Changed
- **Installer** — single-profile wiring.

## [9.2.8] — 2026-09-24

### Added
- Old stuff that must not leak into 9.2.9 notes.
"""


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wm-release-notes-")
        self.addCleanup(self.tmp.cleanup)
        self.changelog = Path(self.tmp.name) / "CHANGELOG.md"
        self.changelog.write_text(CHANGELOG, encoding="utf-8")

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--changelog", str(self.changelog), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_renders_version_section_with_install_and_platforms(self):
        result = self.run_script("--version", "v9.2.9")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("# WhiteMagic 9.2.9", out)
        self.assertIn("### Fixed", out)
        self.assertIn("A door that told two stories", out)
        self.assertNotIn("Old stuff that must not leak", out, "other sections stay out")
        self.assertIn("install.sh | sh", out)
        self.assertIn("install-gated", out)
        self.assertIn("macOS arm64", out)
        self.assertIn("wm connect` previews", out)
        self.assertIn("wm connect --write", out)

    def test_gen3_release_notes_use_only_supported_commands_and_pin_install(self):
        result = self.run_script("--version", "v10.6.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("--version v10.6.1", out)
        self.assertIn("whitemagic-mcp@10.6.1", out)
        self.assertIn("cargo install whitemagic --version 10.6.1", out)
        self.assertIn("lbailey94/whitemagic:v10.6.1", out)
        self.assertNotIn("lbailey94/whitemagic:9", out)
        self.assertIn('wm --store "$HOME/.local/share/whitemagic/gen3" grimoire --plan', out)
        self.assertIn('wm --store "$HOME/.local/share/whitemagic/gen3" serve --profile cyberbrain', out)
        for unsupported in ("wm connect", "wm setup", "wm quickstart", "wm doctor", "--profile curated", "grimoire --write"):
            self.assertNotIn(unsupported, out)

    def test_gen2_release_notes_keep_connect_preview_then_write(self):
        result = self.run_script("--version", "v9.3.4")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("--version v9.3.4", out)
        self.assertLess(out.index("wm connect` previews"), out.index("wm connect --write`"))

    def test_missing_version_is_a_clean_error(self):
        result = self.run_script("--version", "9.9.9")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no [9.9.9] section", result.stderr)

    def test_writes_out_file(self):
        out = Path(self.tmp.name) / "notes.md"
        result = self.run_script("--version", "9.2.9", "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out.is_file())
        self.assertIn("# WhiteMagic 9.2.9", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
