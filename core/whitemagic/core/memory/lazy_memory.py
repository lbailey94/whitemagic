# ruff: noqa: BLE001, F401
#!/usr/bin/env python3
"""
🧠 Lazy Memory System - WhiteMagic v3.0.0
Scalable memory with lazy loading and LRU caching.

Fixes the scalability issue where _load_all() loads everything into RAM.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, cast

from whitemagic.config.paths import WM_ROOT
from whitemagic.core.memory.db_manager import safe_connect


class MemoryType(Enum):
    """Types of memories"""
    SHORT_TERM = auto()
    LONG_TERM = auto()
    EMOTIONAL = auto()
    NARRATIVE = auto()
    SYMBOLIC = auto()
    COLLECTIVE = auto()
    IMMUNE = auto()
    PATTERN = auto()


@dataclass
class MemoryMetadata:
    """Lightweight metadata stored in index"""
    id: str
    memory_type: str
    created_at: str
    importance: float
    tags: list[str]
    content_preview: str  # First 100 chars
    file_path: str


class LazyMemoryStore:
    """
    Scalable memory store with:
    - SQLite index for O(1) lookups
    - Lazy content loading
    - LRU cache for hot memories
    - Minimal RAM footprint
    """

    def __init__(self, base_path: Path | None = None, cache_size: int = 100):
        self.base_path = base_path or WM_ROOT / 'memory_v2'
        self.base_path.mkdir(parents=True, exist_ok=True)

        # SQLite for index
        self.db_path = self.base_path / 'index.db'
        self._init_db()

        # LRU cache for hot memories
        self.cache_size = cache_size
        self._content_cache: dict[str, Any] = {}
        self._cache_order: list[str] = []

        # Stats
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_loads': 0
        }

    def _init_db(self) -> None:
        """Initialize SQLite index"""
        with safe_connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    created_at TEXT,
                    importance REAL,
                    content_preview TEXT,
                    file_path TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    memory_id TEXT,
                    tag TEXT,
                    FOREIGN KEY (memory_id) REFERENCES memories(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON tags(tag)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")

    def _generate_id(self, content: Any) -> str:
        """Generate unique memory ID"""
        content_str = str(content)[:1000]
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{content_str}{timestamp}".encode()).hexdigest()[:16]

    def store(self, content: Any, memory_type: MemoryType = MemoryType.SHORT_TERM,
              tags: set[str] | None = None, importance: float = 0.5,
              metadata: dict | None = None) -> str:
        """Store a memory (content goes to file, metadata to SQLite)"""
        memory_id = self._generate_id(content)
        created_at = datetime.now().isoformat()
        tags = tags or set()

        file_path = self.base_path / f"{memory_id}.json"
        content_data = {
            'id': memory_id,
            'content': content,
            'memory_type': memory_type.name,
            'created_at': created_at,
            'importance': importance,
            'tags': list(tags),
            'metadata': metadata or {}
        }
        with open(file_path, 'w') as f:
            json.dump(content_data, f)

        # Index in SQLite
        content_preview = str(content)[:100] if content else ""
        with safe_connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, memory_type, created_at, importance, content_preview, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (memory_id, memory_type.name, created_at, importance,
                  content_preview, str(file_path)))

            # Index tags
            if tags:
                conn.executemany("INSERT INTO tags (memory_id, tag) VALUES (?, ?)",
                                 [(memory_id, tag) for tag in tags])

        return memory_id

    def recall(self, memory_id: str) -> dict[str, Any] | None:
        """Recall a memory by ID (lazy load from file)"""
        if memory_id in self._content_cache:
            self.stats['cache_hits'] += 1
            # Move to front of LRU
            self._cache_order.remove(memory_id)
            self._cache_order.append(memory_id)
            result = self._content_cache[memory_id]
            return cast(dict[str, Any], result)

        self.stats['cache_misses'] += 1

        file_path = self.base_path / f"{memory_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                content = json.load(f)

            self._add_to_cache(memory_id, content)
            self.stats['total_loads'] += 1

            return cast(dict[str, Any], content)
        except Exception:
            return None

    def _add_to_cache(self, memory_id: str, content: dict[str, Any]) -> None:
        """Add to LRU cache, evicting if necessary"""
        if len(self._cache_order) >= self.cache_size:
            # Evict oldest
            oldest_id = self._cache_order.pop(0)
            del self._content_cache[oldest_id]

        self._content_cache[memory_id] = content
        self._cache_order.append(memory_id)

    def search_by_tag(self, tag: str, limit: int = 10) -> list[MemoryMetadata]:
        """Search memories by tag (O(1) via index)"""
        with safe_connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT m.id, m.memory_type, m.created_at, m.importance,
                       m.content_preview, m.file_path,
                       (SELECT GROUP_CONCAT(t2.tag, '\x1f') FROM tags t2
                        WHERE t2.memory_id = m.id) AS all_tags
                FROM memories m
                JOIN tags t ON m.id = t.memory_id
                WHERE t.tag = ?
                ORDER BY m.importance DESC
                LIMIT ?
            """, (tag, limit))

            results = []
            for row in cursor:
                tags = row[6].split('\x1f') if row[6] else []

                results.append(MemoryMetadata(
                    id=row[0],
                    memory_type=row[1],
                    created_at=row[2],
                    importance=row[3],
                    tags=tags,
                    content_preview=row[4],
                    file_path=row[5]
                ))

            return results

    def search_by_importance(self, min_importance: float = 0.5,
                            limit: int = 10) -> list[MemoryMetadata]:
        """Search memories by importance threshold"""
        with safe_connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT m.id, m.memory_type, m.created_at, m.importance,
                       m.content_preview, m.file_path,
                       (SELECT GROUP_CONCAT(t.tag, '\x1f') FROM tags t
                        WHERE t.memory_id = m.id) AS all_tags
                FROM memories m
                WHERE m.importance >= ?
                ORDER BY m.importance DESC
                LIMIT ?
            """, (min_importance, limit))

            results = []
            for row in cursor:
                tags = row[6].split('\x1f') if row[6] else []

                results.append(MemoryMetadata(
                    id=row[0],
                    memory_type=row[1],
                    created_at=row[2],
                    importance=row[3],
                    tags=tags,
                    content_preview=row[4],
                    file_path=row[5]
                ))

            return results

    def get_count(self) -> int:
        """Get total memory count (O(1))"""
        with safe_connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memories")
            row = cursor.fetchone()
            if row is None:
                return 0
            return int(row[0])

    def get_stats(self) -> dict[str, Any]:
        """Get memory system stats"""
        return {
            'total_memories': self.get_count(),
            'cache_size': len(self._content_cache),
            'cache_capacity': self.cache_size,
            **self.stats
        }

    def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        file_path = self.base_path / f"{memory_id}.json"

        try:
            if memory_id in self._content_cache:
                del self._content_cache[memory_id]
                self._cache_order.remove(memory_id)

            if file_path.exists():
                file_path.unlink()

            with safe_connect(self.db_path) as conn:
                conn.execute("DELETE FROM tags WHERE memory_id = ?", (memory_id,))
                conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

            return True
        except Exception:
            return False


# Singleton
_lazy_store: LazyMemoryStore | None = None


def get_lazy_memory() -> LazyMemoryStore:
    """Get the singleton lazy memory store"""
    global _lazy_store
    if _lazy_store is None:
        _lazy_store = LazyMemoryStore()
    return _lazy_store
