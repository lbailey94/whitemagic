"""Regression tests for v22.0.0 release readiness fixes.

Tests verify that critical issues from RELEASE_READINESS_PLAN.md do not regress.
"""

import os
import sys

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
