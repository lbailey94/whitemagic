#!/usr/bin/env python3
"""Batch embedding backfill for memories without embeddings.

Processes memories in batches to add missing embeddings.
Run with: python scripts/backfill_embeddings.py --batch-size 1000 --limit 10000
"""

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CORE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(CORE_DIR))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Get the database path from environment or default."""
    if "WM_DB_PATH" in os.environ:
        return Path(os.environ["WM_DB_PATH"])
    try:
        from whitemagic.config.paths import WM_ROOT

        return WM_ROOT / "whitemagic_working.db"
    except Exception:
        state_root = os.environ.get(
            "WM_STATE_ROOT", os.path.expanduser("~/.whitemagic")
        )
        return Path(state_root) / "whitemagic_working.db"


def get_memories_without_embeddings(
    db_path: Path, limit: int | None = None
) -> list[tuple[int, str]]:
    """Get memories that don't have embeddings."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT m.id, m.content
        FROM memories m
        LEFT JOIN memory_embeddings e ON m.id = e.memory_id
        WHERE e.memory_id IS NULL
        AND m.content IS NOT NULL
        AND length(m.content) > 10
        ORDER BY m.id
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    memories = cursor.fetchall()
    conn.close()
    return memories


def batch_backfill(
    db_path: Path, batch_size: int = 100, limit: int | None = None
) -> int:
    """Backfill embeddings in batches."""
    memories = get_memories_without_embeddings(db_path, limit)
    total = len(memories)
    logger.info("Found %s memories without embeddings", total)

    if total == 0:
        return 0

    try:
        from whitemagic.core.memory.embeddings import EmbeddingEngine

        engine = EmbeddingEngine()
        logger.info("Embedding engine loaded successfully")
    except ImportError as e:
        logger.error("Failed to import embedding engine: %s", e)
        logger.info("Embedding backfill requires embeddings tier dependencies")
        return 0

    processed = 0
    for i in range(0, total, batch_size):
        batch = memories[i : i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} memories)"
        )

        for memory_id, content in batch:
            try:
                embedding = engine.embed(content)
                if embedding is not None:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                        (memory_id, embedding, engine.model_name),
                    )
                    conn.commit()
                    conn.close()
                    processed += 1
            except Exception as e:
                logger.warning("Failed to embed memory %s: %s", memory_id, e)

    logger.info("Backfill complete: %s/%s memories processed", processed, total)
    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Batch backfill embeddings for memories"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for processing"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of memories to process"
    )
    parser.add_argument(
        "--db-path", type=str, default=None, help="Override database path"
    )
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else get_db_path()

    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        sys.exit(1)

    logger.info("Using database: %s", db_path)
    processed = batch_backfill(db_path, args.batch_size, args.limit)

    if processed > 0:
        logger.info("Successfully backfilled %s embeddings", processed)
    else:
        logger.warning("No embeddings were backfilled")


if __name__ == "__main__":
    main()
