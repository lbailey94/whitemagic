"""5D Coordinate Validation — Measure overlap between 5D spatial and semantic search.

This script validates the 5D coordinate system by:
1. Selecting a random sample of memories that have both coordinates and embeddings.
2. Finding "ground truth" neighbors using pure semantic embedding similarity.
3. Finding neighbors using fast 5D holographic spatial search.
4. Calculating the overlap (Recall@K) between the two methods.
5. Reporting performance and accuracy metrics.

Usage:
    python tests/benchmarks/validate_5d_coordinates.py [--samples 50] [--k 10]
"""

import argparse
import random
import time

from whitemagic.core.memory.holographic import get_holographic_memory
from whitemagic.core.memory.unified import get_unified_memory


def validate_5d(num_samples: int = 50, k: int = 10):
    print(f"🧪 Validating 5D Coordinate System ({num_samples} samples, k={k})")
    print("=" * 60)

    um = get_unified_memory()
    # Trigger lazy loading of holographic index from DB
    _ = um.holographic 
    holo = get_holographic_memory()

    # 1. Check if embedding engine is available (at least for cache)
    from whitemagic.core.memory.embeddings import get_embedding_engine
    engine = get_embedding_engine()
    if not engine or not engine.available(include_cache=True):
        print("❌ ERROR: Embedding engine (and cache) unavailable. Cannot establish semantic ground truth.")
        return
    
    if not engine.available():
        print("⚠️  Warning: Embedding model not installed. Using cached embeddings for ground truth.")

    # 2. Get all memories that HAVE embeddings (otherwise ground truth is impossible)
    db = engine._get_db()
    with db:
        all_ids = [row[0] for row in db.execute("SELECT memory_id FROM memory_embeddings").fetchall()]
    
    # 3. Intersection with memories that have coordinates
    with um.backend.pool.connection() as conn:
        coord_ids = {row[0] for row in conn.execute("SELECT memory_id FROM holographic_coords").fetchall()}
    
    valid_ids = [mid for mid in all_ids if mid in coord_ids]
    
    if not valid_ids:
        print("❌ No memories with both coordinates AND embeddings found.")
        return

    # 4. Create an ISOLATED index for validation to eliminate noise/pollution
    from whitemagic.core.intelligence.hologram.encoder import CoordinateEncoder
    encoder = CoordinateEncoder()
    from whitemagic.utils.rust_helper import get_rust_module
    rs = get_rust_module()
    if not rs or not hasattr(rs, "SpatialIndex5D"):
        print("❌ ERROR: Rust SpatialIndex5D unavailable for isolated validation.")
        return
    
    validation_index = rs.SpatialIndex5D()
    print(f"Created isolated validation index. Populating with {len(valid_ids)} points...")
    
    # Use the encoder directly to ensure we are testing the LATEST logic, 
    # not just what was previously stored in the DB.
    # This also removes DB-storage latency from the validation.
    with um.backend.pool.connection() as conn:
        placeholders = ",".join(["?"] * len(valid_ids))
        # Note: 'tags', 'joy_score', 'resonance_score' are stored inside 'metadata' JSON in the schema
        rows = conn.execute(f"SELECT id, content, title, metadata, memory_type, created_at, importance, access_count, galactic_distance, emotional_valence, neuro_score FROM memories WHERE id IN ({placeholders})", valid_ids).fetchall()
        
        # Get column names from the cursor description of the actual query
        column_names = [description[0] for description in conn.execute(f"SELECT id, content, title, metadata, memory_type, created_at, importance, access_count, galactic_distance, emotional_valence, neuro_score FROM memories LIMIT 1").description]
        
        for r in rows:
            mem_dict = dict(zip(column_names, r))
            # Extract tags and other fields from metadata JSON
            if isinstance(mem_dict.get("metadata"), str):
                import json
                try:
                    meta = json.loads(mem_dict["metadata"])
                    mem_dict["tags"] = meta.get("tags", [])
                    mem_dict["joy_score"] = meta.get("joy_score", 0.0)
                    mem_dict["resonance_score"] = meta.get("resonance_score", 0.0)
                    # CoordinateEncoder also looks at 'metadata' for garden bias
                    mem_dict["metadata"] = meta
                except:
                    mem_dict["tags"] = []
                    mem_dict["joy_score"] = 0.0
                    mem_dict["resonance_score"] = 0.0
                    mem_dict["metadata"] = {}
            else:
                mem_dict["tags"] = []
                mem_dict["joy_score"] = 0.0
                mem_dict["resonance_score"] = 0.0
                mem_dict["metadata"] = {}
            
            coord = encoder.encode(mem_dict)
            validation_index.add(mem_dict["id"], [coord.x, coord.y, coord.z, coord.w, coord.v])
    
    print(f"Isolated index ready (size: {validation_index.size()})")

    if len(valid_ids) < num_samples:
        num_samples = len(valid_ids)

    sample_ids = random.sample(valid_ids, num_samples)
    
    total_overlap_5d = 0
    total_overlap_2d = 0
    total_semantic_time = 0.0
    total_spatial_time = 0.0

    print(f"Evaluating {num_samples} memories...")

    for mid in sample_ids:
        mem = um.recall(mid)
        if not mem:
            continue

        # --- Channel A: True Semantic Similarity (Ground Truth) ---
        start = time.time()
        # Use cached embeddings since model isn't installed
        semantic_hits = engine.search_similar(mid, limit=k+1)
        semantic_ids = [hit["memory_id"] for hit in semantic_hits if hit["memory_id"] != mid]
        total_semantic_time += (time.time() - start)

        # --- Channel B: Fast 5D Spatial Search (Balanced Weights) ---
        start = time.time()
        coord = encoder.encode(mem.to_dict())
        # Use equal weights for X/Y and lower for Z/W/V to emphasize semantic axes
        # but keep them within the same search space.
        weights_5d = [1.0, 1.0, 0.5, 0.5, 0.5]
        query_5d = [
            coord.x * weights_5d[0], 
            coord.y * weights_5d[1], 
            coord.z * weights_5d[2], 
            coord.w * weights_5d[3], 
            coord.v * weights_5d[4]
        ]
        
        spatial_hits_5d = validation_index.query_nearest(query_5d, k+1)
        spatial_ids_5d = [r[0] for r in spatial_hits_5d if r[0] != mid]
        total_spatial_time += (time.time() - start)

        # --- Channel C: 2D Spatial Search (X/Y Only) ---
        # We manually calculate this to verify the semantic signal in X/Y
        query_2d = [coord.x, coord.y]
        # In a real app we'd use a 2D index, but for validation we'll brute force the valid_ids
        # to see if the signal is present in the coordinates themselves.
        # This is for internal diagnostics.
        
        # Calculate overlap for 5D
        overlap_5d = len(set(semantic_ids) & set(spatial_ids_5d))
        total_overlap_5d += overlap_5d

    # --- Results ---
    if num_samples == 0:
        print("No samples to evaluate.")
        return

    avg_overlap_5d = (total_overlap_5d / (num_samples * k)) * 100
    avg_semantic_ms = (total_semantic_time / num_samples) * 1000
    avg_spatial_ms = (total_spatial_time / num_samples) * 1000
    speedup = avg_semantic_ms / avg_spatial_ms if avg_spatial_ms > 0 else float('inf')

    print("-" * 60)
    print(f"📊 5D Weighted Overlap (Recall@{k}): {avg_overlap_5d:.2f}%")
    print(f"⏱️  Avg Semantic Search Time: {avg_semantic_ms:.2f} ms")
    print(f"⏱️  Avg 5D Spatial Search Time: {avg_spatial_ms:.2f} ms")
    print(f"🚀 Speedup Factor: {speedup:.1f}x")
    print("-" * 60)

    if avg_overlap_5d >= 50:
        print("✅ SUCCESS: 5D system effectively predicts semantic relevance.")
    elif avg_overlap_5d >= 10:
        print("⚠️  WARNING: Moderate overlap. Semantic signal is present but diluted.")
    elif avg_overlap_5d > 0:
        print("⚠️  WARNING: Low overlap. Better than 0%, but more tuning needed.")
    else:
        print("❌ FAILURE: 0% overlap. 5D system is completely decoupled from semantics.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=50, help="Number of random memories to sample")
    parser.add_argument("--k", type=int, default=10, help="Number of neighbors to compare")
    args = parser.parse_args()

    validate_5d(num_samples=args.samples, k=args.k)
