import sys
from pathlib import Path

# Setup path to include the core directory
sys.path.append(str(Path.cwd() / "core"))

# Explicit import from manager to avoid __init__ redirection issues
from whitemagic.core.memory.manager import get_memory_manager
from whitemagic.config.paths import DB_PATH

import logging
logger = logging.getLogger(__name__)


def debug_search():
    # Use the same DB path as the benchmark
    db_path = str(DB_PATH)
    manager = get_memory_manager()

    query = "Foundation Comprehensive Project"
    logger.debug(f"Searching for: {query}")

    try:
        # Direct manager search (legacy wrapper)
        results = manager.search_memories(query, limit=10)
        logger.debug(f"Results found (search_memories): {len(results)}")
        for r in results:
            entry = r.get("entry", {})
            logger.debug(
                f" - ID: {entry.get('id')} | Title: {entry.get('title')} | Score: {r.get('score')}"
            )

        # Direct unified search (modern API)
        logger.debug("\nSearching via unified.search directly:")
        unified_results = manager.unified.search(query, limit=10)
        logger.debug(f"Results found (unified.search): {len(unified_results)}")
        for m in unified_results:
            score = m.metadata.get("score", "N/A")
            logger.debug(f" - ID: {m.id} | Title: {m.title} | Score: {score}")

    except Exception as e:
        logger.debug(f"CRITICAL SEARCH FAILURE: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_search()
