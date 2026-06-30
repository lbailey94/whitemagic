import sqlite3
import time
from pathlib import Path

try:
    from whitemagic.config.paths import DB_PATH
except ImportError:
    DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


def full_rebuild_fts(db_path: Path | str | None = None):
    path = Path(db_path) if db_path else Path(DB_PATH)
    print(f"Connecting to {path} for FULL FTS REBUILD...")
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")  # 64MB cache
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
    conn.execute("PRAGMA busy_timeout=30000")

    print("Fetching total memory count...")
    total_mems = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    print(f"Total memories to index: {total_mems}")

    start_time = time.time()
    synced = 0
    batch_size = 5000

    # We use a cursor to stream memories to avoid OOM
    print("Rebuilding index in batches...")

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
        print(f"  Indexed {synced}/{total_mems}...")
        batch_data = []

    end_time = time.time()
    print("FULL REBUILD Finished.")
    print(f"  Total entries indexed: {synced}")
    print(f"  Total time: {end_time - start_time:.2f}s")

    conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('optimize')")
    conn.close()


if __name__ == "__main__":
    full_rebuild_fts()
