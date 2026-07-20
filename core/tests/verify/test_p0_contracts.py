"""
P0 Contract Test Suite

These tests validate the core WhiteMagic contracts that must NEVER be broken.
They are designed to:
- Run on every commit
- Never be skipped (no @pytest.mark.skip, no skipIf)
- Execute quickly (< 30 seconds total)
- Block CI if any fail

Failure of any P0 test indicates a fundamental contract violation that must be
fixed immediately before merging.
"""

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

# =============================================================================
# P0-001: Tool Registry Contract
# =============================================================================


class TestToolRegistryContract:
    """P0: Tool registry must maintain internal consistency."""

    def test_all_dispatched_tools_have_registry_definitions(self):
        """Every tool in DISPATCH_TABLE must have a ToolDefinition in registry."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        from whitemagic.tools.registry import get_tool

        missing_definitions = []
        for tool_name in DISPATCH_TABLE.keys():
            tool_def = get_tool(tool_name)
            if tool_def is None:
                missing_definitions.append(tool_name)

        if missing_definitions:
            pytest.fail(
                f"Tools in DISPATCH_TABLE missing registry definitions: "
                f"{missing_definitions[:10]}{'...' if len(missing_definitions) > 10 else ''}"
            )

    def test_all_registry_tools_have_dispatch_handlers(self):
        """Every ToolDefinition in registry must have a dispatch handler.

        Note: Gana tools (gana_*) are nested organizational categories and are
        accessed through parent tools, not directly dispatched. They are exempt
        from this requirement.
        """
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        from whitemagic.tools.registry import get_all_tools

        all_tools = get_all_tools()
        missing_handlers = []
        for tool in all_tools:
            # Skip Gana tools - they are nested categories, not directly dispatched
            if tool.name.startswith("gana_"):
                continue
            if tool.name not in DISPATCH_TABLE:
                missing_handlers.append(tool.name)

        if missing_handlers:
            pytest.fail(
                f"Tools in registry missing dispatch handlers: "
                f"{missing_handlers[:10]}{'...' if len(missing_handlers) > 10 else ''}"
            )

    def test_no_duplicate_tool_names_in_registry(self):
        """Tool names must be unique in the registry."""
        from whitemagic.tools.registry import get_all_tools

        all_tools = get_all_tools()
        names = [t.name for t in all_tools]
        duplicates = {name for name in names if names.count(name) > 1}

        if duplicates:
            pytest.fail(f"Duplicate tool names in registry: {duplicates}")

    def test_tool_definitions_have_required_fields(self):
        """All tools must have name, description, and category."""
        from whitemagic.tools.registry import get_all_tools

        all_tools = get_all_tools()
        incomplete = []

        for tool in all_tools:
            missing = []
            if not tool.name:
                missing.append("name")
            if not tool.description:
                missing.append("description")
            if not tool.category:
                missing.append("category")
            if missing:
                incomplete.append((tool.name or "<unnamed>", missing))

        if incomplete:
            pytest.fail(f"Tools with incomplete definitions: {incomplete[:5]}")


# =============================================================================
# P0-002: Path Resolution Contract
# =============================================================================


class TestPathResolutionContract:
    """P0: Path resolution must follow the state-root hygiene policy."""

    def test_wm_root_is_absolute_path(self):
        """WM_ROOT must always be an absolute path."""
        from whitemagic.config.paths import WM_ROOT

        assert WM_ROOT.is_absolute(), f"WM_ROOT ({WM_ROOT}) is not absolute"

    def test_db_path_is_absolute_path(self):
        """DB_PATH must always be an absolute path."""
        from whitemagic.config.paths import DB_PATH

        assert DB_PATH.is_absolute(), f"DB_PATH ({DB_PATH}) is not absolute"

    def test_state_root_not_in_repo(self):
        """State root must never be inside the repository."""
        from whitemagic.config.paths import WM_ROOT, get_project_root

        project_root = get_project_root()

        try:
            WM_ROOT.relative_to(project_root)
            # If we get here, WM_ROOT is inside repo - FAIL
            pytest.fail(f"WM_ROOT ({WM_ROOT}) is inside project root ({project_root})")
        except ValueError:
            pass  # Good - WM_ROOT is outside project

    def test_data_dir_under_state_root(self):
        """DATA_DIR must be under WM_ROOT."""
        from whitemagic.config.paths import DATA_DIR, WM_ROOT

        try:
            DATA_DIR.relative_to(WM_ROOT)
        except ValueError:
            pytest.fail(f"DATA_DIR ({DATA_DIR}) is not under WM_ROOT ({WM_ROOT})")


# =============================================================================
# P0-003: Tool Dispatch Contract
# =============================================================================


class TestToolDispatchContract:
    """P0: Tool dispatch must maintain stability guarantees."""

    def test_safe_tools_are_read_only(self):
        """Tools marked as SAFE in risk classification must not write."""
        from whitemagic.security.tool_gating import TOOL_RISK_CLASSIFICATION, ToolRisk

        # These tools are documented as read-only
        read_only_tools = [
            "search_memories",
            "read_memory",
            "capabilities",
            "manifest",
            "state.paths",
            "state.summary",
            "ship.check",
        ]

        for tool_name in read_only_tools:
            risk = TOOL_RISK_CLASSIFICATION.get(tool_name)
            if risk is not None:
                assert risk in (ToolRisk.SAFE, ToolRisk.MODERATE), (
                    f"Read-only tool {tool_name} has incorrect risk: {risk}"
                )

    def test_dispatch_table_not_empty(self):
        """DISPATCH_TABLE must contain tools."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        assert len(DISPATCH_TABLE) > 0, "DISPATCH_TABLE is empty"
        # No-shrink baseline — tools are added, not removed.
        # If tools are intentionally removed, update this baseline.
        BASELINE = 750
        assert len(DISPATCH_TABLE) >= BASELINE, (
            f"DISPATCH_TABLE shrank below baseline {BASELINE}: {len(DISPATCH_TABLE)} tools. "
            f"If tools were intentionally removed, update BASELINE."
        )

    def test_core_tools_have_handlers(self):
        """Core tools must have working dispatch handlers."""
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE

        core_tools = [
            "create_memory",
            "search_memories",
            "capabilities",
            "manifest",
        ]

        for tool_name in core_tools:
            assert tool_name in DISPATCH_TABLE, (
                f"Core tool {tool_name} not in dispatch table"
            )


