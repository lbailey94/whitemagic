"""Regression tests for v22.0.0 release readiness fixes.

Tests verify that critical issues from RELEASE_READINESS_PLAN.md do not regress.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Get repository root (go up from core/tests/unit/regression/ to repo root)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class TestC1_RunMcpShim:
    """C1: Verify whitemagic.run_mcp shim exists and re-exports correctly."""

    def test_shim_module_exists(self):
        """The shim module should be importable."""
        from whitemagic import run_mcp  # noqa: F401

    def test_shim_reexports_main(self):
        """The shim should re-export main() from run_mcp_lean."""
        from whitemagic.run_mcp import main
        from whitemagic.run_mcp_lean import main as main_lean

        assert main is main_lean

    def test_shim_reexports_server(self):
        """The shim should re-export server from run_mcp_lean."""
        from whitemagic.run_mcp import server
        from whitemagic.run_mcp_lean import server as server_lean

        assert server is server_lean


class TestC2_CollectionErrors:
    """C2: Verify collection errors are fixed."""

    def test_continuity_seen_registry_stub(self):
        """continuity.py should have get_seen_registry stub."""
        from whitemagic.core.continuity import get_seen_registry

        registry = get_seen_registry()
        assert hasattr(registry, "mark_seen")

    def test_event_type_values_exist(self):
        """EventType enum should have all required values for voice templates."""
        from whitemagic.core.resonance._consolidated import EventType

        required_attrs = [
            "MEMORY_CREATED",
            "MEMORY_RECALLED",
            "PATTERN_DETECTED",
            "ORACLE_CAST",
            "SYSTEM_STARTED",
            "CLONE_SEARCH_COMPLETE",
            "PATTERN_CONFIRMED",
            "TRUTH_SPOKEN",
            "STORY_TOLD",
            "VOICE_EXPRESSED",
        ]
        for attr in required_attrs:
            assert hasattr(EventType, attr), f"EventType missing {attr}"


class TestC3_LicenseFix:
    """C3: Verify license is MIT, not Apache."""

    def test_root_license_exists(self):
        """Root LICENSE file should exist."""
        license_path = os.path.join(REPO_ROOT, "LICENSE")
        assert os.path.exists(license_path)

    def test_root_license_is_mit(self):
        """Root LICENSE should be MIT."""
        license_path = os.path.join(REPO_ROOT, "LICENSE")
        with open(license_path) as f:
            content = f.read()
        assert "MIT" in content
        assert "Apache" not in content

    def test_core_license_deleted(self):
        """core/LICENSE should not exist (was Apache)."""
        core_license_path = os.path.join(REPO_ROOT, "core", "LICENSE")
        assert not os.path.exists(core_license_path)

    def test_core_readme_license_text(self):
        """core/README.md should reference MIT, not Apache."""
        readme_path = os.path.join(REPO_ROOT, "core", "README.md")
        with open(readme_path) as f:
            content = f.read()
        assert "MIT" in content
        assert "Apache" not in content


class TestH1_VersionDrift:
    """H1: Verify version consistency across docs."""

    def test_version_file_exists(self):
        """core/VERSION should exist."""
        version_path = os.path.join(REPO_ROOT, "core", "VERSION")
        assert os.path.exists(version_path)

    def test_version_file_content(self):
        """core/VERSION should contain 22.0.0."""
        version_path = os.path.join(REPO_ROOT, "core", "VERSION")
        with open(version_path) as f:
            content = f.read().strip()
        assert content == "22.0.0"

    def test_pyproject_version(self):
        """core/pyproject.toml should have version 22.0.0."""
        pyproject_path = os.path.join(REPO_ROOT, "core", "pyproject.toml")
        with open(pyproject_path) as f:
            content = f.read()
        assert 'version = "22.0.0"' in content

    def test_core_readme_version(self):
        """core/README.md should reference v22.0.0."""
        readme_path = os.path.join(REPO_ROOT, "core", "README.md")
        with open(readme_path) as f:
            content = f.read()
        assert "v22.0.0" in content
        assert "v21.0.0" not in content

    def test_agent_json_version(self):
        """core/.well-known/agent.json should have version 22.0.0."""
        agent_path = os.path.join(REPO_ROOT, "core", ".well-known", "agent.json")
        with open(agent_path) as f:
            content = f.read()
        assert '"version": "22.0.0"' in content
        assert '"version": "21.0.0"' not in content

    def test_cargo_toml_version(self):
        """core/whitemagic-rust/Cargo.toml should have version 22.0.0."""
        cargo_path = os.path.join(REPO_ROOT, "core", "whitemagic-rust", "Cargo.toml")
        with open(cargo_path) as f:
            content = f.read()
        assert 'version = "22.0.0"' in content
        assert 'version = "21.0.0"' not in content

    def test_polyglot_status_version(self):
        """polyglot/STATUS.md should reference v22.0.0."""
        status_path = os.path.join(REPO_ROOT, "polyglot", "STATUS.md")
        with open(status_path) as f:
            content = f.read()
        assert "v22.0.0" in content
        assert "v21.0.0" not in content


class TestH6_NoRootRequirements:
    """H6: Verify root requirements.txt is deleted."""

    def test_root_requirements_deleted(self):
        """Root requirements.txt should not exist."""
        requirements_path = os.path.join(REPO_ROOT, "requirements.txt")
        assert not os.path.exists(requirements_path)


class TestH9_ArchiveDeleted:
    """H9: Verify core/whitemagic/archive/ is deleted."""

    def test_archive_directory_deleted(self):
        """core/whitemagic/archive/ should not exist."""
        archive_path = os.path.join(REPO_ROOT, "core", "whitemagic", "archive")
        assert not os.path.exists(archive_path)


class TestH5_CIConfiguration:
    """H5: Verify .github/workflows/ci.yml is valid YAML with expected jobs,
    and that B603 has been removed from bandit's skip list.
    """

    def test_ci_yaml_parses(self):
        """ci.yml must be parseable YAML."""
        import yaml
        ci_path = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
        with open(ci_path) as f:
            doc = yaml.safe_load(f)
        assert doc is not None
        assert "jobs" in doc

    def test_ci_has_core_and_lint_jobs(self):
        """ci.yml must define the canonical job set."""
        import yaml
        ci_path = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
        with open(ci_path) as f:
            doc = yaml.safe_load(f)
        jobs = set(doc["jobs"].keys())
        # Must at minimum include:
        assert {"core", "lint", "security", "packaging"}.issubset(jobs), jobs

    def test_bandit_b603_not_skipped(self):
        """B603 (subprocess without shell=False) must not be in bandit skip list."""
        ci_path = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
        with open(ci_path) as f:
            content = f.read()
        # Look for the --skip line and ensure B603 isn't in it.
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("--skip") or "bandit" in stripped.lower() and "--skip" in stripped:
                # The skip directive itself must not mention B603.
                # Comments about B603 are fine (e.g., "# B603: audited").
                if line.lstrip().startswith("#"):
                    continue
                assert "B603" not in line, f"B603 must not be in bandit skip list: {line!r}"


class TestM6_XRPLTipOptIn:
    """M6: Verify XRPL tip address has no hardcoded maintainer default."""

    def test_no_hardcoded_maintainer_address_in_source(self):
        """No .py file outside tests/ may hardcode the upstream maintainer XRP address.

        The address may appear as a commented example or in gratitude-config
        error messages, but never as a runtime default.
        """
        MAINTAINER_ADDR = "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy"
        pkg_root = os.path.join(REPO_ROOT, "core", "whitemagic")
        offenders = []
        for root, _, files in os.walk(pkg_root):
            if "/tests/" in root or "/_archived/" in root or "/archive/" in root:
                continue
            for name in files:
                if not name.endswith(".py"):
                    continue
                p = os.path.join(root, name)
                with open(p) as f:
                    for lineno, line in enumerate(f, 1):
                        if MAINTAINER_ADDR in line:
                            # Allow clearly-labeled advisory constants.
                            if "_UPSTREAM_MAINTAINER" in line or "_EXAMPLE_ADDR" in line:
                                continue
                            offenders.append(f"{p}:{lineno}: {line.rstrip()}")
        assert not offenders, "Hardcoded maintainer address found:\n" + "\n".join(offenders)

    def test_wallet_manager_disabled_without_env(self):
        """WalletManager must be disabled and have no fallback when WM_XRP_ADDRESS is unset."""
        import importlib
        saved = os.environ.pop("WM_XRP_ADDRESS", None)
        try:
            # Re-import to pick up env change
            from whitemagic.core.economy import wallet_manager as wm_mod
            importlib.reload(wm_mod)
            w = wm_mod.WalletManager()
            assert w.enabled is False, "Wallet must be disabled without WM_XRP_ADDRESS"
            assert w.public_address == "", f"Wallet address must be empty, got {w.public_address!r}"
        finally:
            if saved is not None:
                os.environ["WM_XRP_ADDRESS"] = saved


class TestM7_SecurityContact:
    """M7: Verify security contact is consistent and canonical."""

    def test_security_md_has_correct_versions(self):
        """SECURITY.md should list 22.x as supported, not 21.x."""
        security_path = os.path.join(REPO_ROOT, "SECURITY.md")
        with open(security_path) as f:
            content = f.read()
        assert "| 22.x    | :white_check_mark: |" in content or "22.x" in content
        # Should NOT say 21.x is current supported
        assert "| 21.x    | :white_check_mark: |" not in content

    def test_security_md_prefers_github_advisory(self):
        """SECURITY.md should list GitHub Security Advisory as preferred contact."""
        security_path = os.path.join(REPO_ROOT, "SECURITY.md")
        with open(security_path) as f:
            content = f.read()
        # Should mention GitHub Security Advisory and mark it preferred
        assert "GitHub Security Advisory" in content
        # Should have clear instructions NOT to file public issues
        assert "Do NOT file a public issue" in content


class TestM11_CodeQualityAttribution:
    """M11: Verify no misleading external attribution in code quality review."""

    def test_no_deepmind_or_antigravity_attribution(self):
        """CODE_QUALITY_REVIEW*.md must not claim Google DeepMind or Antigravity AI authorship."""
        review_path = os.path.join(REPO_ROOT, "docs", "CODE_QUALITY_REVIEW_2026-04-15.md")
        if not os.path.exists(review_path):
            pytest.skip("Code quality review file not found")
        with open(review_path) as f:
            content = f.read()
        # Must not claim Google DeepMind endorsement/involvement
        assert "Google DeepMind" not in content, "Misleading attribution to Google DeepMind"
        assert "Antigravity AI" not in content, "Misleading attribution to Antigravity AI"


class TestL2_CitationCff:
    """L2: Verify CITATION.cff exists and is valid."""

    def test_citation_cff_exists(self):
        """CITATION.cff should exist at repo root."""
        cff_path = os.path.join(REPO_ROOT, "CITATION.cff")
        assert os.path.exists(cff_path)

    def test_citation_cff_valid_yaml(self):
        """CITATION.cff must be valid YAML with required fields."""
        import yaml
        cff_path = os.path.join(REPO_ROOT, "CITATION.cff")
        with open(cff_path) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert data.get("title") == "WhiteMagic"
        assert data.get("version") == "22.0.0"
        assert data.get("license") == "MIT"


class TestL3_FundingYml:
    """L3: Verify .github/FUNDING.yml exists."""

    def test_funding_yml_exists(self):
        """.github/FUNDING.yml should exist."""
        funding_path = os.path.join(REPO_ROOT, ".github", "FUNDING.yml")
        assert os.path.exists(funding_path)

    def test_funding_yml_valid_yaml(self):
        """FUNDING.yml must be valid YAML."""
        import yaml
        funding_path = os.path.join(REPO_ROOT, ".github", "FUNDING.yml")
        with open(funding_path) as f:
            data = yaml.safe_load(f)
        assert data is not None
        # Should define either github sponsors or custom funding
        assert "github" in data or "custom" in data


class TestL8_LlmsTxt:
    """L8: Verify llms.txt exists per llmstxt.org convention."""

    def test_llms_txt_exists(self):
        """llms.txt should exist at repo root."""
        llms_path = os.path.join(REPO_ROOT, "llms.txt")
        assert os.path.exists(llms_path)

    def test_llms_txt_has_key_sections(self):
        """llms.txt should have project overview and key documentation links."""
        llms_path = os.path.join(REPO_ROOT, "llms.txt")
        with open(llms_path) as f:
            content = f.read()
        assert "WhiteMagic" in content
        assert "MCP" in content
        assert "AI_PRIMARY.md" in content or "QUICKSTART.md" in content


class TestH10_RustLicenseAndFeatures:
    """H10: Verify Rust crate has correct license and default features."""

    def test_cargo_toml_has_mit_license(self):
        """Cargo.toml should have MIT license."""
        cargo_path = os.path.join(REPO_ROOT, "core", "whitemagic-rust", "Cargo.toml")
        with open(cargo_path) as f:
            content = f.read()
        assert 'license = "MIT"' in content

    def test_cargo_toml_iceoryx2_not_default(self):
        """iceoryx2 should not be in default features."""
        cargo_path = os.path.join(REPO_ROOT, "core", "whitemagic-rust", "Cargo.toml")
        with open(cargo_path) as f:
            content = f.read()
        assert 'iceoryx2 = [' in content or "iceoryx2 = {" in content
        assert 'default = [' in content
        for line in content.split("\n"):
            if line.strip().startswith("default ="):
                assert "iceoryx2" not in line
