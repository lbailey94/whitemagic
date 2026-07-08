import sqlite3

from whitemagic.config.paths import DB_PATH
from whitemagic.core.memory.db_manager import safe_connect


def test_fts():
    db_path = str(DB_PATH)
    conn = safe_connect(db_path)
    conn.row_factory = sqlite3.Row

    # Query that failed: Foundation Comprehensive Project
    # Keywords: foundation, comprehensive, project
    fts_query = '"foundation" OR "comprehensive" OR "project"'

    print(f"Testing MATCH query: {fts_query}")

    sql = """
        SELECT id, rank FROM memories_fts 
        WHERE memories_fts MATCH ? 
        LIMIT 10
    """

    rows = conn.execute(sql, (fts_query,)).fetchall()
    print(f"Rows found in FTS: {len(rows)}")
    for row in rows:
        print(f" - ID: {row['id']} | Rank: {row['rank']}")

    if rows:
        target_id = rows[0]["id"]
        print(f"\nTesting JOIN with ID: {target_id}")
        join_sql = "SELECT id, title FROM memories WHERE id = ?"
        m_row = conn.execute(join_sql, (target_id,)).fetchone()
        if m_row:
            print(f" - SUCCESS: Found in memories table! Title: {m_row['title']}")
        else:
            print(" - FAILURE: NOT found in memories table!")

    conn.close()


if __name__ == "__main__":
    test_fts()
