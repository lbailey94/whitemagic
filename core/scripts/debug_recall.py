import sys
from pathlib import Path

# Setup path to include the core directory
sys.path.append(str(Path.cwd() / "core"))

# Explicit import from manager to avoid __init__ redirection issues
from whitemagic.core.memory.manager import get_memory_manager
from whitemagic.config.paths import DB_PATH


def debug_search():
    # Use the same DB path as the benchmark
    db_path = str(DB_PATH)
    manager = get_memory_manager()

    query = "Foundation Comprehensive Project"
    print(f"Searching for: {query}")

    try:
        # Direct manager search (legacy wrapper)
        results = manager.search_memories(query, limit=10)
        print(f"Results found (search_memories): {len(results)}")
        for r in results:
            entry = r.get("entry", {})
            print(
                f" - ID: {entry.get('id')} | Title: {entry.get('title')} | Score: {r.get('score')}"
            )

        # Direct unified search (modern API)
        print("\nSearching via unified.search directly:")
        unified_results = manager.unified.search(query, limit=10)
        print(f"Results found (unified.search): {len(unified_results)}")
        for m in unified_results:
            score = m.metadata.get("score", "N/A")
            print(f" - ID: {m.id} | Title: {m.title} | Score: {score}")

    except Exception as e:
        print(f"CRITICAL SEARCH FAILURE: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_search()
