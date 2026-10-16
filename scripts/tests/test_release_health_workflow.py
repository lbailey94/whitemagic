"""Offline regression fixtures for release-health trust and checkout ordering."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/release-health.yml"


class ReleaseHealthWorkflowTests(unittest.TestCase):
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

    def test_final_gate_binds_each_certification_to_verified_manifest(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn('.install_certification.npm.bound_manifest_sha256 == .registries["github-release"].manifest_sha256', text)
        self.assertIn('.install_certification.docker.bound_manifest_sha256 == .registries["github-release"].manifest_sha256', text)

    def test_github_asset_identity_metadata_is_required(self) -> None:
        code = (ROOT / "scripts/release_health.py").read_text()
        self.assertIn("GitHub asset size missing or invalid", code)
        self.assertIn("GitHub asset digest missing or unsupported", code)


if __name__ == "__main__":
    unittest.main()
