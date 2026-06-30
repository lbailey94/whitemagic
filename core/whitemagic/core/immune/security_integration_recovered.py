"""Backward-compatibility shim for whitemagic.immune.security_integration.

The canonical location is whitemagic.core.immune.security_integration.
This shim keeps the old import path working for tool_gating.py.
"""

import warnings as _w

_w.warn(
    "whitemagic.immune.security_integration is deprecated; use whitemagic.core.immune.security_integration",
    DeprecationWarning,
    stacklevel=2,
)
from whitemagic.core.immune.security_integration import (  # noqa: F401,E402
    report_threat,
)

__all__ = ["report_threat"]
