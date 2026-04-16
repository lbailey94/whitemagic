import sqlite3
import sys

sys.path.insert(0, '/home/lucas/Desktop/whitemagicdev')
from whitemagic.config.paths import DB_PATH


def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check if relation_type exists
        cursor = conn.execute("PRAGMA table_info(associations)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'relation_type' not in columns:
            print("Adding relation_type column to associations...")
            conn.execute("ALTER TABLE associations ADD COLUMN relation_type TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column already exists.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

migrate_db()
