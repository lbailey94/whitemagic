"""Memory Subsystem Stress Test — v22.0.0 Readiness Validation.

Exercises the memory pipeline under realistic load:
- High-volume store/recall
- Concurrent access patterns
- Embedding generation at scale
- Graph walker deep traversal
- Consolidation under pressure
- Lifecycle edge cases

Usage:
    source .venv/bin/activate && python core/scripts/stress_test_memory.py
"""
from __future__ import annotations

import concurrent.futures
import random
import statistics
import string
import tempfile
import time
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG = {
    "memory_count": 500,          # Total memories to create
    "batch_size": 50,             # Memories per batch
    "concurrent_workers": 4,      # Parallel store threads
    "search_iterations": 100,     # Search operations
    "embedding_dim": 128,         # Vector dimension
    "max_content_length": 2000,   # Characters per memory
    "graph_walk_depth": 5,        # Association graph depth
}

RESULTS: dict[str, list[float]] = {
    "store_latency_ms": [],
    "search_latency_ms": [],
    "recall_latency_ms": [],
    "embed_latency_ms": [],
    "graph_walk_latency_ms": [],
}

ERRORS: list[str] = []


def _random_content(length: int = 200) -> str:
    words = ["architecture", "decision", "neural", "embedding", "vector",
             "knowledge", "graph", "resonance", "synthesis", "memory",
             "consolidation", "dream", "pattern", "abstraction", "insight",
             "consciousness", " substrate", "agentic", "tool", "dispatch",
             "gana", "prat", "mcp", "harmony", "dharma", "karma"]
    return " ".join(random.choices(words, k=length // 5))


def _random_tags() -> list[str]:
    pool = ["design", "research", "bugfix", "feature", "refactor",
            "security", "performance", "docs", "test", "deploy"]
    return random.sample(pool, k=random.randint(1, 3))


# ---------------------------------------------------------------------------
# Phase 1: Store Stress
# ---------------------------------------------------------------------------

def _make_memory(i: int) -> Any:
    """Create a Memory dataclass instance."""
    from whitemagic.core.memory.unified_types import Memory, MemoryType
    return Memory(
        id=f"stress-{i}-{random.randint(1000,9999)}",
        content=_random_content(random.randint(50, CONFIG["max_content_length"])),
        memory_type=MemoryType.SHORT_TERM,
        title=f"Stress memory {i}",
        tags=set(_random_tags()),
        metadata={"stress_test": True, "batch": i // CONFIG["batch_size"]},
    )


def stress_store(backend, count: int) -> list[str]:
    """Create `count` memories and return their IDs."""
    ids: list[str] = []
    for i in range(count):
        start = time.perf_counter()
        try:
            memory = _make_memory(i)
            result = backend.store(memory)
            ids.append(memory.id)
        except Exception as exc:
            ERRORS.append(f"store[{i}]: {exc}")
        finally:
            RESULTS["store_latency_ms"].append((time.perf_counter() - start) * 1000)
    return ids


def stress_store_parallel(backend, count: int, workers: int) -> list[str]:
    """Concurrent store operations."""
    ids: list[str] = []
    per_worker = count // workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
        futures = [exe.submit(stress_store, backend, per_worker) for _ in range(workers)]
        for fut in concurrent.futures.as_completed(futures):
            try:
                ids.extend(fut.result())
            except Exception as exc:
                ERRORS.append(f"parallel_store: {exc}")
    return ids


# ---------------------------------------------------------------------------
# Phase 2: Search Stress
# ---------------------------------------------------------------------------

def stress_search(backend, iterations: int) -> None:
    """Run many search queries."""
    queries = ["architecture", "neural embedding", "graph resonance",
               "knowledge synthesis", "memory consolidation", "dream pattern",
               "vector search", "security refactor", "performance docs"]
    for i in range(iterations):
        start = time.perf_counter()
        try:
            backend.search(
                query=random.choice(queries),
                limit=random.randint(5, 20),
            )
        except Exception as exc:
            ERRORS.append(f"search[{i}]: {exc}")
        finally:
            RESULTS["search_latency_ms"].append((time.perf_counter() - start) * 1000)


# ---------------------------------------------------------------------------
# Phase 3: Recall Stress
# ---------------------------------------------------------------------------

def stress_recall(backend, memory_ids: list[str]) -> None:
    """Recall every memory by ID."""
    for mid in memory_ids:
        start = time.perf_counter()
        try:
            backend.recall(mid)
        except Exception as exc:
            ERRORS.append(f"recall[{mid}]: {exc}")
        finally:
            RESULTS["recall_latency_ms"].append((time.perf_counter() - start) * 1000)


# ---------------------------------------------------------------------------
# Phase 4: Embedding Stress
# ---------------------------------------------------------------------------

def stress_embeddings(count: int) -> None:
    """Generate embeddings for random content."""
    try:
        from whitemagic.core.memory.embeddings import get_embedding_engine
        engine = get_embedding_engine()
        for i in range(count):
            start = time.perf_counter()
            try:
                engine.encode(_random_content(100))
            except Exception as exc:
                ERRORS.append(f"embed[{i}]: {exc}")
            finally:
                RESULTS["embed_latency_ms"].append((time.perf_counter() - start) * 1000)
    except ImportError as exc:
        ERRORS.append(f"embed_import: {exc}")


# ---------------------------------------------------------------------------
# Phase 5: Graph Walker Stress
# ---------------------------------------------------------------------------

def stress_graph_walk(backend, start_id: str, depth: int) -> None:
    """Deep graph traversal from a seed memory."""
    try:
        from whitemagic.core.memory.graph import get_graph_walker
        walker = get_graph_walker()
        start = time.perf_counter()
        walker.walk([start_id], hops=depth)
        RESULTS["graph_walk_latency_ms"].append((time.perf_counter() - start) * 1000)
    except ImportError as exc:
        ERRORS.append(f"graph_walk_import: {exc}")
    except Exception as exc:
        ERRORS.append(f"graph_walk: {exc}")


# ---------------------------------------------------------------------------
# Phase 6: Consolidation Stress
# ---------------------------------------------------------------------------

def stress_consolidation(backend) -> None:
    """Trigger memory consolidation."""
    try:
        from whitemagic.core.memory.consolidation import MemoryConsolidator
        consolidator = MemoryConsolidator()
        consolidator.consolidate()
    except ImportError as exc:
        ERRORS.append(f"consolidation_import: {exc}")
    except Exception as exc:
        ERRORS.append(f"consolidation: {exc}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _summarize(name: str, values: list[float]) -> str:
    if not values:
        return f"  {name}: NO DATA"
    return (
        f"  {name}:"
        f"  n={len(values)},"
        f"  min={min(values):.2f}ms,"
        f"  max={max(values):.2f}ms,"
        f"  mean={statistics.mean(values):.2f}ms,"
        f"  p95={sorted(values)[int(len(values)*0.95)]:.2f}ms"
    )


def report() -> None:
    print("\n" + "=" * 60)
    print("MEMORY SUBSYSTEM STRESS TEST REPORT")
    print("=" * 60)
    print(f"\nConfiguration: {CONFIG}")
    print(f"\nErrors: {len(ERRORS)}")
    for err in ERRORS[:10]:
        print(f"  - {err}")
    if len(ERRORS) > 10:
        print(f"  ... and {len(ERRORS) - 10} more")

    print("\nLatency Summary:")
    for key in RESULTS:
        print(_summarize(key, RESULTS[key]))

    print("\n" + "=" * 60)
    if not ERRORS:
        print("STATUS: PASS — No errors under stress")
    else:
        print(f"STATUS: FAIL — {len(ERRORS)} errors encountered")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("WhiteMagic Memory Subsystem Stress Test")
    print(f"Config: {CONFIG}\n")

    # Use a temp directory for isolation
    with tempfile.TemporaryDirectory(prefix="wm_stress_") as tmp:
        tmp_path = Path(tmp)
        print(f"Using temp state root: {tmp_path}")

        # Initialize backend
        try:
            from whitemagic.core.memory.sqlite_backend import SQLiteBackend
            backend = SQLiteBackend(db_path=tmp_path / "stress.db")
            print(f"Backend: {type(backend).__name__}")
        except ImportError as exc:
            print(f"FATAL: Cannot import SQLiteBackend: {exc}")
            return 1

        # Phase 1: Store
        print(f"\n[Phase 1] Storing {CONFIG['memory_count']} memories...")
        ids = stress_store_parallel(backend, CONFIG["memory_count"], CONFIG["concurrent_workers"])
        print(f"  Created {len(ids)} memories")

        # Phase 2: Search
        print(f"\n[Phase 2] Running {CONFIG['search_iterations']} searches...")
        stress_search(backend, CONFIG["search_iterations"])

        # Phase 3: Recall
        print(f"\n[Phase 3] Recalling {len(ids)} memories...")
        stress_recall(backend, ids)

        # Phase 4: Embeddings
        print(f"\n[Phase 4] Generating {CONFIG['memory_count'] // 5} embeddings...")
        stress_embeddings(CONFIG["memory_count"] // 5)

        # Phase 5: Graph walk
        if ids:
            print(f"\n[Phase 5] Graph walk (depth={CONFIG['graph_walk_depth']})...")
            stress_graph_walk(backend, ids[0], CONFIG["graph_walk_depth"])

        # Phase 6: Consolidation
        print(f"\n[Phase 6] Memory consolidation...")
        stress_consolidation(backend)

    report()
    return 0 if not ERRORS else 1


if __name__ == "__main__":
    raise SystemExit(main())
