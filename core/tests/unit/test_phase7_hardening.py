"""Tests for Phase 7 — Compatibility, Registry, Packaging, and Metadata Cleanup.

Covers:
1. Version metadata consistency across all sources
2. Tool surface consistency (registry ↔ dispatch ↔ gana ↔ mcp-registry)
3. Name-pattern safety inference removal
4. Compatibility package deprecation warnings
5. Optional-dependency matrix validation
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CORE_ROOT = REPO_ROOT / "core"


# ── Slice 1: Version Metadata Consistency ────────────────────────────


class TestVersionConsistency:
    """Validate that all version sources agree."""

    def test_version_file_exists(self) -> None:
        vf = REPO_ROOT / "VERSION"
        assert vf.exists(), "VERSION file must exist at repo root"
        assert vf.read_text().strip(), "VERSION file must not be empty"

    def test_core_version_file_matches(self) -> None:
        vf = REPO_ROOT / "VERSION"
        cvf = CORE_ROOT / "VERSION"
        assert cvf.exists(), "core/VERSION file must exist"
        assert vf.read_text().strip() == cvf.read_text().strip(), (
            "VERSION and core/VERSION must agree"
        )

    def test_pyproject_uses_dynamic_version(self) -> None:
        pp = (CORE_ROOT / "pyproject.toml").read_text()
        assert 'dynamic = ["version"]' in pp, "pyproject.toml must use dynamic version"
        assert "[tool.setuptools.dynamic]" in pp, "pyproject.toml must have setuptools.dynamic section"

    def test_mcp_registry_version_matches_version_file(self) -> None:
        vf_version = (REPO_ROOT / "VERSION").read_text().strip()
        mr = json.loads((REPO_ROOT / "mcp-registry.json").read_text())
        assert mr.get("version") == vf_version, (
            f"mcp-registry.json version {mr.get('version')} != VERSION file {vf_version}"
        )

    def test_server_json_version_matches_version_file(self) -> None:
        vf_version = (REPO_ROOT / "VERSION").read_text().strip()
        sj = json.loads((REPO_ROOT / "server.json").read_text())
        assert sj.get("version") == vf_version, (
            f"server.json version {sj.get('version')} != VERSION file {vf_version}"
        )

    def test_whitemagic_version_matches_version_file(self) -> None:
        vf_version = (REPO_ROOT / "VERSION").read_text().strip()
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic import __version__
            assert __version__ == vf_version, (
                f"whitemagic.__version__ {__version__} != VERSION file {vf_version}"
            )
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))


# ── Slice 2: Tool Surface Consistency ────────────────────────────────


class TestToolSurfaceConsistency:
    """Validate that tool counts agree across surfaces."""

    def test_mcp_registry_nested_count_matches_dispatch(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.tools.dispatch_table import DISPATCH_TABLE
            mr = json.loads((REPO_ROOT / "mcp-registry.json").read_text())
            assert mr.get("nested_tool_count") == len(DISPATCH_TABLE), (
                f"mcp-registry.json nested_tool_count {mr.get('nested_tool_count')} "
                f"!= DISPATCH_TABLE size {len(DISPATCH_TABLE)}"
            )
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_server_json_description_count_matches_dispatch(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.tools.dispatch_table import DISPATCH_TABLE
            sj = json.loads((REPO_ROOT / "server.json").read_text())
            desc = sj.get("description", "")
            m = re.search(r"(\d+) in classic", desc)
            assert m, "server.json description must contain 'N in classic'"
            assert int(m.group(1)) == len(DISPATCH_TABLE), (
                f"server.json description says {m.group(1)} classic tools "
                f"!= DISPATCH_TABLE size {len(DISPATCH_TABLE)}"
            )
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_gana_count_is_28(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.tools.tool_catalog import GANA_NAMES
            assert len(GANA_NAMES) == 28, f"Expected 28 Gana tools, got {len(GANA_NAMES)}"
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_galaxy_use_has_prat_mapping(self) -> None:
        """galaxy.use must be mapped to a Gana (regression for Phase 7 fix)."""
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.tools.prat_mappings import GANA_TO_TOOLS
            all_mapped = {t for tools in GANA_TO_TOOLS.values() for t in tools}
            assert "galaxy.use" in all_mapped, "galaxy.use must have a PRAT Gana mapping"
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))


# ── Slice 3: Name-Pattern Safety Inference Removal ───────────────────


class TestSafetyInferenceRemoval:
    """Validate that safety is no longer inferred from tool name patterns."""

    def test_no_name_pattern_inference_in_catalog(self) -> None:
        """The tool_catalog.py file must not contain name-pattern safety inference."""
        catalog = (CORE_ROOT / "whitemagic" / "tools" / "tool_catalog.py").read_text()
        # The old code had name_lower.startswith patterns for safety inference
        assert "name_lower.startswith" not in catalog, (
            "tool_catalog.py must not infer safety from name patterns (Phase 7 WI 8)"
        )

    def test_dispatch_only_tools_default_to_read(self) -> None:
        """Tools without authored definitions must default to READ safety."""
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.tools.registry import TOOL_REGISTRY
            from whitemagic.tools.tool_types import ToolSafety

            read_count = sum(1 for t in TOOL_REGISTRY if t.safety == ToolSafety.READ)
            write_count = sum(1 for t in TOOL_REGISTRY if t.safety == ToolSafety.WRITE)

            # The majority should be READ (dispatch-only tools default to READ)
            assert read_count > write_count, (
                f"READ tools ({read_count}) should outnumber WRITE tools ({write_count}) "
                "since dispatch-only tools default to READ"
            )
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))


# ── Slice 4: Compatibility Package ───────────────────────────────────


class TestCompatPackage:
    """Validate the whitemagic.compat package."""

    def test_compat_importable(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.compat import _deprecated
            assert callable(_deprecated)
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_compat_galaxy_emits_deprecation(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.compat.galaxy import switch_galaxy
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    switch_galaxy("universal")
                except (KeyError, ValueError, RuntimeError):
                    pass  # Handler may error, we only care about the warning
                dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
                assert len(dep_warnings) > 0, "switch_galaxy must emit DeprecationWarning"
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_compat_resonance_emits_deprecation(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.compat.resonance import get_gan_ying_bus
            with pytest.warns(DeprecationWarning, match="deprecated"):
                get_gan_ying_bus()
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_compat_gardens_emits_deprecation(self) -> None:
        sys.path.insert(0, str(CORE_ROOT))
        try:
            from whitemagic.compat.gardens import get_air_garden
            with pytest.warns(DeprecationWarning, match="deprecated"):
                get_air_garden()
        finally:
            if str(CORE_ROOT) in sys.path:
                sys.path.remove(str(CORE_ROOT))

    def test_compat_package_has_migration_docs(self) -> None:
        """The compat __init__.py docstring must document migration paths."""
        init_file = (CORE_ROOT / "whitemagic" / "compat" / "__init__.py").read_text()
        assert "Migration" in init_file or "migration" in init_file
        assert "25.0.0" in init_file, "Compat package must declare removal version"


# ── Slice 5: Optional-Dependency Matrix ──────────────────────────────


class TestDependencyMatrix:
    """Validate the optional-dependency matrix in pyproject.toml."""

    def test_tiered_bundles_exist(self) -> None:
        import tomllib
        pp = (CORE_ROOT / "pyproject.toml").read_bytes()
        data = tomllib.loads(pp.decode("utf-8"))
        extras = data.get("project", {}).get("optional-dependencies", {})
        for tier in ("lite", "core", "heavy-tier", "full"):
            assert tier in extras, f"Tiered bundle '{tier}' must exist in optional-dependencies"

    def test_no_duplicate_deps_in_extras(self) -> None:
        import tomllib
        pp = (CORE_ROOT / "pyproject.toml").read_bytes()
        data = tomllib.loads(pp.decode("utf-8"))
        extras = data.get("project", {}).get("optional-dependencies", {})
        for extra_name, deps in extras.items():
            names = [re.split(r"[>=<!\[;]", d)[0].strip() for d in deps]
            assert len(names) == len(set(names)), (
                f"Duplicate dependencies in extra '{extra_name}': "
                f"{[n for n in names if names.count(n) > 1]}"
            )

    def test_core_tier_contains_lite_deps(self) -> None:
        import tomllib
        pp = (CORE_ROOT / "pyproject.toml").read_bytes()
        data = tomllib.loads(pp.decode("utf-8"))
        extras = data.get("project", {}).get("optional-dependencies", {})
        lite_deps = {re.split(r"[>=<!\[;]", d)[0].strip() for d in extras.get("lite", [])}
        core_deps = {re.split(r"[>=<!\[;]", d)[0].strip() for d in extras.get("core", [])}
        missing = lite_deps - core_deps
        assert not missing, f"core tier missing deps from lite: {sorted(missing)}"

    def test_heavy_tier_contains_core_deps(self) -> None:
        import tomllib
        pp = (CORE_ROOT / "pyproject.toml").read_bytes()
        data = tomllib.loads(pp.decode("utf-8"))
        extras = data.get("project", {}).get("optional-dependencies", {})
        core_deps = {re.split(r"[>=<!\[;]", d)[0].strip() for d in extras.get("core", [])}
        heavy_deps = {re.split(r"[>=<!\[;]", d)[0].strip() for d in extras.get("heavy-tier", [])}
        missing = core_deps - heavy_deps
        assert not missing, f"heavy-tier missing deps from core: {sorted(missing)}"


# ── Slice 6: Dead Import & Stale Type Ignore Cleanup ─────────────────


class TestStaleTypeIgnoreInventory:
    """Validate type: ignore inventory and legacy cache guard."""

    def test_legacy_cache_has_env_var_guard(self) -> None:
        """Legacy cache fallback must be opt-out via WM_DISABLE_LEGACY_CACHE."""
        middleware = (CORE_ROOT / "whitemagic" / "tools" / "middleware.py").read_text()
        assert "WM_DISABLE_LEGACY_CACHE" in middleware, (
            "Legacy cache fallback must be guarded by WM_DISABLE_LEGACY_CACHE env var"
        )

    def test_bare_type_ignores_are_inventoried(self) -> None:
        """The stale type ignore script must exist and be runnable."""
        script = REPO_ROOT / "scripts" / "check_stale_type_ignores.py"
        assert script.exists(), "check_stale_type_ignores.py must exist"

    def test_no_new_bare_type_ignores_in_compat(self) -> None:
        """The compat package must not introduce bare type: ignore comments."""
        compat_dir = CORE_ROOT / "whitemagic" / "compat"
        for py_file in compat_dir.rglob("*.py"):
            text = py_file.read_text()
            assert "# type: ignore" not in text or "[" in text.split("# type: ignore")[1].split("\n")[0], (
                f"Bare type: ignore in {py_file.name} — must specify error code"
            )
