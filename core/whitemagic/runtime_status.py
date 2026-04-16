from __future__ import annotations

import os
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from whitemagic.tools.tool_surface import get_surface_counts

_VERSION_FILE = Path(__file__).resolve().parent.parent / 'VERSION'


def _env_flag(name: str) -> bool:
    return os.getenv(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}



def get_runtime_status() -> dict[str, Any]:
    version = _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else 'unknown'
    prat_mode = _env_flag('WM_MCP_PRAT')
    lite_mode = _env_flag('WM_MCP_LITE')
    debug_enabled = _env_flag('WM_DEBUG')
    silent_init = _env_flag('WM_SILENT_INIT')

    mode = 'classic'
    if prat_mode:
        mode = 'prat'
    elif lite_mode:
        mode = 'lite'

    surface_counts = get_surface_counts()
    issues: list[str] = []

    rust_available = find_spec('whitemagic_rs') is not None
    fastmcp_available = find_spec('fastmcp') is not None
    if not rust_available:
        issues.append('rust_bridge_unavailable')
    if not fastmcp_available:
        issues.append('fastmcp_unavailable')

    status = 'healthy' if not issues else 'degraded'

    return {
        'status': status,
        'version': version,
        'mode': mode,
        'debug_enabled': debug_enabled,
        'silent_init': silent_init,
        'surface_counts': surface_counts,
        'accelerators': {
            'rust_bridge': rust_available,
            'fastmcp': fastmcp_available,
        },
        'degraded_mode': bool(issues),
        'degraded_reasons': issues,
        'resolution_hints': [
            'Set WM_DEBUG=1 for verbose diagnostics' if not debug_enabled else 'WM_DEBUG=1 is active',
            'Install/build optional accelerators if degraded reasons include missing runtime components',
        ],
    }
