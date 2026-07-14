"""WhiteMagic MCP Server — thin wrapper around whitemagic.run_mcp_lean."""

from __future__ import annotations

import sys


def main() -> None:
    """Launch the WhiteMagic MCP server (stdio or HTTP)."""
    from whitemagic.run_mcp_lean import main as _main

    _main()


if __name__ == "__main__":
    main()
