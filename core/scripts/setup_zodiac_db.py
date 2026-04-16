import sqlite3
from pathlib import Path

def setup_zodiac_table():
    db_path = Path("/home/lucas/.whitemagic/memory/whitemagic.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS zodiac_ledger (
                entry_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                actor_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                parent_hash TEXT NOT NULL,
                context_id TEXT,
                consent_token TEXT,
                hash_signature TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_zodiac_timestamp ON zodiac_ledger(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_zodiac_parent ON zodiac_ledger(parent_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_zodiac_actor ON zodiac_ledger(actor_id)")
        conn.commit()
        print("Zodiac ledger table created successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_zodiac_table()
