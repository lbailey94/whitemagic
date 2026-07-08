import sqlite3
import time
from pathlib import Path

import logging
from whitemagic.core.memory.db_manager import safe_connect
logger = logging.getLogger(__name__)

try:
    from whitemagic.config.paths import DB_PATH
except ImportError:
    DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


def full_rebuild_fts(db_path: Path | str | None = None):
    path = Path(db_path) if db_path else Path(DB_PATH)
    logger.debug("Connecting to %s for FULL FTS REBUILD...", path)
    conn = safe_connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")  # 64MB cache
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
    conn.execute("PRAGMA busy_timeout=30000")

    logger.debug("Fetching total memory count...")
    total_mems = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    logger.debug("Total memories to index: %s", total_mems)

    start_time = time.time()
    synced = 0
    batch_size = 5000

    # We use a cursor to stream memories to avoid OOM
    logger.debug("Rebuilding index in batches...")

    # We iterate over all memories. Since we already purged memories_fts,
    # we can just insert everything.
    # We join with tags to get the tags_text in one go?
    # No, tags table is separate. GROUP_CONCAT is better.

    cursor = conn.execute("""
        SELECT m.id, m.title, m.content, 
               (SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE memory_id = m.id) as tags_text
        FROM memories m
    """)

    batch_data = []
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break

        for rid, title, content, tags in rows:
            batch_data.append((rid, title or "", str(content or ""), tags or ""))

        conn.executemany(
            """
            INSERT INTO memories_fts (id, title, content, tags_text)
            VALUES (?, ?, ?, ?)
        """,
            batch_data,
        )

        conn.commit()
        synced += len(rows)
        logger.debug("  Indexed %s/%s...", synced, total_mems)
        batch_data = []

    end_time = time.time()
    logger.debug("FULL REBUILD Finished.")
    logger.debug("  Total entries indexed: %s", synced)
    logger.debug(f"  Total time: {end_time - start_time:.2f}s")

    conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('optimize')")
    conn.close()


if __name__ == "__main__":
    full_rebuild_fts()
