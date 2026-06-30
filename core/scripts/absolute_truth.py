import sqlite3
from dataclasses import dataclass

from whitemagic.config.paths import DB_PATH


@dataclass
class Coords:
    x: float
    y: float
    z: float
    w: float
    v: float


def absolute_truth_sql():
    db_path = str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Mirror QueryManager logic exactly
    fts_query = '"foundation" OR "comprehensive" OR "project"'
    poled = Coords(0.1, 0.2, 0.3, 0.4, 0.5)
    native = Coords(0.0, 0.0, 0.0, 0.5, 0.5)

    sql = """
        SELECT m.id, m.title, fts.rank,
        MIN(
            COALESCE((hc.x - ?)*(hc.x - ?) + (hc.y - ?)*(hc.y - ?) + (hc.z - ?)*(hc.z - ?) + (hc.w - ?)*(hc.w - ?) + (hc.v - ?)*(hc.v - ?), 10.0),
            COALESCE((hc.x - ?)*(hc.x - ?) + (hc.y - ?)*(hc.y - ?) + (hc.z - ?)*(hc.z - ?) + (hc.w - ?)*(hc.w - ?) + (hc.v - ?)*(hc.v - ?), 10.0)
        ) as sql_dist
        FROM memories m
        JOIN (
            SELECT id, rank
            FROM memories_fts
            WHERE memories_fts MATCH ?
            LIMIT 500 
        ) fts ON m.id = fts.id
        LEFT JOIN holographic_coords hc ON m.id = hc.memory_id
        WHERE m.importance >= 0.0
          AND m.memory_type != 'quarantined'
        GROUP BY m.id 
        ORDER BY fts.rank ASC 
        LIMIT 10
    """

    params = [
        poled.x,
        poled.x,
        poled.y,
        poled.y,
        poled.z,
        poled.z,
        poled.w,
        poled.w,
        poled.v,
        poled.v,
        native.x,
        native.x,
        native.y,
        native.y,
        native.z,
        native.z,
        native.w,
        native.w,
        native.v,
        native.v,
        fts_query,
    ]

    print(f"Executing SQL with {len(params)} params...")
    try:
        rows = conn.execute(sql, params).fetchall()
        print(f"Rows found: {len(rows)}")
        for r in rows:
            print(f" - ID: {r['id']} | Title: {r['title']} | Dist: {r['sql_dist']:.4f}")
    except Exception as e:
        print(f"SQL FAILED: {e}")

    conn.close()


if __name__ == "__main__":
    absolute_truth_sql()
