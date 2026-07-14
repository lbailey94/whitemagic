# ruff: noqa: BLE001
"""Quarantine Galaxy Manager - Memory Deduplication System
Moves noisy/duplicate memories from active DB to archival quarantine.
"""

import hashlib
import logging
import os
from datetime import datetime

from whitemagic.core.memory.db_manager import safe_connect
from whitemagic.core.memory.unified_types import MemoryGalaxy
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


class QuarantineGalaxy(MemoryGalaxy):
    """
    Manages a separate galaxy/DB for noisy, duplicate, or low-value memories.

    Transfer criteria:
    - Near-duplicate content (SimHash similarity > 0.95)
    - Auto-generated logs (scavenged, temp, bench_*)
    - Very low PageRank (no connections, no access)
    - External library noise (HuggingFace files, etc.)
    """

    def __init__(self, quarantine_path: str | None = None):
        if quarantine_path is None:
            from whitemagic.config.paths import MEMORY_DIR
            quarantine_path = str(
                MEMORY_DIR / "galaxies/quarantine/whitemagic.db"
            )
        self.db_path = quarantine_path
        self._ensure_db()

    def _ensure_db(self):
        """Initialize quarantine database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = safe_connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                source_galaxy TEXT,
                reason TEXT NOT NULL,
                moved_at TEXT NOT NULL,
                original_metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_hash ON memories(content_hash);
            CREATE INDEX IF NOT EXISTS idx_reason ON memories(reason);
        ''')
        conn.commit()
        conn.close()

    def calculate_content_hash(self, content: str) -> str:
        """Normalized content hash for deduplication."""
        # Normalize: lowercase, strip whitespace, remove extra spaces
        normalized = ' '.join(content.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def transfer_to_quarantine(
        self,
        memory_id: str,
        content: str,
        source_galaxy: str,
        reason: str,
        original_metadata: dict | None = None
    ) -> bool:
        """Move a memory to quarantine."""

        try:
            conn = safe_connect(self.db_path)
            conn.execute('''
                INSERT OR REPLACE INTO memories
                (id, content, content_hash, source_galaxy, reason, moved_at, original_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory_id,
                content[:10000],  # Limit content size
                self.calculate_content_hash(content),
                source_galaxy,
                reason,
                datetime.now().isoformat(),
                _json_dumps(original_metadata) if original_metadata else None
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.debug("[Quarantine] Error transferring %s: %s", memory_id, e)
            return False

    def find_duplicates(self, content: str, threshold: float = 0.95) -> list[dict]:
        """Find similar content already in quarantine."""

        content_hash = self.calculate_content_hash(content)

        conn = safe_connect(self.db_path)
        cursor = conn.execute(
            'SELECT id, content, reason, moved_at FROM memories WHERE content_hash = ?',
            (content_hash,)
        )
        results = [
            {
                'id': row[0],
                'content': row[1][:200] + '...' if len(row[1]) > 200 else row[1],
                'reason': row[2],
                'moved_at': row[3]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return results

    def get_stats(self) -> dict:
        """Get quarantine statistics."""

        conn = safe_connect(self.db_path)
        cursor = conn.execute('''
            SELECT reason, COUNT(*) FROM memories GROUP BY reason
        ''')
        by_reason = {row[0]: row[1] for row in cursor.fetchall()}

        total = conn.execute('SELECT COUNT(*) FROM memories').fetchone()[0]
        conn.close()

        return {
            'total_quarantined': total,
            'by_reason': by_reason,
            'db_path': self.db_path,
            'db_size_mb': round(os.path.getsize(self.db_path) / (1024*1024), 2)
        }


class NoisyMemoryDetector:
    """Detects memories that should be moved to quarantine."""

    NOISY_PATTERNS = [
        'configuration_',
        'modeling_',
        'modular_',
        'processing_',
        'checkpoint_',
        'variant_',
        'wai-aria',
        'scavenged',
        'temp_',
        'bench_t',
    ]

    # HuggingFace model file patterns (not actual memories)
    HF_PATTERNS = [
        'huggingface',
        'transformers',
        'tokenizers',
        'pytorch_model',
        'model.safetensors',
    ]

    def __init__(self, quarantine: QuarantineGalaxy | None = None):
        self.quarantine = quarantine or QuarantineGalaxy()

    def should_quarantine(self, memory: dict) -> tuple[bool, str]:
        """Determine if a memory should be quarantined."""
        content = memory.get('content') or ''
        title = memory.get('title') or ''
        tags = memory.get('tags', [])

        if any(p in title.lower() or p in content.lower()
               for p in self.HF_PATTERNS):
            return True, 'external_library'

        if any(p in title.lower() for p in self.NOISY_PATTERNS):
            return True, 'noisy_pattern'

        if 'scavenged' in tags or memory.get('source') == 'scavenged':
            return True, 'scavenged'

        if title.startswith('bench_') or title.startswith('temp_'):
            return True, 'temporary'

        if len(content) < 100 and len(title) < 20:
            return True, 'insufficient_content'

        return False, 'active'

    def scan_and_quarantine(
        self,
        db_path: str,
        dry_run: bool = True
    ) -> list[dict]:
        """Scan active DB and identify quarantine candidates."""
        import sqlite3

        conn = safe_connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute('''
            SELECT m.id, m.title, m.content, m.created_at,
                   (SELECT json_group_array(tag) FROM tags WHERE memory_id = m.id) as tags
            FROM memories m
            WHERE m.memory_type != 'quarantined'
        ''')

        to_quarantine = []

        for row in cursor.fetchall():
            memory = {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'tags': _json_loads(row['tags']) if row['tags'] else [],
                'source': 'sqlite',
                'created_at': row['created_at']
            }

            should_move, reason = self.should_quarantine(memory)

            if should_move:
                to_quarantine.append({
                    'id': memory['id'],
                    'title': (memory['title'] or '')[:60],
                    'reason': reason,
                    'content_preview': (memory['content'] or '')[:100]
                })

                if not dry_run:
                    success = self.quarantine.transfer_to_quarantine(
                        memory_id=memory['id'],
                        content=memory['content'],
                        source_galaxy='active',
                        reason=reason,
                        original_metadata=memory
                    )
                    if success:
                        conn.execute("DELETE FROM memories WHERE id = ?", (memory['id'],))
                        conn.execute("DELETE FROM tags WHERE memory_id = ?", (memory['id'],))
                        conn.execute("DELETE FROM associations WHERE source_id = ? OR target_id = ?", (memory['id'], memory['id']))
                        conn.execute("DELETE FROM memories_fts WHERE id = ?", (memory['id'],))
                        conn.execute("DELETE FROM holographic_coords WHERE memory_id = ?", (memory['id'],))
                        conn.commit()

        conn.close()
        return to_quarantine


def run_quarantine_analysis(dry_run: bool = True):
    """Analyze active DB for quarantine candidates."""
    logger.debug("=" * 60)
    logger.debug("Quarantine Galaxy Analysis")
    logger.debug("=" * 60)

    from whitemagic.config.paths import DB_PATH
    db_path = str(DB_PATH)

    detector = NoisyMemoryDetector()
    candidates = detector.scan_and_quarantine(db_path, dry_run=dry_run)

    logger.debug(f"\nFound {len(candidates)} candidates for quarantine:")

    by_reason: dict[str, int] = {}
    for c in candidates:
        reason = c['reason']
        by_reason[reason] = by_reason.get(reason, 0) + 1

    for reason, count in sorted(by_reason.items(), key=lambda x:
        -x[1]):
        logger.debug("  • %s: %s", reason, count)

    if not dry_run and candidates:
        logger.debug(f"\n✓ Moved {len(candidates)} memories to quarantine")
    elif dry_run:
        logger.debug(f"\n[DRY RUN] Would move {len(candidates)} memories")
        logger.debug("Run with dry_run=False to execute")

    # Show quarantine stats
    stats = detector.quarantine.get_stats()
    logger.debug(f"\nQuarantine DB: {stats['total_quarantined']} memories")
    logger.debug(f"DB size: {stats['db_size_mb']} MB")


if __name__ == "__main__":
    run_quarantine_analysis(dry_run=False)
