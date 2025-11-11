"""Embedding cache (Tier 2 - optional)."""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

class EmbeddingCache:
    def __init__(self, database_url: Optional[str] = None):
        self.enabled = HAS_ASYNCPG and database_url
        self.database_url = database_url
        self._pool = None
    
    async def connect(self):
        if self.enabled:
            self._pool = await asyncpg.create_pool(self.database_url)
    
    async def close(self):
        if self._pool:
            await self._pool.close()
    
    async def get(self, memory_id: str) -> Optional[List[float]]:
        if not self.enabled or not self._pool:
            return None
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT embedding FROM memory_embeddings WHERE memory_id = $1",
                    memory_id
                )
                return list(row['embedding']) if row else None
        except:
            return None
    
    async def set(self, memory_id: str, embedding: List[float], 
                  content: str, model: str) -> bool:
        if not self.enabled or not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO memory_embeddings 
                       (memory_id, embedding, content_hash, model, dimensions)
                       VALUES ($1, $2, $3, $4, $5)
                       ON CONFLICT (memory_id) DO UPDATE
                       SET embedding = $2, updated_at = CURRENT_TIMESTAMP""",
                    memory_id, embedding, content[:64], model, len(embedding)
                )
            return True
        except:
            return False
