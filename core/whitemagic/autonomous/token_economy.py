# ruff: noqa: BLE001
"""
Token Economy Tracker — Understand API vs local computation.

Tracks where computation actually happens:
- API tokens (Claude/GPT processing)
- Local CPU
- Local disk I/O
- Rust/Haskell bridges
- MCP tools
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TokenEconomy:
    """Tracks computation distribution across API and local resources."""

    def __init__(self) -> None:
        self.api_tokens: int = 0
        self.local_operations: int = 0
        self.rust_operations: int = 0
        self.mcp_calls: int = 0
        self._history: list[dict[str, Any]] = []

    def record_api(self, tokens: int) -> None:
        """Record API token usage."""
        self.api_tokens += tokens

    def record_local(self, operations: int = 1) -> None:
        """Record local CPU operation."""
        self.local_operations += operations

    def record_rust(self, operations: int = 1) -> None:
        """Record Rust bridge operation."""
        self.rust_operations += operations

    def record_mcp(self, calls: int = 1) -> None:
        """Record MCP tool call."""
        self.mcp_calls += calls

    def local_ratio(self) -> float:
        """Fraction of work done locally vs API."""
        total = self.api_tokens + self.local_operations + self.rust_operations
        if total == 0:
            return 0.0
        return (self.local_operations + self.rust_operations) / total

    def snapshot(self) -> dict[str, Any]:
        """Take a snapshot of token economy."""
        snap = {
            "timestamp": time.time(),
            "api_tokens": self.api_tokens,
            "local_operations": self.local_operations,
            "rust_operations": self.rust_operations,
            "mcp_calls": self.mcp_calls,
            "local_ratio": self.local_ratio(),
        }
        self._history.append(snap)
        return snap

    def summary(self) -> dict[str, Any]:
        return {
            "api_tokens": self.api_tokens,
            "local_operations": self.local_operations,
            "rust_operations": self.rust_operations,
            "mcp_calls": self.mcp_calls,
            "local_ratio": round(self.local_ratio(), 3),
        }


_economy: TokenEconomy | None = None


def get_token_economy() -> TokenEconomy:
    global _economy
    if _economy is None:
        _economy = TokenEconomy()
    return _economy
