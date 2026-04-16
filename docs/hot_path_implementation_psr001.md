# Hot Path Implementation Roadmap - PSR-001 Phase 2 Completion
# Generated from 1.1M clone Monte Carlo analysis + polyglot scouting
# Date: 2026-02-18
# Total Hot Paths: 217 | P0 Candidates: 43 | P1 Candidates: 25

## Phase 2A: Quick Wins (Complexity ≤2, P0 Priority)
### Target: Complete 8 VCs in 30 minutes

1. **browser_tools.py** → Zig (complexity 1, 100-1000x)
   - Hot path: Database-intensive operations
   - Implementation: Zig FFI wrapper with async I/O
   - ETA: 5 min

2. **browser/actions.py** → Zig (complexity 1, 100-1000x)
   - Hot path: Browser automation actions
   - Implementation: Zig string processing + callbacks
   - ETA: 5 min

3. **local_embedder.py** → Mojo (complexity 1, 50-100x)
   - Hot path: LLM inference
   - Implementation: Mojo tensor operations
   - ETA: 5 min

4. **mojo_bridge.py** → Mojo (complexity 1, 50-100x)
   - Hot path: Bridge overhead
   - Implementation: Direct Mojo calls
   - ETA: 5 min

5. **polyglot_embedder.py** → Mojo (complexity 1, 50-100x)
   - Hot path: Embedding generation
   - Implementation: Mojo vectorized ops
   - ETA: 5 min

6. **pattern_engine.py** → Zig (complexity 2, 100-1000x) ✅ ALREADY DONE
   - SIMD scan + batch scoring implemented

7. **galactic_map.py** → Zig (complexity 2, 100-1000x) ✅ ALREADY DONE
   - 5D coords + kNN + centroid implemented

8. **gan_ying_async.py** → Zig (complexity 2, 100-1000x)
   - Hot path: Async resonance calculations
   - Implementation: Zig async/await + channels
   - ETA: 10 min

## Phase 2B: Medium Complexity (Complexity 3, P0/P1)
### Target: Complete 6 VCs in 45 minutes

1. **hrr.py** → Mojo (complexity 2, 50-100x)
   - Hot path: Holographic Reduced Representations
   - Heavy NumPy operations → Mojo GPU tensors
   - ETA: 15 min

2. **surprise_gate.py** → Mojo (complexity 2, 50-100x)
   - Hot path: Novelty detection
   - Implementation: Mojo GPU kernels
   - ETA: 10 min

3. **graph_walker.py** → Mojo (complexity 3, 50-100x)
   - Hot path: Graph traversal
   - Implementation: Parallel BFS/DFS in Mojo
   - ETA: 15 min

4. **embedding_index.py** → Mojo (complexity 3, 50-100x)
   - Hot path: Vector search
   - Implementation: GPU-accelerated FAISS alternative
   - ETA: 15 min

5. **causal_miner.py** → Mojo (complexity 3, 50-100x)
   - Hot path: Causal inference
   - Implementation: Mojo statistical kernels
   - ETA: 15 min

6. **doctrine.py** → Zig (complexity 2, 100-1000x)
   - Hot path: Agent doctrine enforcement
   - Implementation: Zig state machine
   - ETA: 10 min

## Phase 2C: High Complexity (Complexity 4-5, P1)
### Target: Complete 4 VCs in 60 minutes

1. **galaxy_manager.py** → Zig (complexity 4, 100-1000x)
   - Hot path: Galaxy operations
   - Implementation: Full Zig rewrite with async
   - ETA: 20 min

2. **embeddings.py** → Mojo (complexity 4, 50-100x)
   - Hot path: Heavy NumPy + DB operations
   - Implementation: Mojo GPU pipeline
   - ETA: 25 min

3. **scratchpad.py** → Rust (complexity 2, 20-50x)
   - Hot path: Database-intensive
   - Implementation: Rust SQLite ops
   - ETA: 15 min

4. **sqlite_backend.py** → Rust (complexity 5, 20-50x) ✅ ALREADY DONE
   - Rust sqlite_backend_v2.rs compiled

## Current Status Summary
- Phase 1 (Rust Core): 8/8 ✅ COMPLETE
- Phase 2 (Zig Hot Paths): 4/6 → Target: 6/6 (after this session)
- Phase 3 (Mojo/GPU): 1/7 → Target: 5/7
- Phase 4 (Koka): 5/5 ✅ COMPLETE
- Phase 5 (Integration): 1/6 → Target: 3/6

## Total VCs: 19/32 → Target: 27/32 (84%)

## 217 Hot Paths by Category (from 1.1M clone analysis)
- cosine_similarity: 56 → GPU/Mojo
- sorting_lambda: 62 → Zig parallel sort
- regex_compile: 27 → Zig regex
- list_comprehension_heavy: 10 → Mojo vectorized
- distance_calc: 22 → Zig SIMD
- json_serialize: 33 → Native FFI ✅ DONE
- sqlite_format: 7 → Rust ✅ DONE

## Top 5 Files by Hot Path Count
1. simd_unified.py: 16 → Zig SIMD
2. embeddings.py: 12 → Mojo GPU
3. polyglot_db.py: 10 → Rust
4. simd_distance.py: 10 → Zig
5. knowledge_graph.py: 7 → Mojo
