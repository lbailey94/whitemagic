"""Generic caching utilities for WhiteMagic."""
import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional


class FileCache:
    """Simple file-based cache with mtime invalidation."""
    
    def __init__(self, cache_dir: Path, namespace: str = "default"):
        """
        Initialize cache.
        
        Args:
            cache_dir: Base directory for cache files
            namespace: Namespace for this cache (subdirectory)
        """
        self.cache_dir = Path(cache_dir) / namespace
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Use hash of key as filename to avoid path issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str, source_mtime: Optional[float] = None) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            source_mtime: Source file modification time for invalidation
            
        Returns:
            Cached value or None if not found/invalid
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # Check if cache is stale (source newer than cache)
        if source_mtime is not None:
            cache_mtime = cache_path.stat().st_mtime
            if source_mtime > cache_mtime:
                # Source is newer, cache is stale
                return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            # Corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be picklable)
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
        except Exception:
            # Failed to cache, just continue
            pass
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        cache_path = self._get_cache_path(key)
        cache_path.unlink(missing_ok=True)
    
    def clear(self) -> int:
        """Clear all cache entries. Returns number of deleted files."""
        count = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count
    
    def stats(self) -> dict:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }
