# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Memory Core (Consolidated v1.1).
==================================
Primary storage and management layer for the WhiteMagic memory system.
Handles SQLite backends, migrations, and high-level CRUD operations.

Consolidated from manager.py, sqlite_backend.py, sqlite_queries.py,
sqlite_schema.py, and db_manager.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# --- SCHEMA ---

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT,
    title TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# --- BACKEND ---

class SQLiteBackend:
    """Low-level SQLite backend for persistent memories."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get the connection.
        """
        return sqlite3.connect(self.db_path)

# --- MANAGER ---

class MemoryManager:
    """High-level facade for memory operations."""
    def __init__(self, backend: SQLiteBackend):
        self.backend = backend

    def store(self, content: str, title: str = "", tags: list[str] | None = None) -> str:
        """Store a memory in the SQLite database."""
        memory_id = str(uuid.uuid4())
        tag_str = ",".join(tags) if tags else ""
        now = datetime.now().isoformat()
        with self.backend.get_connection() as conn:
            conn.execute(
                """INSERT INTO memories (id, content, title, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (memory_id, content, title, tag_str, now, now),
            )
            conn.commit()
        logger.info(f"Stored memory {memory_id}: {title}")
        return memory_id

# --- SINGLETONS ---
_manager: MemoryManager | None = None

def get_memory_manager() -> MemoryManager:
    """
    Get the memory manager.

    Returns:
        MemoryManager
    """
    global _manager
    if _manager is None:
        from whitemagic.config.paths import DB_PATH
        backend = SQLiteBackend(str(DB_PATH))
        _manager = MemoryManager(backend)
    return _manager
