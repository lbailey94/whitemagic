"""
WhiteMagic Configuration System.

Provides centralized configuration management via ~/.whitemagic/config.yaml
with support for environment variable overrides.
"""

from .manager import ConfigManager
from .schema import (
    APIConfig,
    EmbeddingsConfig,
    SearchConfig,
    TerminalConfig,
    WhiteMagicConfig,
)

__all__ = [
    "ConfigManager",
    "WhiteMagicConfig",
    "EmbeddingsConfig",
    "SearchConfig",
    "TerminalConfig",
    "APIConfig",
]
