#!/usr/bin/env python3
"""
WhiteMagic Performance Audit v21.0.0
Benchmarks for SQLite Batching and SIMD Acceleration.
"""

import time
import json
import random
import os
import sys
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import whitemagic_rust as rs
from whitemagic_rust import rust_cosine_similarity

import logging
logger = logging.getLogger(__name__)

# PySQLiteBackend is in the sqlite_backend submodule
PySQLiteBackend = rs.sqlite_backend.PySQLiteBackend


def python_cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def run_math_benchmark():
    logger.debug("\n[1/3] Benchmarking Math Kernels (SIMD vs Scalar)")
    dim = 384
    count = 5000
    vec_a = [random.random() for _ in range(dim)]
    vec_b = [random.random() for _ in range(dim)]

    # Python Scalar
    t0 = time.perf_counter()
    for _ in range(count):
        python_cosine_similarity(vec_a, vec_b)
    t_py = (time.perf_counter() - t0) * 1000

    # Rust SIMD-hinted
    t0 = time.perf_counter()
    for _ in range(count):
        rust_cosine_similarity(vec_a, vec_b)
    t_rs = (time.perf_counter() - t0) * 1000

    speedup = t_py / t_rs
    logger.debug("  Python (Scalar): %s ms", t_py)
    logger.debug("  Rust (SIMD):   %s ms", t_rs)
    logger.debug("  🔥 Speedup:      %sx", speedup)
    return {"python_ms": t_py, "rust_ms": t_rs, "speedup": speedup}


def run_sqlite_benchmark():
    logger.debug("\n[2/3] Benchmarking SQLite Ingestion (Batch vs Loop)")
    db_path = "/tmp/audit_bench.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    backend = PySQLiteBackend(db_path)
    backend.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, content TEXT, memory_type TEXT, created_at TEXT, updated_at TEXT,
            accessed_at TEXT, access_count INTEGER, emotional_valence REAL, importance REAL,
            neuro_score REAL, novelty_score REAL, recall_count INTEGER, half_life_days REAL,
            is_protected INTEGER, metadata TEXT, title TEXT, galactic_distance REAL,
            retention_score REAL, last_retention_sweep TEXT, content_hash TEXT,
            event_time TEXT, ingestion_time TEXT, is_private INTEGER, model_exclude INTEGER
        )
    """,
        [],
    )
    count = 1000

    # Prepare data
    memories = []
    for i in range(count):
        memories.append(
            {
                "id": f"mem_{i}",
                "content": f"Sample content for memory {i}. " * 5,
                "memory_type": "SHORT_TERM",
                "created_at": "2026-04-09T12:00:00Z",
                "updated_at": "2026-04-09T12:00:00Z",
                "accessed_at": "2026-04-09T12:00:00Z",
                "access_count": 0,
                "emotional_valence": 0.5,
                "importance": 0.8,
                "neuro_score": 1.0,
                "novelty_score": 1.0,
                "recall_count": 0,
                "half_life_days": 30.0,
                "is_protected": 0,
                "metadata": "{}",
                "title": f"Memory {i}",
                "galactic_distance": 0.0,
                "retention_score": 0.5,
                "last_retention_sweep": None,
                "content_hash": f"hash_{i}",
                "event_time": None,
                "ingestion_time": "2026-04-09T12:00:00Z",
                "is_private": 0,
                "model_exclude": 0,
            }
        )

    # 1. Loop Ingestion
    t0 = time.perf_counter()
    for m in memories:
        backend.store_memory(
            m["id"],
            m["content"],
            m["memory_type"],
            m["created_at"],
            m["updated_at"],
            m["accessed_at"],
            m["access_count"],
            m["emotional_valence"],
            m["importance"],
            m["neuro_score"],
            m["novelty_score"],
            m["recall_count"],
            m["half_life_days"],
            m["is_protected"],
            m["metadata"],
            m["title"],
            m["galactic_distance"],
            m["retention_score"],
            m["last_retention_sweep"],
            m["content_hash"],
            m["event_time"],
            m["ingestion_time"],
            m["is_private"],
            m["model_exclude"],
        )
    t_loop = (time.perf_counter() - t0) * 1000

    # Reset DB
    if os.path.exists(db_path):
        os.remove(db_path)
    backend = PySQLiteBackend(db_path)
    backend.execute(
        "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, memory_type TEXT, created_at TEXT, updated_at TEXT, accessed_at TEXT, access_count INTEGER, emotional_valence REAL, importance REAL, neuro_score REAL, novelty_score REAL, recall_count INTEGER, half_life_days REAL, is_protected INTEGER, metadata TEXT, title TEXT, galactic_distance REAL, retention_score REAL, last_retention_sweep TEXT, content_hash TEXT, event_time TEXT, ingestion_time TEXT, is_private INTEGER, model_exclude INTEGER)",
        [],
    )

    # 2. Batch Ingestion
    memories_json = json.dumps(memories)
    t0 = time.perf_counter()
    backend.batch_store_memories(memories_json)
    t_batch = (time.perf_counter() - t0) * 1000

    speedup = t_loop / t_batch
    logger.debug("  Loop Ingestion:  %s ms", t_loop)
    logger.debug("  Batch Ingestion: %s ms", t_batch)
    logger.debug("  🚀 Speedup:       %sx", speedup)

    if os.path.exists(db_path):
        os.remove(db_path)

    return {"loop_ms": t_loop, "batch_ms": t_batch, "speedup": speedup}


def check_wasm():
    logger.debug("\n[3/3] Verifying WASM Integrity")
    wasm_path = (
        REPO_ROOT
        / "whitemagic-math/target/wasm32-unknown-unknown/release/whitemagic_math.wasm"
    )
    if wasm_path.exists():
        size_kb = wasm_path.stat().st_size / 1024
        logger.debug("  File: %s", wasm_path.name)
        logger.debug("  Size: %s KB", size_kb)
        status = "✅ PASS" if size_kb < 400 else "⚠️  OPTIMIZATION NEEDED"
        logger.debug("  Status: %s", status)
        return {"size_kb": size_kb, "status": status}
    else:
        logger.debug("  ❌ WASM artifact not found.")
        return {"size_kb": 0, "status": "FAIL"}


if __name__ == "__main__":
    logger.debug("=" * 60)
    logger.debug("WHITE MAGIC PERFORMANCE AUDIT - PHASE 4 VALIDATION")
    logger.debug("=" * 60)

    math_results = run_math_benchmark()
    sqlite_results = run_sqlite_benchmark()
    wasm_results = check_wasm()

    logger.debug("\n" + "=" * 60)
    logger.debug("FINAL SUMMARY")
    logger.debug("=" * 60)
    logger.debug(f"Math Speedup:   {math_results['speedup']:.1f}x")
    logger.debug(f"SQLite Speedup: {sqlite_results['speedup']:.1f}x")
    logger.debug(
        f"WASM Footprint: {wasm_results['size_kb']:.1f} KB ({wasm_results['status']})"
    )
    logger.debug("=" * 60)
