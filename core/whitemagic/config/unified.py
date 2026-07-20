"""Unified configuration facade — single typed config path for WhiteMagic.

This module bridges the two legacy config systems (``daemon_config.py`` with
``WM_*`` prefix and ``manager.py`` with ``WHITEMAGIC_*`` prefix) into one
coherent entrypoint.  New code should import from here rather than either
legacy module.

Usage::

    from whitemagic.config.unified import get_config, get_daemon_config

    config = get_config()        # WhiteMagicConfig (Pydantic, typed)
    daemon = get_daemon_config() # DaemonConfig (dataclass, WM_* prefix)
"""

from __future__ import annotations

import logging
from functools import lru_cache

from whitemagic.config.daemon_config import DaemonConfig
from whitemagic.config.daemon_config import load_config as _load_daemon_config
from whitemagic.config.manager import ConfigManager, WhiteMagicConfig

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_config() -> WhiteMagicConfig:
    """Return the singleton typed WhiteMagicConfig instance.

    This is the canonical config object for application-level settings
    (database, API, security, logging).  Uses Pydantic validation.
    """
    mgr = ConfigManager()
    return mgr.load_config()


@lru_cache(maxsize=1)
def get_daemon_config() -> DaemonConfig:
    """Return the singleton DaemonConfig instance.

    This is the canonical config object for daemon-level settings
    (loops, inference, gateway, privacy).  Uses dataclass with WM_* env vars.
    """
    return _load_daemon_config()


def reload_config() -> WhiteMagicConfig:
    """Force-reload the typed config (clears cache)."""
    get_config.cache_clear()
    return get_config()


def reload_daemon_config() -> DaemonConfig:
    """Force-reload the daemon config (clears cache)."""
    get_daemon_config.cache_clear()
    return get_daemon_config()
