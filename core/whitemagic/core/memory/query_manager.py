"""Query Manager — Search, list, and query operations for SQLite backend.

Handles FTS5 search, pagination, and memory listing operations.
Extracted from sqlite_backend.py for better separation of concerns.
"""

import logging
import re
import sqlite3
from collections.abc import Generator
from typing import Any

from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)


class QueryManager:
    """Manages query operations for SQLite backend."""

    def __init__(self, pool, batch_hydrate_fn):
        self.pool = pool
        self._batch_hydrate = batch_hydrate_fn

    def search(self, query: str | None = None, tags: set[str] | None = None,
               memory_type: MemoryType | None = None, min_importance: float = 0.0,
               limit: int = 10) -> list[Memory]:
        """Search memories with FTS5 BM25 ranking."""
        with self.pool.connection() as conn:
            conn.row_factory = sqlite3.Row

            if query:
                # FTS search with BM25 ranking (lower rank = better match)
                fts_query = query.strip()
                # Sanitize FTS5-unsafe characters - keep only alphanumeric and spaces
                fts_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', fts_query)
                fts_query = fts_query.strip()

                if not fts_query:
                    # Fallback if sanitization stripped everything
                    fts_query = "memory"

                # Split into keywords and join with OR for broad matching
                keywords = [k for k in fts_query.split() if len(k) > 1]
                if keywords:
                    # Use a combination of phrase and individual keywords
                    fts_query = f'"{ " ".join(keywords) }" OR {" OR ".join(keywords)}'
                else:
                    fts_query = f'"{fts_query}"'

                sql = """
                    SELECT m.*, fts.rank
                    FROM memories m
                    JOIN (
                        SELECT id, bm25(memories_fts, 10.0, 1.0, 5.0) as rank
                        FROM memories_fts
                        WHERE memories_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    ) fts ON m.id = fts.id
                    WHERE m.importance >= ?
                      AND m.memory_type != 'quarantined'
                """
                params = [fts_query, limit * 3, min_importance]

                if memory_type:
                    sql += " AND m.memory_type = ?"
                    params.append(memory_type.name)

                if tags:
                    placeholders = ",".join("?" * len(tags))
                    sql += f" AND m.id IN (SELECT memory_id FROM tags WHERE tag IN ({placeholders}) GROUP BY memory_id HAVING COUNT(DISTINCT tag) = ?)"
                    params.extend(tags)
                    params.append(len(tags))

                # Order by FTS rank (relevance) weighted by galactic proximity
                sql += " ORDER BY (ABS(fts.rank) * (0.5 + COALESCE(m.galactic_distance, 0.5))) ASC, m.importance DESC LIMIT ?"
                params.append(limit)

            else:
                # No query: return recent/important memories
                sql = "SELECT * FROM memories WHERE importance >= ? AND memory_type != 'quarantined'"
                params = [min_importance]

                if memory_type:
                    sql += " AND memory_type = ?"
                    params.append(memory_type.name)

                if tags:
                    placeholders = ",".join("?" * len(tags))
                    sql += f" AND id IN (SELECT memory_id FROM tags WHERE tag IN ({placeholders}) GROUP BY memory_id HAVING COUNT(DISTINCT tag) = ?)"
                    params.extend(tags)
                    params.append(len(tags))

                sql += " ORDER BY COALESCE(galactic_distance, 0.5) ASC, importance DESC, accessed_at DESC LIMIT ?"
                params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return self._batch_hydrate(rows, conn)

    def get_weakest_memories(self, limit: int = 100) -> list[Memory]:
        """Retrieve memories with the lowest neuro_score first."""
        with self.pool.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE is_protected = 0 AND memory_type != 'quarantined' ORDER BY neuro_score ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return self._batch_hydrate(rows, conn)

    def list_recent(self, limit: int = 10, memory_type: MemoryType | None = None) -> list[Memory]:
        """List recent memories."""
        with self.pool.connection() as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM memories WHERE memory_type != 'quarantined'"
            params: list[Any] = []

            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.name)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return self._batch_hydrate(rows, conn)

    def list_all_paginated(self, batch_size: int = 2000) -> Generator[list[Memory], None, None]:
        """Yield ALL memories in batches via OFFSET/LIMIT pagination."""
        offset = 0
        while True:
            with self.pool.connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM memories WHERE memory_type != 'quarantined' ORDER BY rowid LIMIT ? OFFSET ?",
                    (batch_size, offset),
                ).fetchall()
                if not rows:
                    break
                batch = self._batch_hydrate(rows, conn)
            yield batch
            offset += batch_size
            if len(rows) < batch_size:
                break

    def list_accessed(self, limit: int = 10) -> list[Memory]:
        """List recently accessed memories."""
        with self.pool.connection() as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM memories WHERE memory_type != 'quarantined' ORDER BY accessed_at DESC LIMIT ?"
            rows = conn.execute(sql, (limit,)).fetchall()
            return self._batch_hydrate(rows, conn)
