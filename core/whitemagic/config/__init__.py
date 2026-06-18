# ruff: noqa: BLE001
"""Configuration initialization module for WhiteMagic.

This module provides easy access to the configuration system
and handles initialization.

Path definitions are centralized in paths.py:
- PROJECT_ROOT: code/repo location (for scripts, archive)
- WM_ROOT: user state location (configurable, defaults to ~/.whitemagic)
- MEMORY_DIR, DATA_DIR, CACHE_DIR: subdirs of WM_ROOT
"""
from __future__ import annotations

import logging
from typing import Any

from whitemagic.config.paths import (
    ARCHIVE_DIR,
    ARTIFACTS_DIR,
    CACHE_DIR,
    DATA_DIR,
    DB_PATH,
    LOGS_DIR,
    MEMORY_DIR,
    PROJECT_ROOT,
    SCRIPTS_DIR,
    SESSIONS_DIR,
    WM_ROOT,
)

logger = logging.getLogger(__name__)

# Import version from canonical source (VERSION file)
_version_file = PROJECT_ROOT / "VERSION"
if _version_file.exists():
    VERSION = _version_file.read_text().strip()
else:
    try:
        from whitemagic import __version__ as VERSION  # type: ignore
    except (ImportError, ModuleNotFoundError):
        VERSION = "unknown"


_CONCURRENCY_EXPORTS = {
    "ASYNC_TASK_LIMIT",
    "CPU_WORKERS",
    "IO_WORKERS",
    "MAX_WORKERS",
    "get_concurrency_config",
    "get_max_workers",
}

_MANAGER_EXPORTS = {
    "ConfigManager",
    "DatabaseConfig",
    "Environment",
    "SecurityConfig",
    "WhiteMagicConfig",
    "get_config",
    "get_config_manager",
    "setup_config_environment",
    "config",
}


def _load_concurrency_attr(name: str) -> Any:
    from whitemagic.config import concurrency as _concurrency
    return getattr(_concurrency, name)


def _load_manager_attr(name: str) -> Any:
    from whitemagic.config import manager as _manager
    if name == "config":
        cfg = _manager.get_config()
        _manager.setup_config_environment(cfg)
        return cfg
    return getattr(_manager, name)


def __getattr__(name: str) -> Any:
    if name in _CONCURRENCY_EXPORTS:
        value = _load_concurrency_attr(name)
        globals()[name] = value
        return value
    if name in _MANAGER_EXPORTS:
        value = _load_manager_attr(name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def show_config() -> None:
    """Print a safe, minimal configuration summary for diagnostics."""
    try:
        current = _load_manager_attr("config")
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        current = None

    env_value = getattr(current, "environment", "unknown")
    debug_value = getattr(current, "debug", "unknown")

    logger.info("Configuration summary:")
    logger.info(f"  environment: {env_value}")
    logger.info(f"  debug: {debug_value}")


__all__ = [
    "config",
    "get_config",
    "get_config_manager",
    "setup_config_environment",
    "WhiteMagicConfig",
    "ConfigManager",
    "Environment",
    "PROJECT_ROOT",
    "SCRIPTS_DIR",
    "ARCHIVE_DIR",
    "WM_ROOT",
    "MEMORY_DIR",
    "DATA_DIR",
    "CACHE_DIR",
    "SESSIONS_DIR",
    "LOGS_DIR",
    "ARTIFACTS_DIR",
    "DB_PATH",
    "VERSION",
    "show_config",
    "get_max_workers",
    "get_concurrency_config",
    "MAX_WORKERS",
    "CPU_WORKERS",
    "IO_WORKERS",
    "ASYNC_TASK_LIMIT",
]
