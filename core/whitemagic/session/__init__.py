# ruff: noqa: BLE001
"""
Session Management — Total Recall Architecture.

Ensures AI sessions start with full context and end with proper handoff.
"""

from __future__ import annotations

from .bootstrap import SessionBootstrap, SessionContext, quick_bootstrap
from .manifest import SessionManifest, create_manifest
from .seen_registry import SessionSeenRegistry, get_session_seen_registry
from .state_client import StateClient, get_state_client

__all__ = [
    "SessionContext",
    "SessionBootstrap",
    "quick_bootstrap",
    "SessionManifest",
    "create_manifest",
    "StateClient",
    "get_state_client",
    "SessionSeenRegistry",
    "get_session_seen_registry",
]
