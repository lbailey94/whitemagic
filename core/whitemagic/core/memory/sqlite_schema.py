"""SQLite Schema Manager — Database initialization and migrations.

Handles schema creation, column migrations, and backup rotation for the
WhiteMagic memory database. Extracted from sqlite_backend.py for better
separation of concerns.
"""

import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteSchemaManager:
    """Manages database schema and migrations for SQLite backend."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._needs_backup = True

    def auto_backup(self) -> None:
        """Create a pre-migration backup of the database if it has data.

        Keeps at most 3 backups (rotated by suffix).  Backups are named
        ``<db>.bak.1`` through ``<db>.bak.3`` with ``.bak.1`` being the
        most recent.  Only runs when the DB file already exists and is
        non-empty, to avoid creating empty backup files on first launch.
        """
        import shutil

        src = Path(self.db_path)
        if not src.exists() or src.stat().st_size == 0:
            return

        # Rotate: .bak.2 -> .bak.3, .bak.1 -> .bak.2, current -> .bak.1
        for i in (2, 1):
            old = src.with_suffix(f"{src.suffix}.bak.{i}")
            new = src.with_suffix(f"{src.suffix}.bak.{i + 1}")
            if old.exists():
                try:
                    shutil.move(str(old), str(new))
                except OSError:
                    pass

        dst = src.with_suffix(f"{src.suffix}.bak.1")
        try:
            shutil.copy2(str(src), str(dst))
            logger.debug("Pre-migration backup: %s", dst)
        except OSError as exc:
            logger.warning("Could not create backup %s: %s", dst, exc)

    def _quote_identifier(self, ident: str) -> str:
        """Safely quote SQL identifier, rejecting suspicious characters."""
        # Double any double quotes in the identifier
        safe_ident = ident.replace('"', '""')
        return f'"{safe_ident}"'

    def init_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and handle migrations.

        Creates a rotated backup only when schema changes are actually needed.
        PRAGMAs (WAL, mmap_size, cache_size, temp_store, etc.) are
        set centrally in db_manager.ConnectionPool._create_connection().
        """
        self._needs_backup = True

        # 1. Memories table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                created_at TEXT,
                updated_at TEXT,
                accessed_at TEXT,
                access_count INTEGER,
                emotional_valence REAL,
                importance REAL,
                neuro_score REAL DEFAULT 1.0,
                novelty_score REAL DEFAULT 1.0,
                recall_count INTEGER DEFAULT 0,
                half_life_days REAL DEFAULT 30.0,
                is_protected INTEGER DEFAULT 0,
                metadata TEXT,
                title TEXT
            )
        """)

        # Migration: Add missing columns if they don't exist
        cursor = conn.execute("PRAGMA table_info(memories)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        new_columns = {
            "neuro_score": "REAL DEFAULT 1.0",
            "novelty_score": "REAL DEFAULT 1.0",
            "recall_count": "INTEGER DEFAULT 0",
            "half_life_days": "REAL DEFAULT 30.0",
            "is_protected": "INTEGER DEFAULT 0",
            "memory_type": "TEXT DEFAULT 'SHORT_TERM'",
            "updated_at": "TEXT",
            "accessed_at": "TEXT",
            "access_count": "INTEGER DEFAULT 0",
            "emotional_valence": "REAL DEFAULT 0.0",
            "metadata": "TEXT DEFAULT '{}'",
            "galactic_distance": "REAL DEFAULT 0.0",
            "retention_score": "REAL DEFAULT 0.5",
            "last_retention_sweep": "TEXT",
            "content_hash": "TEXT",  # v14.1.1: SHA-256 for dedup
            "event_time": "TEXT",  # v14.2: bitemporal — when the fact became true
            "ingestion_time": "TEXT",  # v14.2: bitemporal — when WM learned it
            "is_private": "INTEGER DEFAULT 0",  # v15: exclude from MCP responses
            "model_exclude": "INTEGER DEFAULT 0",  # v15: exclude from AI context
        }

        _valid_ident = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        for col_name, col_type in new_columns.items():
            if col_name not in existing_columns:
                if not _valid_ident.match(col_name) or not _valid_ident.match(col_type.split()[0]):
                    logger.warning(f"Skipping invalid identifier: {col_name}")
                    continue
                # Deferred backup: only backup before first actual schema change
                if self._needs_backup:
                    self.auto_backup()
                    self._needs_backup = False
                logger.debug(f"Adding column {col_name} to memories table")
                try:
                    safe_col = self._quote_identifier(col_name)
                    safe_type = self._quote_identifier(col_type.split()[0])
                    stmt = f'ALTER TABLE memories ADD COLUMN {safe_col} {safe_type}'
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add column {col_name}: {e}")

        # 2. Tags table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                memory_id TEXT,
                tag TEXT,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                PRIMARY KEY (memory_id, tag)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")

        # 3. Associations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                source_id TEXT,
                target_id TEXT,
                strength REAL,
                FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
                PRIMARY KEY (source_id, target_id)
            )
        """)

        # 4. Full Text Search (FTS5) - Use internal content for string ID support
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id UNINDEXED,
                title,
                content,
                tags_text
            )
        """)

        # 5. Holographic Coordinates table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS holographic_coords (
                memory_id TEXT PRIMARY KEY,
                x REAL,
                y REAL,
                z REAL,
                w REAL,
                v REAL DEFAULT 0.5,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)

        # Migration: add temporal columns to associations if missing
        self._migrate_associations(conn, _valid_ident)

        # Migration: add v column to holographic_coords if missing
        self._migrate_holographic_coords(conn)

        # 6. Constellation Membership table (v14.3 — Recall Boost)
        self._init_constellation_membership(conn)

        # 7. Akashic Seeds table (v5.0 Integration)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS akashic_seeds (
                id TEXT PRIMARY KEY,
                content TEXT,
                bloom_conditions TEXT,
                planted_at TEXT,
                times_bloomed INTEGER DEFAULT 0,
                last_bloomed TEXT,
                potency REAL DEFAULT 1.0,
                keywords TEXT
            )
        """)

        # 8. Dharma Audit Log table (Phase 4)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dharma_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                ethical_score REAL,
                harmony_score REAL,
                consent_level TEXT,
                boundary_type TEXT,
                concerns TEXT,
                context TEXT,
                decision TEXT
            )
        """)

        # Add performance indexes
        self._create_indexes(conn)

    def _migrate_associations(self, conn: sqlite3.Connection, _valid_ident: re.Pattern) -> None:
        """Migrate associations table to add temporal columns."""
        assoc_cursor = conn.execute("PRAGMA table_info(associations)")
        assoc_columns = {row[1] for row in assoc_cursor.fetchall()}
        for col_name, col_def in [
            ("last_traversed_at", "TEXT"),
            ("traversal_count", "INTEGER DEFAULT 0"),
            ("created_at", "TEXT"),
            # v14.0 Living Graph columns (Overlap B — 4 research teams)
            ("direction", "TEXT DEFAULT 'undirected'"),
            ("relation_type", "TEXT DEFAULT 'associated_with'"),
            ("edge_type", "TEXT DEFAULT 'semantic'"),
            ("valid_from", "TEXT"),
            ("valid_until", "TEXT"),
            ("ingestion_time", "TEXT"),
        ]:
            if col_name not in assoc_columns:
                if not _valid_ident.match(col_name):
                    continue
                if self._needs_backup:
                    self.auto_backup()
                    self._needs_backup = False
                try:
                    safe_col = self._quote_identifier(col_name)
                    # Use full col_def to include DEFAULT values
                    stmt = f'ALTER TABLE associations ADD COLUMN {safe_col} {col_def}'
                    conn.execute(stmt)
                    logger.info(f"Added {col_name} column to associations table")
                except sqlite3.OperationalError:
                    pass

    def _migrate_holographic_coords(self, conn: sqlite3.Connection) -> None:
        """Migrate holographic_coords table to add v column."""
        hc_cursor = conn.execute("PRAGMA table_info(holographic_coords)")
        hc_columns = {row[1] for row in hc_cursor.fetchall()}
        if "v" not in hc_columns:
            if self._needs_backup:
                self.auto_backup()
                self._needs_backup = False
            try:
                conn.execute("ALTER TABLE holographic_coords ADD COLUMN v REAL DEFAULT 0.5")
                logger.info("Added v column to holographic_coords table")
            except sqlite3.OperationalError:
                pass

    def _init_constellation_membership(self, conn: sqlite3.Connection) -> None:
        """Initialize constellation_membership table with composite PK migration."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS constellation_membership (
                memory_id TEXT NOT NULL,
                constellation_name TEXT NOT NULL,
                membership_confidence REAL DEFAULT 1.0,
                updated_at TEXT,
                PRIMARY KEY (memory_id, constellation_name),
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)
        cm_cursor = conn.execute("PRAGMA table_info(constellation_membership)")
        cm_columns = cm_cursor.fetchall()
        cm_pk_columns = [
            row[1]
            for row in sorted((row for row in cm_columns if row[5]), key=lambda row: row[5])
        ]
        if cm_pk_columns == ["memory_id"]:
            if self._needs_backup:
                self.auto_backup()
                self._needs_backup = False
            conn.execute("DROP TABLE IF EXISTS constellation_membership_v2")
            conn.execute("""
                CREATE TABLE constellation_membership_v2 (
                    memory_id TEXT NOT NULL,
                    constellation_name TEXT NOT NULL,
                    membership_confidence REAL DEFAULT 1.0,
                    updated_at TEXT,
                    PRIMARY KEY (memory_id, constellation_name),
                    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO constellation_membership_v2 (
                    memory_id, constellation_name, membership_confidence, updated_at
                )
                SELECT cm.memory_id, cm.constellation_name, cm.membership_confidence, cm.updated_at
                FROM constellation_membership cm
                INNER JOIN memories m ON m.id = cm.memory_id
            """)
            conn.execute("DROP TABLE constellation_membership")
            conn.execute(
                "ALTER TABLE constellation_membership_v2 RENAME TO constellation_membership",
            )
            logger.info(
                "Migrated constellation_membership to composite primary key "
                "(memory_id, constellation_name)",
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_constellation_name ON constellation_membership(constellation_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_constellation_memory_id ON constellation_membership(memory_id)")

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create performance indexes for hot query patterns."""
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_composite ON tags(tag, memory_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dharma_timestamp ON dharma_audit(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_content_hash ON memories(content_hash)")
        # P6: Additional indexes for hot query patterns (v13.3.3)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_galactic ON memories(galactic_distance)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_neuro ON memories(neuro_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(accessed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_source ON associations(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_protected ON memories(is_protected)")
        # v14.0: Living Graph indexes for graph traversal
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_target ON associations(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_edge_type ON associations(edge_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_direction ON associations(direction)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_strength ON associations(strength)")
