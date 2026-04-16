# ADR-004: Memory Architecture — Unified SQLite Backend with Galactic Spatial Model

**Status**: Accepted  
**Date**: 2026-04-15  
**Deciders**: WhiteMagic core team  
**Tags**: architecture, memory, sqlite, holographic

---

## Context

WhiteMagic v12 used JSON file storage: one file per memory, serialized to `~/.whitemagic/memory/`.
This worked to ~10K memories but exhibited:
- O(n) scan time for every search operation
- File descriptor limits (~100K memories → inode exhaustion)
- No ACID guarantees (crash could corrupt in-flight writes)
- No FTS (full-text search) without loading all files

## Decision

Migrate to a **unified SQLite backend** (`sqlite_backend.py`) with a galactic spatial index.

### Core Architecture

```
UnifiedMemory (singleton facade)
    └── SQLiteBackend (ACID, FTS5)
            ├── memories table           (content, metadata, timestamps)
            ├── tags table               (memory_id → tag)
            ├── associations table       (source_id, target_id, strength)
            ├── memories_fts FTS5 index  (BM25 search)
            ├── holographic_coords       (5D spatial: x, y, z, w, v)
            └── akashic_seeds            (dormant knowledge, bloom conditions)
```

### The Galactic Distance Model

Every memory has a `galactic_distance` ∈ [0.0, 1.0]:
- **0.0** = galactic core (highly active, recalled frequently)
- **1.0** = galactic edge (deep archive, deprioritized)

**No memory is ever deleted**. `archive_to_edge()` rotates memories outward; they remain
searchable but are filtered from default recall with `min_galactic_distance < threshold`.

### Holographic Coordinates

Memories are embedded in a 5D holographic space (x, y, z, w, v) derived from their
semantic embedding. Spatial proximity = semantic similarity. Used for:
- HNSW approximate nearest-neighbor search (embedded in `embeddings.py`)
- HRR (Holographic Reduced Representation) for compositional reasoning

### Content Hash Deduplication

Every memory is fingerprinted on ingest (`content_hash = SHA-256(content)`).
Duplicates are detected before INSERT, preventing 2× storage of identical content.

### Rust Acceleration (PSR-001)

`PySQLiteBackend` (Rust/PyO3) provides optionally-faster `store()` and `recall()` paths
using lock-free batch writes. Falls back to Python `sqlite3` transparently.

## Consequences

**Positive**:
- FTS5 BM25 search in <10ms for 100K memories
- ACID guarantees — no corruption during crash
- Galactic edge archival preserves all data while keeping active recall focused
- Content hash prevents duplicate ingestion

**Negative**:
- Single file DB: concurrent writers from multiple processes require WAL mode (enabled)
- Cold storage (`.cold.db`) requires separate pool management (implemented)
- SQLite connection leaks were a historical issue — mitigated by `close()`, `__enter__`/`__exit__`, and `atexit` hooks (F-06 fix)

## Alternatives Considered

- **PostgreSQL**: Rejected — too heavy for local-first single-user deployment
- **DuckDB**: Considered for analytics queries; may replace cold-storage scanning in v22.0
- **Weaviate/Qdrant**: Rejected for primary storage — external dependency; kept as optional vector overlay
- **JSON files**: Origin state, fully replaced in v13.0
