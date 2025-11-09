"""
Utilities for managing per-user MemoryManager instances.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from whitemagic import MemoryManager


_memory_managers: Dict[str, MemoryManager] = {}


def get_memory_manager(user) -> MemoryManager:
    """
    Get or create a MemoryManager instance for a user.

    Each user receives an isolated memory directory rooted at
    ``{WM_BASE_PATH}/users/<user_id>``.
    """
    user_id_str = str(user.id)

    if user_id_str not in _memory_managers:
        base_path = Path(os.getenv("WM_BASE_PATH", ".")).resolve()
        user_dir = base_path / "users" / user_id_str
        user_dir.mkdir(parents=True, exist_ok=True)

        _memory_managers[user_id_str] = MemoryManager(base_dir=str(user_dir))

    return _memory_managers[user_id_str]