# =============================================================================
# P0-004: Package Integrity Contract
# =============================================================================


class TestPackageIntegrityContract:
    """P0: Package must be installable and functional."""

    def test_package_version_available(self):
        """Package version must be accessible."""
        from whitemagic import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0
        # Should look like a semantic version
        parts = __version__.split(".")
        assert len(parts) >= 2, f"Version {__version__} doesn't look like semver"

    def test_can_import_core_modules(self):
        """Core modules must be importable without errors."""
        modules = [
            "whitemagic.config.paths",
            "whitemagic.tools.registry",
            "whitemagic.tools.dispatch_table",
            "whitemagic.security.tool_gating",
        ]

        for mod_name in modules:
            try:
                __import__(mod_name)
            except Exception as e:
                pytest.fail(f"Failed to import {mod_name}: {e}")


# =============================================================================
# P0-005: API Response Contract
# =============================================================================


class TestAPIResponseContract:
    """P0: Tool responses must follow the standard envelope format."""

    def test_tool_response_envelope_structure(self):
        """Tool responses must include required envelope fields."""
        from whitemagic.tools.unified_api import call_tool

        # Call a safe read-only tool
        response = call_tool("capabilities")

        # Verify envelope structure
        assert isinstance(response, dict), "Response must be a dict"
        assert "status" in response, "Response must have 'status' field"
        assert response["status"] in ("success", "error"), (
            f"Invalid status: {response['status']}"
        )

        # Ensure full envelope keys are present
        missing = {"envelope_version", "tool", "request_id", "timestamp"}.difference(
            response.keys()
        )
        assert not missing, f"Missing envelope keys: {sorted(missing)}"

    def test_tool_response_includes_details_on_success(self):
        """Successful tool responses should include details."""
        from whitemagic.tools.unified_api import call_tool

        response = call_tool("state.paths")

        if response["status"] == "success":
            assert "details" in response or "data" in response, (
                "Successful response should have 'details' or 'data'"
            )


# =============================================================================
# P0-006: Security Contract
# =============================================================================


class TestSecurityContract:
    """P0: Security gating must function correctly."""

    def test_tool_gate_singleton_exists(self):
        """ToolGate singleton must be accessible."""
        from whitemagic.security.tool_gating import ToolGate, get_tool_gate

        gate = get_tool_gate()
        assert isinstance(gate, ToolGate)

    def test_path_validator_blocks_suspicious_paths(self):
        """PathValidator must block access to sensitive system paths."""
        from whitemagic.security.tool_gating import get_tool_gate

        gate = get_tool_gate()
        validator = gate.path_validator

        # These paths should be blocked
        blocked_paths = [
            "/etc/passwd",
            "~/.ssh/id_rsa",
        ]

        for path in blocked_paths:
            allowed, reason = validator.is_path_allowed(path)
            if allowed:
                pytest.fail(f"Path {path} should be blocked but was allowed: {reason}")


# =============================================================================
# P0 Test Suite Metadata
# =============================================================================

P0_TEST_COUNT = 17  # Update this as tests are added
P0_TEST_MODULES = [
    "test_tool_registry_contract",
    "test_path_resolution_contract",
    "test_tool_dispatch_contract",
    "test_package_integrity_contract",
    "test_api_response_contract",
    "test_security_contract",
]
