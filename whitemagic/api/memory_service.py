"""
Utilities for managing per-user MemoryManager instances with LRU cache.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from whitemagic import MemoryManager


@lru_cache(maxsize=128)
def _create_manager(user_id: str, base_path: str) -> MemoryManager:
    """Create and cache a MemoryManager instance."""
    user_dir = Path(base_path) / "users" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return MemoryManager(base_dir=str(user_dir))


def get_memory_manager(user) -> MemoryManager:
    """
    Get or create a MemoryManager instance for a user with LRU caching.

    Uses functools.lru_cache to limit memory usage. Max 128 active managers.
    
    Each user receives an isolated memory directory rooted at
    ``{WM_BASE_PATH}/users/<user_id>``.
    """
    user_id_str = str(user.id)
    base_path = str(Path(os.getenv("WM_BASE_PATH", ".")).resolve())
    
    return _create_manager(user_id_str, base_path)

    if user_id_str not in _memory_managers:
        base_path = Path(os.getenv("WM_BASE_PATH", ".")).resolve()
        user_dir = base_path / "users" / user_id_str
        user_dir.mkdir(parents=True, exist_ok=True)

        _memory_managers[user_id_str] = MemoryManager(base_dir=str(user_dir))

    return _memory_managers[user_id_str]

    base_path = str(Path(os.getenv("WM_BASE_PATH", ".")).resolve())
    return _create_manager(user_id_str, base_path)
