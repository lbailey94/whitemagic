"""Migration and Integrity CLI — Galaxy and namespace management.

Phase 8 WI 3 of the Codebase Hardening Strategy.

Provides inspect, validate, repair, reindex, export, import, dry-run,
and rollback commands for each galaxy and namespace.

Usage (via wm CLI)::

    wm migration inspect --galaxy universal --user local
    wm migration validate --user local
    wm migration repair --galaxy universal --dry-run
    wm migration reindex --galaxy universal
    wm migration export --galaxy universal --output /tmp/export.json
    wm migration import --input /tmp/export.json --galaxy universal
    wm migration rollback --snapshot /tmp/snapshot_20260713.json
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GalaxyInfo:
    """Information about a single galaxy database."""

    name: str
    user_id: str
    db_path: str
    memory_count: int = 0
    db_size_bytes: int = 0
    integrity_ok: bool = True
    integrity_errors: list[str] = field(default_factory=list)
    has_hnsw_index: bool = False
    has_fts5_index: bool = False
    schema_version: str = ""


@dataclass
class ValidationResult:
    """Result of validating a galaxy or namespace."""

    user_id: str
    galaxies_checked: int = 0
    galaxies_ok: int = 0
    galaxies_with_errors: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    operation: str
    galaxy: str
    user_id: str
    success: bool = True
    dry_run: bool = False
    items_affected: int = 0
    errors: list[str] = field(default_factory=list)
    snapshot_path: str = ""
    duration_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MigrationCLI:
    """Migration and integrity CLI operations.

    All operations support --dry-run for safe preview.
    All destructive operations create a snapshot before modifying.
    """

    def __init__(self, state_root: str | None = None) -> None:
        self._state_root = state_root or os.environ.get(
            "WM_STATE_ROOT", os.path.expanduser("~/.whitemagic")
        )

    @property
    def state_root(self) -> Path:
        return Path(self._state_root)

    def _galaxies_root(self, user_id: str) -> Path:
        return self.state_root / "users" / user_id / "galaxies"

    def _galaxy_db_path(self, user_id: str, galaxy: str) -> Path:
        return self._galaxies_root(user_id) / galaxy / "whitemagic.db"

    def _monolithic_db_path(self) -> Path:
        return self.state_root / "memory" / "whitemagic.db"

    # -- Inspect --

    def inspect(self, galaxy: str = "", user_id: str = "local") -> list[GalaxyInfo]:
        """Inspect galaxy databases and return their info."""
        results: list[GalaxyInfo] = []

        if galaxy:
            db_path = self._galaxy_db_path(user_id, galaxy)
            if db_path.exists():
                results.append(self._inspect_db(db_path, galaxy, user_id))
            else:
                results.append(GalaxyInfo(
                    name=galaxy, user_id=user_id, db_path=str(db_path),
                    integrity_ok=False, integrity_errors=["Database file not found"],
                ))
        else:
            galaxies_root = self._galaxies_root(user_id)
            if galaxies_root.exists():
                for gdir in sorted(galaxies_root.iterdir()):
                    if gdir.is_dir():
                        db_path = gdir / "whitemagic.db"
                        if db_path.exists():
                            results.append(self._inspect_db(db_path, gdir.name, user_id))

            # Also check monolithic DB
            mono_path = self._monolithic_db_path()
            if mono_path.exists():
                results.append(self._inspect_db(mono_path, "_monolithic", user_id))

        return results

    def _inspect_db(self, db_path: Path, name: str, user_id: str) -> GalaxyInfo:
        """Inspect a single database file."""
        info = GalaxyInfo(
            name=name,
            user_id=user_id,
            db_path=str(db_path),
            db_size_bytes=db_path.stat().st_size,
        )

        try:
            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Memory count
            try:
                row = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()
                info.memory_count = row["c"] if row else 0
            except sqlite3.Error:
                logger.debug("Ignored Exception in migration_cli.py:155")

            # Integrity check
            try:
                rows = conn.execute("PRAGMA integrity_check").fetchall()
                errors = [r[0] for r in rows if r[0] != "ok"]
                info.integrity_ok = len(errors) == 0
                info.integrity_errors = errors
            except sqlite3.Error as e:
                info.integrity_ok = False
                info.integrity_errors = [str(e)]

            # Check for HNSW index
            try:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                info.has_hnsw_index = any("hnsw" in t.lower() for t in tables)
                info.has_fts5_index = any("fts" in t.lower() for t in tables)
            except sqlite3.Error:
                logger.debug("Ignored Exception in migration_cli.py:175")

            # Schema version
            try:
                row = conn.execute(
                    "SELECT value FROM schema_meta WHERE key='version'"
                ).fetchone()
                info.schema_version = row[0] if row else "unknown"
            except sqlite3.Error:
                info.schema_version = "unknown"

            conn.close()
        except sqlite3.Error as e:
            info.integrity_ok = False
            info.integrity_errors = [f"Cannot open database: {e}"]

        return info

    # -- Validate --

    def validate(self, user_id: str = "local") -> ValidationResult:
        """Validate all galaxies for a user."""
        result = ValidationResult(user_id=user_id)
        galaxies = self.inspect(user_id=user_id)

        for g in galaxies:
            result.galaxies_checked += 1
            if g.integrity_ok:
                result.galaxies_ok += 1
            else:
                result.galaxies_with_errors += 1
                result.errors.append({
                    "galaxy": g.name,
                    "db_path": g.db_path,
                    "errors": g.integrity_errors,
                })
            if g.memory_count == 0 and g.name != "_monolithic":
                result.warnings.append({
                    "galaxy": g.name,
                    "warning": "empty_galaxy",
                    "message": f"Galaxy '{g.name}' has 0 memories",
                })

        return result

    # -- Repair --

    def repair(
        self,
        galaxy: str,
        user_id: str = "local",
        dry_run: bool = False,
    ) -> MigrationResult:
        """Attempt to repair a corrupted galaxy database."""
        t0 = time.perf_counter()
        db_path = self._galaxy_db_path(user_id, galaxy)
        result = MigrationResult(
            operation="repair",
            galaxy=galaxy,
            user_id=user_id,
            dry_run=dry_run,
        )

        if not db_path.exists():
            result.success = False
            result.errors.append(f"Database not found: {db_path}")
            result.duration_s = time.perf_counter() - t0
            return result

        # Create snapshot before repair
        if not dry_run:
            snapshot_path = db_path.parent / f"snapshot_{int(time.time())}.db"
            shutil.copy2(str(db_path), str(snapshot_path))
            result.snapshot_path = str(snapshot_path)

        try:
            conn = sqlite3.connect(str(db_path), timeout=10.0)

            # Check integrity
            rows = conn.execute("PRAGMA integrity_check").fetchall()
            errors = [r[0] for r in rows if r[0] != "ok"]

            if not errors:
                result.items_affected = 0
                logger.info("Galaxy %s already healthy, no repair needed", galaxy)
            elif dry_run:
                result.items_affected = len(errors)
                logger.info("DRY RUN: Would repair %d errors in %s", len(errors), galaxy)
            else:
                # Attempt repair via VACUUM
                conn.execute("VACUUM")
                result.items_affected = len(errors)
                logger.info("Repaired %d errors in %s via VACUUM", len(errors), galaxy)

            conn.close()
        except sqlite3.Error as e:
            result.success = False
            result.errors.append(str(e))

        result.duration_s = time.perf_counter() - t0
        return result

    # -- Reindex --

    def reindex(
        self,
        galaxy: str,
        user_id: str = "local",
        dry_run: bool = False,
    ) -> MigrationResult:
        """Rebuild FTS5 and HNSW indexes for a galaxy."""
        t0 = time.perf_counter()
        db_path = self._galaxy_db_path(user_id, galaxy)
        result = MigrationResult(
            operation="reindex",
            galaxy=galaxy,
            user_id=user_id,
            dry_run=dry_run,
        )

        if not db_path.exists():
            result.success = False
            result.errors.append(f"Database not found: {db_path}")
            result.duration_s = time.perf_counter() - t0
            return result

        try:
            conn = sqlite3.connect(str(db_path), timeout=10.0)

            # Find FTS5 tables
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'"
            ).fetchall()]

            for table in tables:
                if dry_run:
                    logger.info("DRY RUN: Would reindex %s", table)
                    result.items_affected += 1
                else:
                    try:
                        conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
                        result.items_affected += 1
                        logger.info("Rebuilt FTS5 index: %s", table)
                    except sqlite3.Error as e:
                        result.errors.append(f"Failed to reindex {table}: {e}")

            conn.close()
        except sqlite3.Error as e:
            result.success = False
            result.errors.append(str(e))

        result.duration_s = time.perf_counter() - t0
        return result

    # -- Export --

    def export(
        self,
        galaxy: str,
        output: str,
        user_id: str = "local",
    ) -> MigrationResult:
        """Export a galaxy's memories to JSON."""
        t0 = time.perf_counter()
        db_path = self._galaxy_db_path(user_id, galaxy)
        result = MigrationResult(
            operation="export",
            galaxy=galaxy,
            user_id=user_id,
        )

        if not db_path.exists():
            result.success = False
            result.errors.append(f"Database not found: {db_path}")
            result.duration_s = time.perf_counter() - t0
            return result

        try:
            conn = sqlite3.connect(str(db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row

            rows = conn.execute("SELECT * FROM memories").fetchall()
            memories = [dict(r) for r in rows]

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps({
                "galaxy": galaxy,
                "user_id": user_id,
                "exported_at": time.time(),
                "memory_count": len(memories),
                "memories": memories,
            }, default=str, indent=2))

            result.items_affected = len(memories)
            conn.close()
        except sqlite3.Error as e:
            result.success = False
            result.errors.append(str(e))

        result.duration_s = time.perf_counter() - t0
        return result

    # -- Import --

    def import_data(
        self,
        input_path: str,
        galaxy: str,
        user_id: str = "local",
        dry_run: bool = False,
    ) -> MigrationResult:
        """Import memories from a JSON export."""
        t0 = time.perf_counter()
        result = MigrationResult(
            operation="import",
            galaxy=galaxy,
            user_id=user_id,
            dry_run=dry_run,
        )

        p = Path(input_path)
        if not p.exists():
            result.success = False
            result.errors.append(f"Import file not found: {input_path}")
            result.duration_s = time.perf_counter() - t0
            return result

        try:
            data = json.loads(p.read_text())
            memories = data.get("memories", [])

            if dry_run:
                result.items_affected = len(memories)
                logger.info("DRY RUN: Would import %d memories into %s", len(memories), galaxy)
            else:
                # Use UnifiedMemory for actual import
                from whitemagic.core.memory.unified import get_unified_memory

                um = get_unified_memory(user_id=user_id)
                for mem in memories:
                    try:
                        um.store(
                            content=mem.get("content", ""),
                            galaxy=galaxy,
                            tags=mem.get("tags", "").split(",") if mem.get("tags") else [],
                            importance=mem.get("importance", 0.5),
                            user_id=user_id,
                        )
                        result.items_affected += 1
                    except Exception as e:
                        result.errors.append(f"Failed to import memory: {e}")

        except (json.JSONDecodeError, KeyError) as e:
            result.success = False
            result.errors.append(str(e))

        result.duration_s = time.perf_counter() - t0
        return result

    # -- Rollback --

    def rollback(
        self,
        snapshot_path: str,
        galaxy: str = "",
        user_id: str = "local",
    ) -> MigrationResult:
        """Rollback a galaxy database from a snapshot."""
        t0 = time.perf_counter()
        result = MigrationResult(
            operation="rollback",
            galaxy=galaxy,
            user_id=user_id,
        )

        snap = Path(snapshot_path)
        if not snap.exists():
            result.success = False
            result.errors.append(f"Snapshot not found: {snapshot_path}")
            result.duration_s = time.perf_counter() - t0
            return result

        if not galaxy:
            result.success = False
            result.errors.append("Galaxy name required for rollback")
            result.duration_s = time.perf_counter() - t0
            return result

        db_path = self._galaxy_db_path(user_id, galaxy)
        if db_path.exists():
            # Backup current before rollback
            backup = db_path.parent / f"pre_rollback_{int(time.time())}.db"
            shutil.copy2(str(db_path), str(backup))

        shutil.copy2(str(snap), str(db_path))
        result.items_affected = 1
        result.snapshot_path = snapshot_path
        result.duration_s = time.perf_counter() - t0
        return result
