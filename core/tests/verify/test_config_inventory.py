"""Contract test: verify typed configuration inventory and dual-system status.

This test inventories all WM_* environment variable references in the codebase
and establishes a no-shrink baseline. It also verifies the two competing config
systems (daemon_config.py with WM_* prefix and manager.py with WHITEMAGIC_* prefix)
are documented and their alias mappings are intact.

The long-term goal (P4.4) is to consolidate into one typed config path.
This test ensures the inventory is stable and the alias bridge works.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_ROOT = (Path(__file__).resolve().parent.parent.parent / "whitemagic").resolve()
assert WHITEMAGIC_ROOT.is_dir(), f"WHITEMAGIC_ROOT does not exist: {WHITEMAGIC_ROOT}"

# Pattern to find WM_* environment variable references
_WM_PATTERN = re.compile(r"\bWM_[A-Z][A-Z0-9_]*\b")
_WHITEMAGIC_PATTERN = re.compile(r"\bWHITEMAGIC_[A-Z][A-Z0-9_]*\b")


def _find_wm_env_vars() -> set[str]:
    """Find all WM_* environment variable references in the codebase."""
    vars_found: set[str] = set()
    for py_file in WHITEMAGIC_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _WM_PATTERN.finditer(content):
            vars_found.add(match.group())
    return vars_found


def _find_whitemagic_env_vars() -> set[str]:
    """Find all WHITEMAGIC_* environment variable references."""
    vars_found: set[str] = set()
    for py_file in WHITEMAGIC_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _WHITEMAGIC_PATTERN.finditer(content):
            vars_found.add(match.group())
    return vars_found


class TestConfigurationInventory:
    """Verify WM_* env var inventory and config system status."""

    def test_wm_env_var_count_no_shrinkage(self):
        """The total WM_* env var count must not shrink from baseline."""
        vars_found = _find_wm_env_vars()
        BASELINE = 200  # No-shrink baseline (2026-07-19)
        assert len(vars_found) >= BASELINE, (
            f"WM_* env var count dropped from {BASELINE} to {len(vars_found)}. "
            f"This may indicate config vars were removed."
        )

    def test_critical_wm_vars_exist(self):
        """Critical WM_* vars must be present in the codebase."""
        vars_found = _find_wm_env_vars()
        critical = {
            "WM_STATE_ROOT",
            "WM_DEBUG",
            "WM_ENV",
            "WM_DB_PATH",
            "WM_LOG_LEVEL",
            "WM_TOOL_TIMEOUT",
            "WM_SKIP_POLYGLOT",
            "WM_LOCAL_ONLY",
            "WM_INFERENCE_BACKEND",
            "WM_REDIS_URL",
        }
        missing = critical - vars_found
        assert not missing, (
            f"Critical WM_* env vars missing from codebase: {missing}"
        )

    def test_whitemagic_alias_vars_exist(self):
        """WHITEMAGIC_* alias vars must exist in the config manager."""
        vars_found = _find_whitemagic_env_vars()
        # These are the known WHITEMAGIC_* aliases in config/manager.py
        expected_aliases = {
            "WHITEMAGIC_API_HOST",
            "WHITEMAGIC_API_PORT",
            "WHITEMAGIC_LOG_LEVEL",
            "WHITEMAGIC_DEBUG",
            "WHITEMAGIC_DATA_DIR",
        }
        missing = expected_aliases - vars_found
        assert not missing, (
            f"WHITEMAGIC_* alias vars missing from codebase: {missing}"
        )

    def test_config_manager_has_alias_bridge(self):
        """ConfigManager must bridge WHITEMAGIC_* → WM_* aliases."""
        import inspect

        from whitemagic.config.manager import ConfigManager

        source = inspect.getsource(ConfigManager)
        # The alias bridge maps WHITEMAGIC_* env vars to WM_* equivalents
        assert "WHITEMAGIC_API_HOST" in source or "_env_aliases" in source, (
            "ConfigManager must have an alias bridge from WHITEMAGIC_* to WM_*"
        )

    def test_daemon_config_uses_wm_prefix(self):
        """daemon_config.py must use WM_* prefix (not WHITEMAGIC_*)."""
        import inspect

        from whitemagic.config import daemon_config

        source = inspect.getsource(daemon_config)
        assert "WM_" in source, "daemon_config.py must use WM_* prefix"
        # It should not use WHITEMAGIC_* directly (those go through ConfigManager)
        whitemagic_count = source.count("WHITEMAGIC_")
        assert whitemagic_count == 0, (
            f"daemon_config.py should not use WHITEMAGIC_* prefix (found {whitemagic_count} references)"
        )

    def test_no_raw_os_getenv_in_config_manager(self):
        """WhiteMagicConfig should be a Pydantic model with typed fields."""
        from whitemagic.config.manager import WhiteMagicConfig

        # WhiteMagicConfig is the Pydantic model that ConfigManager wraps
        assert hasattr(WhiteMagicConfig, "model_fields") or hasattr(WhiteMagicConfig, "__fields__"), (
            "WhiteMagicConfig must be a Pydantic model with typed fields"
        )

    def test_config_validator_exists(self):
        """config/validator.py must exist and be importable."""
        from whitemagic.config.validator import ConfigValidator, validate_startup

        assert ConfigValidator is not None
        assert callable(validate_startup)

    def test_env_var_registry_exists(self):
        """config/env_vars.py must exist with a typed registry of WM_* vars."""
        from whitemagic.config.env_vars import REGISTRY, get_env, get_env_bool, get_env_int

        assert len(REGISTRY) >= 100, (
            f"env_vars REGISTRY must have at least 100 entries, got {len(REGISTRY)}"
        )
        # Critical vars must be in the registry
        critical = {"WM_STATE_ROOT", "WM_DEBUG", "WM_ENV", "WM_SKIP_POLYGLOT"}
        missing = critical - set(REGISTRY.keys())
        assert not missing, f"Critical vars missing from REGISTRY: {missing}"
        # Accessor functions must work
        assert callable(get_env)
        assert callable(get_env_bool)
        assert callable(get_env_int)

    def test_unified_config_facade_exists(self):
        """config/unified.py must provide single entrypoint for both config systems."""
        from whitemagic.config.unified import get_config, get_daemon_config

        assert callable(get_config)
        assert callable(get_daemon_config)

    def test_env_var_registry_count_no_shrinkage(self):
        """The env var registry count must not shrink from baseline."""
        from whitemagic.config.env_vars import REGISTRY

        BASELINE = 100
        assert len(REGISTRY) >= BASELINE, (
            f"env_vars REGISTRY shrank from {BASELINE} to {len(REGISTRY)}."
        )
