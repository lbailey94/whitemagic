"""Galaxy-aware backend router for WhiteMagic memory.

Routes memory operations to the correct per-galaxy SQLite database
based on the memory's galaxy field. Falls back to the monolithic
database for backward compatibility.

This is the primary write path — all store/recall/search operations
go through here. The router maintains a cache of SQLiteBackend
instances, one per galaxy.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from whitemagic.core.memory.sqlite_backend import SQLiteBackend
from whitemagic.core.memory.unified_types import Memory, MemoryType

logger = logging.getLogger(__name__)


class GalaxyAwareBackend:
    """Routes memory operations to per-galaxy SQLite databases.

    Each galaxy gets its own SQLiteBackend with its own connection pool.
    This isolates corruption risk and reduces lock contention.

    The monolithic database is used as a fallback for memories without
    a galaxy field or for galaxies that don't have a dedicated DB yet.

    Phase 2: The backend cache is now namespaced by ``user_id/galaxy_name``
    so that two users can have identically named galaxies without collision.
    The ``user_id`` defaults to ``"local"`` for backward compatibility.
    """

    def __init__(self, default_db_path: Path, user_id: str = "local") -> None:
        """Initialize with the default (monolithic) database path.

        Args:
            default_db_path: Path to the fallback monolithic database.
            user_id: The user whose galaxies this backend manages.
                Default ``"local"`` for backward compatibility.
        """
        self._default_path = default_db_path
        self._user_id = user_id
        self._default_backend: SQLiteBackend | None = None
        # Cache keys are now "user_id/galaxy_name" for namespace isolation
        self._galaxy_backends: dict[str, SQLiteBackend] = {}
        self._lock = threading.Lock()
        self._galaxies_dir = self._resolve_galaxies_dir()

    def _resolve_galaxies_dir(self) -> Path:
        """Resolve the per-galaxy database directory for this backend's user."""
        import os
        try:
            state_root = os.getenv("WM_STATE_ROOT")
            if state_root:
                galaxies_dir = Path(state_root) / "users" / self._user_id / "galaxies"
            else:
                from whitemagic.core.user_profile import get_user_dir
                user_dir = get_user_dir(self._user_id)
                galaxies_dir = user_dir / "galaxies"
            galaxies_dir.mkdir(parents=True, exist_ok=True)
            return galaxies_dir
        except Exception:
            # Fallback: use memory/galaxies
            return self._default_path.parent / "galaxies"

    def _get_default_backend(self) -> SQLiteBackend:
        """Get or create the default (monolithic) backend."""
        if self._default_backend is None:
            self._default_backend = SQLiteBackend(self._default_path)
        return self._default_backend

    def _get_galaxy_backend(self, galaxy: str) -> SQLiteBackend:
        """Get or create a per-galaxy SQLiteBackend.

        The backend is cached under a namespace key ``user_id/galaxy_name``
        so that two users with the same galaxy name get separate backends.

        Args:
            galaxy: Galaxy name (e.g., 'sessions', 'codex', 'universal').

        Returns:
            SQLiteBackend for the galaxy's database.
        """
        cache_key = f"{self._user_id}/{galaxy}"
        if cache_key in self._galaxy_backends:
            return self._galaxy_backends[cache_key]

        with self._lock:
            if cache_key in self._galaxy_backends:
                return self._galaxy_backends[cache_key]

            # Validate and sanitize galaxy name for filesystem
            from whitemagic.core.memory.backends.protocol import validate_galaxy_name
            safe_name = validate_galaxy_name(galaxy)
            galaxy_dir = self._galaxies_dir / safe_name
            galaxy_dir.mkdir(parents=True, exist_ok=True)
            db_path = galaxy_dir / "whitemagic.db"

            backend = SQLiteBackend(db_path)
            self._galaxy_backends[cache_key] = backend
            logger.debug("Created per-galaxy backend for '%s' (user='%s') at %s", galaxy, self._user_id, db_path)
            return backend

    def _discover_galaxy_backends(self) -> None:
        """Discover and register all galaxy DBs on disk for this user."""
        try:
            if not self._galaxies_dir.exists():
                return
            for galaxy_dir in self._galaxies_dir.iterdir():
                if not galaxy_dir.is_dir():
                    continue
                name = galaxy_dir.name
                cache_key = f"{self._user_id}/{name}"
                if cache_key in self._galaxy_backends:
                    continue
                db_path = galaxy_dir / "whitemagic.db"
                if db_path.exists():
                    self._galaxy_backends[cache_key] = SQLiteBackend(db_path)
                    logger.debug("Discovered galaxy backend: %s (user='%s')", name, self._user_id)
        except Exception as e:
            logger.debug("Galaxy discovery failed: %s", e)

    def _get_backend_for_memory(self, memory: Memory) -> SQLiteBackend:
        """Determine which backend to use for a memory.

        If the memory has a galaxy and a per-galaxy DB exists (or can
        be created), use that. Otherwise fall back to the default.
        """
        galaxy = getattr(memory, 'galaxy', 'universal')
        if not galaxy or galaxy == 'default':
            galaxy = 'universal'

        # Always use per-galaxy routing — this is the fix for corruption
        return self._get_galaxy_backend(galaxy)

    def _get_backend_for_galaxy(self, galaxy: str | None) -> SQLiteBackend:
        """Get backend for a galaxy name, or default if None."""
        if not galaxy:
            return self._get_default_backend()
        if galaxy == 'default':
            galaxy = 'universal'
        return self._get_galaxy_backend(galaxy)

    # ── Store/recall/search — delegate to the appropriate backend ────────

    def store(self, memory: Memory, content_hash: str | None = None) -> str:
        """Store a memory in the appropriate galaxy database."""
        backend = self._get_backend_for_memory(memory)
        return backend.store(memory, content_hash=content_hash)

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a memory by ID.

        Searches the default backend first, then all galaxy backends
        (including ones not yet cached but present on disk).
        """
        # Try default first (backward compat)
        result = self._get_default_backend().recall(memory_id)
        if result:
            return result

        # Try all cached galaxy backends
        for backend in self._galaxy_backends.values():
            result = backend.recall(memory_id)
            if result:
                return result

        # Check for galaxy DBs on disk that aren't cached yet
        try:
            if self._galaxies_dir.exists():
                for galaxy_dir in self._galaxies_dir.iterdir():
                    if not galaxy_dir.is_dir():
                        continue
                    gname = galaxy_dir.name
                    if gname in self._galaxy_backends:
                        continue  # Already checked
                    db_file = galaxy_dir / "whitemagic.db"
                    if db_file.exists():
                        backend = self._get_galaxy_backend(gname)
                        result = backend.recall(memory_id)
                        if result:
                            return result
        except Exception:
            pass

        return None

    def search(
        self,
        query: str = "",
        tags: set[str] | None = None,
        memory_type: MemoryType | str | None = None,
        limit: int = 20,
        galaxy: str | None = None,
        min_importance: float = 0.0,
        **kwargs: Any,
    ) -> list[Memory]:
        """Search memories.

        If galaxy is specified, search only that galaxy's database.
        If galaxy is None, search all galaxy databases and merge results.
        """
        if galaxy:
            backend = self._get_backend_for_galaxy(galaxy)
            return backend.search(
                query=query, tags=tags, memory_type=memory_type,
                limit=limit, min_importance=min_importance, **kwargs,
            )

        # Search all backends and merge
        all_results: list[Memory] = []
        backends_to_search = [self._get_default_backend()] + list(self._galaxy_backends.values())

        for backend in backends_to_search:
            try:
                results = backend.search(
                    query=query, tags=tags, memory_type=memory_type,
                    limit=limit, min_importance=min_importance, **kwargs,
                )
                all_results.extend(results)
            except Exception as e:
                logger.debug("Search failed in backend %s: %s", backend.db_path, e, exc_info=True)

        # Sort by importance and limit
        all_results.sort(key=lambda m: m.importance, reverse=True)
        return all_results[:limit]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory from whichever backend has it."""
        # Try default first
        if self._get_default_backend().delete(memory_id):
            return True

        # Try galaxy backends
        for backend in self._galaxy_backends.values():
            if backend.delete(memory_id):
                return True
        return False

    def find_by_content_hash(self, content_hash: str) -> str | None:
        """Find a memory by content hash across all backends."""
        # Try default first
        result = self._get_default_backend().find_by_content_hash(content_hash)
        if result:
            return result

        # Try galaxy backends
        for backend in self._galaxy_backends.values():
            result = backend.find_by_content_hash(content_hash)
            if result:
                return result
        return None

    def get_stats(self) -> dict[str, Any]:
        """Aggregate stats across all backends."""
        total = 0
        by_galaxy: dict[str, int] = {}

        # Default backend
        default_stats = self._get_default_backend().get_stats()
        total += default_stats.get("total_memories", 0)
        by_galaxy["(default)"] = default_stats.get("total_memories", 0)

        # Galaxy backends
        for galaxy_name, backend in self._galaxy_backends.items():
            stats = backend.get_stats()
            count = stats.get("total_memories", 0)
            total += count
            by_galaxy[galaxy_name] = count

        return {
            "total_memories": total,
            "by_galaxy": by_galaxy,
            "backend": "galaxy-aware-sqlite",
            "galaxy_count": len(self._galaxy_backends),
        }

    def store_coords(self, memory_id: str, x: float, y: float, z: float, w: float, v: float, u: float = 0.5, galaxy: str | None = None) -> None:
        """Store coordinates in the correct galaxy database.

        If galaxy is known, store directly in that galaxy's DB.
        Otherwise, search all galaxy backends for the memory_id to find the right one.
        Falls back to default backend if the memory can't be located.
        """
        if galaxy and galaxy != "universal":
            backend = self._get_galaxy_backend(galaxy)
            try:
                backend.store_coords(memory_id, x, y, z, w, v, u)
            except sqlite3.IntegrityError:
                logger.warning("FK violation storing coords for %s in galaxy '%s' — memory may not be committed yet", memory_id, galaxy)
            return

        # No galaxy specified — try to find which galaxy DB has this memory
        for gname, gbackend in self._galaxy_backends.items():
            try:
                if gbackend.recall(memory_id):
                    gbackend.store_coords(memory_id, x, y, z, w, v, u)
                    return
            except Exception:
                continue

        # Fallback: try default backend (may fail with FK if memory is in a galaxy DB)
        try:
            self._get_default_backend().store_coords(memory_id, x, y, z, w, v, u)
        except sqlite3.IntegrityError:
            logger.warning("FK violation storing coords for %s in default DB — memory likely in a galaxy DB", memory_id)

    def integrity_check(self) -> str:
        """Check integrity of all backends."""
        results = []
        default_result = self._get_default_backend().pool.integrity_check()
        if default_result != "ok":
            results.append(f"default: {default_result}")

        for name, backend in self._galaxy_backends.items():
            result = backend.pool.integrity_check()
            if result != "ok":
                results.append(f"{name}: {result}")

        return "; ".join(results) if results else "ok"

    def quick_integrity_check(self) -> bool:
        """Quick integrity check across all backends."""
        if not self._get_default_backend().pool.quick_integrity_check():
            return False
        for backend in self._galaxy_backends.values():
            if not backend.pool.quick_integrity_check():
                return False
        return True

    def close(self) -> None:
        """Close all backend connections."""
        if self._default_backend is not None:
            self._default_backend.pool.close_all()
        for backend in self._galaxy_backends.values():
            backend.pool.close_all()

    # ── Transparent delegation for SQLiteBackend-specific methods ──────

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the default SQLiteBackend.

        This allows consumers that call SQLiteBackend-specific methods
        (e.g. ``_init_db``, ``get_dharma_stats``, ``rebuild_fts``,
        ``archive_to_edge``, ``decay_associations``) to transparently
        work through the galaxy-aware backend without explicit proxying.

        Galaxy-aware operations (store, recall, search, delete, etc.)
        are explicitly defined above and take precedence.
        """
        # Avoid recursion for internal attributes
        if name.startswith("_") and name not in ("_init_db", "_auto_backup", "_row_to_memory", "_batch_hydrate", "_get_cold_pool", "_recall_from_pool"):
            raise AttributeError(f"'GalaxyAwareBackend' object has no attribute '{name}'")
        # Delegate to the default backend
        default = self.__dict__.get("_default_backend")
        if default is None:
            default = self._get_default_backend()
        attr = getattr(default, name)
        return attr

    @property
    def pool(self) -> Any:
        """Proxy to the default backend's pool for backward compatibility.

        Subsystems that call um.backend.pool.connection() get the
        default (monolith) backend's connection pool. Galaxy-aware
        code should use the proxied methods instead.
        """
        return self._get_default_backend().pool

    @property
    def db_path(self) -> Path:
        """Proxy to the default backend's db_path."""
        return self._default_path

    # ── Galaxy management ─────────────────────────────────────────────

    def list_galaxies(self) -> list[str]:
        """List all galaxies that have backends for this user."""
        # Strip the user_id prefix from cache keys for the caller
        prefix = f"{self._user_id}/"
        return [
            k[len(prefix):] if k.startswith(prefix) else k
            for k in self._galaxy_backends.keys()
        ]

    def get_galaxy_db_path(self, galaxy: str) -> Path:
        """Get the database path for a galaxy."""
        from whitemagic.core.memory.backends.protocol import validate_galaxy_name
        safe_name = validate_galaxy_name(galaxy)
        return self._galaxies_dir / safe_name / "whitemagic.db"

    def preload_galaxy(self, galaxy: str) -> None:
        """Preload a galaxy backend (creates the DB if it doesn't exist)."""
        self._get_galaxy_backend(galaxy)

    # ── Proxied SQLiteBackend methods ───────────────────────────────

    def add_association(self, source_id: str, target_id: str, strength: float = 0.5) -> bool:
        """Add an association edge — finds which galaxy has the source memory."""
        for gname, gbackend in self._galaxy_backends.items():
            try:
                if gbackend.recall(source_id):
                    return gbackend.add_association(source_id, target_id, strength)
            except Exception:
                continue
        return self._get_default_backend().add_association(source_id, target_id, strength)

    def get_coords(self, memory_id: str) -> tuple | None:
        """Get holographic coordinates — searches all backends."""
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                coords = gbackend.get_coords(memory_id)
                if coords:
                    return coords
            except Exception:
                continue
        return None

    def get_all_coords(self) -> dict[str, tuple]:
        """Get all holographic coordinates across all galaxy backends."""
        all_coords: dict[str, tuple] = {}
        # Default backend first
        try:
            all_coords.update(self._get_default_backend().get_all_coords())
        except Exception as e:
            logger.debug("get_all_coords failed for default backend: %s", e)
        # Galaxy backends
        for gbackend in self._galaxy_backends.values():
            try:
                all_coords.update(gbackend.get_all_coords())
            except Exception as e:
                logger.debug("get_all_coords failed for galaxy backend: %s", e)
        return all_coords

    def list_recent(self, limit: int = 10, memory_type: Any = None, galaxy: str | None = None) -> list:
        """List recent memories across all galaxy backends."""
        if galaxy:
            return self._get_backend_for_galaxy(galaxy).list_recent(limit=limit, memory_type=memory_type)
        all_mems: list = []
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                all_mems.extend(gbackend.list_recent(limit=limit, memory_type=memory_type))
            except Exception:
                continue
        def _sort_key(m):
            ts = getattr(m, "created_at", None)
            if ts is None:
                return ""
            # Normalize offset-aware datetimes to offset-naive for comparison
            if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                return ts.replace(tzinfo=None)
            return ts
        all_mems.sort(key=_sort_key, reverse=True)
        return all_mems[:limit]

    def update_galactic_distance(self, memory_id: str, distance: float) -> bool:
        """Update galactic distance — finds which galaxy has the memory."""
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                if gbackend.recall(memory_id):
                    return gbackend.update_galactic_distance(memory_id, distance)
            except Exception:
                continue
        return self._get_default_backend().update_galactic_distance(memory_id, distance)

    def rebuild_fts(self, batch_size: int = 500) -> int:
        """Rebuild FTS5 index across all backends."""
        total = 0
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                total += gbackend.rebuild_fts(batch_size=batch_size)
            except Exception as e:
                logger.debug("FTS rebuild failed for backend: %s", e)
        return total

    def decay_associations(self, batch_size: int = 5000) -> dict[str, Any]:
        """Decay associations across all backends."""
        total_decayed = 0
        total_pruned = 0
        total_evaluated = 0
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                result = gbackend.decay_associations(batch_size=batch_size)
                total_decayed += result.get("associations_decayed", 0)
                total_pruned += result.get("associations_pruned", 0)
                total_evaluated += result.get("associations_evaluated", 0)
            except Exception:
                continue
        return {
            "status": "success",
            "associations_evaluated": total_evaluated,
            "associations_decayed": total_decayed,
            "associations_pruned": total_pruned,
        }

    def prune_associations(self, min_strength: float = 0.3) -> dict[str, Any]:
        """Prune weak associations across all backends."""
        total_pruned = 0
        total_remaining = 0
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                result = gbackend.prune_associations(min_strength=min_strength)
                total_pruned += result.get("pruned", 0)
                total_remaining += result.get("remaining", 0)
            except Exception:
                continue
        return {
            "status": "success",
            "pruned": total_pruned,
            "remaining": total_remaining,
        }

    def archive_to_edge(self, memory_id: str, galactic_distance: float = 0.95) -> bool:
        """Archive a memory to the galactic edge — finds which galaxy has it."""
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                if gbackend.recall(memory_id):
                    return gbackend.archive_to_edge(memory_id, galactic_distance)
            except Exception:
                continue
        return self._get_default_backend().archive_to_edge(memory_id, galactic_distance)

    def update_retention_score(self, memory_id: str, score: float) -> bool:
        """Update retention score — finds which galaxy has the memory."""
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                if gbackend.recall(memory_id):
                    return gbackend.update_retention_score(memory_id, score)
            except Exception:
                continue
        return self._get_default_backend().update_retention_score(memory_id, score)

    def batch_update_galactic(self, updates: list) -> int:
        """Batch update galactic distances — routes per-memory."""
        updated = 0
        for memory_id, distance, score in updates:
            try:
                if self.update_galactic_distance(memory_id, distance):
                    if score is not None:
                        self.update_retention_score(memory_id, score)
                    updated += 1
            except Exception:
                continue
        return updated

    def fetch_memory_contents(self, memory_type: Any = None, limit: int = 10000) -> list[str]:
        """Fetch memory contents across all backends."""
        # Discover all galaxy DBs on disk, not just lazily-loaded ones
        self._discover_galaxy_backends()
        all_contents: list[str] = []
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                all_contents.extend(gbackend.fetch_memory_contents(memory_type=memory_type, limit=limit))
            except Exception:
                continue
        return all_contents[:limit]

    def get_weakest_memories(self, limit: int = 100) -> list:
        """Get weakest memories across all backends."""
        all_mems: list = []
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                all_mems.extend(gbackend.get_weakest_memories(limit=limit))
            except Exception:
                continue
        all_mems.sort(key=lambda m: getattr(m, "neuro_score", 1.0))
        return all_mems[:limit]

    def get_all_coords(self) -> dict[str, tuple]:
        """Get all coordinates from all backends (merged)."""
        all_coords: dict[str, tuple] = {}
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                all_coords.update(gbackend.get_all_coords())
            except Exception:
                continue
        return all_coords

    def get_constellation_memberships(self, memory_id: str) -> list:
        """Get constellation memberships — searches all backends."""
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                memberships = gbackend.get_constellation_memberships(memory_id)
                if memberships:
                    return memberships
            except Exception:
                continue
        return []

    def consolidate(self) -> int:
        """Consolidate memories across all backends."""
        total = 0
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                total += gbackend.consolidate()
            except Exception:
                continue
        return total

    def list_accessed(self, limit: int = 10) -> list:
        """List recently accessed memories across all backends."""
        all_mems: list = []
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                all_mems.extend(gbackend.list_accessed(limit=limit))
            except Exception:
                continue
        all_mems.sort(key=lambda m: getattr(m, "accessed_at", ""), reverse=True)
        return all_mems[:limit]

    def get_tag_counts(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get tag counts across all backends."""
        tag_map: dict[str, int] = {}
        for gbackend in list(self._galaxy_backends.values()) + [self._get_default_backend()]:
            try:
                for tag, count in gbackend.get_tag_counts(limit=limit * 3):
                    tag_map[tag] = tag_map.get(tag, 0) + count
            except Exception:
                continue
        return sorted(tag_map.items(), key=lambda x: x[1], reverse=True)[:limit]
