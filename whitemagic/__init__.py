"""
WhiteMagic - Memory Infrastructure for AI Agents

2.6.5 "Autonomous Intelligence"
"""

from .core import MemoryManager
from .config import VERSION, show_config

# Auto-display config on import (helps both AI and humans)
import os
if os.getenv("WHITEMAGIC_SHOW_CONFIG", "0") == "1":
    show_config()

__version__ = VERSION
__all__ = ["MemoryManager", "VERSION", "show_config"]
