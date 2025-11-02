#!/usr/bin/env python3
"""
WhiteMagic Memory Manager - Backward Compatibility Wrapper

This file maintains backward compatibility for scripts and tools that
import from memory_manager.py. All functionality has been refactored into
the whitemagic package.

For new code, import directly from whitemagic:
    from whitemagic import MemoryManager

For CLI usage, use cli.py:
    python cli.py create --title "My Memory" --content "Content"
"""

# Import MemoryManager for backward compatibility
from whitemagic import MemoryManager

# Import CLI for backward compatibility
from cli import main, build_parser, COMMAND_HANDLERS

# Re-export for anyone importing from this module
__all__ = ["MemoryManager", "main", "build_parser", "COMMAND_HANDLERS"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
