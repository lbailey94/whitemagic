import sqlite3
import sys
from pathlib import Path

# Make the WhiteMagic package importable regardless of CWD.
_REPO_ROOT = (
    Path(__file__).resolve().parents[3]
)  # core/scripts/maintenance/fixes -> core
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from whitemagic.config.paths import DB_PATH

import logging
from whitemagic.core.memory.db_manager import safe_connect
logger = logging.getLogger(__name__)


def migrate_db():
    conn = safe_connect(DB_PATH)
    try:
        cursor = conn.execute("PRAGMA table_info(associations)")
        columns = [col[1] for col in cursor.fetchall()]

        if "relation_type" not in columns:
            logger.debug("Adding relation_type column to associations...")
            conn.execute("ALTER TABLE associations ADD COLUMN relation_type TEXT")
            conn.commit()
            logger.debug("Migration successful.")
        else:
            logger.debug("Column already exists.")

    except Exception as e:
        logger.debug("Error: %s", e)
    finally:
        conn.close()


migrate_db()
