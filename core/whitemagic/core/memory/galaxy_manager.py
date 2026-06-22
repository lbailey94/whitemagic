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
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._galaxies: dict[str, GalaxyInfo] = {}
        self._active_galaxy: str = "default"
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
                    self._galaxies[name] = GalaxyInfo.from_dict(info_dict)
                self._active_galaxy = data.get("active", "default")
            except Exception as e:
                logger.warning("Failed to load galaxy registry: %s", e, exc_info=True)

        # Ensure "default" galaxy always exists
        if "default" not in self._galaxies:
            default_db = str(MEMORY_DIR / "whitemagic.db")
            self._galaxies["default"] = GalaxyInfo(
                name="default",
                db_path=default_db,
                description="Primary WhiteMagic galaxy — system knowledge and personal memories",
                is_core=False,
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
    ) -> GalaxyInfo:
        """Create a new galaxy with its own database."""
        if name in self._galaxies:
            raise ValueError(f"Galaxy '{name}' already exists")

        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

        # Galaxy DB lives in its own subdirectory
        galaxy_dir = MEMORY_DIR / "galaxies" / safe_name
        galaxy_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(galaxy_dir / "whitemagic.db")

        info = GalaxyInfo(
            name=name,
            db_path=db_path,
            description=description or f"Galaxy for {project_path or name}",
            project_path=project_path,
            tags=tags or [],
        )

        self._galaxies[name] = info
        self._save_registry()

        # Pre-initialize the database
        self._get_memory(name)
        info.memory_count = 0

        logger.info("Created galaxy '%s' at %s", name, db_path, exc_info=True)
        return info

    def delete_galaxy(self, name: str) -> bool:
        """Remove a galaxy from the registry (does NOT delete the database file)."""
        if name == "default":
            raise ValueError("Cannot delete the default galaxy")
        if name not in self._galaxies:
            raise ValueError(f"Galaxy '{name}' not found")
        if self._active_galaxy == name:
            self._active_galaxy = "default"

        # Remove from memory cache
        self._memory_instances.pop(name, None)
        del self._galaxies[name]
        self._save_registry()
        return True

    def list_galaxies(self) -> list[dict[str, Any]]:
        """List all known galaxies with their metadata."""
        result = []
        for name, info in sorted(self._galaxies.items()):
            d = info.to_dict()
            d["is_active"] = name == self._active_galaxy
            # Try to get live memory count
            try:
                um = self._get_memory(name)
                stats = um.backend.get_stats()
                d["memory_count"] = stats.get("total_memories", 0)
                info.memory_count = d["memory_count"]
            except Exception as e:
                logger.debug("Galaxy stats lookup failed for %s: %s", name, e, exc_info=True)
            result.append(d)
        return result

    def switch_galaxy(self, name: str) -> GalaxyInfo:
        """Switch the active galaxy."""
        if name not in self._galaxies:
            raise ValueError(f"Galaxy '{name}' not found. Available: {list(self._galaxies.keys())}")

        self._active_galaxy = name
        self._galaxies[name].last_accessed = time.time()
        self._save_registry()

        # Reset the global singleton so next get_unified_memory() uses the new galaxy
        self._reset_global_memory(name)

        logger.info("Switched to galaxy '%s'", name, exc_info=True)
        return self._galaxies[name]

    def get_active(self) -> GalaxyInfo:
        """Get the currently active galaxy."""
        return self._galaxies.get(self._active_galaxy, self._galaxies["default"])

    def get_galaxy(self, name: str) -> GalaxyInfo | None:
        """Get galaxy info by name."""
        return self._galaxies.get(name)

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
            candidates = src_um.backend.search(
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
                existing = tgt_um.backend.find_by_content_hash(content_hash)
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
                    with src_um.backend.pool.connection() as conn:
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
                            with tgt_um.backend.pool.connection() as tconn:
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
                    pass  # Lineage tracking is best-effort

                # If move (not copy), archive the original
                if not copy:
                    src_um.backend.archive_to_edge(mem.id, galactic_distance=0.95)

                transferred += 1
            except Exception as e:
                logger.warning("Transfer failed for {mem.id[:8]}: %s", e, exc_info=True)
                errors += 1

        # Update registry counts
        for gname in (source_galaxy, target_galaxy):
            try:
                um = self._get_memory(gname)
                stats = um.backend.get_stats()
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
        target_galaxy: str = "default",
        delete_after: bool = False,
    ) -> dict[str, Any]:
        """Merge all memories from source galaxy into target galaxy.

        This is a bulk transfer followed by optional registry removal.
        Source database file is always preserved on disk.
        """
        if source_galaxy not in self._galaxies:
            raise ValueError(f"Source galaxy '{source_galaxy}' not found")
        if source_galaxy == "default":
            raise ValueError("Cannot merge the default galaxy into another")

        result = self.transfer_memories(
            source_galaxy=source_galaxy,
            target_galaxy=target_galaxy,
            limit=10000,
            copy=True,
        )

        if delete_after:
            try:
                self.delete_galaxy(source_galaxy)
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

            # Replace the singleton
            new_um = um_module.UnifiedMemory(base_path=base_path)
            um_module._unified_memory_instance = new_um  # type: ignore[attr-defined]

            # Cache it locally too
            self._memory_instances[galaxy_name] = new_um
        except Exception as e:
            logger.error("Failed to reset global memory to galaxy '%s': %s", galaxy_name, e, exc_info=True)

    # ── Galaxy status ───────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Get overall galaxy manager status."""
        galaxies = self.list_galaxies()
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
    ) -> dict[str, Any]:
        """Ingest files from a directory into a galaxy's memory store.

        Reads text files matching the glob pattern and stores each as a memory.
        """
        if galaxy_name not in self._galaxies:
            raise ValueError(f"Galaxy '{galaxy_name}' not found")

        um = self._get_memory(galaxy_name)
        # Path hygiene: Use WM_ROOT for relative paths, validate absolute paths
        source = Path(source_path)
        if not source.is_absolute():
            source = WM_ROOT / "data" / "imports" / source
        else:
            # Validate against allowed paths
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
            stats = um.backend.get_stats()
            self._galaxies[galaxy_name].memory_count = stats.get("total_memories", 0)
            self._save_registry()
        except Exception as e:
            logger.debug("Ingest stats update failed: %s", e)

        return {
            "galaxy": galaxy_name,
            "source_path": str(source),
            "pattern": pattern,
            "files_found": len(files),
            "ingested": ingested,
            "skipped": skipped,
            "errors": errors,
        }


def get_galaxy_manager() -> GalaxyManager:
    """Get the global GalaxyManager singleton."""
    return GalaxyManager.get_instance()
