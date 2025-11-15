"""
WhiteMagic Configuration System.

Provides centralized configuration management via ~/.whitemagic/config.yaml
with support for environment variable overrides.
"""

from .manager import ConfigManager
from .schema import (
    WhiteMagicConfig,
    EmbeddingsConfig,
    SearchConfig,
    TerminalConfig,
    APIConfig,
)

__all__ = [
    "ConfigManager",
    "WhiteMagicConfig",
    "EmbeddingsConfig",
    "SearchConfig",
    "TerminalConfig",
    "APIConfig",
]
