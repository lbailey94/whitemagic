"""Adhoc script: inspect embedding dimensions in the local memory DB.

Run manually:
    WM_STATE_ROOT=~/.whitemagic python tests/adhoc/test_db_embeddings.py

Not collected by pytest automatically (no test_ functions at module level).
"""

import sqlite3
import sys


def main() -> None:
    try:
        from whitemagic.config.paths import DB_PATH

        db_path = str(DB_PATH)
    except ImportError:
        import os

        db_path = os.path.expanduser("~/.whitemagic/memory/whitemagic.db")

    print(f"Connecting to: {db_path}")
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    rows = cursor.execute(
        "SELECT memory_id, embedding FROM memory_embeddings"
    ).fetchall()
    print(f"Found {len(rows)} embeddings.")

    sizes: dict[int, int] = {}
    for r in rows:
        data = r[1]
        n = len(data) // 4
        sizes[n] = sizes.get(n, 0) + 1

    print("Embedding dimensions in DB:", sizes)
    db.close()


if __name__ == "__main__":
    sys.exit(main())
