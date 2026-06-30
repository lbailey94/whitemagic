"""
WhiteMagic - Holographic Intelligence Core Package

Core Components:
- core: Essential infrastructure (memory, resonance, patterns, consciousness)
- gardens: 17 operational gardens
- rust: Performance-critical Rust implementations (SIMD, parallel search)
- interfaces: User-facing components (CLI, API, Dashboard)
- core.intelligence: AI/ML features (agentic, wisdom, learning)
- utils: Shared utilities
"""

import importlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

# Single source of truth for version:
# 1) Repo `VERSION` file (always fresh for source/editable checkouts)
# 2) Installed package metadata (works for pip installs / wheels)
# 3) "unknown" fallback
_version_file = Path(__file__).resolve().parent.parent / "VERSION"
if _version_file.exists():
    __version__ = _version_file.read_text().strip()
else:
    try:
        __version__ = _pkg_version("whitemagic")
    except PackageNotFoundError:
        __version__ = "unknown"

# Lazy imports to keep base import fast.
_LAZY_MODULES: dict[str, str] = {
    "utils": "whitemagic.utils",
    "memory": "whitemagic.core.memory",
    "resonance": "whitemagic.core.resonance",
    "patterns": "whitemagic.core.patterns",
    "consciousness": "whitemagic.core.consciousness",
    "gardens": "whitemagic.gardens",
    "optimization": "whitemagic.rust.optimization",
    # Note: embeddings, data_lake, bindings removed - these Rust modules don't exist yet
    # Note: agentic removed - no __init__.py, module structure incomplete
    "cli": "whitemagic.interfaces.cli",
    "api": "whitemagic.interfaces.api",
    "dashboard": "whitemagic.interfaces.dashboard",
    "wisdom": "whitemagic.core.intelligence.wisdom",
    "learning": "whitemagic.core.intelligence.learning",
    "immune": "whitemagic.core.immune",
    "automation": "whitemagic.automation",
    "integration": "whitemagic.integration",
    "edge": "whitemagic.edge",
    "autonomous": "whitemagic.autonomous",
    # Recovered from v17
    "parallel": "whitemagic.parallel",
    "plugins": "whitemagic.plugins",
    "cache": "whitemagic.cache",
    "auth": "whitemagic.auth",
    "benchmarks": "whitemagic.benchmarks",
    "search": "whitemagic.search",
    "mesh": "whitemagic.mesh",
}


def __getattr__(name: str) -> Any:
    if name == "MemoryManager":
        from whitemagic.core.memory.manager import MemoryManager

        globals()[name] = MemoryManager
        return MemoryManager

    module_path = _LAZY_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module 'whitemagic' has no attribute '{name}'")

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise AttributeError(f"Optional module '{name}' unavailable: {exc}") from exc

    globals()[name] = module
    return module


def bootstrap() -> None:
    """Initialize the Unified Nervous System and register all organs."""
    from whitemagic.core.bootstrap_organs import bootstrap_nervous_system

    bootstrap_nervous_system()


def __dir__() -> list[str]:
    return sorted(
        list(globals().keys())
        + list(_LAZY_MODULES.keys())
        + ["MemoryManager", "bootstrap"]
    )


__all__ = [
    "memory",
    "resonance",
    "patterns",
    "consciousness",
    "MemoryManager",  # Backward compatibility
    "gardens",
    "optimization",
    "cli",
    "api",
    "dashboard",
    "wisdom",
    "learning",
    "immune",
    "automation",
    "integration",
    "edge",
    "autonomous",
    "utils",
    "bootstrap",
    # Recovered from v17
    "parallel",
    "plugins",
    "cache",
    "auth",
    "benchmarks",
    "search",
    "mesh",
]
