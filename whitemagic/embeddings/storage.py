"""Embedding cache (Tier 2 - optional)."""
import logging
import hashlib
from typing import List, Optional
from pathlib import Path

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


class FileBasedEmbeddingCache:
    """
    File-based embedding cache using mtime invalidation.
    
    Simpler alternative to database cache - no PostgreSQL required.
    Perfect for local-first usage.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize file-based cache.
        
        Args:
            cache_dir: Directory for cache files (default: ~/.whitemagic/cache/embeddings)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".whitemagic" / "cache" / "embeddings"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = True
    
    def _get_cache_key(self, file_path: Path, model: str) -> str:
        """Generate cache key from file path, mtime, and model."""
        mtime = file_path.stat().st_mtime if file_path.exists() else 0
        key_str = f"{file_path}:{mtime}:{model}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a key."""
        return self.cache_dir / f"{cache_key}.emb"
    
    async def get(self, file_path: Path, model: str) -> Optional[List[float]]:
        """
        Get cached embedding for a file.
        
        Args:
            file_path: Path to memory file
            model: Embedding model name
            
        Returns:
            Cached embedding or None if not found/stale
        """
        if not self.enabled or not file_path.exists():
            return None
        
        cache_key = self._get_cache_key(file_path, model)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            import pickle
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.debug(f"Failed to load cache for {file_path}: {e}")
            cache_path.unlink(missing_ok=True)
            return None
    
    async def set(self, file_path: Path, model: str, embedding: List[float]) -> bool:
        """
        Cache embedding for a file.
        
        Args:
            file_path: Path to memory file
            model: Embedding model name
            embedding: Embedding vector to cache
            
        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False
        
        cache_key = self._get_cache_key(file_path, model)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            import pickle
            with open(cache_path, 'wb') as f:
                pickle.dump(embedding, f)
            return True
        except Exception as e:
            logger.debug(f"Failed to cache embedding for {file_path}: {e}")
            return False
    
    def clear(self) -> int:
        """Clear all cached embeddings. Returns number of deleted files."""
        count = 0
        for cache_file in self.cache_dir.glob("*.emb"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count
    
    def stats(self) -> dict:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.emb"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }
