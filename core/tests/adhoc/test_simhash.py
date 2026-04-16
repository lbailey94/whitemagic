import logging

from whitemagic.core.memory.embeddings import EmbeddingEngine

logging.basicConfig(level=logging.DEBUG)
engine = EmbeddingEngine()
print("Engine initialized.")

try:
    ids, vectors = engine._load_vec_cache()
    print("Loaded vectors shape:", vectors.shape)

    # Flatten numpy array to 1D list for efficient Rust transfer
    embeddings_flat = vectors.flatten().tolist()
    embedding_dim = vectors.shape[1]
    print("Flat length:", len(embeddings_flat))
    print("Dim:", embedding_dim)

    import json

    import whitemagic_rust

    result_json = whitemagic_rust.simhash_lsh.simhash_find_duplicates(
        embeddings_flat,
        embedding_dim,
        0.95,
        10
    )
    rust_results = json.loads(result_json)
    print(f"Found {len(rust_results)} duplicates.")
except Exception as e:
    print("Error:", e)
