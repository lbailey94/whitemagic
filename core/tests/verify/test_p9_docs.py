"""P9.1-P9.4 — Documentation, public profiles, compatibility, and guides tests.

Tests that:
- Documentation hierarchy is complete (README, PROJECT_STATE, architecture/, guides/, reference/)
- Public profiles are defined (Core, MCP, Local AI, Research, Violet)
- Compatibility policy covers stable list, semver, deprecation, MCP registry
- Contributor and model guides exist and contain required sections
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
VERSION = (REPO_ROOT / "VERSION").read_text().strip()


class TestDocumentationHierarchy:
    """P9.1 — Documentation hierarchy is complete."""

    def test_readme_exists(self):
        assert (REPO_ROOT / "README.md").exists()

    def test_project_state_exists(self):
        assert (DOCS_ROOT / "PROJECT_STATE.md").exists()

    def test_architecture_dir_exists(self):
        assert (DOCS_ROOT / "architecture").is_dir()

    def test_guides_dir_exists(self):
        assert (DOCS_ROOT / "guides").is_dir()

    def test_reference_dir_exists(self):
        assert (DOCS_ROOT / "reference").is_dir()

    def test_readme_has_correct_version(self):
        content = (REPO_ROOT / "README.md").read_text()
        assert VERSION in content

    def test_readme_has_correct_tool_count(self):
        content = (REPO_ROOT / "README.md").read_text()
        assert "860" in content

    def test_project_state_has_generated_facts(self):
        content = (DOCS_ROOT / "PROJECT_STATE.md").read_text()
        assert "GENERATED_FACTS_START" in content
        assert "GENERATED_FACTS_END" in content


class TestPublicProfiles:
    """P9.2 — Public profiles are defined."""

    def test_profiles_doc_exists(self):
        assert (DOCS_ROOT / "PUBLIC_PROFILES.md").exists()

    def test_profiles_doc_has_all_five_profiles(self):
        content = (DOCS_ROOT / "PUBLIC_PROFILES.md").read_text()
        for profile in ["Core", "MCP", "Local AI", "Research", "Violet"]:
            assert profile in content, f"Profile '{profile}' not found in PUBLIC_PROFILES.md"

    def test_profiles_doc_has_install_commands(self):
        content = (DOCS_ROOT / "PUBLIC_PROFILES.md").read_text()
        assert "pip install whitemagic" in content

    def test_profiles_doc_has_security_boundaries(self):
        content = (DOCS_ROOT / "PUBLIC_PROFILES.md").read_text()
        assert "Dharma" in content


class TestCompatibilityPolicy:
    """P9.3 — Compatibility policy is defined."""

    def test_compatibility_doc_exists(self):
        assert (DOCS_ROOT / "COMPATIBILITY_POLICY.md").exists()

    def test_semver_section(self):
        content = (DOCS_ROOT / "COMPATIBILITY_POLICY.md").read_text()
        assert "MAJOR" in content
        assert "MINOR" in content
        assert "PATCH" in content

    def test_stable_tool_count(self):
        content = (DOCS_ROOT / "COMPATIBILITY_POLICY.md").read_text()
        assert "57" in content
        assert "28 Gana" in content

    def test_deprecation_policy(self):
        content = (DOCS_ROOT / "COMPATIBILITY_POLICY.md").read_text()
        assert "Deprecated" in content or "deprecated" in content
        assert "insight" in content  # deprecated galaxy alias

    def test_mcp_registry_checklist(self):
        content = (DOCS_ROOT / "COMPATIBILITY_POLICY.md").read_text()
        assert "MCP Registry" in content or "registry" in content.lower()
        assert "readOnlyHint" in content

    def test_platform_matrix(self):
        content = (DOCS_ROOT / "COMPATIBILITY_POLICY.md").read_text()
        assert "Linux" in content
        assert "macOS" in content
        assert "Windows" in content


class TestContributorAndModelGuides:
    """P9.4 — Contributor and model guides exist."""

    def test_contributing_guide_exists(self):
        assert (DOCS_ROOT / "CONTRIBUTING.md").exists()

    def test_contributing_has_ci_lanes(self):
        content = (DOCS_ROOT / "CONTRIBUTING.md").read_text()
        assert "Lane A" in content
        assert "Lane B" in content

    def test_contributing_has_test_tiers(self):
        content = (DOCS_ROOT / "CONTRIBUTING.md").read_text()
        assert "Unit" in content
        assert "Integration" in content

    def test_contributing_has_add_tool_steps(self):
        content = (DOCS_ROOT / "CONTRIBUTING.md").read_text()
        assert "ToolDefinition" in content
        assert "prat_mappings" in content

    def test_model_guide_exists(self):
        assert (DOCS_ROOT / "MODEL_GUIDE.md").exists()

    def test_model_guide_has_quick_start(self):
        content = (DOCS_ROOT / "MODEL_GUIDE.md").read_text()
        assert "run_mcp_lean" in content

    def test_model_guide_has_safety_classification(self):
        content = (DOCS_ROOT / "MODEL_GUIDE.md").read_text()
        assert "READ" in content
        assert "WRITE" in content
        assert "DELETE" in content

    def test_model_guide_has_stability_tiers(self):
        content = (DOCS_ROOT / "MODEL_GUIDE.md").read_text()
        assert "STABLE" in content
        assert "OPTIONAL" in content
        assert "EXPERIMENTAL" in content
