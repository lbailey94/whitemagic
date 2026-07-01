"""Non-blocking update checker — compares local version against PyPI.

Usage:
    from whitemagic.core.update_checker import check_for_update
    msg = check_for_update()  # returns str or None
    if msg:
        print(msg, file=sys.stderr)

Respects:
    WM_NO_UPDATE_CHECK=1  — disable entirely
    Caches result for 24 hours in $WM_STATE_ROOT/.update_check
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, cast

from whitemagic.config.paths import UPDATE_CHECK_PATH
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

_PYPI_URL = "https://pypi.org/pypi/whitemagic/json"
_CACHE_TTL_SECONDS = 86400  # 24 hours
_TIMEOUT_SECONDS = 3  # don't slow down startup


def _cache_path() -> Path:
    """Return path to the update-check cache file."""
    return cast(Path, UPDATE_CHECK_PATH)


def _read_cache() -> dict | None:
    """Read cached check result if still valid."""
    try:
        p = _cache_path()
        if not p.exists():
            return None
        data = cast(dict[str, Any], _json_loads(p.read_text(encoding="utf-8")))
        if time.time() - data.get("ts", 0) < _CACHE_TTL_SECONDS:
            return data
    except (OSError, UnicodeDecodeError):
        logger.debug("Swallowed exception", exc_info=True)
    return None


def _write_cache(latest: str, current: str) -> None:
    """Persist check result."""
    try:
        p = _cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            _json_dumps({"ts": time.time(), "latest": latest, "current": current}),
            encoding="utf-8",
        )
    except (OSError, UnicodeDecodeError):
        logger.debug("Swallowed exception", exc_info=True)


def _fetch_latest_version() -> str | None:
    """Fetch latest version from PyPI (blocking, with short timeout)."""
    try:
        from urllib.request import Request, urlopen

        req = Request(_PYPI_URL, headers={"Accept": "application/json"})
        with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            data = cast(dict[str, Any], _json_loads(resp.read()))
            return cast(str | None, data.get("info", {}).get("version"))
    except (OSError, FileNotFoundError, PermissionError):
        return None


def _parse_version(v: str) -> tuple:
    """Parse 'X.Y.Z' into a comparable tuple."""
    try:
        return tuple(int(p) for p in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_for_update() -> str | None:
    """Check if a newer WhiteMagic version is available on PyPI.

    Returns a human-readable message if an update is available, else None.
    Safe to call on every startup — results are cached for 24h.
    """
    # Opt-out
    if os.environ.get("WM_NO_UPDATE_CHECK", "").strip() in ("1", "true", "yes"):
        return None

    try:
        from whitemagic.config import VERSION as current
    except ImportError:
        return None

    cached = _read_cache()
    if cached:
        latest = cached.get("latest", "")
        if _parse_version(latest) > _parse_version(current):
            return (
                f"⬆  WhiteMagic {latest} available (you have {current}). "
                f"Update: pip install -U whitemagic"
            )
        return None

    latest = _fetch_latest_version()
    if not latest:
        return None

    _write_cache(latest, current)

    if _parse_version(latest) > _parse_version(current):
        return (
            f"⬆  WhiteMagic {latest} available (you have {current}). "
            f"Update: pip install -U whitemagic"
        )
    return None
