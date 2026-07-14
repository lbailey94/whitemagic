# ruff: noqa: BLE001
"""Multi-Galaxy Memory Manager
================================
Enables project-scoped memory databases ("galaxies") so WhiteMagic can
maintain separate knowledge bases for different projects, archives, or
domains while sharing the same cognitive infrastructure.

Architecture:
- Each galaxy is a separate SQLite database with its own holographic index
- A galaxy registry (JSON) tracks all known galaxies
- One galaxy is "active" at a time for tool dispatch
- The "core" galaxy ships with WhiteMagic (quickstart/tutorial memories)
- Users can create galaxies for any project folder

Usage via MCP:
  gana_void → tool: galaxy.create   args: {name, path, description}
  gana_void → tool: galaxy.switch   args: {name}
  gana_void → tool: galaxy.list
  gana_void → tool: galaxy.status
  gana_void → tool: galaxy.ingest   args: {name, source_path, pattern}
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import MEMORY_DIR, WM_ROOT
from whitemagic.core.user_profile import get_user_dir, resolve_user_id
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current UTC time as ISO string."""
    from datetime import datetime
    return datetime.now().isoformat()

# Registry file location
_REGISTRY_PATH = WM_ROOT / "galaxies.json"


@dataclass
class GalaxyInfo:
    """Metadata for a single galaxy."""

    name: str
    db_path: str
    description: str = ""
    project_path: str | None = None
    created_at: float = field(default_factory=time.time)
    memory_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    is_core: bool = False
    user_id: str = "local"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GalaxyInfo:
        """
        Convert to/from m dict.

        Args:
            cls: Parameter description.
            d: Parameter description.

        Returns:
            GalaxyInfo
        """
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class GalaxyManager:
    """Manages multiple memory galaxies (project-scoped databases).

    Thread-safe singleton that maintains a registry of galaxies and
    provides switching between them.
    """

    _instance: GalaxyManager | None = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._galaxies: dict[str, GalaxyInfo] = {}
        self._active_galaxy: str = "local/default"
        self._memory_instances: dict[str, Any] = {}  # Lazy UnifiedMemory per galaxy
        self._load_registry()

    @classmethod
    def get_instance(cls) -> GalaxyManager:
        """
        Get the instance.

        Args:
            cls: Parameter description.

        Returns:
            GalaxyManager
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Registry persistence ────────────────────────────────────────

    def _load_registry(self) -> None:
        """Load galaxy registry from disk."""
        if _REGISTRY_PATH.exists():
            try:
                data = _json_loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
                for name, info_dict in data.get("galaxies", {}).items():
                    info = GalaxyInfo.from_dict(info_dict)
                    # Migrate old entries: if key has no "/", prefix with "local/"
                    if "/" not in name:
                        registry_key = f"local/{name}"
                    else:
                        registry_key = name
                    # Ensure user_id is set (backward compat with old registries)
                    if not info.user_id:
                        info.user_id = "local"
                    self._galaxies[registry_key] = info
                # Migrate active_galaxy key
                active = data.get("active", "default")
                if "/" not in active:
                    self._active_galaxy = f"local/{active}"
                else:
                    self._active_galaxy = active
            except Exception as e:
                logger.warning("Failed to load galaxy registry: %s", e, exc_info=True)

        # Ensure "local/default" galaxy always exists
        if "local/default" not in self._galaxies:
            default_db = str(MEMORY_DIR / "whitemagic.db")
            self._galaxies["local/default"] = GalaxyInfo(
                name="default",
                db_path=default_db,
                description="Primary WhiteMagic galaxy — system knowledge and personal memories",
                is_core=False,
                user_id="local",
            )
            self._save_registry()

    def _save_registry(self) -> None:
        """Persist galaxy registry to disk."""
        data = {
            "active": self._active_galaxy,
            "galaxies": {name: info.to_dict() for name, info in self._galaxies.items()},
        }
        try:
            _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
            _REGISTRY_PATH.write_text(_json_dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save galaxy registry: %s", e, exc_info=True)

    # ── Galaxy CRUD ─────────────────────────────────────────────────

    def create_galaxy(
        self,
        name: str,
        project_path: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
        user_id: str | None = None,
    ) -> GalaxyInfo:
        """Create a new galaxy with its own database.

        Args:
            name: Galaxy name (unique within the user's namespace).
            project_path: Optional project path this galaxy is associated with.
            description: Human-readable description.
            tags: Optional tags for the galaxy.
            user_id: Owner user ID. Defaults to ``"local"``.
        """
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if registry_key in self._galaxies:
            raise ValueError(f"Galaxy '{name}' already exists for user '{uid}'")

        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

        # Galaxy DB lives in user's namespace directory
        user_galaxies_dir = get_user_dir(uid) / "galaxies" / safe_name
        user_galaxies_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(user_galaxies_dir / "whitemagic.db")

        info = GalaxyInfo(
            name=name,
            db_path=db_path,
            description=description or f"Galaxy for {project_path or name}",
            project_path=project_path,
            tags=tags or [],
            user_id=uid,
        )

        self._galaxies[registry_key] = info
        self._save_registry()

        # Pre-initialize the database
        self._get_memory(registry_key)
        info.memory_count = 0

        logger.info("Created galaxy '%s' for user '%s' at %s", name, uid, db_path)

        # Publish sync event (best-effort, non-blocking)
        try:
            from whitemagic.core.memory.galaxy_sync import publish_galaxy_event
            publish_galaxy_event("galaxy.created", uid, name, {"db_path": db_path})
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

        return info

    def delete_galaxy(self, name: str, user_id: str | None = None) -> bool:
        """Remove a galaxy from the registry (does NOT delete the database file)."""
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if name == "default" and uid == "local":
            raise ValueError("Cannot delete the default galaxy")
        if registry_key not in self._galaxies:
            raise ValueError(f"Galaxy '{name}' not found for user '{uid}'")
        if self._active_galaxy == registry_key:
            self._active_galaxy = "local/default"

        self._memory_instances.pop(registry_key, None)
        del self._galaxies[registry_key]
        self._save_registry()

        # Publish sync event (best-effort, non-blocking)
        try:
            from whitemagic.core.memory.galaxy_sync import publish_galaxy_event
            publish_galaxy_event("galaxy.deleted", uid, name)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

        return True

    def list_galaxies(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List all known galaxies with their metadata.

        Args:
            user_id: If provided, only list galaxies for this user.
        """
        uid = resolve_user_id(user_id) if user_id else None
        result = []
        for registry_key, info in sorted(self._galaxies.items()):
            if uid is not None and info.user_id != uid:
                continue
            d = info.to_dict()
            d["is_active"] = registry_key == self._active_galaxy
            try:
                um = self._get_memory(registry_key)
                stats = um.get_stats()
                d["memory_count"] = stats.get("total_memories", 0)
                info.memory_count = d["memory_count"]
            except Exception as e:
                logger.debug("Galaxy stats lookup failed for %s: %s", registry_key, e, exc_info=True)
            result.append(d)
        return result

    def switch_galaxy(self, name: str, user_id: str | None = None) -> GalaxyInfo:
        """Switch the active galaxy.

        .. deprecated:: Phase 2
n            Global active-galaxy mutation is unsafe for concurrent requests.
            Use :meth:`get_memory_for_galaxy` for request-scoped access.
            This method remains for CLI/admin use only.

        Args:
            name: Galaxy name to switch to.
            user_id: Owner user ID. Defaults to ``"local"``.
        """
        import warnings
        warnings.warn(
            "switch_galaxy() mutates process-global state and is unsafe for "
            "concurrent requests. Use get_memory_for_galaxy() for request-scoped "
            "galaxy access.",
            DeprecationWarning,
            stacklevel=2,
        )

        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if registry_key not in self._galaxies:
            available = [k for k in self._galaxies if k.startswith(f"{uid}/")]
            raise ValueError(f"Galaxy '{name}' not found for user '{uid}'. Available: {available}")

        self._active_galaxy = registry_key
        self._galaxies[registry_key].last_accessed = time.time()
        self._save_registry()

        # Reset the global singleton so next get_unified_memory() uses the new galaxy
        self._reset_global_memory(registry_key)

        logger.info("Switched to galaxy '%s' for user '%s'", name, uid)

        # Publish sync event (best-effort, non-blocking)
        try:
            from whitemagic.core.memory.galaxy_sync import publish_galaxy_event
            publish_galaxy_event("galaxy.switched", uid, name)
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

        return self._galaxies[registry_key]

    def get_active(self) -> GalaxyInfo:
        """Get the currently active galaxy.

        .. note:: This returns process-global state. For request-scoped
            access, use :meth:`get_galaxy` with an explicit ``user_id``.
        """
        return self._galaxies.get(self._active_galaxy, self._galaxies["local/default"])

    def get_galaxy(self, name: str, user_id: str | None = None) -> GalaxyInfo | None:
        """Get galaxy info by name.

        Args:
            name: Galaxy name.
            user_id: Owner user ID. Defaults to ``"local"``.
        """
        uid = resolve_user_id(user_id)
        return self._galaxies.get(f"{uid}/{name}")

    def get_memory_for_galaxy(
        self, name: str, user_id: str | None = None
    ) -> Any:
        """Get a UnifiedMemory instance for a specific galaxy without mutating
        global active-galaxy state.

        This is the request-scoped replacement for ``switch_galaxy()``.
        It returns a UnifiedMemory instance for the requested galaxy,
        creating one if needed, without changing the process-global
        ``_active_galaxy`` or resetting the global singleton.

        Args:
            name: Galaxy name.
            user_id: Owner user ID. Defaults to ``"local"``.

        Returns:
            UnifiedMemory instance for the requested galaxy.

        Raises:
            ValueError: If the galaxy does not exist for the given user.
        """
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if registry_key not in self._galaxies:
            available = [k.split("/", 1)[1] for k in self._galaxies if k.startswith(f"{uid}/")]
            raise ValueError(
                f"Galaxy '{name}' not found for user '{uid}'. Available: {available}"
            )
        # Update last_accessed (non-mutating to _active_galaxy)
        self._galaxies[registry_key].last_accessed = time.time()
        return self._get_memory(registry_key)

    def galaxy_context(
        self, name: str, user_id: str | None = None
    ) -> Any:
        """Context manager for request-scoped galaxy access.

        Yields a UnifiedMemory instance for the requested galaxy.
        Does NOT mutate global active-galaxy state.

        Usage::

            with gm.galaxy_context("codex", user_id="alice") as um:
                um.store(...)
                results = um.search(...)

        Args:
            name: Galaxy name.
            user_id: Owner user ID. Defaults to ``"local"``.

        Yields:
            UnifiedMemory instance for the requested galaxy.
        """
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            um = self.get_memory_for_galaxy(name, user_id=user_id)
            yield um

        return _ctx()

    # ── Galactic Telepathy (v15.3) ─────────────────────────────────

    def transfer_memories(
        self,
        source_galaxy: str,
        target_galaxy: str,
        query: str | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        max_galactic_distance: float = 1.0,
        limit: int = 500,
        copy: bool = True,
    ) -> dict[str, Any]:
        """Transfer memories between galaxies with coordinate re-mapping.

        Supports selective transfer by query, tags, importance threshold,
        or galactic distance band.  Content-hash dedup prevents duplicates.

        Args:
            source_galaxy: Name of the source galaxy.
            target_galaxy: Name of the target galaxy.
            query: Optional FTS query to select memories.
            tags: Optional tag filter (memories must have ALL listed tags).
            min_importance: Minimum importance threshold.
            max_galactic_distance: Maximum galactic distance (band filter).
            limit: Maximum number of memories to transfer.
            copy: If True, keep originals in source. If False, archive them.

        Returns:
            Summary dict with counts and any errors.
        """
        import hashlib

        if source_galaxy not in self._galaxies:
            raise ValueError(f"Source galaxy '{source_galaxy}' not found")
        if target_galaxy not in self._galaxies:
            raise ValueError(f"Target galaxy '{target_galaxy}' not found")
        if source_galaxy == target_galaxy:
            raise ValueError("Source and target galaxies must be different")

        src_um = self._get_memory(source_galaxy)
        tgt_um = self._get_memory(target_galaxy)

        # Select memories from source
        candidates: list[Any] = []
        if query:
            candidates = src_um.search(query=query, limit=limit)
        else:
            candidates = src_um.search(
                query=None, tags=set(tags) if tags else None,
                min_importance=min_importance, limit=limit,
            )

        # Filter by galactic distance
        if max_galactic_distance < 1.0:
            candidates = [
                m for m in candidates
                if (m.galactic_distance or 0.0) <= max_galactic_distance
            ]

        transferred = 0
        skipped_dedup = 0
        errors = 0

        for mem in candidates[:
            limit]:
            # Content-hash dedup check in target
            content_str = str(mem.content)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()

            try:
                existing = tgt_um.find_by_content_hash(content_hash)
                if existing:
                    skipped_dedup += 1
                    continue
            except Exception as e:
                logger.debug("Dedup check failed: %s", e)

            try:
                # Re-encode coordinates for target galaxy's space
                new_mem = tgt_um.store(
                    content=mem.content,
                    memory_type=mem.memory_type,
                    tags=mem.tags | {f"transferred_from:{source_galaxy}"},
                    emotional_valence=mem.emotional_valence,
                    importance=mem.importance,
                    metadata={
                        **mem.metadata,
                        "source_galaxy": source_galaxy,
                        "source_id": mem.id,
                        "transferred_at": _now_iso(),
                    },
                    title=mem.title,
                )

                # Copy typed associations between transferred memories
                try:
                    with src_um.pool.connection() as conn:
                        conn.row_factory = __import__("sqlite3").Row
                        assocs = conn.execute(
                            """SELECT target_id, strength, direction, relation_type,
                                      edge_type
                               FROM associations
                               WHERE source_id = ?
                               AND relation_type != 'associated_with'""",
                            (mem.id,),
                        ).fetchall()
                        if assocs:
                            now = _now_iso()
                            with tgt_um.pool.connection() as tconn:
                                for a in assocs:
                                    try:
                                        tconn.execute(
                                            """INSERT OR IGNORE INTO associations
                                               (source_id, target_id, strength,
                                                direction, relation_type, edge_type,
                                                created_at, ingestion_time)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (new_mem.id, a["target_id"],
                                             a["strength"], a["direction"],
                                             a["relation_type"], a["edge_type"],
                                             now, now),
                                        )
                                    except Exception as e:
                                        logger.debug("Association copy insert failed: %s", e)
                                tconn.commit()
                except Exception as e:
                    logger.debug("Association copy failed: %s", e)  # Association copy is best-effort

                # Record phylogenetic lineage edge (cross-galaxy bridge)
                try:
                    from whitemagic.core.memory.phylogenetics import get_phylogenetics
                    pg = get_phylogenetics()
                    pg.record_transfer(
                        source_id=mem.id,
                        source_galaxy=source_galaxy,
                        target_galaxy=target_galaxy,
                        target_id=new_mem.id,
                        mechanism="galaxy.transfer",
                    )
                except (ImportError, AttributeError):
                    logger.debug("Optional dependency unavailable: ImportError")

                if not copy:
                    src_um.archive_to_edge(mem.id, galactic_distance=0.95)

                transferred += 1
            except Exception as e:
                logger.warning("Transfer failed for {mem.id[:8]}: %s", e, exc_info=True)
                errors += 1

        # Update registry counts
        for gname in (source_galaxy, target_galaxy):
            try:
                um = self._get_memory(gname)
                stats = um.get_stats()
                self._galaxies[gname].memory_count = stats.get("total_memories", 0)
            except Exception as e:
                logger.debug("Galaxy stats update failed: %s", e)
        self._save_registry()

        return {
            "source": source_galaxy,
            "target": target_galaxy,
            "candidates": len(candidates),
            "transferred": transferred,
            "skipped_dedup": skipped_dedup,
            "errors": errors,
            "mode": "copy" if copy else "move",
        }

    def merge_galaxy(
        self,
        source_galaxy: str,
        target_galaxy: str = "local/default",
        delete_after: bool = False,
    ) -> dict[str, Any]:
        """Merge all memories from source galaxy into target galaxy.

        This is a bulk transfer followed by optional registry removal.
        Source database file is always preserved on disk.
        """
        if source_galaxy not in self._galaxies:
            raise ValueError(f"Source galaxy '{source_galaxy}' not found")
        if source_galaxy == "local/default":
            raise ValueError("Cannot merge the default galaxy into another")

        result = self.transfer_memories(
            source_galaxy=source_galaxy,
            target_galaxy=target_galaxy or "local/default",
            limit=10000,
            copy=True,
        )

        if delete_after:
            try:
                # source_galaxy is a registry key (user_id/name)
                parts = source_galaxy.split("/", 1)
                self.delete_galaxy(parts[1] if len(parts) > 1 else source_galaxy, parts[0] if len(parts) > 1 else None)
                result["source_deleted"] = True
            except Exception as e:
                result["source_deleted"] = False
                result["delete_error"] = str(e)
        else:
            result["source_deleted"] = False

        return result

    def sync_galaxies(
        self,
        galaxy_a: str,
        galaxy_b: str,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
    ) -> dict[str, Any]:
        """Bidirectional sync between two galaxies.

        Copies new memories (by content hash) in both directions.
        Useful for keeping a philosophical corpus galaxy in sync with
        default when new wisdom memories arrive.
        """
        if galaxy_a not in self._galaxies:
            raise ValueError(f"Galaxy '{galaxy_a}' not found")
        if galaxy_b not in self._galaxies:
            raise ValueError(f"Galaxy '{galaxy_b}' not found")

        # A → B
        a_to_b = self.transfer_memories(
            source_galaxy=galaxy_a,
            target_galaxy=galaxy_b,
            tags=tags,
            min_importance=min_importance,
            copy=True,
        )

        # B → A
        b_to_a = self.transfer_memories(
            source_galaxy=galaxy_b,
            target_galaxy=galaxy_a,
            tags=tags,
            min_importance=min_importance,
            copy=True,
        )

        return {
            "a_to_b": a_to_b,
            "b_to_a": b_to_a,
            "total_synced": a_to_b["transferred"] + b_to_a["transferred"],
        }

    # ── Memory instance management ──────────────────────────────────

    def _get_memory(self, name: str) -> Any:
        """Get or create a UnifiedMemory instance for a galaxy."""
        if name not in self._memory_instances:
            info = self._galaxies.get(name)
            if not info:
                raise ValueError(f"Galaxy '{name}' not found")

            from whitemagic.core.memory.unified import UnifiedMemory

            db_path = Path(info.db_path)
            base_path = db_path.parent
            self._memory_instances[name] = UnifiedMemory(base_path=base_path)

        return self._memory_instances[name]

    def get_active_memory(self) -> Any:
        """Get the UnifiedMemory instance for the active galaxy."""
        return self._get_memory(self._active_galaxy)

    def _reset_global_memory(self, galaxy_name: str) -> None:
        """Reset the global get_unified_memory() singleton to use a different galaxy."""
        try:
            import whitemagic.core.memory.unified as um_module

            info = self._galaxies[galaxy_name]
            db_path = Path(info.db_path)
            base_path = db_path.parent

            # Replace the singleton for this user namespace
            new_um = um_module.UnifiedMemory(base_path=base_path)
            uid = getattr(info, 'user_id', 'local')
            um_module._unified_memory_instances[uid] = new_um

            # Cache it locally too
            self._memory_instances[galaxy_name] = new_um
        except Exception as e:
            logger.error("Failed to reset global memory to galaxy '%s': %s", galaxy_name, e, exc_info=True)

    # ── Galaxy status ───────────────────────────────────────────────

    def status(self, user_id: str | None = None) -> dict[str, Any]:
        """Get overall galaxy manager status.

        Args:
            user_id: If provided, filter galaxies to this user.
        """
        galaxies = self.list_galaxies(user_id)
        return {
            "active_galaxy": self._active_galaxy,
            "total_galaxies": len(self._galaxies),
            "galaxies": galaxies,
            "registry_path": str(_REGISTRY_PATH),
        }

    # ── Ingestion ───────────────────────────────────────────────────

    def ingest_files(
        self,
        galaxy_name: str,
        source_path: str,
        pattern: str = "**/*.md",
        max_files: int = 500,
        tags: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Ingest files from a directory into a galaxy's memory store.

        Reads text files matching the glob pattern and stores each as a memory.
        """
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{galaxy_name}"
        if registry_key not in self._galaxies:
            raise ValueError(f"Galaxy '{galaxy_name}' not found for user '{uid}'")

        um = self._get_memory(registry_key)
        # Path hygiene: Use WM_ROOT for relative paths, validate absolute paths
        source = Path(source_path)
        if not source.is_absolute():
            source = WM_ROOT / "data" / "imports" / source
        else:
            from whitemagic.security.tool_gating import get_tool_gate
            gate = get_tool_gate()
            allowed, reason = gate.path_validator.is_path_allowed(str(source))
            if not allowed:
                raise ValueError(f"Import source not allowed: {reason}")

        source = source.resolve()

        if not source.exists():
            raise FileNotFoundError(f"Source path not found: {source}")

        files = list(source.glob(pattern))[:max_files]
        ingested = 0
        errors = 0
        skipped = 0

        base_tags = set(tags or [])
        base_tags.add(f"galaxy:{galaxy_name}")
        base_tags.add("ingested")

        # ── Phase 1: Parallel file reading ─────────────────────────────
        def _read_file(f: Path) -> tuple[Path, str | None]:
            try:
                return f, f.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                return f, None

        file_contents: list[tuple[Path, str | None]] = []
        with ThreadPoolExecutor(max_workers=min(16, len(files) or 1)) as executor:
            file_contents = list(executor.map(_read_file, files))

        # ── Phase 2: Sequential DB store (SQLite prefers single-writer) ─
        for f, content in file_contents:
            if content is None:
                errors += 1
                continue

            if len(content.strip()) < 10:
                skipped += 1
                continue

            # Truncate very large files
            if len(content) > 50_000:
                content = content[:50_000] + "\n\n[... truncated ...]"

            file_tags = base_tags | {f"source:{f.suffix.lstrip('.')}"}
            relative = str(f.relative_to(source)) if f.is_relative_to(source) else f.name

            try:
                um.store(
                    content=content,
                    title=relative,
                    tags=file_tags,
                    importance=0.4,
                    metadata={
                        "source_path": str(f),
                        "relative_path": relative,
                        "file_size": f.stat().st_size,
                        "galaxy": galaxy_name,
                    },
                )
                ingested += 1
            except Exception as e:
                logger.warning("Failed to ingest %s: %s", f, e, exc_info=True)
                errors += 1

        # Update memory count
        try:
            stats = um.get_stats()
            self._galaxies[registry_key].memory_count = stats.get("total_memories", 0)
            self._save_registry()
        except Exception as e:
            logger.debug("Ingest stats update failed: %s", e)

        result = {
            "galaxy": galaxy_name,
            "user_id": uid,
            "source_path": str(source),
            "pattern": pattern,
            "files_found": len(files),
            "ingested": ingested,
            "skipped": skipped,
            "errors": errors,
        }

        # Publish sync event (best-effort, non-blocking)
        try:
            from whitemagic.core.memory.galaxy_sync import publish_galaxy_event
            publish_galaxy_event("galaxy.ingested", uid, galaxy_name, {
                "ingested": ingested,
                "errors": errors,
                "files_found": len(files),
            })
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

        return result

    # ── Multi-Galaxy Parallel Access (v23.4) ───────────────────────

    def search_multi_galaxy(
        self,
        query: str | None = None,
        galaxies: list[str] | None = None,
        tags: set[str] | None = None,
        min_importance: float = 0.0,
        limit: int = 20,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Search across multiple galaxies in parallel.

        Executes searches against each specified galaxy (or all galaxies
        if none specified) and merges results by importance.

        Args:
            query: FTS5 query string (optional).
            galaxies: List of galaxy names to search. If None, searches all.
            tags: Optional tag filter.
            min_importance: Minimum importance threshold.
            limit: Maximum results per galaxy (total results may be larger).
            user_id: Owner user ID. Defaults to "local".

        Returns:
            Dict with merged results, per-galaxy stats, and total count.
        """
        uid = resolve_user_id(user_id)

        # Determine which galaxies to search
        if galaxies is None:
            # Search all galaxies EXCEPT archive (not searched by default)
            galaxy_keys = [
                k for k, info in self._galaxies.items()
                if info.user_id == uid and info.name != "archive"
            ]
        else:
            galaxy_keys = [f"{uid}/{g}" for g in galaxies]
            # Validate
            for gk in galaxy_keys:
                if gk not in self._galaxies:
                    raise ValueError(f"Galaxy '{gk}' not found")

        # Search each galaxy in parallel
        all_results: list[dict[str, Any]] = []
        per_galaxy_stats: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}

        def _search_one(galaxy_key: str) -> tuple[str, list[Any], dict[str, Any], str | None]:
            try:
                um = self._get_memory(galaxy_key)
                results = um.search(
                    query=query,
                    tags=tags,
                    min_importance=min_importance,
                    limit=limit,
                )
                info = self._galaxies[galaxy_key]
                return galaxy_key, results, {
                    "galaxy": info.name,
                    "count": len(results),
                }, None
            except Exception as e:
                return galaxy_key, [], {}, str(e)

        with ThreadPoolExecutor(max_workers=min(len(galaxy_keys), 8)) as executor:
            for gk, results, stats, error in executor.map(_search_one, galaxy_keys):
                if error:
                    errors[gk] = error
                else:
                    per_galaxy_stats[gk] = stats
                    for r in results:
                        all_results.append({
                            "id": r.id,
                            "title": r.title,
                            "content": str(r.content)[:200] if r.content else "",
                            "galaxy": self._galaxies[gk].name,
                            "importance": r.importance,
                            "memory_type": r.memory_type.value if hasattr(r.memory_type, 'value') else str(r.memory_type),
                            "tags": list(r.tags) if hasattr(r, 'tags') and r.tags else [],
                            "created_at": r.created_at if hasattr(r, 'created_at') else None,
                        })

        # Sort by importance (descending)
        all_results.sort(key=lambda x: x.get("importance", 0), reverse=True)

        return {
            "status": "success",
            "query": query,
            "galaxies_searched": len(per_galaxy_stats),
            "total_results": len(all_results),
            "results": all_results[:limit * 2],  # Cap total
            "per_galaxy": per_galaxy_stats,
            "errors": errors if errors else None,
        }

    def get_memory_for_galaxy(self, name: str, user_id: str | None = None) -> Any:
        """Get the UnifiedMemory instance for a specific galaxy (without switching).

        Allows reading/writing to a non-active galaxy without changing
        the active galaxy context.

        Args:
            name: Galaxy name.
            user_id: Owner user ID. Defaults to "local".

        Returns:
            UnifiedMemory instance for the specified galaxy.
        """
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if registry_key not in self._galaxies:
            raise ValueError(f"Galaxy '{name}' not found for user '{uid}'")
        return self._get_memory(registry_key)

    def share_galaxy(
        self,
        name: str,
        target_user_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Share a galaxy with another user by creating a registry entry.

        The target user gets read/write access to the same database file.
        This is a lightweight share — no data copy, just a registry pointer.

        Args:
            name: Galaxy name to share.
            target_user_id: User ID to share with.
            user_id: Owner user ID. Defaults to "local".

        Returns:
            Dict with share status.
        """
        uid = resolve_user_id(user_id)
        registry_key = f"{uid}/{name}"
        if registry_key not in self._galaxies:
            raise ValueError(f"Galaxy '{name}' not found for user '{uid}'")

        info = self._galaxies[registry_key]
        target_key = f"{target_user_id}/{name}"

        if target_key in self._galaxies:
            return {
                "status": "already_shared",
                "galaxy": name,
                "target_user": target_user_id,
            }

        # Create a shared entry pointing to the same DB
        shared_info = GalaxyInfo(
            name=name,
            db_path=info.db_path,
            description=f"[shared from {uid}] {info.description}",
            project_path=info.project_path,
            tags=info.tags + ["shared"],
            is_core=False,
            user_id=target_user_id,
        )
        self._galaxies[target_key] = shared_info
        self._save_registry()

        logger.info(
            "Shared galaxy '%s' from user '%s' to user '%s'",
            name, uid, target_user_id,
        )

        return {
            "status": "shared",
            "galaxy": name,
            "owner": uid,
            "shared_with": target_user_id,
            "db_path": info.db_path,
        }

    def list_shared_galaxies(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List galaxies shared with a user (entries tagged 'shared').

        Args:
            user_id: User ID to check. Defaults to "local".

        Returns:
            List of shared galaxy info dicts.
        """
        uid = resolve_user_id(user_id)
        shared = []
        for key, info in self._galaxies.items():
            if info.user_id == uid and "shared" in info.tags:
                d = info.to_dict()
                d["registry_key"] = key
                shared.append(d)
        return shared


def get_galaxy_manager() -> GalaxyManager:
    """Get the global GalaxyManager singleton."""
    return GalaxyManager.get_instance()
