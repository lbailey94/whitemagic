"""WhiteMagic Configuration - v2.3.6

Centralized configuration for all WhiteMagic systems.
Auto-loaded on startup for both AI and human users.
"""

from pathlib import Path
from typing import Optional

# Version
VERSION = "2.3.9"
VERSION_NAME = "Autonomous Intelligence"

# Memory directories
MEMORY_DIR = Path("memory")
SHORT_TERM_DIR = MEMORY_DIR / "short_term"
LONG_TERM_DIR = MEMORY_DIR / "long_term"
ARCHIVE_DIR = MEMORY_DIR / "archive"

# Symbolic compression (v2.3.5+)
SYMBOLIC_COMPRESSION_ENABLED = True  # Enable Chinese symbolic compression
SYMBOLIC_SHORT_TERM_ONLY = True      # Only compress short-term memories
SYMBOLIC_TOKEN_SAVINGS = 0.37        # Measured: 37% token reduction

# Rapid cognition (v2.3.5+)
RAPID_COGNITION_ENABLED = True
RAPID_COGNITION_INTERVAL = 5         # Seconds between scans (3x faster than v2.3.4)
MEMORY_CREATION_FREQUENCY = 3.0      # Multiplier: 3x faster learning

# Tool sharpening (v2.3.6+)
TOOL_SHARPENING_ENABLED = True
TOOL_SHARPENING_ON_RELEASE = True    # Auto-run on version release
TOOL_SHARPENING_INTERVAL = 3600      # Seconds (1 hour)

# Wisdom integration (v2.3.5+)
WISDOM_INGESTION_ENABLED = True
WISDOM_RATE_LIMIT = 2.0              # Seconds between requests
WISDOM_AUTO_UPDATE = False           # Don't re-fetch by default

# Dashboard & API
WEBSOCKET_ENABLED = True
WEBSOCKET_PORT = 8765
API_PORT = 8000

# User system (v2.3.5+)
FOUNDER_UID = "lucas_founder_001"
FOUNDER_EMAIL = "lucas@whitemagic.ai"

# Performance
USE_RUST_WHEN_AVAILABLE = True
USE_HASKELL_WHEN_AVAILABLE = True
PARALLEL_THREADS_DEFAULT = 64        # I Ching alignment

# Logging
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_DIR = Path("logs")


def get_config(key: str, default: Optional[any] = None) -> any:
    """Get configuration value."""
    return globals().get(key, default)


def show_config():
    """Print current configuration."""
    print(f"WhiteMagic v{VERSION} - {VERSION_NAME}")
    print(f"Symbolic compression: {SYMBOLIC_COMPRESSION_ENABLED} ({SYMBOLIC_TOKEN_SAVINGS*100:.1f}% savings)")
    print(f"Rapid cognition: {RAPID_COGNITION_INTERVAL}s intervals")
    print(f"Tool sharpening: {TOOL_SHARPENING_ENABLED}")
    print(f"Wisdom ingestion: {WISDOM_INGESTION_ENABLED}")


if __name__ == "__main__":
    show_config()
