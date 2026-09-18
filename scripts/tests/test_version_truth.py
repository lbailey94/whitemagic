#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import version_truth as vt  # noqa: E402


def make_tree(version: str = "9.1.4") -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel in vt.SURFACES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel == "Cargo.toml":
            path.write_text(
                f'[workspace]\nversion = "{version}"\n'
                f'wm-core = {{ version = "{version}", path = "crates/wm-core" }}\n',
                encoding="utf-8",
            )
        elif rel.endswith(".json"):
            path.write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")
        elif rel == "CITATION.cff":
            path.write_text(f"version: {version}\n", encoding="utf-8")
        elif rel == "scripts/install.sh":
            path.write_text(f"# install: sh -s -- --version v{version}\n", encoding="utf-8")
        elif rel == "PRIVACY_POLICY.md":
            path.write_text(f"# Privacy\n\n**Version**: {version}\n", encoding="utf-8")
        elif rel == "SECURITY.md":
            path.write_text(
                f"> the fleet runs {version} (the pinned 9.0.0 runtime was removed)\n",
                encoding="utf-8",
            )
        else:
            path.write_text(f"# doc\nwm --version  # wm {version}\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [{version}] — 2026-09-01\n",
        encoding="utf-8",
    )
    return tmp, root


class VersionTruthTest(unittest.TestCase):
    def test_workspace_version_reads_cargo(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            self.assertEqual(vt.workspace_version(root), "9.1.4")

    def test_check_passes_when_consistent(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            self.assertEqual(vt.check(root, None), 0)

    def test_check_reports_drift(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "README.md").write_text("# wm 9.1.3\n", encoding="utf-8")
            self.assertEqual(vt.check(root, None), 1)

    def test_check_honors_expected_version(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            self.assertEqual(vt.check(root, "9.1.5"), 1)
            self.assertEqual(vt.check(root, "9.1.4"), 0)

    def test_set_rewrites_every_surface(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            self.assertEqual(vt.set_version(root, "9.1.5", dry_run=False), 0)
            for rel in vt.SURFACES:
                text = (root / rel).read_text(encoding="utf-8")
                found = set(
                    vt.versions_in(text, frozenset(vt.EXEMPT.get(rel, set())))
                )
                self.assertEqual(found, {"9.1.5"}, f"{rel} not fully bumped: {found}")
            # v-prefixed references keep their prefix.
            self.assertIn("v9.1.5", (root / "scripts/install.sh").read_text())
            # Idempotent.
            self.assertEqual(vt.set_version(root, "9.1.5", dry_run=False), 0)
            # The ceremony step finalizes the changelog (never a version
            # surface — historical strings are records, not truth).
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n## [9.1.5] — 2026-09-01\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.check(root, None), 0)

    def test_historical_versions_are_exempt(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            security = (root / "SECURITY.md").read_text(encoding="utf-8")
            self.assertIn("9.0.0", security)
            # Not drift, and not rewritten.
            self.assertEqual(vt.check(root, None), 0)
            self.assertEqual(vt.set_version(root, "9.1.5", dry_run=False), 0)
            self.assertIn("9.0.0", (root / "SECURITY.md").read_text(encoding="utf-8"))

    def test_set_dry_run_writes_nothing(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            before = (root / "README.md").read_text(encoding="utf-8")
            self.assertEqual(vt.set_version(root, "9.1.5", dry_run=True), 0)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), before)
            self.assertEqual(vt.check(root, None), 0)

    def test_missing_surface_is_an_error(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "skill.md").unlink()
            with self.assertRaises(SystemExit) as ctx:
                vt.scan(root)
            self.assertEqual(ctx.exception.code, 2)

    def test_rejects_non_semver(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            with self.assertRaises(SystemExit):
                vt.set_version(root, "banana", dry_run=False)

    def test_ceremony_flags_unreleased_target(self) -> None:
        # The v9.1.5 tag shipped with `## [Unreleased] — 9.1.5 (in progress)`.
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased] — 9.1.4 (in progress)\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.check(root, None), 1)

    def test_ceremony_requires_dated_release_section(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n## [9.1.4]\n", encoding="utf-8"
            )
            self.assertEqual(vt.check(root, None), 1)
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n## [9.1.4] — 2026-09-01\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.check(root, None), 0)

    def test_ceremony_ignores_unreleased_other_versions(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased] — 9.1.5 (in progress)\n\n"
                "## [9.1.4] — 2026-09-01\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.check(root, None), 0)

    def test_ceremony_missing_changelog_is_drift(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").unlink()
            self.assertEqual(vt.check(root, None), 1)

    def test_open_changelog_dates_the_unreleased_heading(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased] — 9.1.5 in progress (2026-09-01)\n"
                "\n### Stuff\n\n## [9.1.4] — 2026-09-01\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.open_changelog(root, "9.1.5", dry_run=False), 0)
            text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertIn("## [9.1.5] — ", text)
            self.assertNotIn("[Unreleased]", text)
            self.assertEqual(vt.check(root, None), 0)
            # Idempotent once the dated section exists.
            self.assertEqual(vt.open_changelog(root, "9.1.5", dry_run=False), 0)

    def test_open_changelog_preserves_theme_text(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased] — 9.1.5 in progress (2026-09-01)"
                " (themes, kept)\n",
                encoding="utf-8",
            )
            self.assertEqual(vt.open_changelog(root, "9.1.5", dry_run=False), 0)
            self.assertIn(
                "(themes, kept)", (root / "CHANGELOG.md").read_text(encoding="utf-8")
            )

    def test_open_changelog_dry_run_writes_nothing(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            before = (root / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertEqual(vt.open_changelog(root, "9.1.5", dry_run=True), 0)
            self.assertEqual(
                (root / "CHANGELOG.md").read_text(encoding="utf-8"), before
            )

    def test_open_changelog_missing_unreleased_is_error(self) -> None:
        tmp, root = make_tree("9.1.4")
        with tmp:
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [9.1.4] — 2026-09-01\n", encoding="utf-8"
            )
            self.assertEqual(vt.open_changelog(root, "9.1.5", dry_run=False), 1)


if __name__ == "__main__":
    unittest.main()
